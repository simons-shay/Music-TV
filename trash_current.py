import os
import subprocess
from PIL import Image, ImageFilter, ImageEnhance

BASE_DIR = os.path.expanduser("~/art_tv")
TRACKING_FILE = os.path.join(BASE_DIR, "last_artist.txt")
SAVED_ART_DIR = os.path.join(BASE_DIR, "saved_art")
ORIGINAL_COVERS_DIR = os.path.join(BASE_DIR, "original_covers")
IMAGE_OUTPUT_PATH = os.path.join(BASE_DIR, "current_artist.jpg")


def create_ambient_fallback(cover_path, output_path, target_size=(1536, 1024)):
    try:
        cover = Image.open(cover_path).convert("RGB")
        target_w, target_h = target_size

        scale = max(target_w / cover.width, target_h / cover.height)
        bg_w, bg_h = int(cover.width * scale), int(cover.height * scale)
        bg = cover.resize((bg_w, bg_h), Image.Resampling.LANCZOS)

        left = (bg_w - target_w) // 2
        top = (bg_h - target_h) // 2
        bg = bg.crop((left, top, left + target_w, top + target_h))

        bg = bg.filter(ImageFilter.GaussianBlur(radius=60))
        enhancer = ImageEnhance.Brightness(bg)
        bg = enhancer.enhance(0.70)

        center_h = int(target_h * 0.82)
        center_w = center_h
        center_cover = cover.resize((center_w, center_h), Image.Resampling.LANCZOS)

        offset_x = (target_w - center_w) // 2
        offset_y = (target_h - center_h) // 2
        bg.paste(center_cover, (offset_x, offset_y))

        bg.save(output_path, quality=95)
        print("[Trash] Generated ambient fallback image.")
    except Exception as e:
        print(f"[Trash Error] {e}")


def main():
    if not os.path.exists(TRACKING_FILE):
        print("No active track history found.")
        return

    with open(TRACKING_FILE, "r") as f:
        track_id = f.read().strip()

    if "_" not in track_id:
        print("Invalid track format.")
        return

    parts = track_id.split("_", 1)
    artist_name, album_name = parts[0], parts[1]

    clean_artist = "".join(c for c in artist_name if c.isalnum() or c in (" ", "_", "-")).strip()
    clean_album = "".join(c for c in album_name if c.isalnum() or c in (" ", "_", "-")).strip()

    saved_file = os.path.join(SAVED_ART_DIR, f"{clean_artist}_{clean_album}.jpg")
    downloaded_cover = os.path.join(ORIGINAL_COVERS_DIR, f"{clean_album}.jpg")

    # 1. Delete bad AI image from cache
    if os.path.exists(saved_file):
        os.remove(saved_file)
        print(f"[Trash] Deleted AI file: {saved_file}")

    # 2. Create ambient widescreen replacement
    if os.path.exists(downloaded_cover):
        create_ambient_fallback(downloaded_cover, IMAGE_OUTPUT_PATH)

    # 3. Refresh display instantly
    subprocess.run(["pkill", "feh"], stderr=subprocess.DEVNULL)
    os.system(f"feh -F -Z -Y --hide-pointer {IMAGE_OUTPUT_PATH} &")
    print("[Trash] TV Screen refreshed to ambient display!")


if __name__ == "__main__":
    main()