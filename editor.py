import os
import logging
import shutil
import subprocess
from languagecodes import iso_639_alpha3
from settings import CODECS

logger = logging.getLogger(__name__)

def combine_video_and_audio(video_path, audio_path, output_path):
    """
    Add audio to a video file using ffmpeg.

    :param video_path: Path to the input video file.
    :param audio_path: Path to the audio file (e.g., .mp3).
    :param output_path: Path where the output video with audio will be saved.
    :return: Path to the combined output file
    """
    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Created directory: {output_dir}")
    
    if os.path.exists(output_path):
        logger.info("Deleting existing output file " + output_path)
        os.remove(output_path)
    
    # Convert to absolute paths
    video_path = os.path.abspath(video_path)
    audio_path = os.path.abspath(audio_path)
    output_path = os.path.abspath(output_path)
    
    # FFmpeg command to combine video and audio
    ffmpeg_command = [
        'ffmpeg',
        '-i', video_path,
        '-i', audio_path,
        '-c:v', 'copy',
        '-c:a', CODECS[1],
        '-preset', 'fast',
        '-tune', 'film',
        output_path
    ]
    
    logger.info(f"Combining audio from {audio_path} with video {video_path}")
    # Run the FFmpeg command
    subprocess.run(ffmpeg_command, check=True)
    
    # Verify output file was created
    if os.path.isfile(output_path):
        logger.info(f"Video and audio combined successfully. Output file: {output_path}")
        
        # Delete the original video and audio files
        if os.path.exists(video_path):
            os.remove(video_path)
            logger.info(f"Deleted original video file: {video_path}")
        
        if os.path.exists(audio_path):
            os.remove(audio_path)
            logger.info(f"Deleted audio file: {audio_path}")
        
        return output_path
    else:
        logger.error(f"Output file {output_path} was not created")
        raise Exception(f"Failed to create combined video at {output_path}")

    

def add_subtitles(video_path, subtitle_path, output_path, burn=True, lang_code="en"):
    """
    Add subtitles to a video file using ffmpeg.

    :param video_path: Path to the input video file.
    :param subtitle_path: Path to the subtitle file (e.g., .srt).
    :param output_path: Path where the output video with subtitles will be saved.
    :param burn: Whether to burn subtitles into video or add as separate track
    :param lang_code: Language code for subtitle track
    :return: Path to the output file
    """
    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Created directory: {output_dir}")
    
    if os.path.exists(output_path):
        logger.info("Deleting existing output file " + output_path)
        os.remove(output_path)
    
    # Convert to absolute paths
    video_path = os.path.abspath(video_path)
    subtitle_path = os.path.abspath(subtitle_path)
    output_path = os.path.abspath(output_path)
    
    # FFmpeg command to combine video and subtitle
    ffmpeg_command = [
        'ffmpeg',
        '-i', video_path,
        '-vf', f"subtitles='{subtitle_path}':force_style='Alignment=2'",
        '-crf', '18',
        '-preset', 'fast',
        '-tune', 'film',
        output_path
    ]
    
    if not burn:
        lang_code = iso_639_alpha3(lang_code.replace("a.", ""))
        ffmpeg_command = [
            'ffmpeg',
            '-i', video_path,
            '-i', subtitle_path,
            '-c', 'copy',
            '-c:s', 'mov_text',
            '-metadata:s:s:0', f'language={lang_code}',
            output_path
        ]

    logger.info(f"Adding subtitles from {subtitle_path} to {video_path}... with presets burn={burn} and lang: {lang_code}")
    
    # Run the FFmpeg command
    subprocess.run(ffmpeg_command, check=True)
    
    # Verify output file was created
    if os.path.isfile(output_path):
        logger.info(f"Video and subtitle combined successfully. Output file: {output_path}")
        
        # Delete the original video file
        if os.path.exists(video_path):
            os.remove(video_path)
            logger.info(f"Deleted original video file: {video_path}")
        
        return output_path
    else:
        logger.error(f"Output file {output_path} was not created")
        raise Exception(f"Failed to create subtitled video at {output_path}")

    
