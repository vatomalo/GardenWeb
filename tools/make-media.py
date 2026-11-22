"""Generate the opening film, original pixel sprites, and original order chime."""
from array import array
import argparse
import math
from pathlib import Path
import subprocess
import wave

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps


FRAMES_PER_SHOT = 96
FPS = 24
SIZE = (1280, 720)
SHOTS = (
    ("garden-signature.jpg", "", "", (0.50, 0.62)),
    ("hang-bing-fei.jpg", "Hang Bing Fei", "KOKK", (0.67, 0.52)),
    ("zu-kang-zhong.jpg", "Zu Kang Zhong", "KOKK", (0.31, 0.47)),
    ("garden-table.jpg", "Garden Restaurant", "KONGSBERG", (0.56, 0.5)),
)


def font(name, size):
    for directory in (Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype/dejavu")):
        candidate = directory / name
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default(size=size)


def vignette():
    w, h = SIZE
    mask = Image.new("L", (w, h))
    pixels = []
    for y in range(h):
        for x in range(w):
            edge = max(0, abs((y - h / 2) / (h / 2)) - .42)
            left = (1 - min(1, x / (w * .61))) ** 1.7
            pixels.append(round(min(.92, left * .86 + edge * .38) * 255))
    mask.putdata(pixels)
    return mask


def render_frame(photo, title, label, center, progress, mask, fonts):
    w, h = SIZE
    zoom = 1 + .10 * progress
    shot = ImageOps.fit(photo, (round(w * zoom), round(h * zoom)),
                        method=Image.Resampling.LANCZOS, centering=center)
    over_x, over_y = shot.width - w, shot.height - h
    left, top = round(over_x * .55), round(over_y * .45)
    shot = shot.crop((left, top, left + w, top + h))
    image = Image.composite(Image.new("RGB", SIZE, "#211411"), shot, mask)
    if title:
        fade = int(255 * min(1, progress * 7, (1 - progress) * 7))
        credits = Image.new("RGBA", SIZE)
        pen = ImageDraw.Draw(credits)
        x, y = 1190, 570
        pen.text((x + 2, y + 3), title, font=fonts[0], anchor="ra", fill=(25, 12, 10, fade))
        pen.text((x, y), title, font=fonts[0], anchor="ra", fill=(254, 232, 196, fade))
        pen.line((x - 32, y + 55, x, y + 55), fill=(245, 189, 115, fade), width=2)
        pen.text((x - 39, y + 48), label, font=fonts[1], anchor="ra", fill=(248, 203, 148, fade))
        image.paste(credits, (0, 0), credits)
    return image


def film(root, ffmpeg):
    mask = vignette()
    fonts = (font("georgiai.ttf", 43), font("arial.ttf", 15))
    photos = []
    for filename, _, _, _ in SHOTS:
        with Image.open(root / filename) as raw:
            photo = ImageEnhance.Color(raw.convert("RGB")).enhance(.84)
            photos.append(ImageEnhance.Contrast(photo).enhance(1.08))
    dest = root / "garden-opening.mp4"
    args = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pixel_format", "rgb24",
            "-video_size", "1280x720", "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264",
            "-preset", "fast", "-crf", "22", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dest)]
    with subprocess.Popen(args, stdin=subprocess.PIPE) as encoder:
        for shot_id, (_, title, label, center) in enumerate(SHOTS):
            for index in range(FRAMES_PER_SHOT):
                progress = index / (FRAMES_PER_SHOT - 1)
                image = render_frame(photos[shot_id], title, label, center, progress, mask, fonts)
                if shot_id == 0 and index == 0:
                    image.save(root / "hero-poster.jpg", quality=88, optimize=True)
                if index >= FRAMES_PER_SHOT - 9:
                    next_id = (shot_id + 1) % len(SHOTS)
                    ending = (index - (FRAMES_PER_SHOT - 9) + 1) / 10
                    upcoming = render_frame(photos[next_id], *SHOTS[next_id][1:], 0, mask, fonts)
                    image = Image.blend(image, upcoming, ending)
                encoder.stdin.write(image.tobytes())
        encoder.stdin.close()
        if encoder.wait():
            raise RuntimeError("FFmpeg could not encode the hero film")


DUMPLING = (
    "................", "................", "......oo........", ".....ofso.......",
    "....offfso......", "...ofsfffso.....", "..offfffffso....", "..offfffffffso..",
    ".offkffkfffffso.", ".offkffkfffffso.", ".oprffrffppffso.", ".oppffkkfppffso.",
    "..osffffffffffo.", "...ooossssoooo..", "................", "................",
)
CHILI = (
    "................", ".......gg.......", "......gGGg......", "......gogg......",
    ".....orrro......", "....orrRrro.....", "...orrRrrro.....", "...orrrkrro.....",
    "...orrkrro......", "...orrrrrro.....", "...orrrrro......", "....orrrro......",
    ".....orro.......", "......oo........", "................", "................",
)
PALETTE = {"o": "#411b1e", "f": "#ffe3ab", "s": "#e9ae68", "k": "#392120",
           "p": "#efa08d", "r": "#d7474c", "R": "#ffb1a9", "g": "#426648", "G": "#8eb45b"}


def sprites(root):
    for filename, grid in (("dumpling.png", DUMPLING), ("chili.png", CHILI)):
        picture = Image.new("RGBA", (16, 16))
        draw = ImageDraw.Draw(picture)
        for y, row in enumerate(grid):
            for x, pixel in enumerate(row):
                if pixel in PALETTE:
                    draw.point((x, y), fill=PALETTE[pixel])
        picture.resize((80, 80), Image.Resampling.NEAREST).save(root / filename)


def chime(root):
    hz = 44100
    notes = ((0, 659.255), (.083, 880.0), (.172, 1108.731), (.285, 1396.913))
    samples = array("h")
    for index in range(round(hz * .96)):
        time = index / hz
        result = 0.0
        for start, pitch in notes:
            age = time - start
            if age < 0:
                continue
            envelope = min(1, age * 210) * math.exp(-age * 7.0) * min(1, max(0, (.955 - time) * 65))
            phase = 2 * math.pi * pitch * age
            result += envelope * (math.sin(phase) + .28 * math.sin(phase * 2.0) + .10 * math.sin(phase * 3.01))
        samples.append(round(result * 3600))
    with wave.open(str(root / "order-chime.wav"), "wb") as output:
        output.setparams((1, 2, hz, 0, "NONE", "not compressed"))
        output.writeframes(samples.tobytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1] / "docs" / "assets", type=Path)
    args = parser.parse_args()
    sprites(args.root)
    chime(args.root)
    film(args.root, args.ffmpeg)


if __name__ == "__main__":
    main()
