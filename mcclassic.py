import os, json, requests, threading, http.server, socketserver, webbrowser, platform, time, shutil, zipfile, io
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

# --- CONFIG & GITHUB LINKS ---
GITHUB_USER = "JojoplayzMC"
GITHUB_REPO = "Minecraft-Classic-Offline"
HAR_URL = f"https://raw.githubusercontent.com{GITHUB_USER}/{GITHUB_REPO}/main/minecraft.har"
ICON_URL = f"https://raw.githubusercontent.com{GITHUB_USER}/{GITHUB_REPO}/main/icon.png"
MODS_API = f"https://api.github.com{GITHUB_USER}/{GITHUB_REPO}/contents/Mods"

APP_NAME = "mcclassic"
INSTALL_DIR = Path.home() / "Documents" / APP_NAME
GAME_DIR, MODS_DIR, BACKUP_DIR = INSTALL_DIR/"game_files", INSTALL_DIR/"mods", INSTALL_DIR/"backup"
HAR_FILE, ICON_FILE = INSTALL_DIR/"minecraft.har", INSTALL_DIR/"icon.png"
PORT = 8000

for d in [INSTALL_DIR, GAME_DIR, MODS_DIR, BACKUP_DIR]: os.makedirs(d, exist_ok=True)

class MCLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MC Classic Mod Launcher")
        self.geometry("450x550")
        self.bootstrap()
        self.setup_ui()

    def bootstrap(self):
        """Initial self-install and file fetch."""
        print("📦 Bootstrapping...")
        for url, target in [(HAR_URL, HAR_FILE), (ICON_URL, ICON_FILE)]:
            if not target.exists():
                r = requests.get(url)
                with open(target, "wb") as f: f.write(r.content)
        
        # Self-copy to Documents
        this_script = Path(__file__).resolve()
        if this_script != (INSTALL_DIR / "mcclassic.py"):
            shutil.copy2(this_script, INSTALL_DIR / "mcclassic.py")

    def setup_ui(self):
        # Header
        ttk.Label(self, text="Minecraft Classic Launcher", font=("Arial", 16, "bold")).pack(pady=10)
        
        # Mod List (Scrollable)
        self.canvas = tk.Canvas(self)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = ttk.Frame(self.canvas)
        
        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True, padx=10)
        self.scrollbar.pack(side="right", fill="y")

        # Bottom Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", pady=10)
        ttk.Button(btn_frame, text="🚀 Launch Vanilla", command=self.launch_game).pack(side="left", padx=5, expand=True)
        ttk.Button(btn_frame, text="♻️ Reset Vanilla", command=self.reset_game).pack(side="left", padx=5, expand=True)
        ttk.Button(btn_frame, text="🔗 Install from URL", command=self.prompt_mod_url).pack(side="left", padx=5, expand=True)

        self.refresh_mods()

    def refresh_mods(self):
        """Fetches 'Official' mods from GitHub subfolders."""
        for widget in self.scroll_frame.winfo_children(): widget.destroy()
        try:
            r = requests.get(MODS_API)
            if r.status_code == 200:
                for item in r.json():
                    if item['type'] == 'dir':
                        btn = ttk.Button(self.scroll_frame, text=f"📥 Install: {item['name']}", 
                                         command=lambda u=item['html_url']: self.install_mod(u))
                        btn.pack(fill="x", pady=2)
        except: ttk.Label(self.scroll_frame, text="Offline: Couldn't reach GitHub Mods").pack()

    def install_mod(self, url):
        """Downloads a folder as a ZIP and applies it."""
        print(f"🛠️ Downloading mod from {url}...")
        # GitHub Zipball API converts folders to Zips
        # Format: https://github.com
        # For folders, we rely on the manifest inside the repo zip.
        r = requests.get(f"https://codeload.github.com/{GITHUB_USER}/{GITHUB_REPO}/zip/refs/heads/main")
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            # Logic: Find the Manifest.json inside the specific folder path
            mod_folder_name = url.split('/')[-1]
            mod_root = f"{GITHUB_REPO}-main/Mods/{mod_folder_name}/"
            
            with z.open(f"{mod_root}Manifest.json") as f:
                manifest = json.load(f)
            
            for mod_file, game_path in manifest['files'].items():
                target = GAME_DIR / game_path.replace("/", os.sep)
                backup = BACKUP_DIR / game_path.replace("/", os.sep)
                if target.exists() and not backup.exists():
                    os.makedirs(backup.parent, exist_ok=True)
                    shutil.copy2(target, backup)
                
                os.makedirs(target.parent, exist_ok=True)
                with open(target, "wb") as f_out:
                    f_out.write(z.read(f"{mod_root}{mod_file}"))
        messagebox.showinfo("Success", f"Mod applied! Restarting server...")

    def reset_game(self):
        if BACKUP_DIR.exists():
            for b_file in BACKUP_DIR.rglob('*'):
                if b_file.is_file():
                    rel = b_file.relative_to(BACKUP_DIR)
                    shutil.copy2(b_file, GAME_DIR / rel)
            messagebox.showinfo("Reset", "Back to vanilla!")

    def prompt_mod_url(self):
        # Placeholder for a simple entry dialog
        url = tk.simpledialog.askstring("Mod URL", "Paste GitHub Folder URL:")
        if url: self.install_mod(url)

    def launch_game(self):
        self.download_assets()
        threading.Thread(target=self.run_server, daemon=True).start()
        time.sleep(1)
        webbrowser.open(f"http://localhost:{PORT}")

    def download_assets(self):
        with open(HAR_FILE, 'r') as f: har_data = json.load(f)
        for entry in har_data['log']['entries']:
            url = entry['request']['url']
            if "classic.minecraft.net" in url:
                path = url.split("classic.minecraft.net")[-1].split('?').lstrip('/')
                local = GAME_DIR / (path or "index.html").replace("/", os.sep)
                if not local.exists():
                    os.makedirs(local.parent, exist_ok=True)
                    r = requests.get(url)
                    with open(local, "wb") as f_out: f_out.write(r.content)

    def run_server(self):
        os.chdir(GAME_DIR)
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", PORT), http.server.SimpleHTTPRequestHandler) as httpd:
            httpd.serve_forever()

if __name__ == "__main__":
    app = MCLauncher()
    app.mainloop()
