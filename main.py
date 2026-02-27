from quart import Quart, request, jsonify, url_for, send_file
from pytubefix import YouTube
from pytubefix.cli import on_progress
from youtubesearchpython.__future__ import VideosSearch, ResultMode, Suggestions
from pytubefix.exceptions import AgeRestrictedError, LiveStreamError, MaxRetriesExceeded, MembersOnly, VideoPrivate, VideoRegionBlocked, VideoUnavailable, RegexMatchError
from apscheduler.schedulers.background import BackgroundScheduler
from editor import combine_video_and_audio, add_subtitles
from utils import is_valid_youtube_url, is_valid_language, get_proxies, get_info, download_content, get_captions, delete_file_after_delay, write_creds_to_file, fetch_po_token, create_youtube_with_retry
from settings import *
import re
import os
import time
import threading
import logging
import asyncio
import uuid

def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('app.log'),
            logging.StreamHandler()
        ]
    )

setup_logging()

logger= logging.getLogger(__name__)

app = Quart(__name__)

# Configure app to work behind reverse proxy (Render uses HTTPS)
app.config['PREFERRED_URL_SCHEME'] = 'https'

# Always create temp directories
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(AUTH_DIR, exist_ok=True)

if AUTH:
      AUTH_FILE_PATH = os.path.join(AUTH_DIR,AUTH_FILE_NAME)
      logger.info(f"auth file path {AUTH_FILE_PATH}")
      write_creds_to_file(ACCESS_TOKEN, REFRESH_TOKEN, EXPIRES, VISITOR_DATA, PO_TOKEN, AUTH_FILE_PATH)

bitrate_regrex = r'\d{2,3}kbps'
resolution_regrex = r'\d{3,}p'
lang_code_regrex = r'^((a\.)?[a-z]{2})(-[A-Z]{2})?$'
search_amount_reqrex = r'\b\d+\b'


@app.route("/ping")
async def handle_ping():
    return jsonify({"message":"pong"}), 200

@app.route("/")
async def docs():
    return "Life is blissful", 200

@app.route("/tor_status")
async def tor_status():
    """Check if Tor is enabled and working"""
    from settings import USE_TOR, TOR_PROXY_HOST, TOR_PROXY_PORT
    import requests as req
    
    status = {
        "tor_enabled": USE_TOR,
        "tor_configured": False,
        "tor_working": False,
        "exit_ip": None,
        "is_tor_exit": False,
        "error": None
    }
    
    if not USE_TOR:
        status["message"] = "Tor is disabled. Set USE_TOR=True to enable."
        return jsonify(status), 200
    
    status["tor_configured"] = True
    status["proxy_address"] = f"{TOR_PROXY_HOST}:{TOR_PROXY_PORT}"
    
    try:
        # Test Tor connection
        proxies = {
            'http': f'socks5://{TOR_PROXY_HOST}:{TOR_PROXY_PORT}',
            'https': f'socks5://{TOR_PROXY_HOST}:{TOR_PROXY_PORT}'
        }
        
        # Check if we're using Tor
        response = req.get('https://check.torproject.org/api/ip', 
                          proxies=proxies, timeout=15)
        data = response.json()
        
        status["tor_working"] = True
        status["is_tor_exit"] = data.get('IsTor', False)
        status["exit_ip"] = data.get('IP')
        
        if status["is_tor_exit"]:
            status["message"] = "✓ Tor is working perfectly!"
        else:
            status["message"] = "⚠ Connected but not through Tor"
            status["error"] = "Proxy connected but not routing through Tor network"
            
    except Exception as e:
        status["error"] = str(e)
        status["message"] = "✗ Tor connection failed"
        logger.error(f"Tor status check failed: {repr(e)}")
    
    return jsonify(status), 200

search_objs = {}

@app.route('/search', methods=['GET'])
async def search():
    data = request.args or await request.get_json()
    if not data:
      return jsonify({"error": "No parameters passed"}), 400
    q = data.get('q') or data.get('query')
    amount = data.get('amount') or DEFUALT_SEARCH_AMOUNT
    
    if not q:
      return jsonify({"error": "Missing 'query'/'q' parameter in the request body."}), 400
    
    if not (amount and re.match(search_amount_reqrex, str(amount))):
      return jsonify({"error": f"The amount parameter must be an integer between or equal to {MIN_SEARCH_AMOUNT} and {MAX_SEARCH_AMOUNT}"}), 400
    amount = int(amount)
    if not (amount >= MIN_SEARCH_AMOUNT and amount <= MAX_SEARCH_AMOUNT):
      return jsonify({"error": f"The amount parameter must be between or equal to {MIN_SEARCH_AMOUNT} and {MAX_SEARCH_AMOUNT}"}), 400
    
    
    try:
        s = VideosSearch(q, limit=amount)
        search_id = uuid.uuid4()
        response = await s.next()
        search_objs[str(search_id)] = s
        suggestions = await Suggestions.get(q)
        results = response['result']
        if response and results and len(results) > 0:
          res = {
            "search": q,
            "search_suggestions": suggestions['result'],
            "lenght": len(results),
            "results": results,
            "search_id": search_id
          }
          return jsonify(res), 200
        else:
          return jsonify({"error":"No results found.", "suggestions": suggestions['result']}), 400
    except Exception as e:
        logger.error(f"Error searching query: {repr(e)}")
        return jsonify({"error": f"An error occored please report this to the devloper.: {repr(e)}"}), 500

@app.route('/search/<search_id>')
async def next_page(search_id):
  try:
    uuid.UUID(search_id,version=4)
    s = search_objs[search_id]
    response = await s.next()
    if response:
      result = response['result']
      return jsonify({
        "length": len(result),
        "results": result,
        "search_id": search_id
      }), 200
    else: 
      logger.info(f"No pages foind for {str(search_id)}")
      return jsonify({"error": "No more pages"}), 400
  except ValueError as e:
    logger.error(f"Invalid search id Error: {repr(e)}")
    return jsonify({"error": "Invalid search id"}), 400
  except KeyError as e:
    logger.error(f"No search found for passed search id Error: {repr(e)}")
    return jsonify({"error": "No seaech found for search id"}), 400
  except Exception as e:
    logger.error(f"an error occore fetching search results : {repr(e)}")
    return jsonify({"error": f"An error occored if you are seing this message pleas report to the dev Error: {repr(e)}"})

@app.route('/info', methods=['GET'])
async def video_info():
    data = request.args or await request.get_json()
    if not data:
      return jsonify({"error": "No parameters passed"}), 500
    
    url =  data.get('url')
    
    if not url:
      return jsonify({"error": "Missing 'url' parameter in the request body."}), 400

    if not is_valid_youtube_url(url): 
      return jsonify({"error": "Invalid YouTube URL."}), 400
    
    try:
      yt = await asyncio.to_thread(create_youtube_with_retry, url)
      video_info, error = await asyncio.to_thread(get_info, yt)
      
      if video_info:
        return jsonify(video_info), 200
      else:
        return jsonify({"error": error}), 500
    
    except Exception as e:
        logger.error(f"An error occored fetching video info:{repr(e)}")
        return jsonify({"error": f"Server error : {repr(e)}"}), 500

@app.route('/download', methods=['POST'])
async def download_highest_avaliable_resolution():
    data = await request.get_json()
    url = data.get('url')
    hdr = data.get('hdr')
    subtitle = data.get('subtitle') or data.get('caption')
    if isinstance(subtitle, dict):
      burn = subtitle.get('burn')
      lang = subtitle.get('lang')
      translate = subtitle.get('translate')
    else:
      lang = subtitle
      burn = True
      translate = False
    
    logger.info(f"Download request received: url={url}, hdr={hdr}, subtitle={subtitle}")
    
    if not url:
        return jsonify({"error": "Missing 'url' parameter in the request body."}), 400

    if not is_valid_youtube_url(url):
        return jsonify({"error": "Invalid YouTube URL."}), 400
    
    if lang:
      if not is_valid_language(lang):
        return jsonify({"error": "Invalid lang code"}), 400
    
    try:
      logger.info(f"Initializing YouTube object for URL: {url}")
      yt = await asyncio.to_thread(create_youtube_with_retry, url)
      logger.info(f"YouTube object created successfully. Video title: {yt.title}")
      
      video_file = None
      audio_file = None
      logger.info("Calling download_content for video stream...")
      video_stream, error_message = await asyncio.to_thread(download_content,yt, hdr=hdr)
      
      if error_message:
          logger.error(f"Video stream download failed: {error_message}")
          return jsonify({"error": error_message}), 500
      
      get_audio = False
      if not error_message:
          logger.info(f"Downloading video file to {TEMP_DIR}...")
          video_file = await asyncio.to_thread(video_stream.download, output_path=TEMP_DIR)
          logger.info(f"Video file downloaded: {video_file}")
          
          # Check if video stream has audio by checking audio_codec
          if not video_stream.is_progressive:
              logger.info("Video stream is not progressive, need to download audio separately")
              get_audio = True
          else:
              logger.info("Video stream is progressive (includes audio)")
              
          if get_audio:
              logger.info("Calling download_content for audio stream...")
              audio_stream, error_message = await asyncio.to_thread(download_content, yt, content_type="audio")
              if not error_message:
                  logger.info(f"Downloading audio file to {TEMP_DIR}...")
                  audio_file = await asyncio.to_thread(audio_stream.download, output_path=TEMP_DIR)
                  logger.info(f"Audio file downloaded: {audio_file}")
              else:
                  logger.error(f"Audio stream download failed: {error_message}")
          
          if audio_file:
              # Create a temporary output path for the combined file
              combined_output = os.path.join(TEMP_DIR, f"combined_{os.path.basename(video_file)}")
              logger.info(f"Combining video and audio: {video_file} + {audio_file} -> {combined_output}")
              video_file = await asyncio.to_thread(combine_video_and_audio, video_file, audio_file, combined_output)
              logger.info(f"Combined file created: {video_file}")
          
          if subtitle:
              logger.info(f"Getting captions: lang={lang}, translate={translate}")
              caption, error_message = await asyncio.to_thread(get_captions, yt, lang, translate=translate)
              if caption:
                  caption_file = caption.srt()
                  logger.info(f"Caption file created: {caption_file}")
                  # Create a temporary output path for the subtitled file
                  subtitled_output = os.path.join(TEMP_DIR, f"subtitled_{os.path.basename(video_file)}")
                  logger.info(f"Adding subtitles: {video_file} + {caption_file} -> {subtitled_output}")
                  video_file = await asyncio.to_thread(add_subtitles, video_file, caption_file, subtitled_output, burn, lang)
                  logger.info(f"Subtitled file created: {video_file}")
                  threading.Thread(target=delete_file_after_delay, args=(caption_file, EXPIRATION_DELAY)).start()
              else:
                  logger.warning(f"Caption download failed: {error_message}")
                 
      """ 
      video_file, error_message = await asyncio.to_thread(download_content,yt)
      if not error_message:
          audio_file, error_message = await asyncio.to_thread(download_content, yt, content_type="audio")
          if audio_file:
              await asyncio.to_thread(combine_video_and_audio, video_file,audio_file,os.path.join(TEMP_DIR,f"temp_{os.path.basename(video_file)}"))
              #combine_video_and_audio( video_file,audio_file,os.path.join(TEMP_DIR,f"temp_{os.path.basename(video_file)}"))
              if subtitle:
                caption, error_message = await asyncio.to_thread(get_captions, yt, lang)
                if caption:
                  await asyncio.to_thread(add_subtitles, video_file, caption["path"], os.path.join(TEMP_DIR,f"temp_{os.path.basename(video_file)}"), burn, lang)
                  threading.Thread(target=delete_file_after_delay, args=(caption["path"], EXPIRATION_DELAY)).start()
                  del caption["path"]
                  
              threading.Thread(target=delete_file_after_delay, args=(audio_file, EXPIRATION_DELAY)).start()
      """
      
      if video_file:
          logger.info(f"Download successful! Final file: {video_file}")
          threading.Thread(target=delete_file_after_delay, args=(video_file, EXPIRATION_DELAY)).start()
          if data.get("link"):
            download_link =  url_for('get_file', filename=os.path.basename(video_file), _external=True)
            logger.info(f"Returning download link: {download_link}")
            return jsonify(
              {
                "download_link": download_link,
                "video_info": {
                  "quality": {
                    "resolution": getattr(video_stream, 'resolution', 'unknown'),
                    "frame_rate": getattr(video_stream, 'fps', 30),
                    "bit_rate": getattr(video_stream, 'bitrate', 0) or (getattr(audio_stream, 'bitrate', 0) if audio_file else 0),
                    "hdr": getattr(video_stream, 'is_hdr', False)},
                    "filename": getattr(video_stream, 'default_filename', 'video.mp4'),
                    "title": yt.title,
                    "duration": yt.length
                }
              }
              ), 200
          else:
            logger.info(f"Sending file: {video_file}")
            return await send_file(video_file, as_attachment=True), 200
      else:
          logger.error(f"Download failed: {error_message}")
          return jsonify({"error": error_message}), 500
    except Exception as e:
        logger.error(f"An error occored downloading content: {repr(e)}", exc_info=True)
        return jsonify({"error": f"Server error : {repr(e)}"}), 500


@app.route('/download/<resolution>', methods=['POST'])
async def download_by_resolution(resolution):
    data = await request.get_json()
    url = data.get('url')
    hdr = data.get('hdr')
    bitrate = data.get('bitrate')
    subtitle = data.get('subtitle') or data.get('caption')
    frame_rate = int(data.get('frame_rate', 30))
    if isinstance(subtitle, dict):
      burn = subtitle.get('burn')
      lang = subtitle.get('lang')
      translate = subtitle.get('translate')
    else:
      lang = subtitle
      burn = True
      translate = False
    
    if not url:
        return jsonify({"error": "Missing 'url' parameter in the request body."}), 400

    if not is_valid_youtube_url(url):
        return jsonify({"error": "Invalid YouTube URL."}), 400
        
    if not re.match(resolution_regrex,resolution):
        return jsonify({"error": "Invald request URL, input a valid resolution for example 360p"}), 400
    
    if bitrate:
        if not re.match(bitrate_regrex,bitrate):
            return jsonify({"error": "Invalid request URL, input a valid bitrate for example 48kbps"}), 400
    if lang:
        if not is_valid_language(lang):
            return jsonify({"error": "Invalid lang code"}), 400
    
    try:
      yt = await asyncio.to_thread(create_youtube_with_retry, url)
      
      video_stream, error_message = await asyncio.to_thread(download_content,yt, hdr=hdr, resolution=resolution, frame_rate=frame_rate)
      get_audio = False
      if not error_message:
          video_file = await asyncio.to_thread(video_stream.download, output_path=TEMP_DIR)
          audio_file = None
          if not video_stream.is_progressive or bitrate:
              get_audio = True
          if get_audio:
              audio_stream, error_message = await asyncio.to_thread(download_content, yt, content_type="audio", bitrate=bitrate)
              if not error_message:
                  audio_file = await asyncio.to_thread(audio_stream.download, output_path=TEMP_DIR)
          
          if audio_file:
              # Create a temporary output path for the combined file
              combined_output = os.path.join(TEMP_DIR, f"combined_{os.path.basename(video_file)}")
              video_file = await asyncio.to_thread(combine_video_and_audio, video_file, audio_file, combined_output)
          
          if subtitle:
              caption, error_message = await asyncio.to_thread(get_captions, yt, lang, translate=translate)
              if caption:
                  caption_file = caption.srt()
                  # Create a temporary output path for the subtitled file
                  subtitled_output = os.path.join(TEMP_DIR, f"subtitled_{os.path.basename(video_file)}")
                  video_file = await asyncio.to_thread(add_subtitles, video_file, caption_file, subtitled_output, burn, lang)
                  threading.Thread(target=delete_file_after_delay, args=(caption_file, EXPIRATION_DELAY)).start()
      
      """
      yt = YouTube(url,  use_oauth=AUTH, allow_oauth_cache=True, token_file = AUTH and AUTH_FILE_PATH, on_progress_callback = on_progress)
      video_file, error_message = await asyncio.to_thread(download_content, yt, resolution)
      if not error_message:
          if bitrate:
            audio_file, error_message = await asyncio.to_thread(download_content, yt, content_type="audio", bitrate=bitrate)
          else:
            audio_file, error_message = await asyncio.to_thread(download_content, yt, content_type="audio", bitrate="")
          if audio_file:
              await asyncio.to_thread(combine_video_and_audio, video_file,audio_file,os.path.join(TEMP_DIR,f"temp_{os.path.basename(video_file)}"))
              if subtitle:
                caption, error_message = await asyncio.to_thread(get_captions, yt, lang)
                if caption:
                  await asyncio.to_thread(add_subtitles, video_file, caption["path"], os.path.join(TEMP_DIR,f"temp_{os.path.basename(video_file)}"), burn, lang)
                  threading.Thread(target=delete_file_after_delay, args=(caption["path"], EXPIRATION_DELAY)).start()
                  del caption["path"]
              threading.Thread(target=delete_file_after_delay, args=(audio_file, EXPIRATION_DELAY)).start()
      """
      if video_file:
          threading.Thread(target=delete_file_after_delay, args=(video_file, EXPIRATION_DELAY)).start()
          if data.get("link"):
            download_link =  url_for('get_file', filename=os.path.basename(video_file), _external=True)
            return jsonify(
              {
                "download_link": download_link,
                "video_info": {
                  "quality": {
                    "resolution": getattr(video_stream, 'resolution', 'unknown'),
                    "frame_rate": getattr(video_stream, 'fps', 30),
                    "bit_rate": getattr(video_stream, 'bitrate', 0) or (getattr(audio_stream, 'bitrate', 0) if audio_file else 0),
                    "hdr": getattr(video_stream, 'is_hdr', False)},
                    "filename": getattr(video_stream, 'default_filename', 'video.mp4'),
                    "title": yt.title,
                    "duration": yt.length
                } 
              }
              ), 200
          else:
            return await send_file(video_file, as_attachment=True), 200
      else:
          return jsonify({"error": error_message}), 500
    except Exception as e:
        logger.error(f"An error occored downloading content:{repr(e)}")
        return jsonify({"error": f"Server error : {repr(e)}"}), 500
  
@app.route('/download_audio', methods=['POST'])
async def download_highest_quality_audio():
    data = await request.get_json()
    url = data.get('url')
  
    if not url:
      return jsonify({"error": "Missing 'url' parameter in the request body."}), 400
  
    if not is_valid_youtube_url(url):
      return jsonify({"error": "Invalid YouTube URL."}), 400
    try:
      yt = await asyncio.to_thread(create_youtube_with_retry, url)
      audio_stream, error_message = await asyncio.to_thread(download_content, yt, content_type="audio")
      audio_file = None 
      if audio_stream:
          audio_file = await asyncio.to_thread(audio_stream.download, output_path=TEMP_DIR)
      if audio_file:
          threading.Thread(target=delete_file_after_delay, args=(audio_file, EXPIRATION_DELAY)).start()
          if data.get("link"):
              download_link =  url_for('get_file', filename=os.path.basename(audio_file), _external=True)
              return jsonify({"download_link": download_link, "audio_info": {"bitrate": getattr(audio_stream, 'abr', 'unknown'), "title": yt.title, "duration": yt.length} }), 200
          else:
              return await send_file(audio_file, as_attachment=True), 200
      else:
          return jsonify({"error": error_message}), 500
    except Exception as e:
        logger.error(f"An error occored downloading content:{repr(e)}")
        return jsonify({"error": f"Server error : {repr(e)}"}), 500
   

@app.route('/download_audio/<bitrate>', methods=['POST'])
async def download_audio_by_bitrate(bitrate):
    data = await request.get_json()
    url = data.get('url')
    
    if not url:
      return jsonify({"error": "Missing 'url' parameter in the request body."}), 400
  
    if not is_valid_youtube_url(url):
      return jsonify({"error": "Invalid YouTube URL."}), 400
 
    if not re.match(f"{bitrate_regrex}",bitrate):
       return jsonify({"error": "Invalid request URL, input a valid bitrate for example 48kpbs fuck you"}), 400
 
    try:
      yt = await asyncio.to_thread(create_youtube_with_retry, url)
      audio_stream, error_message = await asyncio.to_thread(download_content, yt, content_type="audio", bitrate=bitrate)
      
      audio_file = None
      if audio_stream:
          audio_file = await asyncio.to_thread(audio_stream.download, output_path=TEMP_DIR)
      
      if audio_file:
          threading.Thread(target=delete_file_after_delay, args=(audio_file, EXPIRATION_DELAY)).start()
          if data.get("link"):
              download_link =  url_for('get_file', filename=os.path.basename(audio_file), _external=True)
              return jsonify(
                {
                  "download_link": download_link,
                  "audio_info": {
                    "bitrate": getattr(audio_stream, 'abr', 'unknown'),
                    "title": yt.title,
                    "duration": yt.length
                  }
                }
                ), 200
          else:
              return await send_file(audio_file, as_attachment=True), 200
      else:
          return jsonify({"error": error_message}), 500
    except Exception as e:
        logger.error(f"An error occored downloading content:{repr(e)}")
        return jsonify({"error": f"Server error : {repr(e)}"}), 500
 
@app.route('/captions/<lang>',methods=["GET"])
async def get_subtitles(lang):
    lang = lang.lower()
    data = request.args or await request.get_json()
    if not data:
      return jsonify({"error": "No parameters passed"}), 400
    
    url = data.get('url')
    out_format = data.get('format', '').lower()
    supported_formats = ('txt', 'srt', 'raw')
    
    if not url:
        return jsonify({"error": "Missing 'url' parameter in the request body."}), 400
  
    if not is_valid_youtube_url(url):
        return jsonify({"error": "Invalid YouTube URL."}), 400
    
    if not is_valid_language(lang):
        return jsonify({"error": "Invalid lang code"}), 400
    
    if out_format and out_format not in supported_formats:
        return jsonify({"error": f"Invalid format, supported formats are {supported_formats}"}), 400
    elif not out_format:
        return jsonify({"error": "File format not specfied"}), 400
    
    try:
      yt = await asyncio.to_thread(create_youtube_with_retry, url)
      caption, error_message = await asyncio.to_thread(get_captions,yt,lang)
      if caption:
          if out_format in ('srt', 'txt'):
              if out_format == 'srt':
                  caption_file = caption.srt()
              if out_format == 'txt':
                  caption_file = caption.txt()
              file_name = os.path.basename(caption_file)
              file_url = url_for('get_file', filename=file_name, _external=True)
              return jsonify(
                {
                  "download_url": file_url,
                "format": out_format
                }
                ), 200
          else:
              raw = caption.raw
              return jsonify({"data":raw}), 200
      else:
        return jsonify({"error":error_message}), 500
    except Exception as e:
        logger.error(f"An error occored downloading content:{repr(e)}")
        return jsonify({"error": f"Server error : {repr(e)}"}), 500


@app.route('/temp_file/<filename>', methods=['GET'])
async def get_file(filename):
    file_path = os.path.join(TEMP_DIR, filename)
    if os.path.exists(file_path):
        return await send_file(file_path, as_attachment=True)
    else:
        logger.warning(f"Requested file not found: {filename}")
        return jsonify({"error": "File not found"}), 404


def clear_temp_directory():
  logging.info("Clearing temp files")
  now = time.time()
  for filename in os.listdir(TEMP_DIR): 
    file_path = os.path.join(TEMP_DIR, filename) 
    try:
      file_age = now - os.path.getmtime(file_path)
      if os.path.isfile(file_path) and file_age > 86400:
        os.remove(file_path)
        logger.info(f"sucessfull deleted {file_path}")
    except Exception as e: 
      logger.error(f'Failed to delete {file_path}. Reason: {repr(e)}')
  logger.info("Temp files cleared")

@app.after_request
async def add_dev_details(response):
    if response.content_type == 'application/json':
        data = await response.get_json()
        data['developer_github'] = {
          "user_name": "DannyAkintunde",
          "profile_link": "https://github.com/DannyAkintunde"
        }
        response.set_data(await jsonify(data).data)
        
    return response

if __name__ == '__main__':
    # Log Tor status on startup
    from settings import USE_TOR, TOR_PROXY_HOST, TOR_PROXY_PORT
    if USE_TOR:
        logger.info("=" * 60)
        logger.info("TOR NETWORK ENABLED")
        logger.info(f"Tor Proxy: {TOR_PROXY_HOST}:{TOR_PROXY_PORT}")
        logger.info("All YouTube requests will be routed through Tor")
        logger.info("Check /tor_status endpoint to verify Tor is working")
        logger.info("=" * 60)
    else:
        logger.info("Tor is disabled. Set USE_TOR=True to enable.")
    
    if not DEBUG:
      scheduler = BackgroundScheduler()
      scheduler.add_job(clear_temp_directory, "interval", days=1)
      scheduler.start()
    app.run(debug=DEBUG)
