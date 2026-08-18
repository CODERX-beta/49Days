#!/usr/bin/env python3
"""

Usage:
    python3 txt_to_script.py --input conversation.txt --output script.json

    # Skip the interactive prompts and use a fixed duration for every line:
    python3 txt_to_script.py --input conversation.txt --output script.json --duration 2.5
"""

import argparse
import json
from pathlib import Path
P1_X = 60
P2_X = 400
START_Y = 250
Y_STEP = 0        # how far down the screen each successive line moves
Y_WRAP = 1600       # wrap back to START_Y once y would exceed this


def read_lines(txt_path):
    """Read non-blank, stripped lines from the input text file."""
    with open(txt_path, "r", encoding="utf-8") as f:
        raw_lines = f.readlines()
    return [line.strip() for line in raw_lines if line.strip()]


def ask_duration(speaker, text, default_duration=None):
    """Prompt the user for how long (in seconds) this line should stay on
    screen. If default_duration is given, pressing Enter uses that value
    instead of prompting-until-valid."""
    prompt = f'[{speaker}] "{text}"\n  Duration in seconds'
    if default_duration is not None:
        prompt += f" (Enter for {default_duration}): "
    else:
        prompt += ": "

    while True:
        raw = input(prompt).strip()
        if not raw and default_duration is not None:
            return default_duration
        try:
            value = float(raw)
            if value <= 0:
                print("  Please enter a positive number.")
                continue
            return value
        except ValueError:
            print("  Please enter a valid number (e.g. 2.5).")


def build_script(lines, fixed_duration=None):
    script = []
    start_time = 0.0
    y_p1 = START_Y
    y_p2 = START_Y

    for i, text in enumerate(lines):
        speaker = "P1" if i % 2 == 0 else "P2"

        if fixed_duration is not None:
            duration = fixed_duration
        else:
            duration = ask_duration(speaker, text)

        if speaker == "P1":
            x, y = P1_X, y_p1
            y_p1 += Y_STEP
            if y_p1 > Y_WRAP:
                y_p1 = START_Y
        else:
            x, y = P2_X, y_p2
            y_p2 += Y_STEP
            if y_p2 > Y_WRAP:
                y_p2 = START_Y

        script.append({
            "speaker": speaker,
            "text": text,
            "start": round(start_time, 2),
            "duration": duration,
            "x": x,
            "y": y,
        })

        start_time += duration

    return script


def main():
    parser = argparse.ArgumentParser(
        description="Convert a .txt conversation into a chat_bubble_video.py JSON script."
    )
    parser.add_argument("--input", required=True, help="Path to input .txt file.")
    parser.add_argument("--output", required=True, help="Path to write the output .json file.")
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="If set, use this fixed duration (seconds) for every line instead of "
             "prompting interactively.",
    )
    args = parser.parse_args()

    lines = read_lines(Path(args.input))
    if not lines:
        print("No non-blank lines found in the input file.")
        return

    script = build_script(lines, fixed_duration=args.duration)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(script, f, indent=2)

    print(f"\nDone. Wrote {len(script)} lines to {args.output}")


if __name__ == "__main__":
    main()
