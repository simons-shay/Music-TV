import spotipy
from spotipy.oauth2 import SpotifyOAuth

CLIENT_ID = "7faf3394ff2746bbb08a1e26692f4cef"
CLIENT_SECRET = "4645043415874d42ab3d0783cb79a0d8"
REDIRECT_URI = "http://127.0.0.1:8080"
SCOPE = "user-read-currently-playing user-read-playback-state"


def authorize_user(username):
    sp_oauth = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_path=f".cache-{username}",
        open_browser=True  # Set to False if running headless over SSH
    )

    # This triggers the login URL. If open_browser is False,
    # it will print a link in terminal to copy-paste into a browser.
    token_info = sp_oauth.get_access_token(as_dict=False)
    print(f"Successfully authorized {username}!")


if __name__ == "__main__":
    name = input("Enter the name of the person authenticating: ").strip().lower()
    authorize_user(name)