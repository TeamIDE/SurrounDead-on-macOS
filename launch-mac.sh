#!/bin/bash
# Launch SurrounDead (Windows/DX12) on macOS via GPTK 3.0 + D3DMetal 3.0
# Works on M-series Macs running macOS 15 Sequoia+

# Replace the UUID below with your Whisky bottle UUID, or use ~/surround-prefix if you didn't use Whisky
export WINEPREFIX="$HOME/Library/Containers/com.franke.Whisky/Bottles/YOUR-BOTTLE-UUID"
export WINE="/Applications/Game Porting Toolkit.app/Contents/Resources/wine/bin/wine64"
export WINEDEBUG=-all
export ROSETTA_ADVERTISE_AVX=1

"$WINE" "$HOME/SurrounDead/SurrounDead.exe" --in-process-gpu
