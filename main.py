import time
import logging
import requests
from pypresence import Presence, ActivityType
from dotenv import load_dotenv
import os
from AlbumCoverFetcher import get_song_album_cover_url


load_dotenv()

# Setup logging
logging.basicConfig(
    filename="jellyfin_rpc.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logging.info("Starting Jellyfin Discord RPC script.")

# Jellyfin setup
jellyfin_url = os.getenv("JELLYFIN_URL")
api_key = os.getenv("JELLYFIN_API_KEY")
user_id = os.getenv("JELLYFIN_USER_ID")
omdb_api_key = os.getenv("OMDB_API_KEY")
headers = {"X-Emby-Token": api_key, "Content-Type": "application/json"}

# Discord setup
client_id = os.getenv("DISCORD_CLIENT_ID")
RPC = Presence(client_id)

# Default image URL
default_image_url = (
    "https://raw.githubusercontent.com/Ray-kong/discord_rich_presence/main/Jellyfin.png"
)


def connect_rpc():
    try:
        RPC.connect()
        logging.info("Connected to Discord RPC")
    except Exception as e:
        logging.error(f"Failed to connect to Discord RPC: {e}")


def validate_env_variables():
    if not all([jellyfin_url, api_key, user_id, client_id]):
        raise ValueError("Missing required environment variables")


validate_env_variables()
connect_rpc()


def get_current_playing():
    url = f"{jellyfin_url}/Sessions?activeWithinSeconds=1"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        sessions = response.json()
        # Filter sessions by user_id
        filtered_sessions = [
            session for session in sessions if session.get("UserId") == user_id
        ]
        return filtered_sessions
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch sessions: {e}")
        return None


def get_imdb_id(now_playing):

    urls = now_playing.get("ExternalUrls", [])
    for url in urls:
        if url.get("Name") == "IMDb":
            imdb_url = url.get("Url", "")
            # Extract ID from URL like "https://www.imdb.com/title/tt0368226"
            return imdb_url.split("/")[-1] if imdb_url else None
    return None


FALLBACK = default_image_url


def get_album_cover_url(now_playing):
    # Return FALLBACK immediately if omdb_api_key is not defined
    if not omdb_api_key:
        return FALLBACK
        
    imdb_id = get_imdb_id(now_playing)
    logging.info(f"IMDB id:{imdb_id}")

    if imdb_id:
        omdb_url = f"http://img.omdbapi.com/?i={imdb_id}&h=300&apikey={omdb_api_key}"
        try:
            # Make a HEAD request to check if the image exists
            response = requests.head(omdb_url)
            if response.status_code == 200:
                return omdb_url
        except requests.exceptions.RequestException as e:
            logging.warning(f"Failed to verify OMDB image: {e}")

    return FALLBACK


def extract_now_playing(sessions):
    if not sessions:
        return None

    # Initialize variables with default values
    artists = []
    album = "Unknown Album"
    year = None
    genres = []
    series_name = "Unknown Series"
    season_number = None
    episode_number = None

    for session in sessions:
        now_playing = session.get("NowPlayingItem")
        play_state = session.get("PlayState")

        if not now_playing or not play_state:
            continue

        media_type = now_playing.get("Type", "Unknown")
        item_id = now_playing.get("Id")
        if not item_id:
            continue

        title = now_playing.get("Name", "Unknown Media")

        # --- Logic for Audio ---
        if media_type == "Audio":
            title = now_playing.get("Name", "Unknown Track")
            artists = [
                artist.get("Name") for artist in now_playing.get("ArtistItems", [])
            ]
            if not artists:
                artists = [
                    artist.get("Name") for artist in now_playing.get("AlbumArtists", [])
                ]
            album = now_playing.get("Album", "Unknown Album")
            activity_type = ActivityType.LISTENING
            details = title
            state = f"by {', '.join(artists)} from {album}"

        # --- Logic for Movies ---
        elif media_type == "Movie":
            title = now_playing.get("Name", "Unknown Movie")
            year = now_playing.get("ProductionYear")
            genres = now_playing.get("Genres", [])
            activity_type = ActivityType.WATCHING
            details = title
            state = f"{year} • {', '.join(genres)}" if year and genres else "Movie"

        # --- Logic for TV Episodes ---
        elif media_type == "Episode":
            series_name = now_playing.get("SeriesName", "Unknown Series")
            season_number = now_playing.get("ParentIndexNumber")
            episode_number = now_playing.get("IndexNumber")
            episode_name = now_playing.get("Name", "Unknown Episode")
            activity_type = ActivityType.WATCHING
            details = f"{series_name} S{season_number}E{episode_number}"
            state = episode_name

        else:
            activity_type = ActivityType.PLAYING
            details = title
            state = media_type

        # --- IMAGE FETCHING LOGIC ---
        album_cover_url = default_image_url  # Start with fallback
        
        if media_type == "Audio":
            try:
                # Use the imported music fetcher
                artist_query = ", ".join(artists) if artists else "Unknown Artist"
                fetched_url = get_song_album_cover_url(artist_query, album)
                if fetched_url:
                    album_cover_url = fetched_url
            except Exception as e:
                logging.error(f"MusicBrainz Error: {e}")
                # Keep the default if fetcher fails
        
        elif media_type in ["Movie", "Episode"]:
            # Use your local OMDB function
            album_cover_url = get_album_cover_url(now_playing)

        is_paused = play_state.get("IsPaused", False)
        is_muted = play_state.get("IsMuted", False)
        client = session.get("Client", "Unknown Client")

        media_info = {
            "Type": media_type,
            "Id": item_id,
            "Name": title,
            "Details": details,
            "State": state,
            "AlbumCoverUrl": album_cover_url,
            "RunTimeTicks": now_playing.get("RunTimeTicks"),
            "PositionTicks": play_state.get("PositionTicks"),
            "IsPaused": is_paused,
            "IsMuted": is_muted,
            "ClientName": client,
            "ActivityType": activity_type,
            "ExternalUrls": now_playing.get("ExternalUrls", []),
        }

        # Update metadata based on type
        if media_type == "Audio":
            media_info.update({"Artists": artists, "Album": album})
        elif media_type == "Movie":
            media_info.update({"Year": year, "Genres": genres})
        elif media_type == "Episode":
            media_info.update(
                {
                    "SeriesName": series_name,
                    "SeasonNumber": season_number,
                    "EpisodeNumber": episode_number,
                }
            )

        logging.info(f"Now playing: {media_type} - {title}")
        return media_info

    return None


def format_time(ticks):
    seconds = ticks // 10**7
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes}:{seconds:02}"


def ensure_minimum_length(text, min_length=2):
    return text if len(text) >= min_length else text + " " * (min_length - len(text))


def update_discord_presence(media_info):
    try:
        if not media_info:
            return

        if "PositionTicks" not in media_info or "RunTimeTicks" not in media_info:
            logging.error("Missing timing information")
            return

        current_time = format_time(media_info["PositionTicks"])
        total_time = format_time(media_info["RunTimeTicks"])

        start_time = int(time.time() - media_info["PositionTicks"] // 10**7)
        end_time = start_time + media_info["RunTimeTicks"] // 10**7

        status_details = []

        if media_info["Type"] == "Audio":
            if media_info.get("TrackNumber"):
                status_details.append(f"Track: {media_info['TrackNumber']}")

        elif media_info["Type"] == "Movie":
            if media_info.get("Year"):
                status_details.append(f"Released: {media_info['Year']}")

        elif media_info["Type"] == "Episode":
            if media_info.get("SeriesName"):
                status_details.append(f"Series: {media_info['SeriesName']}")

        if media_info.get("IsPaused"):
            status_details.append("⏸️ Paused")
        if media_info.get("IsMuted"):
            status_details.append("🔇 Muted")

        status_details.append(f"via {media_info.get('ClientName', 'Unknown')}")
        status_text = "\n".join(status_details)

        buttons = []
        # Add external URLs as buttons (maximum of 2 as per Discord's limit)
        if "ExternalUrls" in media_info:
            for url in media_info["ExternalUrls"][:2]:  # Limit to first 2 URLs
                name = url.get("Name", "")
                url_value = url.get("Url", "")
                if name and url_value:
                    buttons.append({"label": f"{name}", "url": url_value})

        # Log the presence details before updating
        logging.info(f"Updating Discord Presence:")
        logging.info(f"Type: {media_info['Type']}")
        logging.info(f"Details: {media_info['Details']}")
        logging.info(f"State: {media_info['State']}")
        logging.info(f"Time: {current_time} / {total_time}")
        logging.info(f"Status: {status_text}")
        if buttons:
            logging.info(f"Button URLs: {[button['url'] for button in buttons]}")
        logging.info("---")

        RPC.update(
            activity_type=media_info["ActivityType"],
            details=media_info["Details"],
            state=media_info["State"],
            start=start_time,
            end=end_time,
            large_image=media_info["AlbumCoverUrl"],
            large_text=media_info.get(
                "Album", media_info.get("SeriesName", media_info["Name"])
            ),
            small_text=f"{current_time} / {total_time}",
            #buttons=buttons, doesnt all ways work and prevents them from showing the Rich Presence
        )
    except Exception as e:
        logging.error(f"Failed to update Discord presence: {e}")
        if "The pipe was closed" in str(e):
            connect_rpc()


def main():
    try:
        while True:
            sessions = get_current_playing()
            now_playing_item = extract_now_playing(sessions)
            if now_playing_item:
                update_discord_presence(now_playing_item)
            else:
                RPC.clear()
            time.sleep(5)
    except KeyboardInterrupt:
        logging.info("Script stopped by user")
        RPC.clear()
    except Exception as e:
        logging.error(f"Script failed: {e}")


if __name__ == "__main__":
    main()
