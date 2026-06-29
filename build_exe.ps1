$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $PSScriptRoot

python -m pip install pyinstaller
python -m PyInstaller `
  --onefile `
  --windowed `
  --name AssistenteJuridico `
  --icon assets/app.ico `
  app.py

$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Assistente Jurídico.lnk"
$targetPath = Join-Path $PSScriptRoot "dist\AssistenteJuridico.exe"

if (Test-Path -LiteralPath $targetPath) {
  $shell = New-Object -ComObject WScript.Shell
  $shortcut = $shell.CreateShortcut($shortcutPath)
  $shortcut.TargetPath = $targetPath
  $shortcut.WorkingDirectory = Split-Path -Parent $targetPath
  $shortcut.IconLocation = "$PSScriptRoot\assets\app.ico"
  $shortcut.Save()
  Write-Host "Atalho criado em: $shortcutPath"
}
