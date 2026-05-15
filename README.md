# Omega Game Sandbox

Integrated sandbox for running **Unity and other Windows games** on Linux (Ubuntu) using Wine or Steam Proton. Runs `.exe` files with proper DLL integration and an optional bubblewrap sandbox.

## Features

- **Run Windows .exe games** via Wine or Proton
- **Isolated Wine prefix** so game installs don’t touch your system Wine
- **Optional sandbox** (bubblewrap) for process isolation
- **DLL / runtime setup** via winetricks (vcredist, .NET, etc.)
- **Python API** for launching games and installing deps from code
- **Configurable** prefix, Proton path, and DLL overrides

## Requirements

- **Ubuntu** (or similar Linux)
- **Python 3** with **tkinter** (`python3-tk`)
- **Wine**, **Vulkan**, and 32-bit libs on x86_64 — one command:
  ```bash
  ./scripts/install-system-packages.sh
  ```
  (Enables `i386` multiarch only on amd64; skips 32-bit packages on arm64. See `requirements-system.txt`.)
- **Wine prefix runtimes** (vcredist, etc.): `./scripts/install-deps.sh`
- **bubblewrap** (optional, for sandbox): `sudo apt install bubblewrap`
- **Steam Proton** (optional alternative to system Wine)

## Quick setup

1. **Clone or copy** this project and go into it:
   ```bash
   cd /path/to/Omega
   ```

2. **Copy and edit config** (optional):
   ```bash
   cp config.env.example config.env
   # Edit config.env: set OMEGA_PROTON_PATH or OMEGA_WINE_PATH if needed
   ```

3. **Install runtimes** in the sandbox prefix (recommended for Unity games):
   ```bash
   ./scripts/install-deps.sh
   # Or: python3 -m api.omega_api install-deps
   ```

4. **Run a game**:
   ```bash
   ./omega-launch /path/to/YourGame.exe
   # With arguments:
   ./omega-launch /path/to/Game.exe -- -windowed
   ```

## Configuration (`config.env`)

| Variable | Description |
|----------|-------------|
| `OMEGA_PROTON_PATH` | Path to Proton (e.g. Steam’s `Proton - Experimental/files`) |
| `OMEGA_WINE_PATH` | Path to `wine` binary if not using Proton |
| `OMEGA_PREFIX` | Wine prefix directory (default: `~/.local/share/omega-sandbox/wine-prefix`) |
| `OMEGA_SANDBOX_ENABLED` | `1` = use bubblewrap, `0` = run without sandbox |
| `OMEGA_DLL_OVERRIDES` | Wine-style overrides, e.g. `dll=n` |

If neither Proton nor Wine is set, the script uses `wine` from your `PATH`.

## CLI

**Launcher (bash):**
```bash
./omega-launch <game.exe> [--workdir DIR] [--] [game args...]
```

**Python API CLI:**
```bash
# Launch (blocks until exit)
python3 -m api.omega_api launch /path/to/game.exe

# Launch in background
python3 -m api.omega_api launch /path/to/game.exe --no-wait

# Install runtimes
python3 -m api.omega_api install-deps
python3 -m api.omega_api install-deps vcredist dotnet48

# Show config
python3 -m api.omega_api config
python3 -m api.omega_api config --prefix
```

## Python API

Use from your own code:

```python
from api.omega_api import launch, install_deps, get_config, get_prefix

# Launch and wait
launch("/path/to/game.exe", args=["-windowed"])

# Launch in background
proc = launch("/path/to/game.exe", wait=False)
# ... later: proc.terminate()

# Custom working directory
launch("/path/to/game.exe", workdir="/path/to/game/data")

# Install dependencies
install_deps(["vcredist", "dotnet48"])

# Config
print(get_prefix())
print(get_config())
```

## Installing Proton (Steam)

If you use Steam:

1. Enable Proton in Steam (Steam → Settings → Steam Play).
2. Find Proton in your Steam library folder, e.g.:
   ```text
   ~/.steam/steam/steamapps/common/Proton - Experimental/files
   ```
3. In `config.env` set:
   ```bash
   export OMEGA_PROTON_PATH="$HOME/.steam/steam/steamapps/common/Proton - Experimental/files"
   ```

## Disabling the sandbox

To run without bubblewrap (e.g. for debugging or if you don’t have it):

- In `config.env`: `export OMEGA_SANDBOX_ENABLED=0`
- Or one-off: `OMEGA_SANDBOX_ENABLED=0 ./omega-launch /path/to/game.exe`

## Layout

```text
Omega/
├── README.md
├── config.env.example   # Copy to config.env
├── omega-launch         # Main launcher script
├── requirements.txt
├── api/
│   ├── __init__.py
│   └── omega_api.py     # Python API + CLI
└── scripts/
    ├── common.sh        # Config and runner detection
    ├── run.sh           # Run game (Wine/Proton ± sandbox)
    └── install-deps.sh  # winetricks runtimes
```

## License

Use and modify as you like. Running games may still be subject to the game’s EULA and your local laws.
