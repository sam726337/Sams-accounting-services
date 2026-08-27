[CmdletBinding()]
param(
    [string]$LogoPath = (Join-Path $PSScriptRoot "..\..\site\assets\logo.jpeg"),
    [string]$OutputDirectory = (Join-Path $PSScriptRoot "store-assets")
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

function New-ListingArtwork {
    param(
        [Parameter(Mandatory)] [string]$OutputPath,
        [Parameter(Mandatory)] [int]$Width,
        [Parameter(Mandatory)] [int]$Height
    )

    if (Test-Path -LiteralPath $OutputPath) {
        throw "Refusing to overwrite existing artwork: $OutputPath"
    }

    $bitmap = [System.Drawing.Bitmap]::new($Width, $Height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit

    try {
        $background = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(8, 21, 39))
        $accent = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(14, 128, 119))
        $white = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::White)
        $muted = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(195, 217, 226))
        $graphics.FillRectangle($background, 0, 0, $Width, $Height)

        $accentHeight = [Math]::Max(18, [int]($Height * 0.018))
        $graphics.FillRectangle($accent, 0, $Height - $accentHeight, $Width, $accentHeight)

        $logo = [System.Drawing.Image]::FromFile((Resolve-Path -LiteralPath $LogoPath))
        try {
            $logoSize = [int]([Math]::Min($Width * 0.34, $Height * 0.25))
            $logoX = [int](($Width - $logoSize) / 2)
            $logoY = [int]($Height * 0.16)
            $graphics.FillRectangle($white, $logoX, $logoY, $logoSize, $logoSize)
            $graphics.DrawImage($logo, $logoX, $logoY, $logoSize, $logoSize)
        }
        finally {
            $logo.Dispose()
        }

        $titleSize = [Math]::Max(42, [int]($Width * 0.064))
        $subtitleSize = [Math]::Max(24, [int]($Width * 0.029))
        $titleFont = [System.Drawing.Font]::new("Segoe UI Semibold", $titleSize, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
        $subtitleFont = [System.Drawing.Font]::new("Segoe UI", $subtitleSize, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
        $center = [System.Drawing.StringFormat]::new()
        $center.Alignment = [System.Drawing.StringAlignment]::Center
        $center.LineAlignment = [System.Drawing.StringAlignment]::Center

        try {
            $titleY = [int]($Height * 0.49)
            $titleRect = [System.Drawing.RectangleF]::new(40, $titleY, $Width - 80, [int]($Height * 0.12))
            $graphics.DrawString("Sams Accounting", $titleFont, $white, $titleRect, $center)

            $subtitleY = [int]($Height * 0.62)
            $subtitleRect = [System.Drawing.RectangleF]::new([int]($Width * 0.10), $subtitleY, [int]($Width * 0.80), [int]($Height * 0.18))
            $graphics.DrawString("Review-ready workflows for Tally Prime", $subtitleFont, $muted, $subtitleRect, $center)
        }
        finally {
            $center.Dispose()
            $subtitleFont.Dispose()
            $titleFont.Dispose()
        }

        $bitmap.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
    }
    finally {
        if ($background) { $background.Dispose() }
        if ($accent) { $accent.Dispose() }
        if ($white) { $white.Dispose() }
        if ($muted) { $muted.Dispose() }
        $graphics.Dispose()
        $bitmap.Dispose()
    }
}

New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
New-ListingArtwork -OutputPath (Join-Path $OutputDirectory "Store-Box-Art-1080x1080.png") -Width 1080 -Height 1080
New-ListingArtwork -OutputPath (Join-Path $OutputDirectory "Store-Poster-1440x2160.png") -Width 1440 -Height 2160

Get-ChildItem -LiteralPath $OutputDirectory -Filter "Store-*.png" | Select-Object FullName, Length
