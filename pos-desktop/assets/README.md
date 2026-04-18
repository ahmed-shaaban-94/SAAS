# Assets

Place the following icon files here:

- `icon.ico` — Windows app icon (256x256, multi-resolution ICO)
- `icon.png` — General icon (512x512 PNG)
- `tray.png` — System tray icon (16x16 or 32x32 PNG, transparent background)

NSIS installer branding images (required for signed/published builds):
- `nsis-header.bmp` — Installer header banner (468×60 px, 24-bit BMP)
- `nsis-sidebar.bmp` — Installer sidebar image (164×314 px, 24-bit BMP)

Generate from the DataPulse logo using:
```bash
# From a 512x512 source PNG:
convert icon-512.png -resize 256x256 icon.ico
convert icon-512.png -resize 16x16 tray.png
# NSIS images (ImageMagick):
convert logo.png -resize 468x60 -background white -flatten nsis-header.bmp
convert logo.png -resize 164x314 -background "#1a1a2e" -flatten nsis-sidebar.bmp
```

If nsis-header.bmp and nsis-sidebar.bmp are absent, remove `installerHeader`
and `installerSidebar` from electron-builder.yml to use the NSIS default UI.
