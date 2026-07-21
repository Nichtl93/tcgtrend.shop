
import threading
from pathlib import Path

from image_processor import (
    ImageProcessor,
    SUPPORTED_EXTENSIONS,
    extract_number,
    natural_key
)

class BatchProcessor:
    def __init__(self, config, events, stats):
        self.config = config
        self.events = events
        self.stats = stats
        self.image_processor = ImageProcessor(config)

        self.processed_images = 0
        self.processed_cards = 0
        self.errors = 0
        self.review_images = 0
        self.ok_images = 0
        self.skipped = 0

        self.lock = threading.Lock()
        self.pending_run = False

    def request_run(self):
        if self.lock.locked():
            self.pending_run = True
            self.events.put(("info", "Neuer Stapel wurde zur Warteschlange hinzugefügt."))
            return
        threading.Thread(target=self.process_folder, daemon=True).start()

    def process_folder(self):
        if not self.lock.acquire(blocking=False):
            self.pending_run = True
            return

        try:
            while True:
                self.pending_run = False
                scan_folder = Path(self.config["scan_folder"])
                scan_folder.mkdir(parents=True, exist_ok=True)

                files = sorted(
                    [
                        path for path in scan_folder.iterdir()
                        if path.is_file()
                        and path.suffix.lower() in SUPPORTED_EXTENSIONS
                    ],
                    key=natural_key
                )

                self.events.put(("batch_start", len(files)))
                processed_now = 0

                for index, path in enumerate(files, start=1):
                    self.events.put(("progress", index - 1, len(files), path.name))

                    try:
                        result = self.image_processor.process(path)

                        if result["status"] == "skipped":
                            self.skipped += 1
                        else:
                            processed_now += 1
                            self.processed_images += 1
                            self.stats.add("images")

                            if result["pair_completed"]:
                                self.processed_cards += 1
                                self.stats.add("cards")

                            if result["actionable"]:
                                self.review_images += 1
                                self.stats.add("review_images")
                            else:
                                self.ok_images += 1

                            self.events.put(("processed", result))

                    except Exception as error:
                        self.errors += 1
                        self.stats.add("errors")
                        self.events.put(("error", path.name, str(error)))

                    self.events.put(("progress", index, len(files), path.name))

                self.update_pairs()
                self.events.put(("batch_done", processed_now, len(files)))

                if not self.pending_run:
                    break
        finally:
            self.lock.release()

    def update_pairs(self):
        output_folder = Path(self.config["active_output_folder"])

        if self.config.get("carduploader_names", True):
            fronts = list(output_folder.glob("card_*_01_front.jpg"))
            backs = list(output_folder.glob("card_*_02_back.jpg"))
        else:
            fronts = list(output_folder.glob("card_*_front.jpg"))
            backs = list(output_folder.glob("card_*_back.jpg"))

        front_numbers = {extract_number(path) for path in fronts if extract_number(path) is not None}
        back_numbers = {extract_number(path) for path in backs if extract_number(path) is not None}

        self.processed_cards = len(front_numbers & back_numbers)

        self.events.put((
            "pair_status",
            sorted(back_numbers - front_numbers),
            sorted(front_numbers - back_numbers)
        ))
