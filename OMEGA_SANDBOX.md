# Omega Gaming Sandbox (`omega_sandbox.py`)

Run Windows games on Linux in **isolated Wine sandboxes**. Each sandbox has its own Wine prefix, so installs and DLLs do not touch your system Wine. Use the **GUI** for everyday play, or the **CLI** for scripting.

---

## What you need

| Requirement | Notes |
|-------------|--------|
| **Linux** (Ubuntu / Debian recommended) | Tested workflow below |
| **Python 3.8+** | 3.10+ recommended |
| **python3-tk** | GUI (`sudo apt install python3-tk`) |
| **Wine + 32-bit + Vulkan** | One-shot install (see below) |

### Install system packages

From the Omega project folder:

```bash
./scripts/install-system-packages.sh
```

On **x86_64**, this enables `i386` multiarch and installs Wine, `wine32`, winetricks, Vulkan drivers, and related libraries. On **arm64**, 32-bit packages are skipped automatically.

Optional: install common Windows runtimes into a prefix (vcredist, etc.) with `./scripts/install-deps.sh` — that targets the main Omega API prefix; sandboxes created by `omega_sandbox.py` use their own prefixes under `~/.omega_sandboxes/`.

---

## Start the app

```bash
cd /path/to/Omega
python3 omega_sandbox.py
# or explicitly:
python3 omega_sandbox.py gui
```

---

## Typical workflow (GUI)

### 1. Create a sandbox

Open **Manage Sandboxes** → **Create Sandbox** → enter a name (e.g. `space`, `rpg`, `fps`).

Each sandbox is a separate Wine prefix at:

`~/.omega_sandboxes/<name>/`

### 2. Install a game

1. Select the sandbox in the list.
2. Click **Install Game**.
3. Pick the **installer** `.exe` (dialog starts in **Downloads** by default).
4. Complete the Windows installer inside Wine.

### 3. Register the game (library)

After install, you are asked to add the game to your library. If you skip that step:

1. Select the sandbox → **Register game EXE**.
2. Choose the **installed** game executable, **not** the installer in Downloads.

**Correct path** (example):

`~/.omega_sandboxes/space/drive_c/Program Files (x86)/GameTop.com/YourGame/Game.exe`

**Wrong path** (runs setup again):

`~/Downloads/Setup.exe`

The file picker opens under **Program Files (x86)** when possible. After you register once, it remembers that folder for that sandbox.

### 4. Play

- **Game Library** tab → select game → **PLAY SELECTED GAME** (or double-click).
- **Manage Sandboxes** → select sandbox → **Play game** or **Quick Play**.

Playing only **starts** the registered `.exe`; it does **not** change your library entry.

---

## GUI reference

### Game Library tab

| Action | Description |
|--------|-------------|
| List | All sandboxes that have a **registered** installed game |
| **PLAY SELECTED GAME** | Launches the registered exe for that entry |
| Double-click | Same as Play |

### Manage Sandboxes tab

| Button | Description |
|--------|-------------|
| **Create Sandbox** | New isolated Wine prefix |
| **Delete Sandbox** | Removes prefix, library entry, and Omega desktop shortcuts |
| **Install Game** | Runs an installer `.exe` in the selected sandbox |
| **Register game EXE** | Adds the **installed** game to the library (and optional shortcut) |
| **Play game** | Starts the registered exe for the selected sandbox |
| **View Logs** | Opens `sandbox.log` for that sandbox |

### Options (bottom of Manage tab)

| Option | Description |
|--------|-------------|
| **Create Desktop Shortcut** | When registering, add a launcher under `~/.local/share/applications/` |
| **Virtual Desktop** | e.g. `1920x1080` — runs the game inside a Wine virtual desktop (helps some fullscreen games) |

If the registered exe is **outside** the sandbox folder (e.g. still pointing at Downloads), Play warns you before launching.

---

## Command line

```bash
python3 omega_sandbox.py <command> [options]
```

| Command | Description |
|---------|-------------|
| `gui` | Open the GUI (default if no command) |
| `create <name>` | Create sandbox |
| `list` | List sandbox names |
| `delete <name>` | Delete sandbox and its shortcuts |
| `install <name> <installer.exe>` | Run installer in sandbox |
| `register <name> <game.exe>` | Add installed game to library |
| `launch <name> <game.exe>` | Run exe (does **not** register) |

### Examples

```bash
# New sandbox
python3 omega_sandbox.py create space

# Run installer
python3 omega_sandbox.py install space ~/Downloads/MyGameSetup.exe

# Register installed game (use path inside drive_c)
python3 omega_sandbox.py register space \
  "$HOME/.omega_sandboxes/space/drive_c/Program Files (x86)/MyGame/game.exe" \
  --game-name "My Game" --shortcut

# Play once without touching the library
python3 omega_sandbox.py launch space \
  "$HOME/.omega_sandboxes/space/drive_c/Program Files (x86)/MyGame/game.exe"

# Virtual desktop
python3 omega_sandbox.py launch space /path/to/game.exe --virtual-desktop 1920x1080

# List / delete
python3 omega_sandbox.py list
python3 omega_sandbox.py delete space
```

---

## Where files live

| Path | Purpose |
|------|---------|
| `~/.omega_sandboxes/<name>/` | Wine prefix for sandbox `<name>` |
| `~/.omega_sandboxes/<name>/drive_c/` | Windows C: drive (Program Files, etc.) |
| `~/.omega_sandboxes/<name>/sandbox.log` | Wine stdout/stderr for that sandbox |
| `~/.omega_sandboxes/games_config.json` | Registered games (exe path, display name, last browse folder) |
| `~/.local/share/applications/omega_<sandbox>_*.desktop` | Desktop shortcuts created by Omega |

---

## Install vs register vs launch

| Step | What it does |
|------|----------------|
| **Install** | Runs the **installer** `.exe` once inside the sandbox |
| **Register** | Saves the **installed game** `.exe` to your library (for Play / shortcuts) |
| **Launch / Play** | Starts the **game** `.exe` only |

**Register** = “this is my installed game.”  
**Launch / Play** = “run it now.”

---

## Troubleshooting

### Setup / installer opens when I click Play

The library points at the **installer** (often in Downloads), not the copy under `drive_c`.

1. **Register game EXE** again.
2. Pick the exe under  
   `~/.omega_sandboxes/<sandbox>/drive_c/Program Files` or `Program Files (x86)`.

### Game does not start / black screen

1. **View Logs** → check `sandbox.log`.
2. Try **Virtual Desktop** `1920x1080` in options.
3. Ensure Vulkan and 32-bit Wine are installed: `./scripts/install-system-packages.sh`.
4. Some games need extra runtimes; install them inside that sandbox with winetricks (manual; prefix is `WINEPREFIX=~/.omega_sandboxes/<name>`).

### GUI does not open

```bash
sudo apt install python3-tk
python3 -c "import tkinter"
```

### `wine` not found

Install Wine via `./scripts/install-system-packages.sh` or your distro’s packages.

---

## Python dependencies

`omega_sandbox.py` uses only the Python standard library. No `pip` packages are required.

```bash
pip install -r requirements.txt   # documents deps; nothing to install via pip
```

System packages: see `requirements-system.txt` and `./scripts/install-system-packages.sh`.

---

## Related

- Main Omega project (Proton API, `config.env`, bubblewrap): see [README.md](README.md).
