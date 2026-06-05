# SurrounDead on macOS — Working Setup Guide

Run the Windows-only UE5/DX12 game SurrounDead (Steam App ID 1645820) on an Apple Silicon Mac using only free tools. **Confirmed working on M4 MacBook Air, macOS 15 Sequoia.**

## What This Uses

| Layer | Tool | Source |
|---|---|---|
| x86 translation | Rosetta 2 | Built into macOS |
| Windows compat | Wine (GPTK build) | GCenX Homebrew cask |
| DX12 → Metal | D3DMetal 3.0 | Apple GPTK 3.0 DMG |
| Game files | SteamCMD | Valve |

**Key insight:** UE5 games go black because the CombineLUTs shader uses geometry shaders. D3DMetal 2.0 (bundled in Whisky) can't handle them. D3DMetal 3.0 (GPTK 3.0) fixes this. Everything else is free and open.

---

## Step 1 — Prerequisites

```bash
# Install Rosetta 2 (needed for x86 Wine)
softwareupdate --install-rosetta --agree-to-license

# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install SteamCMD
brew install steamcmd
```

---

## Step 2 — Download Game Files

```bash
mkdir ~/SurrounDead
steamcmd +@sSteamCmdForcePlatformType windows \
         +login YOUR_STEAM_USERNAME \
         +force_install_dir ~/SurrounDead \
         +app_update 1645820 validate \
         +quit
```

Replace `YOUR_STEAM_USERNAME` with your Steam account. It will prompt for your password and Steam Guard code. The download is ~3GB.

For the **experimental** branch (v0.8+, newer content), add `-beta experimental` before `validate`:
```bash
steamcmd +@sSteamCmdForcePlatformType windows \
         +login YOUR_STEAM_USERNAME \
         +force_install_dir ~/SurrounDead \
         +app_update 1645820 -beta experimental validate \
         +quit
```

---

## Step 3 — Get GPTK 3.0 (D3DMetal 3.0)

**Part A — Download from Apple (free account required):**
1. Go to `developer.apple.com/games` in Safari
2. Sign in with your Apple ID
3. Download **Evaluation environment for Windows games 3.0** (this is the only DMG you need)
4. Double-click the DMG to mount it

**Part B — Install the GCenX GPTK Wine cask:**
```bash
brew install --cask gcenx/wine/game-porting-toolkit
```
This installs `/Applications/Game Porting Toolkit.app` with a Wine build that supports D3DMetal.

**Part C — Update to D3DMetal 3.0 from the mounted DMG:**
```bash
WINELIB="/Applications/Game Porting Toolkit.app/Contents/Resources/wine/lib"

# Back up originals
mv "$WINELIB/external" "$WINELIB/external.old" 2>/dev/null

# Install D3DMetal 3.0 framework
ditto "/Volumes/Evaluation environment for Windows games 3.0/redist/lib/external/" "$WINELIB/external/"

# Copy new Windows-side DLLs (d3d12.dll, dxgi.dll, etc.)
ditto "/Volumes/Evaluation environment for Windows games 3.0/redist/lib/wine/x86_64-windows/" "$WINELIB/wine/x86_64-windows/"
```

---

## Step 4 — Create a Wine Prefix

Install Whisky (free) to create and manage the Wine prefix. Download from: `https://github.com/Whisky-App/Whisky`

Or create a prefix manually:
```bash
WINEPREFIX=~/surround-prefix /Applications/Game\ Porting\ Toolkit.app/Contents/Resources/wine/bin/wine64 wineboot --init
```

If using Whisky, note your bottle's UUID from:
`~/Library/Containers/com.franke.Whisky/Bottles/<UUID>/`

---

## Step 4b — Install VC++ 2015-2022 Redist (v0.8+ requires it)

The experimental branch ships a VC++ runtime dependency that v0.7 didn't have. Install the bundled installer into your prefix:

```bash
WINEPREFIX="$HOME/Library/Containers/com.franke.Whisky/Bottles/<YOUR-BOTTLE-UUID>" \
  /Applications/Game\ Porting\ Toolkit.app/Contents/Resources/wine/bin/wine64 \
  ~/SurrounDead/_CommonRedist/vcredist/2022/VC_redist.x64.exe /quiet /norestart
```

Without this, v0.8+ will pop a "Microsoft Visual C++ 2015-2022 Redistributable (x64) required" dialog on launch.

---

## Step 5 — Configure UE5 Render Settings

Copy `Engine.ini` from this repo to your Wine prefix:

```bash
BOTTLE="$HOME/Library/Containers/com.franke.Whisky/Bottles/<YOUR-BOTTLE-UUID>"
SAVEDIR="$BOTTLE/drive_c/users/$USER/AppData/Local/SurrounDead/Saved/Config/Windows"
mkdir -p "$SAVEDIR"
cp Engine.ini "$SAVEDIR/Engine.ini"
```

These settings disable features D3DMetal can't handle (Nanite, Lumen, ray tracing) and the geometry-shader-based tonemapper that caused the black world.

---

## Step 6 — Launch

Copy `launch-mac.sh` from this repo and edit the `WINEPREFIX` path to match your bottle UUID:

```bash
cp launch-mac.sh ~/SurrounDead/launch-mac.sh
chmod +x ~/SurrounDead/launch-mac.sh
# Edit WINEPREFIX in the script to point to your bottle
~/SurrounDead/launch-mac.sh
```

When the AMD driver warning appears, click **No** — this is just the game seeing a spoofed GPU, it still runs fine.

---

## Step 7 — Steam Launch (Optional)

`setup.sh` generates a `SurrounDead.app` bundle in `~/SurrounDead/`. Adding it to Steam lets you launch the game (with controller support) directly from your library.

1. In Steam: **Games → Add a Non-Steam Game**
2. Click **Browse** and select `~/SurrounDead/SurrounDead.app`
3. Click **Add Selected Programs**

On first launch macOS will ask for **Accessibility** and **Bluetooth** permissions for python3 — grant both. You only need to do this once.

---

## Step 8 — PS4 Controller (Optional)

SurrounDead's in-game controller binding doesn't work under Wine. Use the included `controller.py` script instead — it reads the DS4 directly via HID and maps inputs to keyboard/mouse.

**Install dependencies:**
```bash
brew install hidapi
pip3 install hid pynput pyobjc-framework-Quartz
```

**Grant permissions** (one-time, macOS will prompt):
- System Settings → Privacy & Security → Accessibility → add Terminal (or Python)
- System Settings → Privacy & Security → Bluetooth → add Terminal (or Python)

**Connect controller:** pair via Bluetooth (hold PS + Share until light flashes). USB cable is charge-only on Mac.

**Run alongside the game:**
```bash
DYLD_LIBRARY_PATH=/opt/homebrew/lib python3 ~/SurrounDead/controller.py &
```

**Button layout:**

| Button | Action |
|---|---|
| Left stick | WASD movement |
| D-pad | WASD movement |
| Right stick | Mouse (camera) |
| Cross (X) | F |
| Circle | Space |
| Square | J |
| Triangle | Tab |
| L1 (hold) | Left Shift |
| L1 (double-tap) | Left Ctrl |
| L2 | Z |
| R1 | Right-click |
| R2 | Left-click |
| L3 | Left Ctrl |
| R3 | V |
| Options | Esc |
| Share | Enter |

---

## Troubleshooting

**Black screen / black world:**
- Verify `Engine.ini` is in the right path and has the `[SystemSettings]` section
- Make sure D3DMetal 3.0 is installed (check `external/D3DMetal.framework` exists in GPTK app)

**"A D3D11-compatible GPU is required" error:**
- You're using the wrong Wine binary. Use `/Applications/Game Porting Toolkit.app/Contents/Resources/wine/bin/wine64`, not Homebrew's `wine` or `wine64`

**Game won't download with SteamCMD:**
- Make sure to include `+@sSteamCmdForcePlatformType windows` — without it SteamCMD won't find the Windows depot on macOS

**"Microsoft Visual C++ 2015-2022 Redistributable (x64) required" on launch:**
- v0.8+ depends on it; v0.7 did not. Install the bundled redist into your prefix (see Step 4b).

**Whisky Sparkle updater crash loop:**
```bash
defaults write com.franke.Whisky SUEnableAutomaticChecks -bool false
defaults write com.franke.Whisky SUAutomaticallyUpdate -bool false
defaults write com.franke.Whisky SUHasLaunchedBefore -bool true
defaults write com.franke.Whisky SULastCheckTime "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

---

## Dead Ends (Don't Repeat These)

- **VKD3D-Proton** — Requires `VK_EXT_transform_feedback` which MoltenVK doesn't support on macOS. Won't work.
- **Wine upstream VKD3D** — Can't match DXGI adapter LUID to Vulkan device on macOS. Won't work.
- **DXMT** — Only handles D3D11. SurrounDead uses DX12. Won't work.
- **`-dx11` launch flag** — Forces fully black screen with no artifacts. Worse than default.
- **DXVK + MoltenVK** — Same problem as VKD3D-Proton, missing Metal Vulkan extensions.

The only working path for UE5 DX12 games on macOS is **D3DMetal 3.0 via GPTK 3.0**.
