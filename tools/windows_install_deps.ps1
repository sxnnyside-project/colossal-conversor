# Installs Colossal Conversor's external conversion tools on Windows via
# winget (preferred) or Chocolatey (used only if already present).
# Safe to re-run: skips anything already resolvable on PATH.
$ErrorActionPreference = "Stop"

function Test-CommandExists($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

$wingetAvailable = Test-CommandExists "winget"
$chocoAvailable = Test-CommandExists "choco"

if (-not $wingetAvailable -and -not $chocoAvailable) {
    Write-Error "Neither winget nor Chocolatey is available. Install winget (bundled with modern Windows / App Installer) or Chocolatey (https://chocolatey.org), then re-run this script."
    exit 1
}

if ($wingetAvailable) {
    Write-Host "Using winget."
    $tools = @(
        @{ Name = "ffmpeg"; WingetId = "Gyan.FFmpeg" },
        @{ Name = "soffice"; WingetId = "TheDocumentFoundation.LibreOffice" },
        @{ Name = "pdftoppm"; WingetId = "oschwartz10612.Poppler" },
        @{ Name = "pandoc"; WingetId = "JohnMacFarlane.Pandoc" },
        @{ Name = "magick"; WingetId = "ImageMagick.ImageMagick" }
    )
} else {
    Write-Host "winget not found; using Chocolatey."
    $tools = @(
        @{ Name = "ffmpeg"; ChocoId = "ffmpeg" },
        @{ Name = "soffice"; ChocoId = "libreoffice-fresh" },
        @{ Name = "pdftoppm"; ChocoId = "poppler" },
        @{ Name = "pandoc"; ChocoId = "pandoc" },
        @{ Name = "magick"; ChocoId = "imagemagick" }
    )
}

$failures = 0
foreach ($tool in $tools) {
    $name = $tool.Name

    if (Test-CommandExists $name) {
        Write-Host "OK  $name already available, skipping"
        continue
    }

    if ($wingetAvailable) {
        $id = $tool.WingetId
        Write-Host "Installing $id (for $name)..."
        winget install --id $id --silent --accept-package-agreements --accept-source-agreements
    } else {
        $id = $tool.ChocoId
        Write-Host "Installing $id (for $name)..."
        choco install $id -y
    }

    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Failed to install $name"
        $failures++
        continue
    }

    if (Test-CommandExists $name) {
        Write-Host "OK  $name installed successfully"
    } else {
        Write-Warning "$name installed but is not yet on PATH — you may need to open a new terminal"
    }
}

if ($failures -gt 0) {
    Write-Error "$failures tool(s) failed to install. See messages above."
    exit 1
}

Write-Host "All dependencies available."
