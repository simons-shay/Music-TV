# Music TV

An automated ambient artwork display for smart TVs. Music TV detects the song that's currently playing, finds the original studio album cover, and shows it full-screen on your TV, with an optional AI face-swap that puts your own photos onto the cover art.

![Kind of Blue example output](docs/examples/Miles_Davis_Kind_Of_Blue_Legacy_Edition.jpg)

## Example Output

Each frame is generated automatically from the currently playing track. These examples show the original studio album covers with faces swapped from local reference photos.

| | |
| --- | --- |
| ![Kind of Blue](docs/examples/Miles_Davis_Kind_Of_Blue_Legacy_Edition.jpg) | ![Ballads](docs/examples/John_Coltrane_Quartet_Ballads_Deluxe_Edition_-_Rudy_Van_Gelder_Remaster.jpg) |
| ![Workin' with the Miles Davis Quintet](docs/examples/Miles_Davis_Quintet_Workin_With_The_Miles_Davis_Quintet.jpg) | ![Duke Ellington & John Coltrane](docs/examples/Duke_Ellington_Duke_Ellington__John_Coltrane.jpg) |

### Who was swapped in

| Album | Original artist | Swapped in |
| --- | --- | --- |
| *Kind of Blue* | Miles Davis | Roomamte One |
| *Ballads* | John Coltrane | Myself |
| *Workin' with the Miles Davis Quintet* | Miles Davis Quintet | Myself |
| *Duke Ellington & John Coltrane* | Duke Ellington & John Coltrane | Roommate Two (left, piano), Roommate One (right, saxophone) |

## Features

- **Multi-source detection:** Tracks playback through the Spotify API or by recognizing ambient audio with the microphone (Shazam).
- **Studio album resolution:** Maps tracks from compilations and "Best Of" albums back to their original studio album artwork.
- **Ambient display engine:** Generates a full-screen 16:9 frame with a blurred background and the sharp cover art centered on top.
- **AI face swapping:** Uses OpenAI image models to detect faces on album covers and swap them with reference photos from a local folder.
- **TV power management:** Turns the TV on and off over HDMI-CEC based on playback activity.
- **Speaker-based activation:** Runs only when playback is on a speaker you specify, so it stays quiet when you're listening elsewhere.

## Requirements

- Python 3.10 or higher
- A Spotify Developer application (client ID and secret)
- An OpenAI API key
- A display device that supports HDMI-CEC, such as a Raspberry Pi or a dedicated PC

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/simons-shay/Music-TV.git
   cd Music-TV
   ```

2. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. Copy `.env.example` to `.env` in the project root and fill in your credentials:

   ```
   SPOTIFY_CLIENT_ID=your_spotify_client_id
   SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
   REDIRECT_URI=http://127.0.0.1:8080
   OPENAI_API_KEY=your_openai_api_key
   ```

   The redirect URI must also be added to your app's settings in the Spotify Developer Dashboard.

2. Add portrait photos for face swapping to a `real_faces/` folder in the project root:

   ```
   real_faces/
   ├── Person1.jpg
   └── Person2.jpg
   ```

   Only use photos of people who have agreed to appear in the display.

3. Choose your OpenAI image model by editing the model setting in `art_tv_pipeline.py`.

4. Set up your household in `art_tv_pipeline.py`:
   - **Roommates / Spotify users:** the people whose accounts and photos the display should use.
   - **Allowed devices:** the name of your speaker exactly as it appears in Spotify (for example, `Shays Bedroom`). Music TV only runs while playback is on a listed device.

## Usage

Start the pipeline:

```bash
python art_tv_pipeline.py
```

On first run, a browser window will open so you can authorize Spotify access.

## Project Structure

| File | Purpose |
| --- | --- |
| `art_tv_pipeline.py` | Main entry point: detection, artwork generation, and TV control |
| `auth_users.py` | Spotify authorization for the configured users |
| `prompt.txt` | Prompt used for the AI face-swap step |
| `.env.example` | Template for required environment variables |
| `requirements.txt` | Python dependencies |

## Notes

- Never commit your `.env` file. It is already listed in `.gitignore`.
- Face swapping calls the OpenAI API, so it uses your API credits.
