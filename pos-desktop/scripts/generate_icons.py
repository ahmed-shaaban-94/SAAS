"""Regenerate placeholder POS desktop icons from brand primitives.

Run once to regenerate `pos-desktop/assets/icon.ico`, `icon.png`, `tray.png`.

Design primitives (placeholder-level — swap for branded artwork before GA):
  - Outer: rounded-rectangle navy (#0A1F3A)
  - Inner: teal disk (#00C7B7) with subtle radial lift
  - Mark: white "DP" wordmark, bold, centered
  - Tray: pure teal disk on transparent bg — letters are illegible at 32px anyway

ICO: multi-resolution bundle, PRIMARY entry first (256→16 descending) —
electron-builder on windows-latest reads only the primary entry and rejects
icons whose first entry is <256x256 (see commit eba3a3e5).
PNG: 1024x1024 master, for Linux/macOS targets + future asset pipelines.
Tray PNG: 64x64 with alpha, Windows taskbar scales it down as needed.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ASSETS = Path(__file__).resolve().parent.parent / "assets"

NAVY = (10, 31, 58, 255)
TEAL = (0, 199, 183, 255)
TEAL_HI = (64, 224, 208, 255)
WHITE = (255, 255, 255, 255)
TRANSPARENT = (0, 0, 0, 0)


def _find_bold_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _radial_teal(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), TRANSPARENT)
    steps = 24
    for i in range(steps, 0, -1):
        r = int(size / 2 * i / steps)
        cx = cy = size // 2
        t = i / steps
        color = (
            int(TEAL[0] * t + TEAL_HI[0] * (1 - t)),
            int(TEAL[1] * t + TEAL_HI[1] * (1 - t)),
            int(TEAL[2] * t + TEAL_HI[2] * (1 - t)),
            255,
        )
        ImageDraw.Draw(img).ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
    return img


def make_app_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), TRANSPARENT)
    draw = ImageDraw.Draw(img)

    # Rounded-rectangle navy outer
    corner_radius = int(size * 0.18)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=corner_radius, fill=NAVY)

    # Inner teal disk w/ radial lift
    margin = int(size * 0.14)
    disk_size = size - 2 * margin
    disk = _radial_teal(disk_size)
    img.paste(disk, (margin, margin), disk)

    # Wordmark — white "DP", centered, bold
    font_size = int(size * 0.42)
    font = _find_bold_font(font_size)
    text = "DP"
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), text, font=font, anchor="lt")
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (size - tw) // 2 - bbox[0]
    ty = (size - th) // 2 - bbox[1] - int(size * 0.015)  # slight optical lift
    draw.text((tx, ty), text, font=font, fill=WHITE)

    return img


def make_tray_icon(size: int = 64) -> Image.Image:
    """Tray icon — pure teal disk on transparent bg.

    Letters are illegible at 16–32px, so we drop them. The disk alone is
    recognizably "the DataPulse mark" when paired with the app name tooltip.
    """
    img = Image.new("RGBA", (size, size), TRANSPARENT)
    draw = ImageDraw.Draw(img)

    # Soft outer ring for contrast on both dark + light taskbars
    draw.ellipse((0, 0, size - 1, size - 1), fill=NAVY)
    pad = max(2, size // 16)
    draw.ellipse((pad, pad, size - 1 - pad, size - 1 - pad), fill=TEAL)

    # Subtle highlight
    highlight = Image.new("RGBA", (size, size), TRANSPARENT)
    hd = ImageDraw.Draw(highlight)
    hd.ellipse(
        (int(size * 0.2), int(size * 0.15), int(size * 0.55), int(size * 0.4)),
        fill=(255, 255, 255, 60),
    )
    highlight = highlight.filter(ImageFilter.GaussianBlur(radius=size // 16))
    img = Image.alpha_composite(img, highlight)

    return img


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)

    master = make_app_icon(1024)
    master.save(ASSETS / "icon.png", format="PNG", optimize=True)
    print(f"wrote {ASSETS / 'icon.png'} (1024x1024)")

    # ICO — descending sizes so the 256x256 is the PRIMARY entry
    ico_sizes = [256, 128, 64, 48, 32, 16]
    ico_images = [make_app_icon(s) for s in ico_sizes]
    ico_images[0].save(
        ASSETS / "icon.ico",
        format="ICO",
        sizes=[(s, s) for s in ico_sizes],
        append_images=ico_images[1:],
    )
    print(f"wrote {ASSETS / 'icon.ico'} (sizes: {ico_sizes})")

    tray = make_tray_icon(64)
    tray.save(ASSETS / "tray.png", format="PNG", optimize=True)
    print(f"wrote {ASSETS / 'tray.png'} (64x64, transparent)")


if __name__ == "__main__":
    main()
