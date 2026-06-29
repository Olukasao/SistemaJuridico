#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

python3 -m pip install -r requirements.txt
python3 -m pip install pyinstaller

PYINSTALLER_ARGS=(
  --noconfirm
  --clean
  --windowed
  --name AssistenteJuridico
  --osx-bundle-identifier br.com.assistentejuridico.thays
  --add-data "prompts:prompts"
)

if [ -f "assets/app.icns" ]; then
  PYINSTALLER_ARGS+=(--icon "assets/app.icns")
fi

python3 -m PyInstaller "${PYINSTALLER_ARGS[@]}" app.py

if [ -d "dist/AssistenteJuridico.app" ]; then
  chmod +x "dist/AssistenteJuridico.app/Contents/MacOS/AssistenteJuridico"
  xattr -cr "dist/AssistenteJuridico.app" || true
  codesign --force --deep --sign - "dist/AssistenteJuridico.app" || true
fi

if [ -d "$HOME/Desktop" ] && [ -d "dist/AssistenteJuridico.app" ]; then
  rm -rf "$HOME/Desktop/AssistenteJuridico.app"
  cp -R "dist/AssistenteJuridico.app" "$HOME/Desktop/AssistenteJuridico.app"
  xattr -cr "$HOME/Desktop/AssistenteJuridico.app" || true
  echo "App copiado para: $HOME/Desktop/AssistenteJuridico.app"
fi

echo "Build macOS concluido em: dist/AssistenteJuridico.app"
