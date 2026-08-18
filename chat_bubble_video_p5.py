#!/usr/bin/env python3
"""
Dependencies (all modern, actively maintained, no ImageMagick needed):
    pip install moviepy pillow

Usage:
    python3 chat_bubble_video.py --video input.mp4 --script script.json --out output.mp4 \\
        [--font /path/to/font.ttf] [--font-size 48] [--screen-width 1080] [--screen-height 1920] \\
        [--duration 20] \\
        [--box] [--box-color 20,20,20] [--box-opacity 200] [--box-padding 16] [--box-radius 18]

"""

import argparse
import json
import math
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips
import numpy as np

# Style config

STYLES = {
    "P1": {
        "text_color": (0, 0, 0, 255),   # white
        "outline_color": (0, 0, 0, 0),      # black outline for legibility
    },
    "P2": {
        "text_color": (0, 0, 0, 255),    
        "outline_color": (0, 0, 0, 0),
    },
}

DEFAULT_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
DEFAULT_FONT_SIZE = 42
PADDING_X = 3         # small margin so the outline/anti-aliasing isn't clipped
PADDING_Y = 3
LINE_SPACING = 10
OUTLINE_WIDTH = 0
RIGHT_MARGIN = 20      # keep this much space between wrapped text and the screen edge
MIN_WRAP_WIDTH = 80    # never wrap tighter than this, even if x is near the edge

# Background "chat bubble" box behind the text -- off by default so existing
# callers get the old plain-text-only look unless they opt in.
DEFAULT_BOX_ENABLED = False
DEFAULT_BOX_COLOR = (20, 20, 20)   # RGB, no alpha -- alpha comes from --box-opacity
DEFAULT_BOX_OPACITY = 200          # 0 (fully transparent) - 255 (fully opaque)
DEFAULT_BOX_PADDING = 16           # px of box visible around the text on every side
DEFAULT_BOX_RADIUS = 18            # corner radius in px; 0 = sharp rectangle


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
                   font_size=DEFAULT_FONT_SIZE,
                   box_enabled=DEFAULT_BOX_ENABLED,
                   box_color=DEFAULT_BOX_COLOR,
                   box_opacity=DEFAULT_BOX_OPACITY,
                   box_padding=DEFAULT_BOX_PADDING,
                   box_radius=DEFAULT_BOX_RADIUS):
    """Render a single line of dialogue as text on a transparent RGBA PIL
    Image, with a thin outline drawn behind the fill color so the text
    stays legible over any video background.

    If box_enabled is True, a solid/translucent rounded-rectangle box is
    drawn behind the text first, sized to the text block plus box_padding
    on every side. At box_opacity=255 the box is fully opaque and
    completely hides the video frame behind it.
    """
    style = STYLES.get(speaker, STYLES["P1"])
    font = load_font(font_path, font_size)

    # Dummy draw context just for text measurement
    dummy_img = Image.new("RGBA", (10, 10))
    dummy_draw = ImageDraw.Draw(dummy_img)

    # Padding between the text and the edge of the image (= edge of the
    # box, when the box is on). Without a box we still need PADDING_X/Y as
    # a small safety margin so the outline/anti-aliasing isn't clipped by
    # the image edge. With the box on, box_padding is that margin instead
    # -- so box_padding=0 means the box hugs the outline with zero extra
    # gap (rather than silently adding PADDING_X/Y on top of it).
    pad_x = box_padding if box_enabled else PADDING_X
    pad_y = box_padding if box_enabled else PADDING_Y

    # The box eats into the available width just like screen-edge wrapping
    # does, so text doesn't wrap wider than the box will end up being.
    wrap_budget = max(max_px_width - 2 * pad_x, MIN_WRAP_WIDTH)

    lines = wrap_text(text, font, dummy_draw, wrap_budget)

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

    # Padding between the text and the edge of the image (= edge of the
    # box, when the box is on). Without a box we still need PADDING_X/Y as
    # a small safety margin so the outline/anti-aliasing isn't clipped by
    # the image edge. With the box on, box_padding is that margin instead
    # -- so box_padding=0 means the box hugs the outline with zero extra
    # gap (rather than silently adding PADDING_X/Y on top of it).
    pad_x = box_padding if box_enabled else PADDING_X
    pad_y = box_padding if box_enabled else PADDING_Y

    img_w = int(text_block_width + 2 * pad_x + 2 * OUTLINE_WIDTH)
    img_h = int(text_block_height + 2 * pad_y + 2 * OUTLINE_WIDTH)

    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if box_enabled:
        r, g, b = box_color[:3]
        alpha = max(0, min(255, int(box_opacity)))
        box_fill = (r, g, b, alpha)
        rect = (0, 0, img_w - 1, img_h - 1)
        if box_radius > 0:
            draw.rounded_rectangle(rect, radius=box_radius, fill=box_fill)
        else:
            draw.rectangle(rect, fill=box_fill)

    y_cursor = pad_y + OUTLINE_WIDTH
    for i, line in enumerate(lines):
        draw.text(
            (pad_x + OUTLINE_WIDTH, y_cursor),
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
                 screen_width=None, screen_height=None, target_duration=None,
                 box_enabled=DEFAULT_BOX_ENABLED,
                 box_color=DEFAULT_BOX_COLOR,
                 box_opacity=DEFAULT_BOX_OPACITY,
                 box_padding=DEFAULT_BOX_PADDING,
                 box_radius=DEFAULT_BOX_RADIUS):
    video_path = Path(video_path)
    script_path = Path(script_path)

    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    source_clip = VideoFileClip(str(video_path))

    # Screen size used only to decide where a line must wrap -- defaults to
    # the actual video resolution if not given explicitly. Computed from the
    # source clip since looping doesn't change frame size.
    screen_w = screen_width or source_clip.size[0]
    screen_h = screen_height or source_clip.size[1]

    if target_duration is not None and target_duration > source_clip.duration:
        # Requested length is longer than the source footage -- loop the
        # source (play it again from the start) enough times to cover it,
        # then cut off exactly at target_duration.
        loops_needed = math.ceil(target_duration / source_clip.duration)
        print(
            f"Requested duration {target_duration}s exceeds source video "
            f"duration {source_clip.duration:.2f}s -- looping source "
            f"{loops_needed}x and trimming to {target_duration}s."
        )
        looped = concatenate_videoclips([source_clip] * loops_needed)
        base_clip = looped.subclipped(0, target_duration)
        final_duration = target_duration
    elif target_duration is not None:
        # Requested length fits within (or equals) the source -- just trim.
        base_clip = source_clip.subclipped(0, target_duration)
        final_duration = target_duration
    else:
        base_clip = source_clip
        final_duration = source_clip.duration

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
            box_enabled=box_enabled,
            box_color=box_color,
            box_opacity=box_opacity,
            box_padding=box_padding,
            box_radius=box_radius,
        )
        bubble_arr = np.array(bubble_img)  # RGBA numpy array

        # When the box is on, the rendered image is padded outward by
        # box_padding on every side relative to the plain-text case, so
        # shift the placement back by that amount to keep the *text*
        # anchored at (x, y) the way it always was.
        pos_x = x - box_padding if box_enabled else x
        pos_y = y - box_padding if box_enabled else y

        clip = (
            ImageClip(bubble_arr)
            .with_start(start)
            .with_duration(duration)
            .with_position((pos_x, pos_y))
        )
        overlay_clips.append(clip)

    final = CompositeVideoClip(overlay_clips, size=base_clip.size)
    final = final.with_duration(final_duration)

    final.write_videofile(
        str(out_path),
        codec="libx264",
        audio_codec="aac",
        fps=source_clip.fps,
        preset="medium",
        threads=4,
    )

    base_clip.close()
    if base_clip is not source_clip:
        source_clip.close()
    final.close()


def parse_color(s):
    """Parse an 'R,G,B' CLI string into an (R, G, B) int tuple."""
    parts = [p.strip() for p in s.split(",")]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError(
            f"Color must be 'R,G,B' (e.g. '20,20,20'), got: {s!r}"
        )
    try:
        r, g, b = (int(p) for p in parts)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Color values must be integers 0-255, got: {s!r}"
        )
    for v in (r, g, b):
        if not (0 <= v <= 255):
            raise argparse.ArgumentTypeError(
                f"Color values must be 0-255, got: {s!r}"
            )
    return (r, g, b)


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
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Length of the output video in seconds (default: same as the source "
             "video). If longer than the source, the source is looped until it "
             "reaches this length, then cut off exactly at that point.",
    )
    parser.add_argument(
        "--box",
        action="store_true",
        default=DEFAULT_BOX_ENABLED,
        help="Draw a background box behind each line of text (like a chat "
             "bubble). Off by default -- text is drawn directly over the "
             "video otherwise.",
    )
    parser.add_argument(
        "--box-color",
        type=parse_color,
        default=DEFAULT_BOX_COLOR,
        metavar="R,G,B",
        help="Box fill color as 'R,G,B', 0-255 each "
             f"(default '{','.join(str(c) for c in DEFAULT_BOX_COLOR)}'). "
             "Only used when --box is set.",
    )
    parser.add_argument(
        "--box-opacity",
        type=int,
        default=DEFAULT_BOX_OPACITY,
        metavar="0-255",
        help="Box opacity/alpha, 0 (invisible) to 255 (fully solid -- "
             f"completely hides the video behind it) (default {DEFAULT_BOX_OPACITY}). "
             "Only used when --box is set.",
    )
    parser.add_argument(
        "--box-padding",
        type=int,
        default=DEFAULT_BOX_PADDING,
        metavar="PX",
        help="How many pixels of box show around the text on every side "
             f"(default {DEFAULT_BOX_PADDING}). Only used when --box is set.",
    )
    parser.add_argument(
        "--box-radius",
        type=int,
        default=DEFAULT_BOX_RADIUS,
        metavar="PX",
        help="Corner radius of the box in pixels, 0 for sharp corners "
             f"(default {DEFAULT_BOX_RADIUS}). Only used when --box is set.",
    )
    args = parser.parse_args()

    if not (0 <= args.box_opacity <= 255):
        parser.error("--box-opacity must be between 0 and 255")
    if args.box_padding < 0:
        parser.error("--box-padding must be >= 0")
    if args.box_radius < 0:
        parser.error("--box-radius must be >= 0")

    build_video(
        args.video, args.script, args.out,
        max_bubble_width=args.bubble_width,
        font_path=args.font,
        font_size=args.font_size,
        screen_width=args.screen_width,
        screen_height=args.screen_height,
        target_duration=args.duration,
        box_enabled=args.box,
        box_color=args.box_color,
        box_opacity=args.box_opacity,
        box_padding=args.box_padding,
        box_radius=args.box_radius,
    )
    print(f"Done. Wrote {args.out}")


if __name__ == "__main__":
    main()
