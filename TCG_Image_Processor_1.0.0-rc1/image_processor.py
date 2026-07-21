
import re
import shutil
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}

def natural_key(path):
    parts = re.split(r"(\d+)", path.name.lower())
    return [int(part) if part.isdigit() else part for part in parts]

def extract_number(path):
    match = re.search(r"(\d+)(?=\.[^.]+$)", path.name)
    return int(match.group(1)) if match else None

def wait_until_ready(path, timeout=45):
    started = time.time()
    previous_size = -1
    stable_rounds = 0

    while time.time() - started < timeout:
        try:
            current_size = path.stat().st_size
        except FileNotFoundError:
            time.sleep(0.25)
            continue

        if current_size > 0 and current_size == previous_size:
            stable_rounds += 1
            if stable_rounds >= 4:
                return True
        else:
            stable_rounds = 0

        previous_size = current_size
        time.sleep(0.35)

    return False

def detect_and_crop_card(image):
    rgb = np.array(image)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    height, width = gray.shape

    patch = max(3, min(height, width) // 50)
    corners = np.concatenate([
        gray[:patch, :patch].ravel(),
        gray[:patch, -patch:].ravel(),
        gray[-patch:, :patch].ravel(),
        gray[-patch:, -patch:].ravel(),
    ])

    background = float(np.median(corners))
    difference = cv2.absdiff(gray, np.full_like(gray, int(background)))
    _, mask = cv2.threshold(difference, 12, 255, cv2.THRESH_BINARY)

    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return image, False, 1.0

    contour = max(contours, key=cv2.contourArea)
    x, y, crop_width, crop_height = cv2.boundingRect(contour)
    area_ratio = (crop_width * crop_height) / float(width * height)

    if area_ratio < 0.45 or area_ratio > 0.995:
        return image, False, area_ratio

    pad_x = max(2, int(crop_width * 0.008))
    pad_y = max(2, int(crop_height * 0.008))

    return image.crop((
        max(0, x - pad_x),
        max(0, y - pad_y),
        min(width, x + crop_width + pad_x),
        min(height, y + crop_height + pad_y)
    )), True, area_ratio

def verify_output(path, expected_size):
    try:
        if not path.exists() or path.stat().st_size < 10_000:
            return False
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            return image.size == (expected_size, expected_size)
    except Exception:
        return False

def quality_report(image, crop_success, area_ratio, config):
    actionable = []
    information = []

    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
    brightness = float(gray.mean())

    if blur_score < float(config.get("blur_threshold", 90.0)):
        actionable.append(f"möglicherweise unscharf ({blur_score:.0f})")
    if brightness < float(config.get("dark_threshold", 45.0)):
        actionable.append("ungewöhnlich dunkel")
    if brightness > float(config.get("bright_threshold", 235.0)):
        actionable.append("ungewöhnlich hell")

    side_ratio = image.width / max(1, image.height)
    if side_ratio > 1.2 or side_ratio < 0.55:
        actionable.append("ungewöhnliches Seitenverhältnis / möglicher Doppeleinzug")

    if config.get("auto_crop", True) and not crop_success:
        information.append("Kartenausschnitt nicht sicher erkannt – Originalausschnitt verwendet")
    elif crop_success and (area_ratio < 0.50 or area_ratio > 0.97):
        actionable.append("Ausschnitt bitte kontrollieren")

    return actionable, information

class ImageProcessor:
    def __init__(self, config):
        self.config = config

    def output_info(self, source):
        number = extract_number(source)
        if number is None:
            raise ValueError("Keine Nummer im Dateinamen gefunden.")

        odd = number % 2 == 1
        role = "front" if odd == bool(self.config.get("odd_is_front", True)) else "back"
        pair = (number + 1) // 2

        output_folder = Path(self.config["active_output_folder"])
        output_folder.mkdir(parents=True, exist_ok=True)

        if self.config.get("carduploader_names", True):
            sequence = "01" if role == "front" else "02"
            output_path = output_folder / f"card_{pair:06d}_{sequence}_{role}.jpg"
        else:
            output_path = output_folder / f"card_{pair:06d}_{role}.jpg"

        return output_path, role, pair

    def paired_paths(self, pair):
        output_folder = Path(self.config["active_output_folder"])

        if self.config.get("carduploader_names", True):
            return (
                output_folder / f"card_{pair:06d}_01_front.jpg",
                output_folder / f"card_{pair:06d}_02_back.jpg"
            )

        return (
            output_folder / f"card_{pair:06d}_front.jpg",
            output_folder / f"card_{pair:06d}_back.jpg"
        )

    def process(self, source):
        if not wait_until_ready(source):
            raise RuntimeError("Datei wurde nicht vollständig gespeichert.")

        output, role, pair = self.output_info(source)

        if output.exists() and verify_output(output, int(self.config["image_size"])):
            return {"status": "skipped"}

        with Image.open(source) as original:
            image = ImageOps.exif_transpose(original).convert("RGB")

        cropped = False
        area_ratio = 1.0
        if self.config.get("auto_crop", True):
            image, cropped, area_ratio = detect_and_crop_card(image)

        actionable, information = ([], [])
        if self.config.get("quality_check", True):
            actionable, information = quality_report(image, cropped, area_ratio, self.config)

        size = int(self.config["image_size"])
        margin = int(self.config.get("margin_percent", 7))
        available = max(100, int(size * (1 - 2 * margin / 100)))

        image.thumbnail((available, available), Image.Resampling.LANCZOS)

        canvas = Image.new("RGB", (size, size), "white")
        canvas.paste(image, ((size - image.width) // 2, (size - image.height) // 2))

        temporary = output.with_suffix(".tmp.jpg")
        canvas.save(
            temporary,
            "JPEG",
            quality=int(self.config["jpg_quality"]),
            optimize=True,
            progressive=True
        )

        if not verify_output(temporary, size):
            temporary.unlink(missing_ok=True)
            raise RuntimeError("Ausgabedatei konnte nicht geprüft werden.")

        temporary.replace(output)

        review_copy = None
        if actionable and self.config.get("copy_review_images", True):
            review_folder = Path(self.config["review_folder"])
            review_folder.mkdir(parents=True, exist_ok=True)
            review_copy = review_folder / output.name
            shutil.copy2(output, review_copy)

        if self.config.get("delete_originals", True):
            source.unlink()

        front, back = self.paired_paths(pair)
        pair_completed = role == "back" and front.exists() and back.exists()

        return {
            "status": "processed",
            "source": source.name,
            "output": output.name,
            "output_path": str(output),
            "role": role,
            "pair": pair,
            "actionable": actionable,
            "information": information,
            "review_copy": review_copy.name if review_copy else "",
            "pair_completed": pair_completed
        }
