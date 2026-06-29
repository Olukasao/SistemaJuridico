#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

python3 -m pip install -r requirements.txt
python3 -m pip install pyinstaller

ICON_ARGS=()
if [ -f "assets/app.icns" ]; then
  ICON_ARGS=(--icon "assets/app.icns")
fi

python3 -m PyInstaller \
  --windowed \
  --name AssistenteJuridico \
  "${ICON_ARGS[@]}" \
  app.py

if [ -d "$HOME/Desktop" ] && [ -d "dist/AssistenteJuridico.app" ]; then
  rm -rf "$HOME/Desktop/AssistenteJuridico.app"
  cp -R "dist/AssistenteJuridico.app" "$HOME/Desktop/AssistenteJuridico.app"
  echo "App copiado para: $HOME/Desktop/AssistenteJuridico.app"
fi

echo "Build macOS concluido em: dist/AssistenteJuridico.app"
