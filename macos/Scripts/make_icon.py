"""Create a monochrome macOS-compatible .iconset; Apple iconutil creates .icns."""
from pathlib import Path
from PIL import Image, ImageDraw
import sys

out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("build/WhiteSwitcher.iconset")
out.mkdir(parents=True, exist_ok=True)
N = 1024
im = Image.new("RGBA", (N, N), (0, 0, 0, 0))
d = ImageDraw.Draw(im)
# Black graphite rounded-rect field with restrained native-looking macOS silhouette.
d.rounded_rectangle((35, 35, 989, 989), radius=215, fill="#18181B")
# Bidirectional switch: two minimal terminal circles and crossing angled cables.
white = "#FAFAFA"
d.line([(238, 356), (448, 356), (584, 668), (790, 668)], fill=white, width=70, joint="curve")
d.line([(238, 668), (448, 668), (584, 356), (790, 356)], fill=white, width=70, joint="curve")
for x, y in [(238, 356), (238, 668)]:
    d.ellipse((x-47, y-47, x+47, y+47), fill=white)
for x, y in [(790, 356), (790, 668)]:
    d.ellipse((x-48, y-48, x+48, y+48), fill=white)
for size, suffix in [(16,"16x16"),(32,"16x16@2x"),(32,"32x32"),(64,"32x32@2x"),
                     (128,"128x128"),(256,"128x128@2x"),(256,"256x256"),(512,"256x256@2x"),
                     (512,"512x512"),(1024,"512x512@2x")]:
    im.resize((size,size), Image.Resampling.LANCZOS).save(out / f"icon_{suffix}.png")
