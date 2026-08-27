param(
    [string]$StoreIdentityPath = "",
    [string]$ReleaseRoot = "",
    [string]$OutputRoot = ""
)

$ErrorActionPreference = "Stop"
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$desktopRoot = Split-Path -Parent $scriptRoot
$workspaceRoot = Split-Path -Parent $desktopRoot

if (-not $ReleaseRoot) {
    $ReleaseRoot = Join-Path $desktopRoot "release-1.0.3-r3\SamsAccountingDesktop"
}
if (-not (Test-Path -LiteralPath (Join-Path $ReleaseRoot "SamsAccountingDesktop.exe"))) {
    throw "Release payload is missing: $ReleaseRoot"
}

$buildId = Get-Date -Format "yyyyMMdd-HHmmss"
if (-not $OutputRoot) {
    $OutputRoot = Join-Path $desktopRoot "msix-output\build-$buildId"
}
if (Test-Path -LiteralPath $OutputRoot) {
    throw "Refusing to overwrite an existing MSIX output: $OutputRoot"
}

$stagingRoot = Join-Path $OutputRoot "staging"
$assetsRoot = Join-Path $stagingRoot "Assets"
$verifyRoot = Join-Path $OutputRoot "verified-unpack"
$packagePath = Join-Path $OutputRoot "SamsAccountingDesktop-1.0.3-x64.msix"
New-Item -ItemType Directory -Path $assetsRoot -Force | Out-Null
Copy-Item -Path (Join-Path $ReleaseRoot "*") -Destination $stagingRoot -Recurse -Force

$identity = [ordered]@{
    identity_name = "SamsAccountingDesktop.Dev"
    publisher = "CN=Sams Accounting Desktop Development"
    publisher_display_name = "The Jishu IT Solution"
    version = "1.0.3.0"
}
if ($StoreIdentityPath) {
    if (-not (Test-Path -LiteralPath $StoreIdentityPath)) {
        throw "Store identity file does not exist: $StoreIdentityPath"
    }
    $provided = Get-Content -LiteralPath $StoreIdentityPath -Raw | ConvertFrom-Json
    foreach ($field in @("identity_name", "publisher", "publisher_display_name", "version")) {
        $value = [string]$provided.$field
        if (-not $value -or $value.StartsWith("REPLACE_")) {
            throw "Store identity field is not ready: $field"
        }
        $identity[$field] = $value
    }
}

$manifestTemplate = Get-Content -LiteralPath (Join-Path $scriptRoot "Package.Store.template.appxmanifest") -Raw
$manifest = $manifestTemplate.Replace("{{IDENTITY_NAME}}", $identity.identity_name)
$manifest = $manifest.Replace("{{PUBLISHER}}", $identity.publisher)
$manifest = $manifest.Replace("{{PUBLISHER_DISPLAY_NAME}}", $identity.publisher_display_name)
$manifest = $manifest.Replace("{{VERSION}}", $identity.version)
$manifestPath = Join-Path $stagingRoot "AppxManifest.xml"
[System.IO.File]::WriteAllText($manifestPath, $manifest, [System.Text.UTF8Encoding]::new($false))

Add-Type -AssemblyName System.Drawing
$logoPath = Join-Path $workspaceRoot "site\assets\logo.jpeg"
if (-not (Test-Path -LiteralPath $logoPath)) {
    throw "Logo asset is missing: $logoPath"
}

function Write-LogoAsset {
    param(
        [string]$Path,
        [int]$Width,
        [int]$Height,
        [System.Drawing.Color]$Background
    )
    $canvas = [System.Drawing.Bitmap]::new($Width, $Height)
    $graphics = [System.Drawing.Graphics]::FromImage($canvas)
    $source = [System.Drawing.Image]::FromFile($logoPath)
    try {
        $graphics.Clear($Background)
        $graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
        $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
        $margin = [Math]::Max(2, [int]([Math]::Min($Width, $Height) * 0.08))
        $availableWidth = $Width - (2 * $margin)
        $availableHeight = $Height - (2 * $margin)
        $ratio = [Math]::Min($availableWidth / $source.Width, $availableHeight / $source.Height)
        $drawWidth = [int]($source.Width * $ratio)
        $drawHeight = [int]($source.Height * $ratio)
        $x = [int](($Width - $drawWidth) / 2)
        $y = [int](($Height - $drawHeight) / 2)
        $graphics.DrawImage($source, $x, $y, $drawWidth, $drawHeight)
        $canvas.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    }
    finally {
        $source.Dispose()
        $graphics.Dispose()
        $canvas.Dispose()
    }
}

$white = [System.Drawing.Color]::White
$navy = [System.Drawing.Color]::FromArgb(12, 22, 38)
Write-LogoAsset (Join-Path $assetsRoot "StoreLogo.png") 50 50 $white
Write-LogoAsset (Join-Path $assetsRoot "Square44x44Logo.png") 44 44 $white
Write-LogoAsset (Join-Path $assetsRoot "Square150x150Logo.png") 150 150 $white
Write-LogoAsset (Join-Path $assetsRoot "Square310x310Logo.png") 310 310 $white
Write-LogoAsset (Join-Path $assetsRoot "Wide310x150Logo.png") 310 150 $navy

$sdkBin = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64"
$makeAppx = Join-Path $sdkBin "makeappx.exe"
if (-not (Test-Path -LiteralPath $makeAppx)) {
    throw "MakeAppx is missing: $makeAppx"
}

& $makeAppx pack /d $stagingRoot /p $packagePath
if ($LASTEXITCODE -ne 0) {
    throw "MakeAppx packaging failed with exit code $LASTEXITCODE"
}
New-Item -ItemType Directory -Path $verifyRoot | Out-Null
& $makeAppx unpack /p $packagePath /d $verifyRoot
if ($LASTEXITCODE -ne 0) {
    throw "MakeAppx verification unpack failed with exit code $LASTEXITCODE"
}

$packedManifest = [xml](Get-Content -LiteralPath (Join-Path $verifyRoot "AppxManifest.xml") -Raw)
$payloadFiles = Get-ChildItem -LiteralPath $verifyRoot -Recurse -File
$sha256 = (Get-FileHash -LiteralPath $packagePath -Algorithm SHA256).Hash
$result = [ordered]@{
    package = $packagePath
    sha256 = $sha256
    bytes = (Get-Item -LiteralPath $packagePath).Length
    identity_name = $packedManifest.Package.Identity.Name
    publisher = $packedManifest.Package.Identity.Publisher
    version = $packedManifest.Package.Identity.Version
    architecture = $packedManifest.Package.Identity.ProcessorArchitecture
    payload_files = @($payloadFiles).Count
    executable_present = Test-Path -LiteralPath (Join-Path $verifyRoot "SamsAccountingDesktop.exe")
    public_key_present = Test-Path -LiteralPath (Join-Path $verifyRoot "_internal\sams_accounting_desktop\assets\license-public.pem")
    store_identity_supplied = [bool]$StoreIdentityPath
}
$result | ConvertTo-Json -Depth 4
