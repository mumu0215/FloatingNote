"""Generate assets/app.ico and assets/app.png for FloatingNote.

Produces a classic multi-size ICO (BMP-style entries) that Nuitka / Windows
resource compilers accept reliably.
"""

from __future__ import annotations

import struct
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "assets"
# Keep sizes modest: large multi-PNG ICOs have crashed Nuitka resource embed on some setups.
SIZES = [16, 24, 32, 48, 64]


def make_note_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    s = size / 64.0
    radius = max(1, int(12 * s))
    draw.rounded_rectangle(
        (4 * s, 4 * s, 60 * s, 60 * s),
        radius=radius,
        fill=(137, 180, 250, 255),
    )
    line = (17, 17, 27, 255)
    for y0, y1, x1 in ((20, 26, 48), (32, 38, 40), (44, 50, 44)):
        # Use rectangles (not rounded) for cleaner small sizes
        draw.rectangle(
            (int(16 * s), int(y0 * s), int(x1 * s), int(y1 * s)),
            fill=line,
        )
    return img


def _rgba_to_ico_bmp(img: Image.Image) -> bytes:
    """Encode one ICO image entry as BIP-style DIB (BITMAPINFOHEADER + XOR + AND)."""
    img = img.convert("RGBA")
    w, h = img.size
    # XOR bitmap: 32-bit BGRA, bottom-up
    pixels = img.load()
    xor = bytearray()
    for y in range(h - 1, -1, -1):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            xor += bytes((b, g, r, a))
    # AND mask: 1 bit/pixel, padded to 32-bit rows
    row_bytes = ((w + 31) // 32) * 4
    and_mask = bytearray()
    for y in range(h - 1, -1, -1):
        row = 0
        bits = 0
        row_data = bytearray()
        for x in range(w):
            a = pixels[x, y][3]
            row = (row << 1) | (0 if a > 0 else 1)
            bits += 1
            if bits == 8:
                row_data.append(row)
                row = 0
                bits = 0
        if bits:
            row_data.append(row << (8 - bits))
        while len(row_data) < row_bytes:
            row_data.append(0)
        and_mask += row_data

    header = struct.pack(
        "<IIIHHIIIIII",
        40,  # biSize
        w,
        h * 2,  # height includes AND mask
        1,  # planes
        32,  # bit count
        0,  # compression
        len(xor) + len(and_mask),
        0,
        0,
        0,
        0,
    )
    return header + xor + and_mask


def write_ico(path: Path, images: list[Image.Image]) -> None:
    """Write a multi-size ICO file with classic BMP entries."""
    entries: list[tuple[int, int, bytes]] = []
    for im in images:
        data = _rgba_to_ico_bmp(im)
        entries.append((im.width, im.height, data))

    count = len(entries)
    # ICONDIR + ICONDIRENTRY * count
    offset = 6 + 16 * count
    buf = BytesIO()
    buf.write(struct.pack("<HHH", 0, 1, count))
    for w, h, data in entries:
        buf.write(
            struct.pack(
                "<BBBBHHII",
                w if w < 256 else 0,
                h if h < 256 else 0,
                0,  # palette
                0,  # reserved
                1,  # planes
                32,  # bitcount
                len(data),
                offset,
            )
        )
        offset += len(data)
    for _, _, data in entries:
        buf.write(data)
    path.write_bytes(buf.getvalue())


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    images = [make_note_icon(sz) for sz in SIZES]
    ico = OUT_DIR / "app.ico"
    png = OUT_DIR / "app.png"
    write_ico(ico, images)
    make_note_icon(256).save(png)
    print(f"[icon] wrote {ico} ({ico.stat().st_size} bytes)")
    print(f"[icon] wrote {png} ({png.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
