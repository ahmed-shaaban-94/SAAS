# Assets

Place the following icon files here:

- `icon.ico` — Windows app icon (256x256, multi-resolution ICO)
- `icon.png` — General icon (512x512 PNG)
- `tray.png` — System tray icon (16x16 or 32x32 PNG, transparent background)

Generate from the DataPulse logo using:
```bash
# From a 512x512 source PNG:
convert icon-512.png -resize 256x256 icon.ico
convert icon-512.png -resize 16x16 tray.png
```
