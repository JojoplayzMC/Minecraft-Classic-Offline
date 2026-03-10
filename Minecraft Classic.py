import os
import json
import requests
import threading
import http.server
import socketserver
import webbrowser
import platform
import time

# --- CONFIG ---
HAR_FILE = 'minecraft.har'
ASSET_DIR = 'game_files'
PORT = 8000
APP_NAME = "Minecraft Classic"
ICON_NAME = "icon.png"  # Assumes icon.png is in the same folder as this script

def create_desktop_shortcut():
    system = platform.system()
    script_path = os.path.abspath(__file__)
    working_dir = os.path.dirname(script_path)
    icon_path = os.path.join(working_dir, ICON_NAME)

    if system == "Linux":
        # GNOME looks in this folder for the app grid
        launcher_dir = os.path.expanduser("~/.local/share/applications")
        os.makedirs(launcher_dir, exist_ok=True)
        
        shortcut_full_path = os.path.join(launcher_dir, f"{APP_NAME.replace(' ', '_')}.desktop")
        
        if os.path.exists(shortcut_full_path):
            print(f"ℹ️ GNOME Launcher icon already exists.")
            return

        content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name={APP_NAME}
Exec=python3 "{script_path}"
Path={working_dir}
Icon={icon_path}
Terminal=true
Categories=Game;
"""
        with open(shortcut_full_path, "w") as f:
            f.write(content)
        os.chmod(shortcut_full_path, 0o755)
        print(f"✅ Added to GNOME Launcher!")


    elif system == "Windows":
        # Windows .bat files don't support custom icons easily, 
        # but the shortcut will work perfectly.
        content = f'@echo off\ncd /d "{working_dir}"\npython "{script_path}"\npause'
        with open(shortcut_full_path, "w") as f:
            f.write(content)

    elif system == "Darwin":
        content = f'#!/bin/zsh\ncd "{working_dir}"\npython3 "{script_path}"'
        with open(shortcut_full_path, "w") as f:
            f.write(content)
        os.chmod(shortcut_full_path, 0o755)
        # Note: Setting icons on Mac via script requires 'sips' or AppleScript, 
        # usually easier to do manually via "Get Info" -> Drag & Drop icon.

    print(f"✅ Shortcut created!")

def download_assets():
    if not os.path.exists(HAR_FILE):
        return False
    
    with open(HAR_FILE, 'r', encoding='utf-8') as f:
        har_data = json.load(f)

    os.makedirs(ASSET_DIR, exist_ok=True)
    
    for entry in har_data['log']['entries']:
        url = entry['request']['url']
        if "classic.minecraft.net" in url:
            # Cross-platform URL to Path conversion
            rel_url = url.split("classic.minecraft.net")[-1].split('?')[0].lstrip('/')
            path_part = rel_url.replace("/", os.sep)
            
            if not path_part: 
                path_part = "index.html"
            
            local_path = os.path.join(os.getcwd(), ASSET_DIR, path_part)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            if not os.path.exists(local_path):
                try:
                    r = requests.get(url, timeout=5)
                    if r.status_code == 200:
                        with open(local_path, 'wb') as f_out:
                            f_out.write(r.content)
                except:
                    pass
    return True

def start_server():
    # Force the server to run from the ASSET_DIR relative to the script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(os.path.join(base_dir, ASSET_DIR))
    
    handler = http.server.SimpleHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        httpd.serve_forever()

if __name__ == "__main__":
    create_desktop_shortcut()
    download_assets()
    
    threading.Thread(target=start_server, daemon=True).start()
    time.sleep(1)
    webbrowser.open(f"http://localhost:{PORT}")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping Server...")
