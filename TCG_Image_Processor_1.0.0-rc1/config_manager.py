
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"
STATS_FILE = BASE_DIR / "stats.json"
HISTORY_FILE = BASE_DIR / "history.json"
CHANGELOG_FILE = BASE_DIR / "CHANGELOG.md"
ROADMAP_FILE = BASE_DIR / "ROADMAP.md"

DEFAULT_CONFIG = {
    "scan_folder": r"C:\Users\Mein PC\Desktop\Foto TCG",
    "output_folder": r"C:\Users\Mein PC\Desktop\Foto TCG\Fertig",
    "review_folder": r"C:\Users\Mein PC\Desktop\Foto TCG\Bilder prüfen",
    "image_size": 2000,
    "jpg_quality": 95,
    "margin_percent": 7,
    "odd_is_front": True,
    "batch_delay_seconds": 2.0,
    "auto_crop": True,
    "delete_originals": True,
    "carduploader_names": True,
    "open_carduploader_url": False,
    "carduploader_url": "https://carduploader.com/",
    "quality_check": True,
    "copy_review_images": True,
    "blur_threshold": 90.0,
    "dark_threshold": 45.0,
    "bright_threshold": 235.0,
    "project_mode": False,
    "project_game": "Pokémon",
    "project_name": "",
    "show_live_preview": True,
    "preview_zoom": 100,
    "last_project_folder": ""
}

def load_json(path: Path, default):
    result = default.copy() if isinstance(default, dict) else list(default)
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(default, dict) and isinstance(loaded, dict):
                result.update(loaded)
            elif isinstance(default, list) and isinstance(loaded, list):
                result = loaded
        except Exception:
            pass
    return result

def save_json(path: Path, data):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    temporary.replace(path)

def validate_config(config):
    validated = DEFAULT_CONFIG.copy()
    validated.update(config)

    validated["image_size"] = int(validated.get("image_size", 2000))
    if validated["image_size"] not in (1500, 2000, 2500):
        validated["image_size"] = 2000

    validated["jpg_quality"] = max(70, min(100, int(validated.get("jpg_quality", 95))))
    validated["margin_percent"] = max(0, min(30, int(validated.get("margin_percent", 7))))
    validated["batch_delay_seconds"] = max(0.5, float(validated.get("batch_delay_seconds", 2.0)))
    zoom = int(validated.get("preview_zoom", 100))
    validated["preview_zoom"] = zoom if zoom in (50, 75, 100, 125, 150, 200) else 100
    return validated

def load_config():
    return validate_config(load_json(CONFIG_FILE, DEFAULT_CONFIG))

def save_config(config):
    save_json(CONFIG_FILE, validate_config(config))
