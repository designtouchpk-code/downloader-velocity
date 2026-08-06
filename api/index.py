import os
import re
import io
import base64
import urllib.request
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import yt_dlp

app = FastAPI(title="Velocity API")

# Allow CORS for local debug states
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    url: str
    category: str = "📹 Video/Audio Only"

def get_thumbnail_base64(url: str) -> str:
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = response.read()
            mime = "image/jpeg"
            if ".png" in url.lower():
                mime = "image/png"
            elif ".webp" in url.lower():
                mime = "image/webp"
            encoded = base64.b64encode(data).decode('utf-8')
            return f"data:{mime};base64,{encoded}"
    except Exception as e:
        print(f"Error base64 encoding thumbnail: {e}")
        return None

@app.post("/api/analyze")
async def analyze_url(req_data: AnalyzeRequest):
    url = req_data.url.strip()
    category = req_data.category
    
    if not url:
        raise HTTPException(status_code=400, detail="URL cannot be empty")

    # Instagram username normalization
    if category == "👤 Profile Pic" and not url.startswith("http"):
        username = url.lstrip("@").strip()
        url = f"https://www.instagram.com/{username}/"

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': 'in_playlist',
        'skip_download': True,
        'check_formats': False,
        'youtube_include_dash_manifest': False,
        'youtube_include_hls_manifest': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as extract_err:
        if "instagram.com" in url or "instagram" in category.lower():
            info = {
                'title': "Instagram Media Asset",
                'uploader': "instagram.com",
                'duration': None,
                'thumbnail': None
            }
        else:
            raise HTTPException(status_code=400, detail=str(extract_err))

    title = info.get('title', 'Unknown Title')
    channel = info.get('uploader') or info.get('uploader_id') or info.get('webpage_url_domain', 'Generic')
    
    duration = info.get('duration')
    if duration:
        mins, secs = divmod(duration, 60)
        hours, mins = divmod(mins, 60)
        duration_str = f"{hours}h {mins}m {secs}s" if hours else f"{mins}m {secs}s"
    else:
        duration_str = "Unknown"

    thumbnail_url = info.get('thumbnail')
    thumbnail_base64 = get_thumbnail_base64(thumbnail_url)

    # Collect entries (for playlist/stories/carousels)
    is_playlist = 'entries' in info or '_type' in info and info['_type'] == 'playlist'
    entries = []
    if is_playlist:
        raw_entries = info.get('entries', [])
        for idx, entry in enumerate(raw_entries):
            if entry:
                url_entry = entry.get('url') or entry.get('thumbnail')
                if url_entry:
                    entries.append({
                        'index': idx + 1,
                        'url': url_entry,
                        'title': entry.get('title') or f"Slide #{idx+1}"
                    })

    return {
        "title": title,
        "channel": channel,
        "duration": duration_str,
        "thumbnail": thumbnail_base64,
        "entries": entries,
        "original_url": url
    }

@app.get("/api/download")
async def download_media(url: str, format: str = "MP4", quality: str = "720p"):
    if not url:
        raise HTTPException(status_code=400, detail="Missing URL parameter")

    # If it is a generic image/thumbnail URL, proxy directly
    if not ("youtube.com" in url or "youtu.be" in url or "instagram.com" in url):
        # Treat as direct file proxying
        try:
            async def direct_stream():
                async with httpx.AsyncClient(timeout=None) as client:
                    async with client.stream("GET", url, headers={'User-Agent': 'Mozilla/5.0'}) as r:
                        r.raise_for_status()
                        async for chunk in r.iter_bytes(chunk_size=16384):
                            yield chunk
            filename = "downloaded_file"
            if "cover" in url or "thumb" in url:
                filename = "cover_thumbnail.jpg"
            return StreamingResponse(
                direct_stream(),
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Content-Type": "application/octet-stream"
                }
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Proxy error: {str(e)}")

    # Otherwise, resolve through yt-dlp
    height = quality.replace("p", "") if quality.isdigit() else "720"
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }
    
    if "youtube.com" in url or "youtu.be" in url:
        if format == "MP3":
            ydl_opts['format'] = 'bestaudio/best'
        else:
            # Force pre-merged format selection for serverless compatibility without ffmpeg
            ydl_opts['format'] = f"best[height<={height}]/best"
    else:
        # Instagram downloads
        ydl_opts['format'] = 'best'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Locate stream URL
            stream_url = None
            if 'url' in info:
                stream_url = info['url']
            elif 'formats' in info and len(info['formats']) > 0:
                # Fallback to the last available format
                stream_url = info['formats'][-1]['url']
                
            if not stream_url:
                raise HTTPException(status_code=400, detail="Failed to locate downloadable media stream URL")

            title = info.get('title', 'download')
            safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
            ext = "mp3" if format == "MP3" else info.get('ext', 'mp4')
            filename = f"{safe_title}.{ext}"

            async def file_streamer():
                async with httpx.AsyncClient(timeout=None) as client:
                    async with client.stream("GET", stream_url) as r:
                        r.raise_for_status()
                        async for chunk in r.iter_bytes(chunk_size=16384):
                            yield chunk

            return StreamingResponse(
                file_streamer(),
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Content-Type": "application/octet-stream"
                }
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

from fastapi.responses import HTMLResponse, FileResponse

@app.get("/", response_class=HTMLResponse)
async def read_index():
    for path in ["index.html", "../index.html", "api/../index.html"]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    return "<h3>Velocity UI Error: index.html not found.</h3>"

@app.get("/styles.css")
async def read_css():
    for path in ["styles.css", "../styles.css", "api/../styles.css"]:
        if os.path.exists(path):
            return FileResponse(path, media_type="text/css")
    raise HTTPException(status_code=404, detail="styles.css not found")

@app.get("/app.js")
async def read_js():
    for path in ["app.js", "../app.js", "api/../app.js"]:
        if os.path.exists(path):
            return FileResponse(path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="app.js not found")
