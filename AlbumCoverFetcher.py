import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def get_song_album_cover_url(artist: str, album: str) -> str | None:
    session = requests.Session()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) JellyfinRPC/1.0",
        "Connection": "close" 
    }

    
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)

    
    mb_url = "https://musicbrainz.org/ws/2/release/"
    params = {
        "query": f'release:"{album}" AND artist:"{artist}"', 
        "fmt": "json"
    }

    try:
        mb_resp = session.get(mb_url, headers=headers, params=params, timeout=10)
        mb_resp.raise_for_status()
        
        data = mb_resp.json()
        releases = data.get("releases", [])
        
        if not releases:
            return None
            
        mbid = releases[0]["id"]
    except Exception as e:
        # We log this, but main.py will now stay alive
        print(f"MusicBrainz API unreachable: {e}")
        return None

    # Step 2: Check cover art availability
    caa_url = f"https://coverartarchive.org/release/{mbid}"
    try:
        caa_resp = session.get(caa_url, headers=headers, timeout=10)
        caa_resp.raise_for_status()
        
        images = caa_resp.json().get("images", [])
        for img in images:
            if img.get("front"):
               
                return img.get("thumbnails", {}).get("large") or img.get("image")
                
    except Exception:
        # If no cover art exists, CAA returns 404, which is handled here
        return None
    finally:
        session.close() # Explicitly close the session

    return None
