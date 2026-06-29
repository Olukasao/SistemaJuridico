#!/usr/bin/env bash
set -euo pipefail

APP_PATH="${1:-$HOME/Desktop/AssistenteJuridico.app}"
EXEC_PATH="$APP_PATH/Contents/MacOS/AssistenteJuridico"

if [ ! -d "$APP_PATH" ]; then
  echo "App nao encontrado em: $APP_PATH"
  echo "Uso: ./fix_mac_app.sh /caminho/para/AssistenteJuridico.app"
  exit 1
fi

if [ ! -f "$EXEC_PATH" ]; then
  echo "Executavel interno nao encontrado em: $EXEC_PATH"
  exit 1
fi

chmod +x "$EXEC_PATH"
xattr -cr "$APP_PATH" || true
codesign --force --deep --sign - "$APP_PATH" || true

echo "Reparo concluido: $APP_PATH"
open "$APP_PATH"
