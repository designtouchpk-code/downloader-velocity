import uvicorn
import socket
import sys
import os

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == "__main__":
    local_ip = get_local_ip()
    print("=" * 60)
    print("          VELOCITY WEB SERVER - PORTABLE PORTAL")
    print("=" * 60)
    print(f" * Localhost access:       http://localhost:8000")
    print(f" * Local Wi-Fi (Phone):    http://{local_ip}:8000")
    print("=" * 60)
    print(" Starting Uvicorn backend... Press Ctrl+C to terminate.")
    print("=" * 60)
    
    # Ensure api folder is in python path
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    uvicorn.run("api.index:app", host="0.0.0.0", port=8000, reload=False, log_level="info")
