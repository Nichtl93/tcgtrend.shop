
from datetime import date
from config_manager import STATS_FILE, load_json, save_json

class DailyStats:
    def __init__(self):
        self.data = load_json(STATS_FILE, self._empty())
        self.ensure_today()

    @staticmethod
    def _empty():
        return {
            "date": str(date.today()),
            "images": 0,
            "cards": 0,
            "review_images": 0,
            "errors": 0
        }

    def ensure_today(self):
        if self.data.get("date") != str(date.today()):
            self.data = self._empty()
            self.save()

    def add(self, key, amount=1):
        self.ensure_today()
        self.data[key] = int(self.data.get(key, 0)) + amount
        self.save()

    def save(self):
        save_json(STATS_FILE, self.data)
