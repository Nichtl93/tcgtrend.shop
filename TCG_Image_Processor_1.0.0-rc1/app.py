
import os
import queue
import time
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk
from watchdog.observers import Observer

from batch_processor import BatchProcessor
from config_manager import load_config, save_config
from folder_watcher import DebouncedHandler
from history_manager import HistoryManager
from project_manager import (
    TRADING_CARD_GAMES,
    build_project_folder_name,
    list_projects,
    project_folder_path
)
from stats_manager import DailyStats

APP_NAME = "TCG Image Processor"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} – Version 1.0.0-rc1")
        self.geometry("1280x940")
        self.minsize(1160, 840)

        self.config_data = load_config()
        self.stats = DailyStats()
        self.history = HistoryManager()
        self.events = queue.Queue()
        self.observer = None
        self.current_project_folder = None
        self.preview_photo = None
        self.preview_original = None
        self.last_preview_path = None
        self.session_started = False

        self.scan_var = tk.StringVar(value=self.config_data["scan_folder"])
        self.output_var = tk.StringVar(value=self.config_data["output_folder"])
        self.review_var = tk.StringVar(value=self.config_data["review_folder"])
        self.size_var = tk.IntVar(value=self.config_data["image_size"])
        self.quality_var = tk.IntVar(value=self.config_data["jpg_quality"])
        self.margin_var = tk.IntVar(value=self.config_data["margin_percent"])
        self.odd_front_var = tk.BooleanVar(value=self.config_data["odd_is_front"])
        self.crop_var = tk.BooleanVar(value=self.config_data["auto_crop"])
        self.delete_var = tk.BooleanVar(value=self.config_data["delete_originals"])
        self.names_var = tk.BooleanVar(value=self.config_data["carduploader_names"])
        self.quality_check_var = tk.BooleanVar(value=self.config_data["quality_check"])
        self.copy_review_var = tk.BooleanVar(value=self.config_data["copy_review_images"])
        self.open_url_var = tk.BooleanVar(value=self.config_data["open_carduploader_url"])
        self.carduploader_url_var = tk.StringVar(value=self.config_data["carduploader_url"])
        self.project_mode_var = tk.BooleanVar(value=self.config_data.get("project_mode", False))
        self.project_game_var = tk.StringVar(value=self.config_data.get("project_game", "Pokémon"))
        self.project_name_var = tk.StringVar(value=self.config_data.get("project_name", ""))
        self.preview_var = tk.BooleanVar(value=self.config_data.get("show_live_preview", True))
        self.preview_zoom_var = tk.IntVar(value=self.config_data.get("preview_zoom", 100))
        self.project_search_var = tk.StringVar()

        self.status_var = tk.StringVar(value="Gestoppt")
        self.scanner_status_var = tk.StringVar(value="⚪ Überwachung aus")
        self.folder_status_var = tk.StringVar(value="⚪ Scanordner nicht geprüft")
        self.project_status_var = tk.StringVar(value="⚪ Kein Projekt aktiv")
        self.stats_var = tk.StringVar()
        self.daily_var = tk.StringVar()
        self.last_var = tk.StringVar(value="Noch keine Datei verarbeitet")
        self.pair_var = tk.StringVar(value="Kartenpaare wurden noch nicht geprüft.")
        self.progress_text_var = tk.StringVar(value="0 / 0")
        self.preview_side_var = tk.StringVar(value="Seite: –")
        self.preview_quality_var = tk.StringVar(value="Qualität: –")
        self.preview_filename_var = tk.StringVar(value="Datei: –")
        self.summary_var = tk.StringVar(value="Noch keine Projektzusammenfassung verfügbar.")

        self.processor = self.create_processor()

        self.build_ui()
        self.restore_last_project()
        self.refresh_stats()
        self.refresh_folder_status()
        self.after(200, self.poll_events)
        self.after(1000, self.periodic_status_update)
        self.protocol("WM_DELETE_WINDOW", self.close_app)

    def create_processor(self):
        config = self.current_config()
        config["active_output_folder"] = str(
            self.current_project_folder or Path(config["output_folder"])
        )
        return BatchProcessor(config, self.events, self.stats)

    def build_ui(self):
        outer = ttk.Frame(self, padding=14)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="TCG Image Processor", font=("Segoe UI", 22, "bold")).pack(anchor="w")
        ttk.Label(outer, text="Epson-Scanstapel automatisch für CardUploader vorbereiten").pack(anchor="w", pady=(0, 12))

        status_bar = ttk.LabelFrame(outer, text="Systemstatus", padding=10)
        status_bar.pack(fill="x", pady=(0, 12))
        ttk.Label(status_bar, textvariable=self.scanner_status_var).pack(side="left", padx=(0, 24))
        ttk.Label(status_bar, textvariable=self.folder_status_var).pack(side="left", padx=(0, 24))
        ttk.Label(status_bar, textvariable=self.project_status_var).pack(side="left")

        content = ttk.Panedwindow(outer, orient="horizontal")
        content.pack(fill="both", expand=True)

        left = ttk.Frame(content, padding=(0, 0, 10, 0))
        right = ttk.Frame(content, padding=(10, 0, 0, 0))
        content.add(left, weight=3)
        content.add(right, weight=2)

        folders = ttk.LabelFrame(left, text="Ordner", padding=10)
        folders.pack(fill="x")
        self.folder_row(folders, 0, "Scanordner", self.scan_var, self.choose_scan)
        self.folder_row(folders, 1, "Zielordner", self.output_var, self.choose_output)
        self.folder_row(folders, 2, "Bilder prüfen", self.review_var, self.choose_review)

        project = ttk.LabelFrame(left, text="Projektverwaltung", padding=10)
        project.pack(fill="x", pady=10)

        ttk.Checkbutton(
            project,
            text="Für diese Session eigenen Projektordner verwenden",
            variable=self.project_mode_var
        ).grid(row=0, column=0, columnspan=4, sticky="w")

        ttk.Label(project, text="Trading Card Game:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Combobox(
            project,
            textvariable=self.project_game_var,
            values=TRADING_CARD_GAMES,
            state="readonly",
            width=24
        ).grid(row=1, column=1, sticky="w", padx=8, pady=(8, 0))

        ttk.Label(project, text="Projektname:").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(project, textvariable=self.project_name_var).grid(
            row=2, column=1, columnspan=2, sticky="ew", padx=8, pady=(8, 0)
        )
        ttk.Button(project, text="Projekt starten", command=self.start_project).grid(
            row=2, column=3, pady=(8, 0)
        )

        ttk.Button(project, text="Letztes Projekt fortsetzen", command=self.continue_last_project).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )
        ttk.Button(project, text="Projektliste öffnen", command=self.open_project_manager).grid(
            row=3, column=2, columnspan=2, sticky="e", pady=(8, 0)
        )
        project.columnconfigure(1, weight=1)
        project.columnconfigure(2, weight=1)

        settings = ttk.LabelFrame(left, text="Bildausgabe", padding=10)
        settings.pack(fill="x", pady=(0, 10))

        ttk.Label(settings, text="Bildgröße:").grid(row=0, column=0, sticky="w")
        for column, value in enumerate((1500, 2000, 2500), start=1):
            ttk.Radiobutton(
                settings,
                text=f"{value} × {value}",
                variable=self.size_var,
                value=value
            ).grid(row=0, column=column, padx=6)

        ttk.Label(settings, text="JPEG-Qualität:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Spinbox(settings, from_=70, to=100, textvariable=self.quality_var, width=8).grid(
            row=1, column=1, sticky="w", pady=(8, 0)
        )

        ttk.Label(settings, text="Weißer Rand:").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Spinbox(settings, from_=0, to=30, textvariable=self.margin_var, width=8).grid(
            row=2, column=1, sticky="w", pady=(8, 0)
        )
        ttk.Label(settings, text="% je Seite").grid(row=2, column=2, sticky="w", pady=(8, 0))

        checks = [
            ("Scanner-Rand automatisch erkennen und entfernen", self.crop_var),
            ("Originalscan nach erfolgreicher Verarbeitung löschen", self.delete_var),
            ("CardUploader-kompatible Dateinamen verwenden", self.names_var),
            ("Qualitätsprüfung aktivieren", self.quality_check_var),
            ("Auffällige Bilder zusätzlich nach „Bilder prüfen“ kopieren", self.copy_review_var),
            ("Live-Vorschau anzeigen", self.preview_var),
        ]
        for row, (text, variable) in enumerate(checks, start=3):
            ttk.Checkbutton(settings, text=text, variable=variable).grid(
                row=row, column=0, columnspan=4, sticky="w", pady=(6, 0)
            )

        pairing = ttk.LabelFrame(left, text="Zuordnung", padding=10)
        pairing.pack(fill="x", pady=(0, 10))
        ttk.Radiobutton(
            pairing,
            text="Ungerade Nummern = Vorderseite, gerade Nummern = Rückseite",
            variable=self.odd_front_var,
            value=True
        ).pack(anchor="w")
        ttk.Radiobutton(
            pairing,
            text="Ungerade Nummern = Rückseite, gerade Nummern = Vorderseite",
            variable=self.odd_front_var,
            value=False
        ).pack(anchor="w", pady=(4, 0))

        browser_box = ttk.LabelFrame(left, text="CardUploader", padding=10)
        browser_box.pack(fill="x", pady=(0, 10))
        ttk.Checkbutton(
            browser_box,
            text="CardUploader nach Abschluss eines Stapels öffnen",
            variable=self.open_url_var
        ).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Entry(browser_box, textvariable=self.carduploader_url_var).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0)
        )
        ttk.Button(browser_box, text="Jetzt öffnen", command=self.open_carduploader_now).grid(
            row=1, column=2, padx=(8, 0), pady=(6, 0)
        )
        browser_box.columnconfigure(0, weight=1)

        controls = ttk.Frame(left)
        controls.pack(fill="x", pady=(0, 10))
        self.start_button = ttk.Button(controls, text="Überwachung starten", command=self.start_watch)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(controls, text="Stop", command=self.stop_watch, state="disabled")
        self.stop_button.pack(side="left", padx=6)
        ttk.Button(controls, text="Vorhandene Bilder verarbeiten", command=self.process_existing).pack(side="left")
        ttk.Button(controls, text="Zielordner öffnen", command=self.open_active_output).pack(side="right")

        progress_frame = ttk.LabelFrame(left, text="Fortschritt", padding=10)
        progress_frame.pack(fill="x", pady=(0, 10))
        self.progress = ttk.Progressbar(progress_frame, mode="determinate", maximum=100)
        self.progress.pack(side="left", fill="x", expand=True)
        ttk.Label(progress_frame, textvariable=self.progress_text_var, width=12, anchor="e").pack(
            side="right", padx=(10, 0)
        )

        status = ttk.LabelFrame(left, text="Protokoll", padding=10)
        status.pack(fill="both", expand=True)
        ttk.Label(status, textvariable=self.status_var, font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Label(status, textvariable=self.stats_var).pack(anchor="w", pady=(6, 0))
        ttk.Label(status, textvariable=self.daily_var).pack(anchor="w", pady=(3, 0))
        ttk.Label(status, textvariable=self.pair_var, wraplength=620).pack(anchor="w", pady=(5, 0))
        ttk.Label(status, textvariable=self.last_var, wraplength=620).pack(anchor="w", pady=(5, 8))

        self.log = tk.Text(status, height=12, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True)
        self.log.tag_configure("ok", foreground="#187A2F")
        self.log.tag_configure("review", foreground="#9A6A00")
        self.log.tag_configure("error", foreground="#B00020")
        self.log.tag_configure("info", foreground="#1558A6")

        preview_box = ttk.LabelFrame(right, text="Live-Vorschau", padding=10)
        preview_box.pack(fill="both", expand=True)

        preview_meta = ttk.Frame(preview_box)
        preview_meta.pack(fill="x", pady=(0, 8))
        ttk.Label(preview_meta, textvariable=self.preview_side_var, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        ttk.Label(preview_meta, textvariable=self.preview_quality_var).pack(anchor="w", pady=(2, 0))
        ttk.Label(preview_meta, textvariable=self.preview_filename_var, wraplength=440).pack(anchor="w", pady=(2, 0))

        zoom_frame = ttk.Frame(preview_box)
        zoom_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(zoom_frame, text="Zoom:").pack(side="left")
        ttk.Combobox(
            zoom_frame,
            textvariable=self.preview_zoom_var,
            values=(50, 75, 100, 125, 150, 200),
            width=7,
            state="readonly"
        ).pack(side="left", padx=6)
        ttk.Label(zoom_frame, text="%").pack(side="left")
        ttk.Button(
            zoom_frame,
            text="Vorschau aktualisieren",
            command=self.refresh_preview_zoom
        ).pack(side="right")

        self.preview_canvas = tk.Canvas(
            preview_box,
            background="white",
            highlightthickness=1,
            highlightbackground="#cccccc"
        )
        self.preview_canvas.pack(fill="both", expand=True)

        summary_box = ttk.LabelFrame(right, text="Projektzusammenfassung", padding=10)
        summary_box.pack(fill="x", pady=(10, 0))
        ttk.Label(
            summary_box,
            textvariable=self.summary_var,
            justify="left",
            wraplength=450
        ).pack(anchor="w")

        summary_buttons = ttk.Frame(summary_box)
        summary_buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(
            summary_buttons,
            text="Projektordner öffnen",
            command=self.open_active_output
        ).pack(side="left")
        ttk.Button(
            summary_buttons,
            text="CardUploader öffnen",
            command=self.open_carduploader_now
        ).pack(side="right")

        history = ttk.LabelFrame(right, text="Letzte Projekte", padding=10)
        history.pack(fill="x", pady=(10, 0))
        self.history_list = tk.Listbox(history, height=11)
        self.history_list.pack(fill="x")
        self.history_list.bind("<Double-Button-1>", self.open_history_entry)
        self.refresh_history()

    def folder_row(self, parent, row, label, variable, command):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", padx=8)
        ttk.Button(parent, text="Ändern", command=command).grid(row=row, column=2)
        parent.columnconfigure(1, weight=1)

    def choose_scan(self):
        folder = filedialog.askdirectory(initialdir=self.scan_var.get())
        if folder:
            self.scan_var.set(folder)

    def choose_output(self):
        folder = filedialog.askdirectory(initialdir=self.output_var.get())
        if folder:
            self.output_var.set(folder)

    def choose_review(self):
        folder = filedialog.askdirectory(initialdir=self.review_var.get())
        if folder:
            self.review_var.set(folder)

    def start_project(self):
        if not self.project_mode_var.get():
            self.current_project_folder = None
            self.project_status_var.set("⚪ Projektmodus deaktiviert")
            self.processor = self.create_processor()
            return

        game = self.project_game_var.get().strip()
        name = self.project_name_var.get().strip()
        if not name:
            messagebox.showwarning("Projektname fehlt", "Bitte einen Projektnamen eingeben.")
            return

        folder = project_folder_path(self.output_var.get(), game, name)

        if folder.exists():
            answer = messagebox.askyesnocancel(
                "Projekt existiert bereits",
                f"Das Projekt\n\n{folder.name}\n\nexistiert bereits.\n\n"
                "Ja = Weiterarbeiten\nNein = neuen Ordner mit Zusatz erstellen\nAbbrechen = nichts tun"
            )
            if answer is None:
                return
            if answer is False:
                counter = 2
                candidate = folder.with_name(f"{folder.name} ({counter})")
                while candidate.exists():
                    counter += 1
                    candidate = folder.with_name(f"{folder.name} ({counter})")
                folder = candidate

        folder.mkdir(parents=True, exist_ok=True)
        self.current_project_folder = folder
        self.project_status_var.set(f"🟢 Projekt aktiv: {folder.name}")
        self.processor = self.create_processor()
        self.session_started = True

        config = self.current_config()
        config["last_project_folder"] = str(folder)
        save_config(config)

        self.write_log(f"Projekt aktiv: {folder}", "info")
        self.update_summary()

    def restore_last_project(self):
        last_folder = self.config_data.get("last_project_folder", "")
        if last_folder and Path(last_folder).exists():
            self.project_status_var.set(f"🟡 Letztes Projekt verfügbar: {Path(last_folder).name}")

    def continue_last_project(self):
        last_folder = self.config_data.get("last_project_folder", "")
        if not last_folder or not Path(last_folder).exists():
            messagebox.showwarning("Kein Projekt", "Es wurde kein vorhandenes letztes Projekt gefunden.")
            return

        folder = Path(last_folder)
        self.current_project_folder = folder
        self.project_mode_var.set(True)
        self.project_status_var.set(f"🟢 Projekt aktiv: {folder.name}")
        self.processor = self.create_processor()
        self.session_started = True
        self.write_log(f"Projekt fortgesetzt: {folder}", "info")
        self.update_summary()

    def open_project_manager(self):
        window = tk.Toplevel(self)
        window.title("Projektverwaltung")
        window.geometry("760x500")

        search_frame = ttk.Frame(window, padding=10)
        search_frame.pack(fill="x")
        ttk.Label(search_frame, text="Suche:").pack(side="left")
        search_entry = ttk.Entry(search_frame, textvariable=self.project_search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=8)

        listbox = tk.Listbox(window)
        listbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        def refresh(*_):
            term = self.project_search_var.get().strip().lower()
            listbox.delete(0, "end")
            projects = list_projects(self.output_var.get())
            listbox.projects = [p for p in projects if term in p.name.lower()]
            for project in listbox.projects:
                listbox.insert("end", project.name)

        def open_selected():
            selection = listbox.curselection()
            if not selection:
                return
            os.startfile(listbox.projects[selection[0]])

        def continue_selected():
            selection = listbox.curselection()
            if not selection:
                return
            folder = listbox.projects[selection[0]]
            self.current_project_folder = folder
            self.project_mode_var.set(True)
            self.project_status_var.set(f"🟢 Projekt aktiv: {folder.name}")
            self.processor = self.create_processor()
            self.session_started = True

            config = self.current_config()
            config["last_project_folder"] = str(folder)
            save_config(config)

            self.write_log(f"Projekt fortgesetzt: {folder}", "info")
            self.update_summary()
            window.destroy()

        buttons = ttk.Frame(window, padding=10)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Ordner öffnen", command=open_selected).pack(side="left")
        ttk.Button(buttons, text="Projekt fortsetzen", command=continue_selected).pack(side="left", padx=8)
        ttk.Button(buttons, text="Schließen", command=window.destroy).pack(side="right")

        self.project_search_var.trace_add("write", refresh)
        listbox.bind("<Double-Button-1>", lambda _event: continue_selected())
        refresh()

    def active_output_folder(self):
        return self.current_project_folder or Path(self.output_var.get())

    def open_active_output(self):
        folder = self.active_output_folder()
        folder.mkdir(parents=True, exist_ok=True)
        os.startfile(folder)

    def open_carduploader_now(self):
        url = self.carduploader_url_var.get().strip()
        if url:
            webbrowser.open(url)

    def current_config(self):
        return {
            "scan_folder": self.scan_var.get(),
            "output_folder": self.output_var.get(),
            "review_folder": self.review_var.get(),
            "image_size": self.size_var.get(),
            "jpg_quality": self.quality_var.get(),
            "margin_percent": self.margin_var.get(),
            "odd_is_front": self.odd_front_var.get(),
            "batch_delay_seconds": 2.0,
            "auto_crop": self.crop_var.get(),
            "delete_originals": self.delete_var.get(),
            "carduploader_names": self.names_var.get(),
            "quality_check": self.quality_check_var.get(),
            "copy_review_images": self.copy_review_var.get(),
            "open_carduploader_url": self.open_url_var.get(),
            "carduploader_url": self.carduploader_url_var.get(),
            "blur_threshold": 90.0,
            "dark_threshold": 45.0,
            "bright_threshold": 235.0,
            "project_mode": self.project_mode_var.get(),
            "project_game": self.project_game_var.get(),
            "project_name": self.project_name_var.get(),
            "show_live_preview": self.preview_var.get(),
            "preview_zoom": self.preview_zoom_var.get(),
            "last_project_folder": str(self.current_project_folder or self.config_data.get("last_project_folder", ""))
        }

    def apply_config(self):
        save_config(self.current_config())
        self.config_data = load_config()
        self.processor = self.create_processor()

    def process_existing(self):
        self.apply_config()
        self.status_var.set("Stapel wird verarbeitet …")
        self.processor.request_run()
        self.session_started = True

    def start_watch(self):
        scan_folder = Path(self.scan_var.get())
        output_folder = Path(self.output_var.get())
        review_folder = Path(self.review_var.get())

        if scan_folder.resolve() == output_folder.resolve():
            messagebox.showerror("Fehler", "Scan- und Zielordner dürfen nicht identisch sein.")
            return

        scan_folder.mkdir(parents=True, exist_ok=True)
        output_folder.mkdir(parents=True, exist_ok=True)
        review_folder.mkdir(parents=True, exist_ok=True)

        if self.project_mode_var.get() and not self.current_project_folder:
            self.start_project()
            if not self.current_project_folder:
                return

        self.apply_config()

        handler = DebouncedHandler(self.processor.request_run, delay=2.0)
        self.observer = Observer()
        self.observer.schedule(handler, str(scan_folder), recursive=False)
        self.observer.start()

        self.status_var.set("Überwachung aktiv – wartet auf Epson-Speicherung")
        self.scanner_status_var.set("🟢 Überwachung aktiv")
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.write_log(f"Überwachung gestartet: {scan_folder}", "info")
        self.processor.request_run()
        self.session_started = True

    def stop_watch(self):
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5)
            self.observer = None

        self.status_var.set("Gestoppt")
        self.scanner_status_var.set("⚪ Überwachung aus")
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")

        if self.session_started and self.processor.processed_images > 0:
            self.history.add_or_update_session(
                self.project_game_var.get(),
                self.project_name_var.get().strip() or "Ohne Projektname",
                self.active_output_folder(),
                self.processor.processed_cards,
                self.processor.processed_images,
                self.processor.review_images,
                self.processor.errors
            )
            self.refresh_history()
            self.session_started = False
            self.update_summary()

    def refresh_folder_status(self):
        folder = Path(self.scan_var.get())
        if not folder.exists():
            self.folder_status_var.set("⚪ Scanordner fehlt")
            return

        image_count = len([
            p for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
        ])
        self.folder_status_var.set("🟢 Scanordner leer" if image_count == 0 else f"🟡 {image_count} Dateien warten")

    def periodic_status_update(self):
        self.refresh_folder_status()
        self.after(1000, self.periodic_status_update)

    def maybe_open_carduploader(self):
        if self.open_url_var.get():
            url = self.carduploader_url_var.get().strip()
            if url:
                webbrowser.open(url)
                self.write_log("CardUploader wurde im Browser geöffnet.", "info")

    def update_preview(self, image_path, role=None, actionable=None):
        self.last_preview_path = image_path
        self.preview_original = None

        if not self.preview_var.get():
            self.preview_canvas.delete("all")
            self.preview_canvas.create_text(
                220, 280,
                text="Live-Vorschau ist deaktiviert",
                fill="#666666",
                font=("Segoe UI", 12)
            )
            return

        try:
            self.preview_original = Image.open(image_path).convert("RGB")
            self.preview_side_var.set(
                "Seite: Vorderseite" if role == "front" else "Seite: Rückseite"
            )
            self.preview_quality_var.set(
                "Qualität: 🟡 Bitte prüfen"
                if actionable
                else "Qualität: 🟢 In Ordnung"
            )
            self.preview_filename_var.set(f"Datei: {Path(image_path).name}")
            self.render_preview()
        except Exception:
            self.preview_canvas.delete("all")
            self.preview_canvas.create_text(
                220, 280,
                text="Vorschau konnte nicht geladen werden",
                fill="#B00020",
                font=("Segoe UI", 12)
            )

    def render_preview(self):
        if self.preview_original is None:
            return

        self.update_idletasks()
        canvas_width = max(320, self.preview_canvas.winfo_width())
        canvas_height = max(440, self.preview_canvas.winfo_height())

        zoom = self.preview_zoom_var.get() / 100.0
        image = self.preview_original.copy()
        fit_ratio = min(canvas_width / image.width, canvas_height / image.height)
        ratio = fit_ratio * zoom

        image = image.resize(
            (
                max(1, int(image.width * ratio)),
                max(1, int(image.height * ratio))
            ),
            Image.Resampling.LANCZOS
        )

        self.preview_photo = ImageTk.PhotoImage(image)
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(
            canvas_width // 2,
            canvas_height // 2,
            image=self.preview_photo,
            anchor="center"
        )

    def refresh_preview_zoom(self):
        self.render_preview()

    def update_summary(self):
        project_name = (
            self.current_project_folder.name
            if self.current_project_folder
            else "Kein aktives Projekt"
        )
        self.summary_var.set(
            f"Projekt: {project_name}\n"
            f"Karten: {self.processor.processed_cards}\n"
            f"Bilder: {self.processor.processed_images}\n"
            f"Zu prüfen: {self.processor.review_images}\n"
            f"Fehler: {self.processor.errors}\n"
            f"Zielordner: {self.active_output_folder()}"
        )

    def refresh_stats(self):
        daily = self.stats.data
        self.daily_var.set(
            f"Heute: {daily['cards']} Karten · {daily['images']} Bilder · "
            f"{daily['review_images']} Bilder prüfen · {daily['errors']} Fehler"
        )
        self.stats_var.set(
            f"Aktuelle Session: {self.processor.ok_images} in Ordnung · "
            f"{self.processor.review_images} prüfen · {self.processor.errors} Fehler"
        )

    def refresh_history(self):
        self.history_list.delete(0, "end")
        for entry in self.history.entries[:10]:
            timestamp = entry["timestamp"].replace("T", " ")
            text = (
                f"{timestamp} | {entry.get('project_game', '')} | "
                f"{entry['project_name']} | {entry['cards']} Karten"
            )
            self.history_list.insert("end", text)

    def open_history_entry(self, _event):
        selection = self.history_list.curselection()
        if not selection:
            return
        folder = Path(self.history.entries[selection[0]]["output_folder"])
        if folder.exists():
            os.startfile(folder)

    def poll_events(self):
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break

            kind = event[0]

            if kind == "processed":
                result = event[1]
                role_text = "Vorderseite" if result["role"] == "front" else "Rückseite"
                self.last_var.set(f"Zuletzt: {result['output']}")
                self.update_preview(
                    result["output_path"],
                    result["role"],
                    result["actionable"]
                )

                if result["actionable"]:
                    self.write_log(
                        f"{result['source']} → {result['output']} | "
                        f"Karte {result['pair']}, {role_text} | "
                        + " | ".join(result["actionable"]),
                        "review"
                    )
                else:
                    self.write_log(
                        f"{result['source']} → {result['output']} | "
                        f"Karte {result['pair']}, {role_text}",
                        "ok"
                    )

                for information in result["information"]:
                    self.write_log(f"{result['source']}: {information}", "info")

            elif kind == "error":
                _, source, error = event
                self.write_log(f"{source}: {error}", "error")

            elif kind == "batch_start":
                _, total = event
                self.status_var.set(f"Stapel mit {total} Dateien wird verarbeitet …")
                self.progress.configure(maximum=max(total, 1), value=0)
                self.progress_text_var.set(f"0 / {total}")

            elif kind == "progress":
                _, current, total, filename = event
                self.progress.configure(maximum=max(total, 1), value=current)
                self.progress_text_var.set(f"{current} / {total}")
                if current < total:
                    self.status_var.set(f"Verarbeite {filename} …")

            elif kind == "batch_done":
                _, done, total = event
                self.progress.configure(maximum=max(total, 1), value=total)
                self.progress_text_var.set(f"{total} / {total}")
                self.status_var.set(f"Bereit – {done} neue Bilder aus {total} Dateien verarbeitet")
                self.write_log(f"Stapel abgeschlossen: {done} neue Bilder verarbeitet.", "info")
                self.update_summary()
                if done > 0:
                    self.maybe_open_carduploader()

            elif kind == "pair_status":
                _, missing_front, missing_back = event
                if not missing_front and not missing_back:
                    self.pair_var.set("✓ Alle vorhandenen Kartenpaare sind vollständig.")
                else:
                    parts = []
                    if missing_front:
                        parts.append("Vorderseite fehlt bei Karte(n): " + ", ".join(map(str, missing_front[:20])))
                    if missing_back:
                        parts.append("Rückseite fehlt bei Karte(n): " + ", ".join(map(str, missing_back[:20])))
                    self.pair_var.set("⚠ " + " | ".join(parts))

            elif kind == "info":
                _, text = event
                self.write_log(text, "info")

            self.refresh_stats()

        self.after(200, self.poll_events)

    def write_log(self, text, tag):
        timestamp = time.strftime("%H:%M:%S")
        prefix = {"ok": "🟢", "review": "🟡", "error": "🔴", "info": "🔵"}[tag]
        self.log.configure(state="normal")
        self.log.insert("end", f"[{timestamp}] {prefix} {text}\n", tag)
        self.log.see("end")
        self.log.configure(state="disabled")

    def close_app(self):
        self.stop_watch()
        save_config(self.current_config())
        self.destroy()
