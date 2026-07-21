
from datetime import datetime
from config_manager import HISTORY_FILE, load_json, save_json

class HistoryManager:
    def __init__(self):
        self.entries = load_json(HISTORY_FILE, [])

    def save(self):
        save_json(HISTORY_FILE, self.entries)

    def add_or_update_session(self, project_game, project_name, output_folder, cards, images, review_images, errors):
        folder = str(output_folder)
        for entry in self.entries:
            if entry.get("output_folder") == folder:
                entry.update({
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "project_game": project_game,
                    "project_name": project_name,
                    "cards": int(cards),
                    "images": int(images),
                    "review_images": int(review_images),
                    "errors": int(errors)
                })
                self.entries.sort(key=lambda item: item.get("timestamp", ""), reverse=True)
                self.save()
                return

        self.entries.insert(0, {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "project_game": project_game,
            "project_name": project_name,
            "output_folder": folder,
            "cards": int(cards),
            "images": int(images),
            "review_images": int(review_images),
            "errors": int(errors)
        })
        self.entries = self.entries[:100]
        self.save()

    def find_by_folder(self, folder):
        folder = str(folder)
        return next((entry for entry in self.entries if entry.get("output_folder") == folder), None)
