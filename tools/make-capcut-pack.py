"""Produce frame-accurate CapCut import media for the Garden opening."""
import argparse
import csv
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFont

SHOTS = (
    ("plane-travel", "I. Reisen", 81, "Plane window, boarding or arrival. Start the score quietly."),
    ("bridge-in-darkness", "II. Broen", 87, "Wide silhouette first, then a low shot of footsteps. Keep the night visible."),
    ("chen-sifu-vegetables", "Chen Sifu", 81, "Hands and knife, vegetables landing on the board, then a brief look up."),
    ("sifu-at-the-wok", "Sifu", 99, "Shoot the first flare from a safe distance. Cut into an overhead toss or a close plate."),
    ("xin-makes-sushi", "Xin", 81, "Start with hands forming sushi. Finish on a clean knife cut and a look up."),
    ("yong-and-ping", "Yong & Ping", 99, "Film them together in a natural moment. Hold just long enough for the shared look."),
    ("yong-alone", "Yong", 108, "Use an honest quiet moment in Yong's own space. Let the camera and score settle."),
    ("garden-full-of-guests", "VIII. Full sal", 168, "Wide room, plates passing, tables in motion. Cut to the room at its busiest."),
    ("garden-title", "I kveld på Garden", 96, "Return to the bridge or hold on the restaurant at night. Let the title arrive on the downbeat."),
)
FPS=30
SIZE=(1280,720)


def ts(frame, separator=","):
    time = round(frame / FPS * 1000)
    return f"{time//3600000:02d}:{time//60000%60:02d}:{time//1000%60:02d}{separator}{time%1000:03d}"


def typeface(name, size):
    p = Path("C:/Windows/Fonts") / name
    return ImageFont.truetype(str(p), size) if p.exists() else ImageFont.load_default(size=size)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args=parser.parse_args()
    root=args.destination
    clips=root/"Clips"
    clips.mkdir(parents=True,exist_ok=True)
    data, captions, paths = [], [], []
    start = 0
    for index,(slug,title,frames,direction) in enumerate(SHOTS,1):
        end = start + frames
        name = f"{index:02d}-{slug}.mp4"
        paths.append("Clips/" + name)
        data.append((name,ts(start,"."),ts(end,"."),frames,title,direction))
        if slug in {"chen-sifu-vegetables","sifu-at-the-wok","xin-makes-sushi","yong-and-ping","yong-alone","garden-title"}:
            captions.append(f"{len(captions)+1}\n{ts(start+12)} --> {ts(end-9)}\n{title}")
        shot = Image.new("RGB", SIZE, "#241410")
        d = ImageDraw.Draw(shot)
        d.rectangle((45,45,1235,675),outline="#ba8158",width=2)
        d.line((118,152,264,152),fill="#f4c785",width=2)
        d.text((116,106),"IRL GARDEN GAIDEN",fill="#f4c785",font=typeface("arialbd.ttf",22))
        d.text((116,225),title,fill="#fae5c4",font=typeface("georgiai.ttf",94))
        d.text((120,389),slug.replace("-"," ").upper(),fill="#d9ad94",font=typeface("arial.ttf",25))
        d.text((120,578),f"SHOT {index:02d}    {ts(start,'.')} – {ts(end,'.')}",
               fill="#f4c785",font=typeface("arial.ttf",24))
        art = root/"slate-temporary.png"
        shot.save(art)
        subprocess.run([args.ffmpeg,"-hide_banner","-loglevel","error","-y","-loop","1",
                        "-framerate",str(FPS),"-i",str(art),"-frames:v",str(frames),
                        "-an","-c:v","libx264","-preset","fast","-crf","21","-pix_fmt","yuv420p",
                        "-movflags","+faststart",str(clips/name)],check=True)
        art.unlink()
        start = end
    (root/"Garden-credits.srt").write_text("\n\n".join(captions)+"\n",encoding="utf-8")
    with (root/"Garden-shot-timeline.csv").open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.writer(f)
        writer.writerow(("Clip","In","Out","Frames at 30fps","Credit or card","Direction"))
        writer.writerows(data)
    path=root/"concat-temporary.txt"
    path.write_text("".join(f"file '{item}'\n" for item in paths),encoding="utf-8")
    subprocess.run([args.ffmpeg,"-hide_banner","-loglevel","error","-y","-f","concat","-safe","1",
                    "-i",str(path),"-c","copy","-movflags","+faststart",
                    str(root/"Garden-opening-timing-preview.mp4")],check=True)
    path.unlink()
    print(f"{len(SHOTS)} edit slots and {len(captions)} credits, {start/FPS:.1f} seconds")


if __name__=="__main__":
    main()
