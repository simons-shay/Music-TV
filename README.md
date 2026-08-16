# Music TV

Music TV is an automated ambient artwork display pipeline designed for smart TVs. It tracks currently playing music via Spotify or ambient microphone recognition (Shazam), retrieves original studio album covers, and generates full-screen 16:9 ambient artwork with optional AI face-swapping.

## Features

* Multi-Source Ingestion: Tracks active playback via Spotify API or ambient microphone recognition.
* Studio Album Resolution: Automatically maps compilation and "Best Of" tracks back to original studio album artwork.
* Ambient Display Engine: Generates full-screen 16:9 blurred background artwork with crisp centered cover art.
* AI Face Swapping: Uses OpenAI models to detect human faces on album covers and swap them with local reference photos.
* Display Management: Controls TV power states via HDMI-CEC based on playback activity.

## Requirements

* Python 3.10 or higher
* Spotify Developer application credentials
* OpenAI API key
* Display device supporting HDMI-CEC (e.g., Raspberry Pi or dedicated PC)

## Configuration

1. Create a `.env` file in the root directory with the following environment variables:

```env
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
REDIRECT_URI=[http://127.0.0.1:8080](http://127.0.0.1:8080)
OPENAI_API_KEY=your_openai_api_key
```

2. Add portrait reference images for face-swapping into a real_faces/ directory:

```
real_faces/
├── Person1.jpg
└── Person2.jpg
```
3. Install the required Python packages

4. Change open ai image model based on preference
5. Change roomates, spotify users, and allowed devices. Use the name of your speaker, for example my bedroom speaker is named Shays Bedroom. Doing this makes the software only run when connected to that speaker.

## Usage

To start, run art_tv_pipeline.py