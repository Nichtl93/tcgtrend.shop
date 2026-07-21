
import re
from datetime import date
from pathlib import Path

TRADING_CARD_GAMES = [
    "Pokémon",
    "Magic: The Gathering",
    "Yu-Gi-Oh!",
    "One Piece",
    "Lorcana",
    "Dragon Ball",
    "Digimon",
    "Weiss Schwarz",
    "Union Arena",
    "Star Wars Unlimited",
    "Sonstiges"
]

def safe_name(name):
    name = re.sub(r'[<>:"/\\|?*]+', "-", name.strip())
    name = re.sub(r"\s+", " ", name)
    return name[:80] or "Projekt"

def build_project_folder_name(game, project_name):
    return f"{safe_name(game)} - {safe_name(project_name)} - {date.today().isoformat()}"

def project_folder_path(base_output, game, project_name):
    return Path(base_output) / build_project_folder_name(game, project_name)

def list_projects(base_output):
    base = Path(base_output)
    if not base.exists():
        return []
    return sorted(
        [path for path in base.iterdir() if path.is_dir()],
        key=lambda path: path.name.lower()
    )
