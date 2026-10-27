"""Build a crisp monochrome application icon (build-time Pillow only).

The mark uses two opposite routing arrows in a rounded black tile.
No externally downloaded SVG/font/icon assets are required.
"""
from pathlib import Path
from PIL import Image, ImageDraw

SIZE = 1024
INK = (24, 24, 27, 255)
WHITE = (250, 250, 250, 255)


def build_icon():
    root = Path(__file__).resolve().parents[1]
    directory = root / "build"
    directory.mkdir(exist_ok=True)
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    d.rounded_rectangle((32, 32, 992, 992), radius=232, fill=INK)
    # Symmetric direction switch. Slightly thicker than in-app for 16px legibility.
    width = 68
    d.line([(240, 365), (794, 365), (681, 252)], fill=WHITE, width=width, joint="curve")
    d.line([(794, 365), (681, 478)], fill=WHITE, width=width, joint="curve")
    d.line([(784, 665), (230, 665), (343, 552)], fill=WHITE, width=width, joint="curve")
    d.line([(230, 665), (343, 778)], fill=WHITE, width=width, joint="curve")
    for pos in [(240,365),(794,365),(681,252),(681,478),(784,665),(230,665),(343,552),(343,778)]:
        x,y=pos
        d.ellipse((x-width/2,y-width/2,x+width/2,y+width/2),fill=WHITE)
    image.save(directory / "WhiteSwitcher.png")
    image.save(directory / "WhiteSwitcher.ico", sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
    print(f"Generated monochrome icons in {directory}")


if __name__ == "__main__":
    build_icon()
