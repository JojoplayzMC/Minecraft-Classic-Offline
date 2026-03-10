import os, json, requests, threading, http.server, socketserver
import webbrowser, platform, time, shutil, zipfile
from pathlib import Path

# --- REMOTE ASSETS ---
HAR_URL = "https://raw.githubusercontent.com/JojoplayzMC/Minecraft-Classic-Offline/refs/heads/main/minecraft.har"
ICON_URL = "https://raw.githubusercontent.com/JojoplayzMC/Minecraft-Classic-Offline/refs/heads/main/icon.png"

# --- CONFIG ---
APP_NAME = "mcclassic"
INSTALL_DIR = Path.home() / "Documents" / APP_NAME
GAME_DIR = INSTALL_DIR / "game_files"
MODS_DIR = INSTALL_DIR / "mods"
BACKUP_DIR = INSTALL_DIR / "backup"
HAR_FILE = INSTALL_DIR / "minecraft.har"
ICON_FILE = INSTALL_DIR / "icon.png"
PORT = 8000

# Ensure directories exist
for d in [INSTALL_DIR, GAME_DIR, MODS_DIR, BACKUP_DIR]:
    os.makedirs(d, exist_ok=True)

def bootstrap():
    """Downloads necessary bootstrap files if missing."""
    print("📦 Checking core files...")
    for url, target in [(HAR_URL, HAR_FILE), (ICON_URL, ICON_FILE)]:
        if not target.exists():
            print(f"⬇️ Downloading bootstrap: {target.name}...")
            r = requests.get(url)
            with open(target, "wb") as f: f.write(r.content)

def create_launcher_icon():
    """Creates OS-specific shortcut pointing to the Documents installation."""
    system = platform.system()
    desktop = Path.home() / "Desktop"
    script_path = INSTALL_DIR / "mcclassic.py"
    
    if system == "Linux":
        launcher_path = desktop / f"{APP_NAME}.desktop"
        if not launcher_path.exists():
            content = f"[Desktop Entry]\nName={APP_NAME}\nExec=python3 \"{script_path}\"\nPath={INSTALL_DIR}\nIcon={ICON_FILE}\nTerminal=true\nType=Application\nCategories=Game;"
            with open(launcher_path, "w") as f: f.write(content)
            os.chmod(launcher_path, 0o755)
    elif system == "Windows":
        launcher_path = desktop / f"{APP_NAME}.bat"
        if not launcher_path.exists():
            with open(launcher_path, "w") as f: 
                f.write(f'@echo off\ncd /d "{INSTALL_DIR}"\npython "{script_path}"\npause')

def apply_mod(zip_path):
    """Extracts mod and backups originals."""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            with zip_ref.open('Manifest.json') as f:
                manifest = json.load(f)
            print(f"🛠️ Applying Mod: {manifest.get('name', 'Unknown')}")
            for mod_file, game_path in manifest['files'].items():
                target = GAME_DIR / game_path.replace("/", os.sep)
                backup = BACKUP_DIR / game_path.replace("/", os.sep)
                if target.exists() and not backup.exists():
                    os.makedirs(backup.parent, exist_ok=True)
                    shutil.copy2(target, backup)
                os.makedirs(target.parent, exist_ok=True)
                with open(target, "wb") as f_out: f_out.write(zip_ref.read(mod_file))
            print("✅ Mod applied!")
    except Exception as e: print(f"❌ Mod Error: {e}")

def restore_originals():
    """Reverts game to vanilla using backup folder."""
    if not BACKUP_DIR.exists(): return
    print("♻️ Restoring vanilla files...")
    for backup_path in BACKUP_DIR.rglob('*'):
        if backup_path.is_file():
            rel_path = backup_path.relative_to(BACKUP_DIR)
            shutil.copy2(backup_path, GAME_DIR / rel_path)
    print("✅ Vanilla restored.")

def download_game_assets():
    """Downloads game files based on the HAR log."""
    with open(HAR_FILE, 'r') as f:
        har_data = json.load(f)
    print("🌍 Syncing game assets (this may take a moment)...")
    for entry in har_data['log']['entries']:
        url = entry['request']['url']
        if "classic.minecraft.net" in url:
            path_part = url.split("classic.minecraft.net")[-1].split('?')[0].lstrip('/')
            if not path_part: path_part = "index.html"
            local_path = GAME_DIR / path_part.replace("/", os.sep)
            if not local_path.exists():
                os.makedirs(local_path.parent, exist_ok=True)
                r = requests.get(url)
                if r.status_code == 200:
                    with open(local_path, 'wb') as f_out: f_out.write(r.content)
    return True

if __name__ == "__main__":
    # 1. Self-Install
    this_script = Path(__file__).resolve()
    target_script = INSTALL_DIR / "mcclassic.py"
    if this_script != target_script:
        shutil.copy2(this_script, target_script)
    
    # 2. Setup Files
    bootstrap()
    create_launcher_icon()
    
    # 3. Mod Menu
    print(f"\n--- {APP_NAME.upper()} LAUNCHER ---")
    print("1. Launch Vanilla")
    print("2. Install Mod (URL)")
    print("3. Reset to Vanilla")
    choice = input("Choice: ")

    if choice == "2":
        url = input("ZIP URL: ")
        r = requests.get(url); zip_p = MODS_DIR / "temp.zip"
        with open(zip_p, "wb") as f: f.write(r.content)
        apply_mod(zip_p)
    elif choice == "3":
        restore_originals()

    # 4. Run Game
    if download_game_assets():
        os.chdir(GAME_DIR)
        threading.Thread(target=lambda: socketserver.TCPServer(("", PORT), http.server.SimpleHTTPRequestHandler).serve_forever(), daemon=True).start()
        print(f"🚀 Running at http://localhost:{PORT}")
        time.sleep(1); webbrowser.open(f"http://localhost:{PORT}")
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
