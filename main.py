#!/usr/bin/env python3
"""
Dependencies (all modern, actively maintained, no ImageMagick needed):
    pip install moviepy pillow

Usage:
    python3 chat_bubble_video.py --video input.mp4 --script script.json --out output.mp4 \\
        [--font /path/to/font.ttf] [--font-size 48] [--screen-width 1080] [--screen-height 1920]

Script JSON format (a list of dialogue lines):
[
  {
    "speaker": "P1",
    "text": "hey are you coming tonight?",
    "start": 0.0,
    "duration": 2.5,
    "x": 60,
    "y": 300
  },
  {
    "speaker": "P2",
    "text": "yeah omw",
    "start": 2.5,
    "duration": 2.0,
    "x": 600,
    "y": 500
  }
]

- speaker: "P1" or "P2" (controls text color)
- text: the message text
- start: seconds into the video when the text should appear
- duration: how long the text stays on screen (seconds)
- x, y: top-left pixel coordinates of the text on the video frame

--screen-width / --screen-height let you tell the script what size screen
the text needs to fit on (defaults to the input video's own resolution if
omitted). Each line automatically wraps onto a new line before it would
run past the right edge of that screen, based on where its "x" sits --
text starting further right has less room before it wraps, text starting
near the left edge has more. There's no need to manually pick a wrap
width per line.

Each line is rendered once as a transparent PNG (via Pillow, so no
ImageMagick / font-cache issues) and then placed on the video as a timed
ImageClip using MoviePy. This avoids MoviePy's TextClip entirely, which is
the single biggest source of "works on my machine" compatibility problems
(it depends on ImageMagick being installed and configured correctly).
"""

import argparse
import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoFileClip, ImageClip, CompositeVideoClip
import numpy as np

# ---------------------------------------------------------------------------
# Style config - tweak these to change the look of the text
# ---------------------------------------------------------------------------

STYLES = {
    "P1": {
        "text_color": (255, 255, 255, 255),   # white
        "outline_color": (0, 0, 0, 255),      # black outline for legibility
    },
    "P2": {
        #"text_color": (10, 132, 255, 255),
        # iMessage blue
        "text_color": (255, 255, 255, 255),
        "outline_color": (0, 0, 0, 255),
    },
}

DEFAULT_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
DEFAULT_FONT_SIZE = 42
PADDING_X = 6         # small margin so the outline/anti-aliasing isn't clipped
PADDING_Y = 6
LINE_SPACING = 10
OUTLINE_WIDTH = 2
RIGHT_MARGIN = 20      # keep this much space between wrapped text and the screen edge
MIN_WRAP_WIDTH = 80    # never wrap tighter than this, even if x is near the edge


def load_font(font_path=DEFAULT_FONT_PATH, size=DEFAULT_FONT_SIZE):
    try:
        return ImageFont.truetype(font_path, size)
    except OSError:
        # Fallback to Pillow's built-in default if the given font isn't found
        print(f"Warning: could not load font '{font_path}', using Pillow default.")
        return ImageFont.load_default()


def wrap_text(text, font, draw, max_px_width):
    """Wrap text so each line fits within max_px_width, measured with the
    actual font metrics (more reliable than a fixed character count)."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        w = draw.textlength(candidate, font=font)
        if w <= max_px_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def render_bubble(text, speaker, max_px_width=560, font_path=DEFAULT_FONT_PATH,
                   font_size=DEFAULT_FONT_SIZE):
    """Render a single line of dialogue as plain text on a transparent
    RGBA PIL Image (no background bubble). A thin outline is drawn behind
    the fill color so the text stays legible over any video background."""
    style = STYLES.get(speaker, STYLES["P1"])
    font = load_font(font_path, font_size)

    # Dummy draw context just for text measurement
    dummy_img = Image.new("RGBA", (10, 10))
    dummy_draw = ImageDraw.Draw(dummy_img)

    lines = wrap_text(text, font, dummy_draw, max_px_width - 2 * PADDING_X)

    line_heights = []
    line_widths = []
    for line in lines:
        # Measure with the same stroke_width used at draw time below --
        # otherwise the stroke expands each glyph beyond this box and the
        # padding ends up inconsistent from line to line (varies with which
        # characters happen to start/end the line), which looks like the
        # text position "shifting" between different lines at the same x,y.
        bbox = dummy_draw.textbbox((0, 0), line, font=font, stroke_width=OUTLINE_WIDTH)
        line_widths.append(bbox[2] - bbox[0])
        line_heights.append(bbox[3] - bbox[1])

    text_block_width = max(line_widths) if line_widths else 0
    text_block_height = sum(line_heights) + LINE_SPACING * (len(lines) - 1)

    img_w = int(text_block_width + 2 * PADDING_X + 2 * OUTLINE_WIDTH)
    img_h = int(text_block_height + 2 * PADDING_Y + 2 * OUTLINE_WIDTH)

    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    y_cursor = PADDING_Y + OUTLINE_WIDTH
    for i, line in enumerate(lines):
        draw.text(
            (PADDING_X + OUTLINE_WIDTH, y_cursor),
            line,
            font=font,
            fill=style["text_color"],
            stroke_width=OUTLINE_WIDTH,
            stroke_fill=style["outline_color"],
        )
        y_cursor += line_heights[i] + LINE_SPACING

    return img


def build_video(video_path, script_path, out_path, max_bubble_width=560,
                 font_path=DEFAULT_FONT_PATH, font_size=DEFAULT_FONT_SIZE,
                 screen_width=None, screen_height=None):
    video_path = Path(video_path)
    script_path = Path(script_path)

    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    base_clip = VideoFileClip(str(video_path))

    # Screen size used only to decide where a line must wrap -- defaults to
    # the actual video resolution if not given explicitly.
    screen_w = screen_width or base_clip.size[0]
    screen_h = screen_height or base_clip.size[1]

    overlay_clips = [base_clip]

    for i, line in enumerate(script):
        speaker = line.get("speaker", "P1")
        text = line["text"]
        start = float(line["start"])
        duration = float(line["duration"])
        x = int(line.get("x", 40))
        y = int(line.get("y", 40))

        # Room left before hitting the right edge of the screen from x --
        # capped at max_bubble_width so lines starting near the left edge
        # don't stretch all the way across a wide screen.
        available_width = screen_w - x - RIGHT_MARGIN
        wrap_width = max(MIN_WRAP_WIDTH, min(max_bubble_width, available_width))

        bubble_img = render_bubble(
            text, speaker,
            max_px_width=wrap_width,
            font_path=font_path,
            font_size=font_size,
        )
        bubble_arr = np.array(bubble_img)  # RGBA numpy array

        clip = (
            ImageClip(bubble_arr)
            .with_start(start)
            .with_duration(duration)
            .with_position((x, y))
        )
        overlay_clips.append(clip)

    final = CompositeVideoClip(overlay_clips, size=base_clip.size)
    final = final.with_duration(base_clip.duration)

    final.write_videofile(
        str(out_path),
        codec="libx264",
        audio_codec="aac",
        fps=base_clip.fps,
        preset="medium",
        threads=4,
    )

    base_clip.close()
    final.close()


def main():
    parser = argparse.ArgumentParser(description="Overlay chat bubbles onto a video.")
    parser.add_argument("--video", required=True, help="Path to input video (mp4).")
    parser.add_argument("--script", required=True, help="Path to script JSON file.")
    parser.add_argument("--out", required=True, help="Path to output video (mp4).")
    parser.add_argument(
        "--bubble-width",
        type=int,
        default=560,
        help="Max text width in pixels before it wraps to the next line, capped by "
             "screen edge (default 560).",
    )
    parser.add_argument(
        "--font",
        default=DEFAULT_FONT_PATH,
        help=f"Path to a .ttf/.otf font file (default {DEFAULT_FONT_PATH}).",
    )
    parser.add_argument(
        "--font-size",
        type=int,
        default=DEFAULT_FONT_SIZE,
        help=f"Font size in pixels (default {DEFAULT_FONT_SIZE}).",
    )
    parser.add_argument(
        "--screen-width",
        type=int,
        default=None,
        help="Screen width in pixels used to decide where lines wrap (default: the "
             "input video's own width).",
    )
    parser.add_argument(
        "--screen-height",
        type=int,
        default=None,
        help="Screen height in pixels, for reference/future use (default: the input "
             "video's own height).",
    )
    args = parser.parse_args()

    build_video(
        args.video, args.script, args.out,
        max_bubble_width=args.bubble_width,
        font_path=args.font,
        font_size=args.font_size,
        screen_width=args.screen_width,
        screen_height=args.screen_height,
    )
    print(f"Done. Wrote {args.out}")


if __name__ == "__main__":
    main()
