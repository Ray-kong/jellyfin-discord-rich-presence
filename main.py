import time
import logging
import requests
from pypresence import Presence, InvalidID, InvalidPipe
from dotenv import load_dotenv
import os
from AlbumCoverFetcher import get_song_album_cover_url
from colorama import Fore, Style, init

init(autoreset=True)

load_dotenv()

# Setup logging
logging.basicConfig(
    filename="jellyfin_rpc.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

def print_header():
    print(f"\n{Fore.CYAN}{'=' * 60}")
    print(f"{Fore.CYAN}║{' ' * 58}║")
    print(f"{Fore.CYAN}║{Fore.MAGENTA}     🎵  Jellyfin Discord Rich Presence  🎬{Fore.CYAN}               ║")
    print(f"{Fore.CYAN}║{' ' * 58}║")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")

print_header()
logging.info("Starting Jellyfin Discord RPC script.")

# Jellyfin setup
jellyfin_url = os.getenv("JELLYFIN_URL")
api_key = os.getenv("JELLYFIN_API_KEY")
user_id = os.getenv("JELLYFIN_USER_ID")
omdb_api_key = os.getenv("OMDB_API_KEY")
headers = {"X-Emby-Token": api_key, "Content-Type": "application/json"}

# Discord setup
client_id = os.getenv("DISCORD_CLIENT_ID")
RPC = None
rpc_connected = False
last_connection_attempt = 0
connection_retry_delay = 5  # seconds

def connect_rpc(retry_count=0, max_retries=3):
    """Connect to Discord RPC with automatic retry logic"""
    global RPC, rpc_connected, last_connection_attempt
    
    current_time = time.time()
    if current_time - last_connection_attempt < connection_retry_delay:
        return False
    
    last_connection_attempt = current_time
    
    try:
        if RPC is None:
            RPC = Presence(client_id)
        
        if retry_count == 0:
            print(f"{Fore.YELLOW}⏳ Connecting to Discord...{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}⏳ Reconnecting to Discord (attempt {retry_count + 1}/{max_retries})...{Style.RESET_ALL}")
        
        RPC.connect()
        rpc_connected = True
        print(f"{Fore.GREEN}✓ Connected to Discord RPC{Style.RESET_ALL}")
        logging.info("Connected to Discord RPC")
        return True
        
    except (InvalidID, InvalidPipe, ConnectionError, Exception) as e:
        rpc_connected = False
        error_msg = str(e)
        
        if "Discord not running" in error_msg or "InvalidPipe" in str(type(e)):
            print(f"{Fore.RED}✗ Discord is not running{Style.RESET_ALL}")
            logging.warning("Discord is not running")
        else:
            print(f"{Fore.RED}✗ Failed to connect: {error_msg}{Style.RESET_ALL}")
            logging.error(f"Failed to connect to Discord RPC: {e}")
        
        if retry_count < max_retries - 1:
            wait_time = min(5 * (2 ** retry_count), 30)  # Exponential backoff, max 30s
            print(f"{Fore.YELLOW}⏳ Retrying in {wait_time} seconds...{Style.RESET_ALL}")
            time.sleep(wait_time)
            return connect_rpc(retry_count + 1, max_retries)
        
        return False

def ensure_rpc_connected():
    """Ensure RPC is connected, attempt reconnection if needed"""
    global rpc_connected
    
    if not rpc_connected:
        return connect_rpc()
    
    # Test connection with a simple operation
    try:
        # Try to clear presence as a connection test
        RPC.clear()
        return True
    except Exception:
        rpc_connected = False
        logging.warning("RPC connection lost, attempting to reconnect")
        return connect_rpc()


def validate_env_variables():
    print(f"{Fore.CYAN}📋 Checking environment variables...{Style.RESET_ALL}\n")
    missing = []
    
    if not jellyfin_url:
        missing.append("JELLYFIN_URL")
    else:
        print(f"{Fore.GREEN}  ✓ JELLYFIN_URL: {Fore.WHITE}{jellyfin_url}{Style.RESET_ALL}")
    
    if not api_key:
        missing.append("JELLYFIN_API_KEY")
    else:
        print(f"{Fore.GREEN}  ✓ JELLYFIN_API_KEY: {Fore.WHITE}{'*' * 10}{Style.RESET_ALL}")
    
    if not user_id:
        missing.append("JELLYFIN_USER_ID")
    else:
        print(f"{Fore.GREEN}  ✓ JELLYFIN_USER_ID: {Fore.WHITE}{user_id}{Style.RESET_ALL}")
    
    if not client_id:
        missing.append("DISCORD_CLIENT_ID")
    else:
        print(f"{Fore.GREEN}  ✓ DISCORD_CLIENT_ID: {Fore.WHITE}{client_id}{Style.RESET_ALL}")
    
    if not omdb_api_key:
        print(f"{Fore.YELLOW}  ⚠ OMDB_API_KEY: Not set (optional){Style.RESET_ALL}")
    else:
        print(f"{Fore.GREEN}  ✓ OMDB_API_KEY: {Fore.WHITE}{'*' * 10}{Style.RESET_ALL}")
    
    if missing:
        print(f"\n{Fore.RED}✗ Missing required environment variables: {', '.join(missing)}{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}Please create a .env file with the following variables:{Style.RESET_ALL}")
        for var in missing:
            print(f"  {var}=your_value_here")
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    print(f"\n{Fore.GREEN}✓ All required environment variables are set{Style.RESET_ALL}\n")


try:
    validate_env_variables()
    connect_rpc()
except ValueError as e:
    print(f"\n{Fore.RED}Error: {e}{Style.RESET_ALL}")
    print(f"\n{Fore.YELLOW}Exiting...{Style.RESET_ALL}")
    exit(1)
except Exception as e:
    print(f"\n{Fore.RED}Unexpected error during startup: {e}{Style.RESET_ALL}")
    print(f"\n{Fore.YELLOW}Exiting...{Style.RESET_ALL}")
    exit(1)


def get_current_playing():
    """Fetch current playing sessions from Jellyfin"""
    url = f"{jellyfin_url}/Sessions?activeWithinSeconds=1"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        sessions = response.json()
        # Filter sessions by user_id
        filtered_sessions = [
            session for session in sessions if session.get("UserId") == user_id
        ]
        return filtered_sessions
    except requests.exceptions.Timeout:
        logging.error("Jellyfin request timed out")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch sessions: {e}")
        return None


def get_thumbnail_url(item_id, max_width=800, max_height=1200, quality=95):
    """Returns high-quality thumbnail URL for Jellyfin items"""
    if not item_id:
        return "https://raw.githubusercontent.com/Ray-kong/discord_rich_presence/main/Jellyfin.png"
    return f"{jellyfin_url}/Items/{item_id}/Images/Primary?maxWidth={max_width}&maxHeight={max_height}&quality={quality}&api_key={api_key}"


def get_imdb_id(now_playing):
    """Extract IMDb ID from external URLs"""
    urls = now_playing.get("ExternalUrls", [])
    for url in urls:
        if url.get("Name") == "IMDb":
            imdb_url = url.get("Url", "")
            # Extract ID from URL like "https://www.imdb.com/title/tt0368226"
            return imdb_url.split("/")[-1] if imdb_url else None
    return None


def get_omdb_poster(now_playing):
    """Get movie poster from OMDB API as fallback"""
    if not omdb_api_key:
        return None
        
    imdb_id = get_imdb_id(now_playing)
    if not imdb_id:
        return None
    
    omdb_url = f"http://img.omdbapi.com/?i={imdb_id}&h=600&apikey={omdb_api_key}"
    try:
        # Make a HEAD request to check if the image exists
        response = requests.head(omdb_url, timeout=5)
        if response.status_code == 200:
            logging.info(f"Using OMDB poster for IMDb ID: {imdb_id}")
            return omdb_url
    except requests.exceptions.RequestException as e:
        logging.warning(f"Failed to verify OMDB image: {e}")
    
    return None


def extract_now_playing(sessions):
    """Extract and format currently playing media information"""
    if not sessions:
        return None

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
        is_paused = play_state.get("IsPaused", False)
        is_muted = play_state.get("IsMuted", False)
        client = session.get("Client", "Unknown Client")
        external_urls = now_playing.get("ExternalUrls", [])
        
        if media_type == "Audio":
            artists = [artist.get("Name") for artist in now_playing.get("ArtistItems", [])]
            if not artists:
                artists = [artist.get("Name") for artist in now_playing.get("AlbumArtists", [])]
            album = now_playing.get("Album", "Unknown Album")
            details = title
            state = f"by {', '.join(artists)}" if artists else "Unknown Artist"
            album_cover_url = get_song_album_cover_url("".join(artists), album) or "https://raw.githubusercontent.com/Ray-kong/discord_rich_presence/main/Jellyfin.png"
            activity_type = 2  # Listening

        elif media_type == "Movie":
            year = now_playing.get("ProductionYear")
            genres = now_playing.get("Genres", [])
            details = f"Watching {title}"
            state = f"{year} • {', '.join(genres[:2])}" if year and genres else "Movie"
            album_cover_url = get_omdb_poster(now_playing) or get_thumbnail_url(item_id)
            activity_type = 3  # Watching

        elif media_type == "Episode":
            series_name = now_playing.get("SeriesName", "Unknown Series")
            season_number = now_playing.get("ParentIndexNumber", 0)
            episode_number = now_playing.get("IndexNumber", 0)
            series_id = now_playing.get("SeriesId")
            details = f"Watching {series_name}"
            state = f"S{season_number}E{episode_number} - {title}"
            album_cover_url = get_thumbnail_url(series_id) if series_id else get_thumbnail_url(item_id)
            activity_type = 3  # Watching

        else:
            details = title
            state = media_type
            album_cover_url = "https://raw.githubusercontent.com/Ray-kong/discord_rich_presence/main/Jellyfin.png"
            activity_type = 0  # Playing
        
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
            "ExternalUrls": external_urls,
            "ActivityType": activity_type,
        }

        logging.info(f"Now playing: {media_type} - {title}")
        return media_info

    return None


def format_time(ticks):
    """Convert ticks to HH:MM:SS or MM:SS format"""
    if not ticks:
        return "00:00"
    seconds = ticks // 10**7
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}:{minutes:02}:{seconds:02}"
    return f"{minutes}:{seconds:02}"


def update_discord_presence(media_info, retry_count=0, max_retries=2):
    """Update Discord presence with automatic retry on failure"""
    global rpc_connected
    
    if not media_info:
        return False

    if not ensure_rpc_connected():
        return False

    try:
        if "PositionTicks" not in media_info or "RunTimeTicks" not in media_info:
            logging.error("Missing timing information")
            return False

        current_time = format_time(media_info["PositionTicks"])
        total_time = format_time(media_info["RunTimeTicks"])
        
        start_time = int(time.time() - media_info["PositionTicks"] // 10**7)
        end_time = start_time + media_info["RunTimeTicks"] // 10**7

        status_details = []
        if media_info.get("IsPaused"):
            status_details.append("⏸️ Paused")
        if media_info.get("IsMuted"):
            status_details.append("🔇 Muted")
        status_details.append(f"via {media_info.get('ClientName', 'Unknown')}")
        
        buttons = []
        if "ExternalUrls" in media_info:
            for url in media_info["ExternalUrls"][:2]:
                name = url.get("Name", "")
                url_value = url.get("Url", "")
                if name and url_value:
                    buttons.append({"label": name, "url": url_value})
        
        logging.info(f"Updating Discord Presence:")
        logging.info(f"  Type: {media_info['Type']}")
        logging.info(f"  Details: {media_info['Details']}")
        logging.info(f"  State: {media_info['State']}")
        logging.info(f"  Time: {current_time} / {total_time}")
        logging.info(f"  Status: {', '.join(status_details)}")
        if buttons:
            logging.info(f"  Buttons: {[btn['label'] for btn in buttons]}")

        update_params = {
            "details": media_info["Details"],
            "state": media_info["State"],
            "start": start_time,
            "end": end_time,
            "large_image": media_info["AlbumCoverUrl"],
            "large_text": media_info["Name"],
            "small_text": f"{current_time} / {total_time}"
        }
        
        if buttons:
            update_params["buttons"] = buttons
        
        RPC.update(**update_params)
        return True
        
    except Exception as e:
        rpc_connected = False
        error_msg = str(e)
        logging.error(f"Failed to update Discord presence: {error_msg}")
        
        if retry_count < max_retries:
            logging.info(f"Retrying presence update (attempt {retry_count + 1}/{max_retries})")
            if connect_rpc():
                return update_discord_presence(media_info, retry_count + 1, max_retries)
        
        return False


def main():
    global RPC, rpc_connected, last_connection_attempt
    
    print(f"{Fore.CYAN}{'─' * 60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}🚀 Monitoring started{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}⏱  Checking for media playback every 5 seconds...{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}⌨  Press Ctrl+C to stop{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'─' * 60}{Style.RESET_ALL}\n")
    
    last_item_id = None
    consecutive_errors = 0
    max_consecutive_errors = 5
    
    try:
        while True:
            try:
                connection_status = f"{Fore.GREEN}●{Style.RESET_ALL}" if rpc_connected else f"{Fore.RED}●{Style.RESET_ALL}"
            except NameError:
                rpc_connected = False
                connection_status = f"{Fore.RED}●{Style.RESET_ALL}"
            
            sessions = get_current_playing()
            
            if sessions is None:
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    print(f"\n{Fore.RED}✗ Too many consecutive errors connecting to Jellyfin{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}Please check your Jellyfin server and network connection{Style.RESET_ALL}")
                    consecutive_errors = 0
                time.sleep(5)
                continue
            
            consecutive_errors = 0
            now_playing_item = extract_now_playing(sessions)
            
            if now_playing_item:
                if now_playing_item['Id'] != last_item_id:
                    print(f"\n{Fore.CYAN}{'─' * 60}{Style.RESET_ALL}")
                    
                    type_icon = "🎵" if now_playing_item['Type'] == "Audio" else "🎬" if now_playing_item['Type'] == "Movie" else "📺"
                    print(f"{Fore.MAGENTA}{type_icon} {now_playing_item['Type'].upper()}{Style.RESET_ALL}")
                    print(f"{Fore.WHITE}   {now_playing_item['Details']}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}   {now_playing_item['State']}{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}   📱 {now_playing_item['ClientName']}{Style.RESET_ALL}")
                
                current_time = format_time(now_playing_item["PositionTicks"])
                total_time = format_time(now_playing_item["RunTimeTicks"])
                
                if now_playing_item["RunTimeTicks"]:
                    percentage = int((now_playing_item["PositionTicks"] / now_playing_item["RunTimeTicks"]) * 100)
                else:
                    percentage = 0
                
                status_icons = []
                if now_playing_item["IsPaused"]:
                    status_icons.append(f"{Fore.YELLOW}⏸{Style.RESET_ALL}")
                else:
                    status_icons.append(f"{Fore.GREEN}▶{Style.RESET_ALL}")
                
                if now_playing_item["IsMuted"]:
                    status_icons.append(f"{Fore.RED}🔇{Style.RESET_ALL}")
                
                status_text = " ".join(status_icons)
                print(f"\r{connection_status} {status_text} {Fore.WHITE}{current_time} / {total_time}{Style.RESET_ALL} {Fore.CYAN}({percentage}%){Style.RESET_ALL}", end="", flush=True)
                
                update_discord_presence(now_playing_item)
                last_item_id = now_playing_item['Id']
            else:
                if last_item_id is not None:
                    print(f"\n\n{Fore.YELLOW}⏹ No media playing{Style.RESET_ALL}")
                    if rpc_connected:
                        try:
                            RPC.clear()
                        except Exception:
                            rpc_connected = False
                    last_item_id = None
                else:
                    print(f"\r{connection_status} {Fore.YELLOW}⏹ No media playing{Style.RESET_ALL}     ", end="", flush=True)
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print(f"\n\n{Fore.CYAN}{'─' * 60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🛑 Stopping script...{Style.RESET_ALL}")
        logging.info("Script stopped by user")
        if rpc_connected:
            try:
                RPC.clear()
                print(f"{Fore.GREEN}✓ Discord presence cleared{Style.RESET_ALL}")
            except Exception:
                pass
        print(f"{Fore.MAGENTA}👋 Goodbye!{Style.RESET_ALL}\n")
    except Exception as e:
        import traceback
        print(f"\n{Fore.RED}✗ Script failed: {e}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Error details:{Style.RESET_ALL}")
        traceback.print_exc()
        logging.error(f"Script failed: {e}")
        logging.error(traceback.format_exc())


if __name__ == "__main__":
    main()
