#!/bin/bash
# Launch SurrounDead (Windows/DX12) on macOS via GPTK 3.0 + D3DMetal 3.0
# Works on M-series Macs running macOS 15 Sequoia+

export WINEPREFIX="$HOME/Library/Containers/com.franke.Whisky/Bottles/23EDD227-500C-4714-9194-931C529E6F53"
export WINE="/Applications/Game Porting Toolkit.app/Contents/Resources/wine/bin/wine64"
export WINEDEBUG=-all
export ROSETTA_ADVERTISE_AVX=1

"$WINE" "$HOME/SurrounDead/SurrounDead.exe" --in-process-gpu
