import os
import subprocess
import shutil
import argparse
import sys
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

class OmegaSandbox:
    def __init__(self):
        self.base_dir = Path.home() / ".omega_sandboxes"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.desktop_dir = Path.home() / ".local" / "share" / "applications"
        self.desktop_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.base_dir / "games_config.json"
        self.games_config = self._load_config()

    def _load_config(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_config(self):
        with open(self.config_file, "w") as f:
            json.dump(self.games_config, f, indent=4)

    def register_game(self, sandbox_name, exe_path, game_name=None):
        if not game_name:
            game_name = Path(exe_path).stem
        try:
            exe_resolved = str(Path(exe_path).expanduser().resolve())
        except OSError:
            exe_resolved = str(exe_path)
        entry = dict(self.games_config.get(sandbox_name) or {})
        entry["exe_path"] = exe_resolved
        entry["game_name"] = game_name
        try:
            entry["last_register_dir"] = str(Path(exe_resolved).parent.resolve())
        except OSError:
            pass
        self.games_config[sandbox_name] = entry
        self._save_config()

    @staticmethod
    def install_dialog_initialdir():
        """Avoid starting in the app's cwd (e.g. project clone); prefer Downloads then home."""
        home = Path.home()
        downloads = home / "Downloads"
        if downloads.is_dir():
            return str(downloads.resolve())
        return str(home.resolve())

    def get_registered_game(self, sandbox_name):
        return self.games_config.get(sandbox_name)

    def get_sandbox_path(self, name):
        return self.base_dir / name

    def exe_inside_wine_prefix(self, sandbox_name, exe_path):
        """True if the executable path lives under this sandbox (e.g. …/drive_c/Program Files/…)."""
        try:
            prefix = self.get_sandbox_path(sandbox_name).resolve()
            exe = Path(exe_path).expanduser().resolve()
            exe.relative_to(prefix)
            return True
        except (ValueError, OSError):
            return False

    def register_dialog_initialdir(self, sandbox_name):
        """Open near installed games: last folder used for this sandbox, else game folder, else Program Files (x86)."""
        cfg = self.games_config.get(sandbox_name) or {}
        last = cfg.get("last_register_dir")
        if last:
            try:
                lp = Path(last).expanduser().resolve()
                if lp.is_dir():
                    return str(lp)
            except OSError:
                pass

        exe = cfg.get("exe_path")
        if exe and self.exe_inside_wine_prefix(sandbox_name, exe):
            try:
                parent = Path(exe).expanduser().resolve().parent
                if parent.is_dir():
                    return str(parent)
            except OSError:
                pass

        drive = self.get_sandbox_path(sandbox_name) / "drive_c"
        # (x86) first — typical for installers like GameTop, GOG, older 32-bit games
        for sub in (
            drive / "Program Files (x86)",
            drive / "Program Files",
            drive / "Program Files (Arm)",
            drive,
        ):
            if sub.is_dir():
                return str(sub.resolve())
        return str(self.get_sandbox_path(sandbox_name).resolve())

    def run_wine(self, sandbox_name, cmd_args, wait=True, virtual_desktop=None, cwd=None):
        sandbox_path = self.get_sandbox_path(sandbox_name)
        if not sandbox_path.exists():
            print(f"Error: Sandbox '{sandbox_name}' does not exist.")
            return False

        env = os.environ.copy()
        env["WINEPREFIX"] = str(sandbox_path.absolute())
        env["WINEDEBUG"] = "-all" 

        log_file_path = sandbox_path / "sandbox.log"

        if cwd is None and cmd_args:
            p0 = Path(cmd_args[0])
            if p0.exists() and p0.is_file():
                cwd = str(p0.parent.resolve())
        
        try:
            print(f"[*] Running in sandbox '{sandbox_name}': {' '.join(cmd_args)}")
            
            final_args = ["wine"]
            if virtual_desktop:
                final_args += ["explorer", f"/desktop=Omega,{virtual_desktop}"]
            
            final_args += cmd_args
            
            # Open log file in append mode. We don't use 'with' here for async processes
            # to ensure the file handle stays valid for the child process.
            log_file = open(log_file_path, "a")
            log_file.write(f"\n--- New Run: {' '.join(cmd_args)} ---\n")
            log_file.flush()

            process = subprocess.Popen(
                final_args, 
                env=env, 
                cwd=cwd,
                stdout=log_file, 
                stderr=log_file,
                start_new_session=True # Detach from terminal
            )

            if wait:
                process.wait()
                log_file.close()
            else:
                # For async, we let the process keep the handle until it exits
                print(f"[*] Game launched asynchronously. Logs: {log_file_path}")
                
            return True
        except Exception as e:
            print(f"Error running wine: {e}")
            return False

    def create(self, name):
        sandbox_path = self.get_sandbox_path(name)
        if sandbox_path.exists():
            print(f"Error: Sandbox '{name}' already exists.")
            return False

        print(f"[*] Creating sandbox '{name}' at {sandbox_path}...")
        sandbox_path.mkdir(parents=True)
        
        env = os.environ.copy()
        env["WINEPREFIX"] = str(sandbox_path.absolute())
        env["WINEDEBUG"] = "-all"
        
        print("[*] Initializing Wine prefix (this may take a moment)...")
        subprocess.run(["wineboot", "--init"], env=env, capture_output=True)
        
        subprocess.run(["wine", "reg", "add", "HKEY_CURRENT_USER\\Software\\Wine\\WineDbg", "/v", "ShowCrashDialog", "/t", "REG_DWORD", "/d", "0", "/f"], env=env, capture_output=True)
        
        print(f"[+] Sandbox '{name}' created successfully.")
        return True

    def install(self, name, installer_path):
        installer_path = Path(installer_path).absolute()
        if not installer_path.exists():
            print(f"Error: Installer not found at {installer_path}")
            return False

        return self.run_wine(name, [str(installer_path)])

    def create_desktop_shortcut(self, sandbox_name, game_name, exe_path, virtual_desktop=None):
        shortcut_path = self.desktop_dir / f"omega_{sandbox_name}_{game_name.replace(' ', '_')}.desktop"
        
        script_path = os.path.abspath(__file__)
        exec_cmd = f"python3 {script_path} launch {sandbox_name} \"{exe_path}\""
        if virtual_desktop:
            exec_cmd += f" --virtual-desktop {virtual_desktop}"

        content = f"""[Desktop Entry]
Name={game_name} (Omega Sandbox: {sandbox_name})
Exec={exec_cmd}
Type=Application
Categories=Game;
Terminal=false
Icon=game-controller
"""
        with open(shortcut_path, "w") as f:
            f.write(content)
        
        os.chmod(shortcut_path, 0o755)
        print(f"[+] Desktop shortcut created at {shortcut_path}")

    def launch(self, name, exe_path, create_shortcut=False, game_name=None, virtual_desktop=None):
        """Start the game executable in the sandbox. Does not modify the library."""
        p = Path(exe_path)
        if p.exists():
            exe_path = str(p.absolute())

        if create_shortcut:
            if not game_name:
                game_name = p.stem
            self.create_desktop_shortcut(name, game_name, exe_path, virtual_desktop)

        return self.run_wine(name, [exe_path], wait=False, virtual_desktop=virtual_desktop)

    def list_sandboxes(self):
        return [d.name for d in self.base_dir.iterdir() if d.is_dir()]

    def delete(self, name):
        sandbox_path = self.get_sandbox_path(name)
        if not sandbox_path.exists():
            print(f"Error: Sandbox '{name}' does not exist.")
            return False

        print(f"[*] Deleting sandbox '{name}'...")
        shutil.rmtree(sandbox_path)
        
        # Remove registration
        if name in self.games_config:
            del self.games_config[name]
            self._save_config()

        for shortcut in self.desktop_dir.glob(f"omega_{name}_*.desktop"):
            shortcut.unlink()
            
        print(f"[+] Sandbox '{name}' and associated shortcuts deleted.")
        return True

class OmegaSandboxGUI:
    def __init__(self, root, sandbox_mgr):
        self.root = root
        self.mgr = sandbox_mgr
        self.root.title("Omega Gaming Sandbox")
        self.root.geometry("700x550")
        
        self.setup_ui()
        self.refresh_all()

    def setup_ui(self):
        # Use Notebook for Tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Tab 1: Game Library ---
        self.library_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.library_frame, text=" 🎮 Game Library ")

        lib_label = ttk.Label(self.library_frame, text="Your Installed Games", font=("Helvetica", 14, "bold"))
        lib_label.pack(anchor=tk.W, pady=(0, 10))

        lib_list_frame = ttk.Frame(self.library_frame)
        lib_list_frame.pack(fill=tk.BOTH, expand=True)

        self.library_listbox = tk.Listbox(lib_list_frame, font=("Helvetica", 11), selectmode=tk.SINGLE, exportselection=False)
        self.library_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.library_listbox.bind("<Double-1>", lambda e: self.on_library_play())

        lib_scrollbar = ttk.Scrollbar(lib_list_frame, orient=tk.VERTICAL, command=self.library_listbox.yview)
        lib_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.library_listbox.config(yscrollcommand=lib_scrollbar.set)

        lib_btn_frame = ttk.Frame(self.library_frame, padding="10")
        lib_btn_frame.pack(fill=tk.X)

        self.lib_play_btn = ttk.Button(lib_btn_frame, text="PLAY SELECTED GAME", command=self.on_library_play, style="Accent.TButton")
        self.lib_play_btn.pack(fill=tk.X, ipady=10)

        # --- Tab 2: Sandbox Management ---
        self.manage_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.manage_frame, text=" ⚙️ Manage Sandboxes ")

        # Main layout for Management
        main_frame = self.manage_frame

        # Sandbox List
        list_label = ttk.Label(main_frame, text="Available Sandboxes:", font=("Helvetica", 12, "bold"))
        list_label.pack(anchor=tk.W, pady=(0, 5))

        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.listbox = tk.Listbox(
            list_frame,
            font=("Helvetica", 10),
            exportselection=False,
            selectmode=tk.BROWSE,
        )
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.listbox.bind("<<ListboxSelect>>", self.on_select_sandbox)
        # <<ListboxSelect>> does not fire when clicking the already-selected row;
        # sync details after the pointer release once Tk has applied the selection.
        self.listbox.bind("<ButtonRelease-1>", self._on_sandbox_list_pointer_up)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=scrollbar.set)

        # Buttons Frame
        btn_frame = ttk.Frame(main_frame, padding="10")
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="Create Sandbox", command=self.on_create).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ttk.Button(btn_frame, text="Delete Sandbox", command=self.on_delete).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(btn_frame, text="Install Game", command=self.on_install).grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        ttk.Button(btn_frame, text="Register game EXE", command=self.on_register_game).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(btn_frame, text="Play game", command=self.on_play).grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        ttk.Button(btn_frame, text="View Logs", command=self.on_view_logs).grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)

        # Options Frame
        opt_frame = ttk.LabelFrame(main_frame, text="Sandbox Options & Quick Play", padding="10")
        opt_frame.pack(fill=tk.X, pady=10)

        self.game_info_label = ttk.Label(opt_frame, text="No game registered for this sandbox.", font=("Helvetica", 10, "italic"))
        self.game_info_label.pack(anchor=tk.W, pady=(0, 5))

        self.quick_play_btn = ttk.Button(opt_frame, text="Quick Play", command=self.on_quick_play, state=tk.DISABLED)
        self.quick_play_btn.pack(fill=tk.X, pady=(0, 10))

        self.shortcut_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt_frame, text="Create Desktop Shortcut", variable=self.shortcut_var).pack(anchor=tk.W)

        vdesktop_frame = ttk.Frame(opt_frame)
        vdesktop_frame.pack(fill=tk.X, pady=5)
        ttk.Label(vdesktop_frame, text="Virtual Desktop (e.g. 1920x1080):").pack(side=tk.LEFT)
        self.vdesktop_entry = ttk.Entry(vdesktop_frame)
        self.vdesktop_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

    def refresh_all(self):
        self.refresh_list()
        self.refresh_library()

    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        for s in self.mgr.list_sandboxes():
            self.listbox.insert(tk.END, s)
        self.on_select_sandbox(None)

    def refresh_library(self):
        self.library_listbox.delete(0, tk.END)
        self.library_data = [] # Store (sandbox_name, game_data) pairs
        
        for sandbox_name, game_data in self.mgr.games_config.items():
            display_text = f"{game_data['game_name']}  [Sandbox: {sandbox_name}]"
            self.library_listbox.insert(tk.END, display_text)
            self.library_data.append((sandbox_name, game_data))

    def on_library_play(self):
        selection = self.library_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a game from the library.")
            return
        
        sandbox_name, game_data = self.library_data[selection[0]]
        exe_path = game_data["exe_path"]
        if not self._confirm_launch_exe(sandbox_name, exe_path):
            return
        vdesktop = self.vdesktop_entry.get().strip() or None

        if self.mgr.launch(sandbox_name, exe_path, create_shortcut=False, virtual_desktop=vdesktop):
            messagebox.showinfo("Info", f"Starting {game_data['game_name']}...")
        else:
            messagebox.showerror("Error", "Could not start the game. Check sandbox.log in the sandbox folder.")

    def _on_sandbox_list_pointer_up(self, event):
        self.root.after_idle(lambda: self.on_select_sandbox(None))

    def on_select_sandbox(self, event):
        name = self.get_selected(quiet=True)
        if not name:
            self.game_info_label.config(text="Select a sandbox to see details.")
            self.quick_play_btn.config(state=tk.DISABLED, text="Quick Play")
            return

        game = self.mgr.get_registered_game(name)
        if game:
            self.game_info_label.config(text=f"Registered Game: {game['game_name']}", font=("Helvetica", 10, "bold"))
            self.quick_play_btn.config(state=tk.NORMAL, text=f"Play {game['game_name']}")
        else:
            self.game_info_label.config(text="No game registered. After installing, use Register game EXE and pick the game's .exe under this sandbox's drive_c/Program Files.", font=("Helvetica", 10, "italic"))
            self.quick_play_btn.config(state=tk.DISABLED, text="Quick Play")

    def get_selected(self, quiet=False):
        selection = self.listbox.curselection()
        if not selection:
            if not quiet:
                messagebox.showwarning("Warning", "Please select a sandbox first.")
            return None
        return self.listbox.get(selection[0])

    def on_create(self):
        name = simpledialog.askstring("Create Sandbox", "Enter sandbox name:")
        if name:
            if self.mgr.create(name):
                self.refresh_all()
                messagebox.showinfo("Success", f"Sandbox '{name}' created.")
            else:
                messagebox.showerror("Error", f"Failed to create sandbox '{name}'. It might already exist.")

    def on_delete(self):
        name = self.get_selected()
        if name:
            if messagebox.askyesno("Confirm", f"Are you sure you want to delete sandbox '{name}'?"):
                if self.mgr.delete(name):
                    self.refresh_all()
                    messagebox.showinfo("Success", f"Sandbox '{name}' deleted.")

    def on_install(self):
        name = self.get_selected()
        if name:
            path = filedialog.askopenfilename(
                initialdir=OmegaSandbox.install_dialog_initialdir(),
                title="Select Installer",
                filetypes=[("Executables", "*.exe"), ("All Files", "*.*")],
            )
            if path:
                messagebox.showinfo("Info", "Installation starting. Please follow the installer prompts.")
                ok = self.mgr.install(name, path)
                if ok and messagebox.askyesno(
                    "Add to library",
                    "Add the installed game's main executable to your library now? (You can also do this later with Register game EXE.)",
                ):
                    self._register_installed_exe_dialog(name)

    def _confirm_launch_exe(self, sandbox_name, exe_path):
        if self.mgr.exe_inside_wine_prefix(sandbox_name, exe_path):
            return True
        prefix = self.mgr.get_sandbox_path(sandbox_name)
        return messagebox.askyesno(
            "Registered file is outside the sandbox",
            "This game is registered to a .exe that is not inside this sandbox's Wine folder:\n\n"
            f"{prefix}\n\n"
            "That usually means the original installer (for example in Downloads). Playing it runs setup again, not the copy you installed into the sandbox.\n\n"
            "Use “Register game EXE” and pick the game's main .exe under drive_c → Program Files (or Program Files (x86)).\n\n"
            "Launch this path anyway?",
        )

    def _register_installed_exe_dialog(self, sandbox_name):
        initial = self.mgr.register_dialog_initialdir(sandbox_name)
        path = filedialog.askopenfilename(
            initialdir=initial,
            title="Select the installed game's main EXE (under drive_c/Program Files, not your installer download)",
            filetypes=[("Executables", "*.exe"), ("All Files", "*.*")],
        )
        if not path:
            return
        p = Path(path)
        suggested = p.stem
        game_name = simpledialog.askstring("Game name", "Display name in library:", initialvalue=suggested)
        if game_name is None:
            return
        game_name = game_name.strip() or suggested
        self.mgr.register_game(sandbox_name, str(p.resolve()), game_name)
        if not self.mgr.exe_inside_wine_prefix(sandbox_name, str(p.resolve())):
            messagebox.showwarning(
                "Outside sandbox",
                "The file you chose is not inside this sandbox's Wine folder. "
                "Play will run that exact file (often your downloaded installer), not the copy installed in the prefix.\n\n"
                "For the installed game, choose the .exe under drive_c → Program Files (or Program Files (x86)).",
            )
        if self.shortcut_var.get():
            vdesktop = self.vdesktop_entry.get().strip() or None
            self.mgr.create_desktop_shortcut(sandbox_name, game_name, str(p.resolve()), vdesktop)
        self.refresh_all()
        messagebox.showinfo("Success", f"Registered '{game_name}' in your library.")

    def on_register_game(self):
        name = self.get_selected()
        if name:
            self._register_installed_exe_dialog(name)

    def on_play(self):
        name = self.get_selected()
        if not name:
            return
        game = self.mgr.get_registered_game(name)
        if not game:
            messagebox.showwarning(
                "No game registered",
                "This sandbox has no registered game executable. Use Register game EXE after installation, or add it when prompted after install.",
            )
            return
        exe_path = game["exe_path"]
        if not self._confirm_launch_exe(name, exe_path):
            return
        vdesktop = self.vdesktop_entry.get().strip() or None
        if self.mgr.launch(name, exe_path, create_shortcut=False, virtual_desktop=vdesktop):
            messagebox.showinfo("Info", f"Starting {game['game_name']}...")
        else:
            messagebox.showerror("Error", "Could not start the game. Check sandbox.log in the sandbox folder.")

    def on_quick_play(self):
        name = self.get_selected()
        if name:
            game = self.mgr.get_registered_game(name)
            if game:
                exe_path = game["exe_path"]
                if not self._confirm_launch_exe(name, exe_path):
                    return
                vdesktop = self.vdesktop_entry.get().strip() or None
                if self.mgr.launch(name, exe_path, create_shortcut=False, virtual_desktop=vdesktop):
                    messagebox.showinfo("Info", f"Starting {game['game_name']}...")
                else:
                    messagebox.showerror("Error", "Could not start the game. Check sandbox.log in the sandbox folder.")

    def on_view_logs(self):
        name = self.get_selected()
        if name:
            log_path = self.mgr.get_sandbox_path(name) / "sandbox.log"
            if log_path.exists():
                # Open with the default system application (usually a text editor)
                if sys.platform == "linux":
                    subprocess.Popen(["xdg-open", str(log_path)])
                else:
                    os.startfile(str(log_path))
            else:
                messagebox.showinfo("Info", "No logs found for this sandbox yet.")

def main():
    parser = argparse.ArgumentParser(description="Omega Gaming Sandbox for Ubuntu")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Create
    create_parser = subparsers.add_parser("create", help="Create a new sandbox")
    create_parser.add_argument("name", help="Name of the sandbox")

    # Install
    install_parser = subparsers.add_parser("install", help="Install a game in a sandbox")
    install_parser.add_argument("name", help="Name of the sandbox")
    install_parser.add_argument("path", help="Path to the installer .exe")

    # Launch
    launch_parser = subparsers.add_parser("launch", help="Run a game .exe in the sandbox (does not change library)")
    launch_parser.add_argument("name", help="Name of the sandbox")
    launch_parser.add_argument("path", help="Path to the game .exe")
    launch_parser.add_argument("--shortcut", action="store_true", help="Create a desktop shortcut")
    launch_parser.add_argument("--game-name", help="Name for the shortcut (optional)")
    launch_parser.add_argument("--virtual-desktop", help="Launch in a virtual desktop (e.g. 1920x1080)")

    # Register (library entry for installed game)
    reg_parser = subparsers.add_parser("register", help="Register an installed game EXE for this sandbox")
    reg_parser.add_argument("name", help="Name of the sandbox")
    reg_parser.add_argument("path", help="Path to the installed game .exe")
    reg_parser.add_argument("--game-name", help="Display name (default: exe stem)")
    reg_parser.add_argument("--shortcut", action="store_true", help="Create a desktop shortcut")
    reg_parser.add_argument("--virtual-desktop", help="Virtual desktop size for shortcut launches (e.g. 1920x1080)")

    # List
    subparsers.add_parser("list", help="List all sandboxes")

    # Delete
    delete_parser = subparsers.add_parser("delete", help="Delete a sandbox")
    delete_parser.add_argument("name", help="Name of the sandbox")

    # GUI
    subparsers.add_parser("gui", help="Launch the GUI (default if no command given)")

    args = parser.parse_args()
    sandbox = OmegaSandbox()

    if args.command == "create":
        sandbox.create(args.name)
    elif args.command == "install":
        sandbox.install(args.name, args.path)
    elif args.command == "launch":
        sandbox.launch(args.name, args.path, create_shortcut=args.shortcut, game_name=args.game_name, virtual_desktop=args.virtual_desktop)
    elif args.command == "register":
        p = Path(args.path).resolve()
        sandbox.register_game(args.name, str(p), args.game_name)
        if args.shortcut:
            gn = args.game_name or p.stem
            sandbox.create_desktop_shortcut(args.name, gn, str(p), args.virtual_desktop)
    elif args.command == "list":
        for s in sandbox.list_sandboxes():
            print(f" - {s}")
    elif args.command == "delete":
        sandbox.delete(args.name)
    elif args.command == "gui" or args.command is None:
        root = tk.Tk()
        gui = OmegaSandboxGUI(root, sandbox)
        root.mainloop()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
