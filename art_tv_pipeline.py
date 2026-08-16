import os
import time
import spotipy
import requests
from spotipy.oauth2 import SpotifyOAuth
from openai import OpenAI
import platform
import base64
import glob
import asyncio
from shazamio import Shazam
import subprocess
import random
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw
from dotenv import load_dotenv

# =====================================================================
# 1. CONSTANTS & INITIAL CONFIGURATION
# =====================================================================
load_dotenv()

SPOTIFY_USERS = ["shay"]
ALLOWED_DEVICES = ["Living Room Speaker", "Art TV", "Shays Bedroom"]
ROOMMATES = ["Shay", "Nick", "Matt", "Dylan"]

BEST_OF_KEYWORDS = [
    "best of", "greatest hits", "essential", "anthology",
    "ultimate collection", "singles collection", "discography",
    "retrospective", "the definitive", "very best of",
    "hits", "collection", "compilation", "greatest" , "singles" # <--- Added these solo keywords!
]

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://127.0.0.1:8080")
SCOPE = "user-read-currently-playing user-read-playback-state"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

IMAGE_OUTPUT_PATH = "current_artist.jpg"
TRACKING_FILE_PATH = "last_artist.txt"
screen_is_off = False


# =====================================================================
# 2. IMAGE ENHANCEMENT & FILTER HELPERS
# =====================================================================
def is_best_of_album(album_name):
    """
    Checks if the album title matches known best-of or compilation keywords.
    """
    clean_title = album_name.lower()
    return any(keyword in clean_title for keyword in BEST_OF_KEYWORDS)


def create_ambient_fallback(cover_path, output_path, target_size=(1536, 1024)):
    """
    Creates a 16:9 full-screen ambient artwork for any album cover.
    Fills the monitor edge-to-edge with a blurred background (zero black bars)
    and places the crisp square artwork cleanly in the center.
    """
    try:
        cover = Image.open(cover_path).convert("RGB")
        target_w, target_h = target_size

        # 1. Background: Scale & Crop to fill 16:9 canvas completely
        scale = max(target_w / cover.width, target_h / cover.height)
        bg_w, bg_h = int(cover.width * scale), int(cover.height * scale)
        bg = cover.resize((bg_w, bg_h), Image.Resampling.LANCZOS)

        left = (bg_w - target_w) // 2
        top = (bg_h - target_h) // 2
        bg = bg.crop((left, top, left + target_w, top + target_h))

        # Heavy Gaussian blur + slight ambient dimming
        bg = bg.filter(ImageFilter.GaussianBlur(radius=60))
        enhancer = ImageEnhance.Brightness(bg)
        bg = enhancer.enhance(0.70)

        # 2. Scale crisp centered cover
        center_h = int(target_h * 0.82)
        center_w = center_h
        center_cover = cover.resize((center_w, center_h), Image.Resampling.LANCZOS)

        # 3. Composite center cover onto 16:9 canvas
        offset_x = (target_w - center_w) // 2
        offset_y = (target_h - center_h) // 2
        bg.paste(center_cover, (offset_x, offset_y))

        bg.save(output_path, quality=95)
        print(f"[Ambient Display] Generated full-screen 16:9 ambient artwork at {output_path}")

    except Exception as e:
        print(f"[Ambient Error] Failed to generate ambient image: {e}")


def apply_edge_blur(image_path, border_width=35, blur_radius=25):
    """
    Applies a smooth, feathered blur along outer edges if needed.
    """
    try:
        img = Image.open(image_path).convert("RGB")
        w, h = img.size

        blurred_img = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)

        for i in range(border_width):
            alpha = int(255 * (1 - (i / border_width)))
            draw.rectangle([i, i, w - 1 - i, h - 1 - i], outline=alpha)

        mask = mask.filter(ImageFilter.GaussianBlur(radius=border_width // 2))
        final_img = Image.composite(blurred_img, img, mask)
        final_img.save(image_path, quality=95)

    except Exception as e:
        print(f"[Edge Blur Error] Failed to soften borders: {e}")


# =====================================================================
# 3. MUSIC INGESTION (Spotify & Mic)
# =====================================================================
def get_active_spotify_artist():
    for user in SPOTIFY_USERS:
        try:
            auth_manager = SpotifyOAuth(
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                redirect_uri=REDIRECT_URI,
                scope=SCOPE,
                cache_path=f".cache-{user}"
            )
            sp = spotipy.Spotify(auth_manager=auth_manager)
            playback_state = sp.current_playback()

            if playback_state and playback_state.get('is_playing'):
                device_name = playback_state.get('device', {}).get('name')

                if device_name in ALLOWED_DEVICES:
                    item = playback_state.get('item', {})
                    artist_name = item['artists'][0]['name']
                    album_name = item['album']['name']
                    album_image_url = item['album']['images'][0]['url']

                    print(f"\n[Spotify] {user} listening to '{artist_name}' on '{device_name}'.")
                    return artist_name, album_name, album_image_url

        except Exception as e:
            print(f"[Spotify Error] {e}")
            continue

    return None, None, None


def resolve_studio_album_from_spotify(artist_name, track_name, fallback_album, fallback_url):
    """
    When Shazam identifies a track, queries Spotify to swap any Best Of/compilation
    artwork for the original studio album cover art.
    """
    try:
        auth_manager = SpotifyOAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            scope=SCOPE,
            cache_path=f".cache-{SPOTIFY_USERS[0]}"
        )
        sp = spotipy.Spotify(auth_manager=auth_manager)

        query = f"track:{track_name} artist:{artist_name}"
        results = sp.search(q=query, type="track", limit=10)

        for item in results.get("tracks", {}).get("items", []):
            album = item.get("album", {})
            album_type = album.get("album_type", "").lower()
            album_name = album.get("name", "")

            # Match standard studio release ('album' or 'single') that isn't a compilation/best-of
            if album_type in ["album", "single"] and not is_best_of_album(album_name):
                image_url = album["images"][0]["url"]
                print(f"[Mic -> Studio Lookup] Mapped '{track_name}' to studio album '{album_name}'.")
                return artist_name, album_name, image_url

    except Exception as e:
        print(f"[Mic Resolver Error] {e}")

    # Fallback to Shazam's result if Spotify search fails
    return artist_name, fallback_album, fallback_url


async def identify_room_audio(file_path):
    shazam = Shazam()
    try:
        out = await shazam.recognize(file_path)
        if 'track' in out:
            artist_name = out['track']['subtitle']
            track_title = out['track']['title']
            images = out['track'].get('images', {})
            fallback_url = images.get('coverarthq') or images.get('coverart')

            # Extract Shazam's default album name if available
            sections = out['track'].get('sections', [])
            shazam_album = track_title
            for sec in sections:
                if sec.get('type') == 'SONG':
                    for meta in sec.get('metadata', []):
                        if meta.get('title') == 'Album':
                            shazam_album = meta.get('text')

            # Search Spotify for the original studio album cover
            print(f"[Mic Match] Identified '{artist_name} - {track_title}'. Fetching studio album...")
            return resolve_studio_album_from_spotify(artist_name, track_title, shazam_album, fallback_url)

    except Exception as e:
        print(f"[Shazam Error] {e}")

    return None, None, None

def listen_and_identify():
    record_path = "room_audio.wav"
    print("[Mic] Listening to room audio...")
    try:
        if platform.system() == "Windows":
            import sounddevice as sd
            from scipy.io.wavfile import write

            sample_rate = 44100
            duration = 5
            recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
            sd.wait()
            write(record_path, sample_rate, recording)
        else:
            subprocess.run(
                ["arecord", "-D", "plughw:1,0", "-d", "5", "-f", "cd", record_path],
                stderr=subprocess.DEVNULL
            )

        return asyncio.run(identify_room_audio(record_path))
    except Exception as e:
        print(f"[Mic Error] {e}")
        return None, None, None


def push_to_tv_display():
    print("[Display] Refreshing TV screen...")
    if platform.system() == "Windows":
        os.startfile(IMAGE_OUTPUT_PATH)
    else:
        subprocess.run(["pkill", "feh"], stderr=subprocess.DEVNULL)
        os.system(f"feh -F -Z -Y --hide-pointer {IMAGE_OUTPUT_PATH} &")



# =====================================================================
# 4. GENERATION & HYBRID AMBIENT PIPELINE
# =====================================================================
def execute_reactive_outpainting(artist_name, album_name, all_roommates):
    clean_artist_name = "".join(c for c in artist_name if c.isalnum() or c in (' ', '_', '-')).strip()
    clean_album_name = "".join(c for c in album_name if c.isalnum() or c in (' ', '_', '-')).strip()
    output_folder = "saved_art"

    downloaded_cover_path = f"original_covers/{clean_album_name}.jpg"
    permanent_path = os.path.join(output_folder, f"{clean_artist_name}_{clean_album_name}.jpg")

    # 1. CACHE CHECK: If 16:9 ambient artwork was generated previously, display it instantly!
    if os.path.exists(permanent_path):
        print(f"[Cache] Reusing existing ambient artwork for '{artist_name} - {album_name}'.")
        with open(permanent_path, 'rb') as source, open(IMAGE_OUTPUT_PATH, 'wb') as dest:
            dest.write(source.read())
        push_to_tv_display()
        return

    if not os.path.exists(downloaded_cover_path):
        print(f"[Error] Cover not found at {downloaded_cover_path}.")
        return

    # 2. INSTANT AMBIENT DISPLAY: Show blurred 16:9 album art NOW while AI processes!
    print("\n[Instant Display] Rendering ambient cover to TV...")
    create_ambient_fallback(downloaded_cover_path, IMAGE_OUTPUT_PATH)
    push_to_tv_display()

    # 3. LOCAL BEST-OF FILTER: Skip AI face-swapping if album title matches best-of/compilation keywords

    cover_file = None
    opened_faces = []

    try:
        def encode_image_to_b64(path):
            with open(path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')

        cover_b64 = encode_image_to_b64(downloaded_cover_path)

        # STAGE 1: SMART CLASSIFIER FILTER
        print(f"[Smart Filter] Checking if '{album_name}' has clear band members...")
        filter_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an image analysis system.\n"
                        "Classify if this album cover is suitable for AI face-swapping and band member replacement.\n\n"
                        "CRITERIA FOR 'EDIT':\n"
                        "- Must feature ONE OR MORE CLEAR, REALISTIC PHOTOGRAPHIC HUMAN FACES/BAND MEMBERS.\n"
                        "- The faces must be clearly visible and prominent.\n\n"
                        "CRITERIA FOR 'SKIP':\n"
                        "- Best of, Greatest Hits, Anthology, or Compilation album covers.\n"
                        "- No human faces present (landscapes, objects, abstract art, text/logos).\n"
                        "- Cartoon, vector, anime, drawn, heavily stylized, shadow/silhouette, or low-quality faces.\n"
                        "- Crowd scenes where faces are tiny or distant.\n\n"
                        "If suitable for edit, reply with ONLY 'EDIT_X' where X is the number of clear faces (e.g., EDIT_1, EDIT_2).\n"
                        "Otherwise, reply with ONLY 'SKIP'."
                    )
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{cover_b64}"}}
                    ]
                }
            ],
            max_tokens=10
        )

        decision = filter_response.choices[0].message.content.strip().upper()
        print(f"[Smart Filter Decision] -> {decision}")

        # ROUTE 1: SKIP -> Keep ambient display active and cache it
        if not decision.startswith("EDIT"):
            print("[Smart Filter] Cover skipped for face-swap. Saving ambient display.")
            os.makedirs(output_folder, exist_ok=True)
            create_ambient_fallback(downloaded_cover_path, permanent_path)
            return

        # ROUTE 2: EDIT -> AI Face Swap & Center Cover Adaptation
        try:
            detected_count = int(decision.split("_")[-1])
        except ValueError:
            detected_count = len(all_roommates)

        num_to_select = min(detected_count, len(all_roommates))
        active_roommates = random.sample(all_roommates, num_to_select)

        print(f"[AI] Modifying {detected_count} band members with roommates: {', '.join(active_roommates)}...")

        image_inputs = []

        cover_file = open(downloaded_cover_path, "rb")
        image_inputs.append(cover_file)

        roommate_index_map = []
        current_image_index = 1

        for name in active_roommates:
            matched_files = glob.glob(f"real_faces/{name}*.jpg")
            if matched_files:
                indices_for_this_person = []
                for face_path in matched_files:
                    f_stream = open(face_path, "rb")
                    opened_faces.append(f_stream)
                    image_inputs.append(f_stream)
                    indices_for_this_person.append(f"Image {current_image_index}")
                    current_image_index += 1

                guide_line = f"- {name} is strictly defined ONLY by: {', '.join(indices_for_this_person)}"
                roommate_index_map.append(guide_line)

        formatted_index_guide = "\n".join(roommate_index_map)

        system_instruction = (
            "You are an expert technical art director. Your task is to write a highly precise prompt for an inpainting AI model. "
            "You are adapting a square album cover while specifically mapping provided portrait references onto the original subjects.\n\n"
            "### CORE OBJECTIVES ###\n"
            "1. FACIAL ADAPTATION: Morph the facial features of the existing band members to match the provided references, retaining original expressions, hairstyles, art style, and lighting.\n\n"
            "### PORTRAIT MAPPING GUIDE ###\n"
            "Image 0 is the base album cover. Map the reference faces onto the band members using this strict index:\n"
            f"{formatted_index_guide}\n"
        )

        user_content = f"Album cover: '{album_name}' by '{artist_name}'. Adapt the facial features of the {detected_count} subjects using the provided portrait references."

        analysis_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": [{"type": "text", "text": user_content}]}
            ],
            max_tokens=600
        )
        reactive_prompt = analysis_response.choices[0].message.content

        print("[AI] Sending payload to gpt-image-1.5...")
        result = client.images.edit(
            model="gpt-image-1.5",
            image=image_inputs,
            prompt=reactive_prompt,
            size="1024x1024",  # <--- Clean 1:1 square output
        )

        image_base64 = result.data[0].b64_json
        img_bytes = base64.b64decode(image_base64)

        if img_bytes:
            temp_swapped_path = "temp_swapped.jpg"
            with open(temp_swapped_path, 'wb') as handler:
                handler.write(img_bytes)

            # Composite 1:1 face-swapped square cover into the universal 16:9 ambient frame
            create_ambient_fallback(temp_swapped_path, IMAGE_OUTPUT_PATH)

            # Save permanent ambient artwork to cache
            os.makedirs(output_folder, exist_ok=True)
            with open(permanent_path, 'wb') as handler:
                handler.write(open(IMAGE_OUTPUT_PATH, 'rb').read())

            if os.path.exists(temp_swapped_path):
                os.remove(temp_swapped_path)

            print(f"[AI] Face swap complete! Swapping TV display to custom hybrid ambient artwork...")
            push_to_tv_display()

    except Exception as e:
        print(f"[API Error] Face swap failed/denied: {e}")

    finally:
        if cover_file and not cover_file.closed:
            cover_file.close()
        for stream in opened_faces:
            if stream and not stream.closed:
                stream.close()


# =====================================================================
# 5. HARDWARE & DISPLAY OUTPUT
# =====================================================================
def set_screen_power(turn_on):
    global screen_is_off

    if platform.system() == "Windows":
        state = "ON" if turn_on else "OFF"
        print(f"[TV Control (Dev Mode)] Mocking TV power -> {state}")
        screen_is_off = not turn_on
        return

    if turn_on:
        print("[TV Control] Turning TV ON...")
        subprocess.call("echo 'on 0' | cec-client -s -d 1 > /dev/null 2>&1", shell=True)
        subprocess.call("echo 'as' | cec-client -s -d 1 > /dev/null 2>&1", shell=True)
        screen_is_off = False
    else:
        print("[TV Control] 5 minutes of silence. Turning TV OFF...")
        subprocess.call("echo 'standby 0' | cec-client -s -d 1 > /dev/null 2>&1", shell=True)
        screen_is_off = True


# =====================================================================
# 6. MAIN PIPELINE LOOP
# =====================================================================
def main():
    global screen_is_off
    idle_seconds = 0

    print("==============================================")
    print("   Art TV Pipeline initialized and running    ")
    print("   Auto-Sleep Timeout: 5 minutes of silence   ")
    print("==============================================")

    os.makedirs("original_covers", exist_ok=True)
    os.makedirs("saved_art", exist_ok=True)

    last_track_id = ""
    if os.path.exists(TRACKING_FILE_PATH):
        try:
            with open(TRACKING_FILE_PATH, "r") as f:
                last_track_id = f.read().strip()
        except Exception:
            pass

    while True:
        try:
            artist_name, album_name, album_image_url = get_active_spotify_artist()

            if not artist_name:
                artist_name, album_name, album_image_url = listen_and_identify()

            if artist_name and album_name:
                idle_seconds = 0

                if screen_is_off:
                    set_screen_power(turn_on=True)

                current_track_id = f"{artist_name}_{album_name}"

                if current_track_id != last_track_id:
                    print(f"\n[Pipeline] Track change: '{artist_name}' - '{album_name}'")

                    clean_album_name = "".join(c for c in album_name if c.isalnum() or c in (' ', '_', '-')).strip()
                    downloaded_cover_path = f"original_covers/{clean_album_name}.jpg"

                    if album_image_url and not os.path.exists(downloaded_cover_path):
                        try:
                            resp = requests.get(album_image_url, timeout=10)
                            if resp.status_code == 200:
                                with open(downloaded_cover_path, "wb") as f:
                                    f.write(resp.content)
                        except Exception as e:
                            print(f"[Download Error] {e}")

                    execute_reactive_outpainting(artist_name, album_name, ROOMMATES)
                    push_to_tv_display()

                    last_track_id = current_track_id
                    with open(TRACKING_FILE_PATH, "w") as f:
                        f.write(last_track_id)

            else:
                idle_seconds += 5

                if idle_seconds % 30 == 0 and not screen_is_off:
                    print(f"[Idle Timer] System idle for {idle_seconds}/300 seconds...")

                if idle_seconds >= 300 and not screen_is_off:
                    set_screen_power(turn_on=False)
                    last_track_id = ""

        except Exception as e:
            print(f"[Loop Error] {e}")

        time.sleep(5)


if __name__ == "__main__":
    main()