# TCG Image Processor 1.0.0-rc1

Dies ist der erste Release Candidate der Hauptversion 1.0.

## Enthalten

- vollständiger Epson-Scanworkflow
- automatische Bildbearbeitung
- CardUploader-kompatible Dateinamen
- Qualitätsprüfung und Prüf-Ordner
- Projektverwaltung
- Live-Vorschau und Zoom
- Projektzusammenfassung
- Windows-Build mit PyInstaller
- automatischer GitHub-Actions-Build
- Portable-ZIP
- Vorbereitung für einen Inno-Setup-Installer

## Lokal unter Windows bauen

1. `BUILD_WINDOWS.bat` starten.
2. Nach erfolgreichem Build liegt das Programm hier:

   `dist\TCG Image Processor\TCG Image Processor.exe`

3. Optional `PAKET_ERSTELLEN.bat` starten, um ein Portable-ZIP zu erzeugen.
4. Optional Inno Setup 6 installieren und danach `INSTALLER_BAUEN.bat` starten.

## Über GitHub bauen

1. Alle Dateien in dein GitHub-Repository hochladen.
2. Auf GitHub den Reiter **Actions** öffnen.
3. Workflow **Build Windows RC** auswählen.
4. **Run workflow** anklicken.
5. Nach Abschluss das Artifact herunterladen.

## Test für RC1

- Programm ohne Python-Konsole starten
- Projekt anlegen und fortsetzen
- 20 bis 50 Karten scannen
- Originale löschen lassen
- Prüf-Ordner kontrollieren
- CardUploader im Browser öffnen
- Programm schließen und erneut starten
- Einstellungen und Historie kontrollieren
