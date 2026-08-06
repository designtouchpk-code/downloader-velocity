import os
import re
import zipfile
import tempfile
import urllib.request

def download_instagram_carousel(items, folder, zip_it, title, log_callback, progress_callback):
    """
    Download select carousel/story multimedia items from Instagram posts.
    Creates a zip archive or writes files directly based on zip_it boolean flags.
    """
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
    total = len(items)
    
    if zip_it:
        zip_filename = f"{safe_title}_instagram_media.zip"
        zip_path = os.path.join(folder, zip_filename)
        log_callback(f"ZIP compression target active: {zip_path}")
        
        with zipfile.ZipFile(zip_path, 'w') as zip_file:
            with tempfile.TemporaryDirectory() as temp_dir:
                for idx, item in enumerate(items):
                    log_callback(f"Downloading stream {idx+1}/{total}: {item['title']}")
                    
                    ext = ".jpg"
                    if ".mp4" in item['url'].lower():
                        ext = ".mp4"
                        
                    filename = f"media_{idx+1}{ext}"
                    temp_filepath = os.path.join(temp_dir, filename)
                    
                    # Download using urllib
                    req = urllib.request.Request(item['url'], headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req) as resp:
                        with open(temp_filepath, 'wb') as f:
                            f.write(resp.read())
                    
                    zip_file.write(temp_filepath, filename)
                    progress_callback((idx+1)/total, idx+1, total)
        return zip_path
    else:
        log_callback(f"Multiple extraction path active. Saving items separately to {folder}...")
        for idx, item in enumerate(items):
            log_callback(f"Downloading file {idx+1}/{total}...")
            
            ext = ".jpg"
            if ".mp4" in item['url'].lower():
                ext = ".mp4"
                
            filename = f"{safe_title}_slide_{idx+1}{ext}"
            filepath = os.path.join(folder, filename)
            
            req = urllib.request.Request(item['url'], headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as resp:
                with open(filepath, 'wb') as f:
                    f.write(resp.read())
            progress_callback((idx+1)/total, idx+1, total)
        return folder
