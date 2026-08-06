import os
import shutil
import yt_dlp

class LoggerProxy:
    def __init__(self, log_callback):
        self.log_callback = log_callback

    def debug(self, msg):
        # Ignore excessive progress logs to keep UI logging panel tidy
        if not msg.startswith('[download]') and not msg.startswith('[frag]'):
            self.log_callback(msg)

    def warning(self, msg):
        self.log_callback(f"Warning: {msg}")

    def error(self, msg):
        self.log_callback(f"Error: {msg}")

def download_youtube_media(url, folder, fmt, quality, progress_hook, log_callback):
    """
    Download YouTube streams (video MP4 or audio MP3) utilizing yt-dlp formats matching resolution criteria.
    """
    height = quality.replace("p", "")
    if not height.isdigit():
        height = "720"

    ffmpeg_available = shutil.which("ffmpeg") is not None
    log_callback(f"Checking environment: FFmpeg available = {ffmpeg_available}.")

    ydl_opts = {
        'outtmpl': os.path.join(folder, '%(title)s.%(ext)s'),
        'progress_hooks': [progress_hook],
        'logger': LoggerProxy(log_callback)
    }

    if fmt == "MP3":
        log_callback("Config select: Audio MP3 extract")
        if ffmpeg_available:
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        else:
            log_callback("FFmpeg missing: Downloading audio tracks without conversion.")
            ydl_opts['format'] = 'bestaudio/best'
    else:  # MP4
        log_callback(f"Config select: Video MP4 (Max: {quality})")
        if ffmpeg_available:
            ydl_opts['format'] = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best[height<={height}]/best"
            ydl_opts['merge_output_format'] = 'mp4'
        else:
            log_callback("FFmpeg missing: Downloading pre-merged video format.")
            ydl_opts['format'] = f"best[height<={height}]/best"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
