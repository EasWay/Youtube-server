import json
import random
import requests
import logging
import os
import shutil
import time
import socks
import socket
from langcodes import find
from quart import url_for
from pytubefix import YouTube
from pytubefix.exceptions import AgeRestrictedError, LiveStreamError, MaxRetriesExceeded, MembersOnly, VideoPrivate, VideoRegionBlocked, VideoUnavailable, RegexMatchError
from youtube_urls_validator import validate_url
# from youtube_transcript_api import YouTubeTranscriptApi
# from youtube_transcript_api.formatters import JSONFormatter, SRTFormatter, TextFormatter
from urllib.parse import urlparse, parse_qs
from urllib.error import HTTPError
from settings import MAX_DOWNLOAD_SIZE, TEMP_DIR, CODECS, AUTH, VISITOR_DATA, PO_TOKEN, PROXIES, DEBUG, USE_TOR, TOR_PROXY_HOST, TOR_PROXY_PORT, TOR_CONTROL_PORT

logger = logging.getLogger(__name__)

# Global proxy rotation state
_proxy_index = 0
_failed_proxies = set()

# Tor-specific imports and state
_tor_controller = None
_tor_circuit_age = 0
_tor_max_circuit_age = 10  # Renew Tor circuit every 10 requests
_original_socket = None  # Store original socket for cleanup

try:
    if USE_TOR:
        from stem import Signal
        from stem.control import Controller
        logger.info("Stem library loaded for Tor control")
except ImportError:
    if USE_TOR:
        logger.warning("stem library not available, Tor circuit renewal disabled")
    pass


def get_free_mem() -> int:
  disc = shutil.disk_usage('/')
  return disc[2]

def get_first_item(my_list):
    return my_list[0] if my_list else None

def remove_duplicates(items):
  return list(set(items))

def get_avaliable_resolutions(yt):
    return sorted(remove_duplicates(filter(lambda x: x is not None, [stream.resolution for stream in yt.streams.filter(file_extension='mp4', adaptive=True)])), key= lambda char: int(char[:-1]),reverse=True)

def get_avaliable_bitrates(yt):
    return sorted(remove_duplicates(filter(lambda x: x is not None, [stream.abr for stream in yt.streams.filter(only_audio=True)])), key= lambda char: int(char[:-4]),reverse=True)

def get_proxies():
    """Parse proxy configuration from environment"""
    reason = "AUTH = False"
    
    # Check if Tor is enabled first
    if USE_TOR:
        logger.info("Using Tor proxy")
        tor_proxy = f"socks5://{TOR_PROXY_HOST}:{TOR_PROXY_PORT}"
        return [{
            'server': tor_proxy,
            'username': '',
            'password': '',
            'type': 'tor'
        }]
    
    if AUTH:
        reason = "No proxies available"
        if PROXIES and PROXIES[0]:  # Check if PROXIES is not empty
            logger.info("Using proxies")
            proxies_list = []
            for proxy in PROXIES:
                if not proxy.strip():  # Skip empty strings
                    continue
                proxy_dict = {}
                data = proxy.split('@')
                if len(data) == 2:
                    userdata = data[0].split('://')
                    protocol = userdata[0]
                    server = f'{protocol}://{data[1]}'
                    username_password = userdata[1].split(':')
                    username = username_password[0] if len(username_password) > 0 else ''
                    password = username_password[1] if len(username_password) > 1 else ''
                    proxy_dict['server'] = server
                    proxy_dict['username'] = username
                    proxy_dict['password'] = password
                    proxy_dict['type'] = 'regular'
                else:
                    proxy_dict['server'] = data[0]  # No authentication case
                    proxy_dict['type'] = 'regular'
                proxies_list.append(proxy_dict)
            return proxies_list
    logger.warning("Not using proxies because {}".format(reason))
    return []


def renew_tor_circuit():
    """Request a new Tor circuit (new IP address)"""
    global _tor_controller, _tor_circuit_age
    
    if not USE_TOR:
        return False
    
    try:
        from stem import Signal
        from stem.control import Controller
        
        # Connect to Tor control port
        with Controller.from_port(port=TOR_CONTROL_PORT) as controller:
            controller.authenticate()
            controller.signal(Signal.NEWNYM)
            _tor_circuit_age = 0
            logger.info("Tor circuit renewed - new IP address obtained")
            time.sleep(3)  # Wait for new circuit to establish
            return True
    except Exception as e:
        logger.warning(f"Failed to renew Tor circuit: {e}")
        return False


def should_renew_tor_circuit():
    """Check if Tor circuit should be renewed"""
    global _tor_circuit_age
    
    if not USE_TOR:
        return False
    
    _tor_circuit_age += 1
    if _tor_circuit_age >= _tor_max_circuit_age:
        return True
    return False


def enable_tor_proxy():
    """Enable SOCKS5 proxy globally for all socket connections"""
    global _original_socket
    
    if _original_socket is None:
        _original_socket = socket.socket
    
    # Set default proxy for all socket connections
    socks.set_default_proxy(socks.SOCKS5, TOR_PROXY_HOST, TOR_PROXY_PORT)
    socket.socket = socks.socksocket
    logger.info(f"Enabled SOCKS5 proxy: {TOR_PROXY_HOST}:{TOR_PROXY_PORT}")


def disable_tor_proxy():
    """Disable SOCKS5 proxy and restore original socket"""
    global _original_socket
    
    if _original_socket is not None:
        socket.socket = _original_socket
        logger.info("Disabled SOCKS5 proxy")


def get_next_proxy():
    """Get the next proxy in rotation, skipping failed ones"""
    global _proxy_index, _failed_proxies
    
    proxies = get_proxies()
    if not proxies:
        return None
    
    # Filter out failed proxies
    available_proxies = [p for i, p in enumerate(proxies) if i not in _failed_proxies]
    
    if not available_proxies:
        # All proxies failed, reset and try again
        logger.warning("All proxies failed, resetting failed proxy list")
        _failed_proxies.clear()
        available_proxies = proxies
    
    # Round-robin selection
    proxy = available_proxies[_proxy_index % len(available_proxies)]
    _proxy_index += 1
    
    return proxy


def mark_proxy_failed(proxy_index):
    """Mark a proxy as failed"""
    global _failed_proxies
    _failed_proxies.add(proxy_index)
    logger.warning(f"Marked proxy {proxy_index} as failed")


def create_youtube_with_retry(url, max_retries=3, initial_delay=2):
    """
    Create YouTube object with automatic proxy rotation and retry logic
    Supports both regular proxies and Tor network
    
    Args:
        url: YouTube video URL
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds (doubles with each retry)
    
    Returns:
        YouTube object or raises exception
    """
    proxies_list = get_proxies()
    use_proxies = bool(proxies_list)
    is_tor = use_proxies and proxies_list[0].get('type') == 'tor'
    
    # Enable Tor SOCKS proxy globally if using Tor
    if is_tor:
        enable_tor_proxy()
    
    try:
        for attempt in range(max_retries):
            try:
                proxy_dict = None
                
                if use_proxies:
                    # Renew Tor circuit if needed
                    if is_tor and should_renew_tor_circuit():
                        logger.info("Renewing Tor circuit for fresh IP...")
                        renew_tor_circuit()
                    
                    proxy = get_next_proxy()
                    if proxy:
                        if is_tor:
                            # For Tor, SOCKS proxy is already enabled globally
                            logger.info(f"Attempt {attempt + 1}: Using Tor network (SOCKS5 proxy)")
                            proxy_dict = None  # Don't pass proxy_dict for Tor
                        else:
                            # Convert to pytubefix proxy format for regular HTTP/HTTPS proxies
                            proxy_dict = {
                                'http': proxy['server'],
                                'https': proxy['server']
                            }
                            
                            # Add authentication for non-Tor proxies
                            if 'username' in proxy and proxy['username']:
                                auth = f"{proxy['username']}:{proxy['password']}@"
                                proxy_dict['http'] = proxy_dict['http'].replace('://', f'://{auth}')
                                proxy_dict['https'] = proxy_dict['https'].replace('://', f'://{auth}')
                            
                            logger.info(f"Attempt {attempt + 1}: Using proxy {proxy['server']}")
                
                # Create YouTube object
                yt = YouTube(
                    url,
                    use_oauth=AUTH,
                    allow_oauth_cache=True,
                    token_file=AUTH and os.path.join('auth', 'temp.json'),
                    proxies=proxy_dict  # Will be None for Tor (uses global SOCKS proxy)
                )
                
                # Test the connection by accessing a property
                _ = yt.title
                
                logger.info(f"Successfully created YouTube object for: {yt.title}")
                
                return yt
                
            except HTTPError as e:
                if e.code == 429:
                    delay = initial_delay * (2 ** attempt)
                    logger.warning(f"Rate limited (429) on attempt {attempt + 1}/{max_retries}")
                    
                    if is_tor:
                        logger.info("Rate limited on Tor, renewing circuit...")
                        renew_tor_circuit()
                    elif use_proxies and proxy:
                        logger.info(f"Switching to next proxy due to rate limit")
                    
                    if attempt < max_retries - 1:
                        logger.info(f"Waiting {delay} seconds before retry...")
                        time.sleep(delay)
                    else:
                        logger.error("Max retries reached, all attempts failed")
                        if is_tor:
                            raise Exception("YouTube rate limit exceeded even with Tor. Try again later.")
                        else:
                            raise Exception("YouTube rate limit exceeded. Please try again later or configure more proxies.")
                else:
                    logger.error(f"HTTP Error {e.code}: {e}")
                    raise
                    
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {repr(e)}")
                
                # Try renewing Tor circuit on failure
                if is_tor and attempt < max_retries - 1:
                    logger.info("Renewing Tor circuit after failure...")
                    renew_tor_circuit()
                
                if attempt < max_retries - 1:
                    delay = initial_delay * (2 ** attempt)
                    logger.info(f"Waiting {delay} seconds before retry...")
                    time.sleep(delay)
                else:
                    raise
        
        raise Exception("Failed to create YouTube object after all retries")
    
    finally:
        # Always disable Tor proxy when done
        if is_tor:
            disable_tor_proxy()

def filter_stream_by_codec(streams, codec):
    return [stream  for stream in streams if codec in stream.video_codec]
    


def is_valid_youtube_url(url):
    #pattern = r"^(https?://)?(www\.)?youtube\.com/watch\?v=[\w-]+(&\S*)?$"
    try:
      if validate_url(url=url):
         return True
    except:
      return False
      #return re.match(pattern, url) is not None

def is_valid_language(value):
    try:
        find(value)
        return True
    except:
      return False

"""    
def get_proxies():
    if AUTH:
      try:
        payload = {
          "request": "display_proxies",
          "protocol": "http",
          "proxy_format": "protocolipport",
          "format": "text",
          "anonymity": "Elite,Anonymous",
          "timeout": 150
        }
        response = requests.get("https://api.proxyscrape.com/v4/free-proxy-list/get", params=payload)
        logger.info(f"fetching proxies from {response.url}")
        response.raise_for_status()
        if response.status_code == 200:
          proxy_list = response.text.split("\n")
          if len(proxy_list) >= 10:
            proxy_list = proxy_list[:10]
          else:
            proxy_list = proxy_list
      except requests.exceptions.HTTPError as e:
        logger.error(f"An error occored fetching proxy list from {response.url}:\n  {e.args[0]}")
        return {}
      except requests.exceptions.Timeout as e:
        logger.error(f"Connection timed out when fetching proxy list from {response.url}:\n {e}")
        return {}
      else:
        proxy = random.choice(proxy_list)
        return {
          "http": proxy,
          "https": proxy
        }
    else:
      logger.info(f"Cannot use proxies with authentication")
      return {}
"""


def video_id(value):
    if not value: return
    query = urlparse(value)
    if query.hostname == 'youtu.be':
        return query.path[1:]
    if query.hostname in ('www.youtube.com', 'youtube.com'):
        if query.path == '/watch':
            p = parse_qs(query.query)
            return p['v'][0]
        if query.path[:7] == '/embed/':
            return query.path.split('/')[2]
        if query.path[:3] == '/v/':
            return query.path.split('/')[2]
    # fail?
    raise ValueError


def get_info(yt):
    try:
        video_info = yt.dict()
        print(video_info)
        video_info['video_id'] = video_id(video_info.get('view_url'))
        return video_info, None
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        return None, str(e)


def validate_download(stream):
  if stream.filesize_approx <= MAX_DOWNLOAD_SIZE:
      filesize = stream.filesize
      logger.info(f"stream filesize is {filesize / 1024**3}mb storage left on server is {get_free_mem() / 1024 ** 3}mb")
      if filesize <= get_free_mem():
            logger.info(f"stream filesize is {filesize / 1024**3}mb storage left on server is {get_free_mem() / 1024 ** 3}mb")
            return True, None
      return False, "Not enough memory on the server try agin later"
  return None, f"File excedds max download size of {MAX_DOWNLOAD_SIZE}"
    

def download_content(yt, resolution: str ="", bitrate: str ="", frame_rate: int =30, content_type: str ="video", hdr: bool | None =None):
    try:
        logger.info(f"Starting download_content: type={content_type}, resolution={resolution}, bitrate={bitrate}, frame_rate={frame_rate}, hdr={hdr}")
        #yt = YouTube(url, use_oauth=AUTH, allow_oauth_cache=True, on_progress_callback = on_progress)
        stream = None
        if content_type.lower() == "video":
            logger.debug(f"Fetching video streams...")
            if resolution:
                logger.debug(f"Filtering streams: is_video=True, frame_rate={frame_rate}, resolution={resolution}, hdr={hdr}")
                streams = yt.streams.filter(is_video=True, frame_rate=frame_rate, resolution=resolution, hdr=(hdr if hdr != None else None))
                streams.order_by('hdr')
                logger.debug(f"Found {len(streams)} matching streams")
                if len(streams) > 0:
                    stream = streams.first()
                    logger.info(f"Selected stream: {stream}")
            else:
                # Default to 720p instead of highest resolution
                logger.debug("No resolution specified, trying 720p...")
                stream = yt.streams.filter(res="720p").first()
                if not stream:
                    logger.debug("720p not available, getting highest resolution...")
                    # Fallback to highest if 720p not available
                    stream = yt.streams.get_highest_resolution()
                logger.info(f"Selected stream: {stream}")
            if stream:
                is_valid, error = True, None # validate_download(yt)
                if is_valid:
                    logger.info(f"Stream validated successfully")
                    return stream, None
                else:
                  logger.error(f"Stream validation failed: {error}")
                  return None, error
            else:
                available_resolutions = yt.streams.get_available_resolutions()
                available_frame_rates = yt.streams.get_highest_frame_rates()
                error_msg = f"Video with the specified resolution of frame rate not found. Avaliable resolutions are: {available_resolutions} and frame rates are {available_frame_rates}"
                logger.error(error_msg)
                return None, error_msg
        elif content_type.lower() == "audio":
            logger.debug(f"Fetching audio streams...")
            if bitrate:
              logger.debug(f"Filtering audio streams: only_audio=True, abr={bitrate}")
              stream = yt.streams.filter(only_audio=True, abr=bitrate).first()
            else:
              logger.debug("Getting highest quality audio...")
              stream = yt.streams.get_audio_only()
            
            if stream:
                logger.info(f"Selected audio stream: {stream}")
                is_valid, error = True, None # validate_download(stream)
                if is_valid:
                    logger.info(f"Audio stream validated successfully")
                    return stream, None
                else:
                    logger.error(f"Audio stream validation failed: {error}")
                    return None, error
            else:
                available_bitrates = yt.streams.get_available_bit_rates()
                error_msg = f"Audio stream with the specified bitrate not found. Avaliable bitrates are: {available_bitrates}"
                logger.error(error_msg)
                return None, error_msg
        else:
            error_msg = "Invalid content type specified. Use 'video' or 'audio'."
            logger.error(error_msg)
            return None, error_msg
        
    except Exception as e:
        logger.error(f"Error downloding {content_type} content: {e}", exc_info=True)
        return None, f'An error occored: {e} if you are seeing this message please contact administrator or open a issue at github.com/DannyAkintunde/Youtube-dl-api'

def get_captions(yt,lang, translate=False):
    try:
      #yt = YouTube(url, use_oauth=AUTH, allow_oauth_cache=True,on_progress_callback=on_progress)
      
      # transcripts = YouTubeTranscriptApi.list_transcripts(yt.video_id, proxies = proxies)
      captions = yt.captions
      if not translate:
          caption = captions.get_captions_by_lang_code(lang)
          # transcript = transcripts.find_transcript([lang])
      else:
          caption = captions.get_translated_captions_by_lang_code(lang)
      
      if caption:
          return caption, None
      else:
        return None, f"No captions found. Avaliable captions are: {captions.captions} and Translations are {captions.translations}"
    except Exception as e:
      logger.error(f"Error getting caption content: {e}")
      return None, repr(e)

def delete_file_after_delay(file_path, delay):
    time.sleep(delay)
    if os.path.exists(file_path):
        logger.info("Deleting temp file " + file_path)
        os.remove(file_path)


def write_creds_to_file(access_token, refresh_token, expires, visitor_data, po_token, file_path):
    if os.path.exists(file_path): return
    data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires": int(expires),
        "visitorData": visitor_data,
        "po_token": po_token
    }
    logger.debug(f"creds content: {data}")
    with open(file_path, 'w') as file:
        logger.info("writing creds")
        json.dump(data, file, indent=2)

def fetch_po_token():
  return VISITOR_DATA, PO_TOKEN
  
