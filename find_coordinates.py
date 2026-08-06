#!/usr/bin/env python3
"""
find_coordinates.py

Helper tool: extracts a frame from your video and draws a pixel coordinate
grid over it, so you can visually read off the x,y values to use in your
chat_bubble_video.py script.

Dependencies:
    pip install pillow
    ffmpeg must be installed and on PATH (used to grab the frame)

Usage:
    python3 find_coordinates.py --video input.mp4 --time 1.5 --out grid.png

    --time is the timestamp (in seconds) to grab a frame from -- pick a
    moment where the video looks representative of where you'll be placing
    text (e.g. a moment with no other person's dialogue on screen yet).

Then open grid.png. Grid lines are drawn every 100px with labels, plus
faint lines every 50px, so you can read the approximate x,y of wherever
you want a line of dialogue to start, and plug those numbers straight into
your script.json's "x" and "y" fields.
"""

import argparse
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

MAJOR_STEP = 100   # labeled grid line every N pixels
MINOR_STEP = 50    # faint unlabeled grid line every N pixels
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
LABEL_FONT_SIZE = 22


def extract_frame(video_path, timestamp, frame_path):
    """Use ffmpeg to grab a single frame at `timestamp` seconds."""
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(timestamp),
        "-i", str(video_path),
        "-frames:v", "1",
        "-update", "1",
        str(frame_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed to extract frame:\n{result.stderr}")


def draw_grid(frame_path, out_path):
    img = Image.open(frame_path).convert("RGB")
    w, h = img.size
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype(FONT_PATH, LABEL_FONT_SIZE)
    except OSError:
        font = ImageFont.load_default()

    def label(text, x, y, anchor_bg=(0, 0, 0)):
        bbox = draw.textbbox((x, y), text, font=font)
        pad = 2
        draw.rectangle(
            [bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad],
            fill=anchor_bg,
        )
        draw.text((x, y), text, font=font, fill=(255, 255, 0))

    # Minor grid lines (faint, unlabeled) -- just visual reference ticks
    for x in range(0, w, MINOR_STEP):
        draw.line([(x, 0), (x, h)], fill=(200, 60, 60), width=1)
    for y in range(0, h, MINOR_STEP):
        draw.line([(0, y), (w, y)], fill=(200, 60, 60), width=1)

    # Major grid lines (brighter)
    for x in range(0, w, MAJOR_STEP):
        draw.line([(x, 0), (x, h)], fill=(255, 60, 60), width=2)
    for y in range(0, h, MAJOR_STEP):
        draw.line([(0, y), (w, y)], fill=(255, 60, 60), width=2)

    # X labels along the top edge, and again along the bottom for tall videos
    for x in range(0, w, MAJOR_STEP):
        label(f"x={x}", x + 3, 3)
        label(f"x={x}", x + 3, h - LABEL_FONT_SIZE - 8)

    # Y labels down the left edge, and again down the right for wide videos
    for y in range(0, h, MAJOR_STEP):
        if y == 0:
            continue  # avoid overlapping the x=0 label at the corner
        label(f"y={y}", 3, y + 3)

    img.save(out_path)
    print(f"Video size: {w}x{h}")
    print(f"Grid saved to {out_path}")
    print("Read the x= label from the top/bottom edge and the y= label from "
          "the left edge nearest where you want each line of dialogue to "
          "start (its top-left corner), and use those numbers as \"x\" and "
          "\"y\" in your script.json. Grid lines are every "
          f"{MAJOR_STEP}px (bright) and {MINOR_STEP}px (faint) for finer alignment.")


def main():
    parser = argparse.ArgumentParser(
        description="Overlay a coordinate grid on a video frame to help you pick x,y positions."
    )
    parser.add_argument("--video", required=True, help="Path to the input video.")
    parser.add_argument("--time", type=float, default=0.0,
                         help="Timestamp in seconds to grab the frame from (default 0.0).")
    parser.add_argument("--out", default="grid.png", help="Output image path (default grid.png).")
    args = parser.parse_args()

    video_path = Path(args.video)
    out_path = Path(args.out)
    tmp_frame = out_path.with_name(out_path.stem + "_raw.png")

    extract_frame(video_path, args.time, tmp_frame)
    draw_grid(tmp_frame, out_path)
    tmp_frame.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
