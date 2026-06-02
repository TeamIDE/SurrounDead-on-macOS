#!/bin/bash
set -e

# SurrounDead on macOS — automated setup
# Run this after mounting both GPTK DMGs from developer.apple.com/games:
#   - Game Porting Toolkit 3.0
#   - Evaluation environment for Windows games 3.0
#
# Usage: ./setup.sh <steam-username> [bottle-uuid]
#
# If no bottle UUID is provided, a fresh Wine prefix is created at ~/surround-prefix

STEAM_USER="${1:-}"
BOTTLE_UUID="${2:-}"
GAME_DIR="$HOME/SurrounDead"
GPTK_WINE="/Applications/Game Porting Toolkit.app/Contents/Resources/wine/bin/wine64"
EVAL_VOL="/Volumes/Evaluation environment for Windows games 3.0"

# ── helpers ──────────────────────────────────────────────────────────────────

print() { echo "[setup] $*"; }
die()   { echo "[error] $*" >&2; exit 1; }

require_mounted() {
    [ -d "$EVAL_VOL" ] || die "Mount 'Evaluation environment for Windows games 3.0.dmg' first (from developer.apple.com/games)"
}

# ── Step 1: Rosetta 2 ─────────────────────────────────────────────────────────

print "Checking Rosetta 2..."
if ! arch -x86_64 true 2>/dev/null; then
    print "Installing Rosetta 2..."
    softwareupdate --install-rosetta --agree-to-license
fi
print "Rosetta 2 OK"

# ── Step 2: Homebrew ──────────────────────────────────────────────────────────

print "Checking Homebrew..."
if ! command -v brew &>/dev/null; then
    print "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
print "Homebrew OK"

# ── Step 3: SteamCMD ─────────────────────────────────────────────────────────

print "Checking SteamCMD..."
if ! command -v steamcmd &>/dev/null; then
    print "Installing SteamCMD..."
    brew install steamcmd
fi
print "SteamCMD OK"

# ── Step 4: GPTK Wine cask ───────────────────────────────────────────────────

print "Checking Game Porting Toolkit..."
if [ ! -f "$GPTK_WINE" ]; then
    # Remove conflicting wine installs
    brew uninstall wine@staging 2>/dev/null || true
    brew uninstall --cask wine-staging 2>/dev/null || true

    print "Installing Game Porting Toolkit cask..."
    brew install --cask gcenx/wine/game-porting-toolkit
fi
print "GPTK Wine OK"

# ── Step 5: D3DMetal 3.0 ─────────────────────────────────────────────────────

require_mounted
WINELIB="/Applications/Game Porting Toolkit.app/Contents/Resources/wine/lib"

print "Installing D3DMetal 3.0..."
# Back up existing external if present and not already backed up
[ -d "$WINELIB/external" ] && [ ! -d "$WINELIB/external.old" ] && mv "$WINELIB/external" "$WINELIB/external.old"

# Install D3DMetal 3.0 framework
ditto "$EVAL_VOL/redist/lib/external/" "$WINELIB/external/"

# Update Windows-side DLLs (d3d12, dxgi, d3d11, etc.)
ditto "$EVAL_VOL/redist/lib/wine/x86_64-windows/" "$WINELIB/wine/x86_64-windows/"
print "D3DMetal 3.0 OK"

# ── Step 6: Wine prefix ───────────────────────────────────────────────────────

if [ -n "$BOTTLE_UUID" ]; then
    WINEPREFIX="$HOME/Library/Containers/com.franke.Whisky/Bottles/$BOTTLE_UUID"
    [ -d "$WINEPREFIX" ] || die "Bottle not found: $WINEPREFIX"
    print "Using Whisky bottle: $BOTTLE_UUID"
else
    WINEPREFIX="$HOME/surround-prefix"
    if [ ! -d "$WINEPREFIX" ]; then
        print "Creating Wine prefix at $WINEPREFIX..."
        WINEPREFIX="$WINEPREFIX" "$GPTK_WINE" wineboot --init
    fi
    print "Wine prefix OK: $WINEPREFIX"
fi

# ── Step 7: Engine.ini render overrides ──────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SAVE_DIR="$WINEPREFIX/drive_c/users/$USER/AppData/Local/SurrounDead/Saved/Config/Windows"
mkdir -p "$SAVE_DIR"

if [ -f "$SCRIPT_DIR/Engine.ini" ]; then
    cp "$SCRIPT_DIR/Engine.ini" "$SAVE_DIR/Engine.ini"
    print "Engine.ini installed"
else
    print "Warning: Engine.ini not found in repo, skipping"
fi

# ── Step 8: Download game files ───────────────────────────────────────────────

mkdir -p "$GAME_DIR"

if [ ! -f "$GAME_DIR/SurrounDead.exe" ]; then
    if [ -z "$STEAM_USER" ]; then
        print "Skipping game download — no Steam username provided."
        print "Run manually:"
        print "  steamcmd +@sSteamCmdForcePlatformType windows +login YOUR_USERNAME +force_install_dir $GAME_DIR +app_update 1645820 validate +quit"
    else
        print "Downloading SurrounDead (~3GB)..."
        steamcmd \
            +@sSteamCmdForcePlatformType windows \
            +login "$STEAM_USER" \
            +force_install_dir "$GAME_DIR" \
            +app_update 1645820 validate \
            +quit
    fi
else
    print "Game files already present"
fi

# ── Step 9: Write launch script ───────────────────────────────────────────────

LAUNCH="$GAME_DIR/launch-mac.sh"
cat > "$LAUNCH" <<EOF
#!/bin/bash
export WINEPREFIX="$WINEPREFIX"
export WINE="$GPTK_WINE"
export WINEDEBUG=-all
export ROSETTA_ADVERTISE_AVX=1

"\$WINE" "$GAME_DIR/SurrounDead.exe" --in-process-gpu
EOF
chmod +x "$LAUNCH"
print "Launch script written to $LAUNCH"

# ── Done ──────────────────────────────────────────────────────────────────────

echo ""
echo "Setup complete. To play:"
echo "  $LAUNCH"
echo ""
echo "When the AMD driver warning appears, click No."
