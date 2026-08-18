#!/usr/bin/env python3
"""
edit_script.py

Interactive, menu-driven editor for chat_bubble_video.py JSON scripts.

Repeatedly lists every line of dialogue. Pick one to open a parameter
menu for it, then pick exactly which parameter you want to change --
speaker, start time, duration, x position, or y position. The dialogue
text itself is never editable here.

There's also a bulk mode: pick a speaker (P1 or P2) and set one x/y
position that gets applied to every line spoken by that speaker at once,
instead of editing each line individually.

Usage:
    python3 edit_script.py --script script.json

Each edit is saved back to the file immediately, so you can quit at any
point (via a menu's 'q' option, or Ctrl+C) without losing progress.
"""

import argparse
import json
from pathlib import Path

PARAM_MENU = [
    ("speaker", "Speaker (P1/P2)"),
    ("start", "Start time (seconds)"),
    ("duration", "Duration (seconds)"),
    ("x", "X position"),
    ("y", "Y position"),
]


def load_script(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_script(path, script):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(script, f, indent=2)


def print_line_menu(script):
    print("\n=== Dialogue Lines ===")
    for i, line in enumerate(script, start=1):
        preview = line.get("text", "")
        if len(preview) > 40:
            preview = preview[:37] + "..."
        print(
            f'{i:2}. [{line.get("speaker", "?")}] "{preview}"  '
            f'start={line.get("start")}s  dur={line.get("duration")}s  '
            f'pos=({line.get("x")},{line.get("y")})'
        )
    print()


def print_param_menu(line):
    preview = line.get("text", "")
    if len(preview) > 60:
        preview = preview[:57] + "..."
    print(f'\n--- Editing: "{preview}" ---')
    print(f'  speaker  = {line.get("speaker")}')
    print(f'  start    = {line.get("start")}')
    print(f'  duration = {line.get("duration")}')
    print(f'  x        = {line.get("x")}')
    print(f'  y        = {line.get("y")}')
    print()
    for i, (key, label) in enumerate(PARAM_MENU, start=1):
        print(f"  {i}. {label}")
    print("  b. Back to line list")
    print()


def prompt_float(prompt, current):
    while True:
        raw = input(f"{prompt} [{current}]: ").strip()
        if raw == "":
            return current
        try:
            return float(raw)
        except ValueError:
            print("  Please enter a number, or leave blank to keep the current value.")


def prompt_int(prompt, current):
    while True:
        raw = input(f"{prompt} [{current}]: ").strip()
        if raw == "":
            return current
        try:
            return int(raw)
        except ValueError:
            print("  Please enter a whole number, or leave blank to keep the current value.")


def prompt_speaker(current):
    while True:
        raw = input(f"Speaker P1/P2 [{current}]: ").strip().upper()
        if raw == "":
            return current
        if raw in ("P1", "P2"):
            return raw
        print("  Please enter P1 or P2, or leave blank to keep the current value.")


def prompt_speaker_required():
    while True:
        raw = input("Which speaker do you want to bulk-edit, P1 or P2? ").strip().upper()
        if raw in ("P1", "P2"):
            return raw
        print("  Please enter P1 or P2.")


def edit_param(line, key):
    if key == "speaker":
        line["speaker"] = prompt_speaker(line.get("speaker", "P1"))
    elif key == "start":
        line["start"] = prompt_float("Start time (seconds)", line.get("start", 0.0))
    elif key == "duration":
        line["duration"] = prompt_float("Duration (seconds)", line.get("duration", 2.0))
    elif key == "x":
        line["x"] = prompt_int("X position", line.get("x", 40))
    elif key == "y":
        line["y"] = prompt_int("Y position", line.get("y", 40))
    return line


def bulk_edit_speaker_position(script, script_path):
    """Set one x/y position that applies to every line spoken by a chosen
    speaker at once. Leaving x or y blank leaves that axis untouched on
    every matching line (so you can bulk-set just y while keeping each
    line's own x, for example)."""
    speaker = prompt_speaker_required()
    matching = [i for i, line in enumerate(script) if line.get("speaker") == speaker]

    if not matching:
        print(f"No lines found for speaker {speaker}.")
        return

    print(f"\n{len(matching)} line(s) found for {speaker}:")
    for i in matching:
        line = script[i]
        preview = line.get("text", "")
        if len(preview) > 40:
            preview = preview[:37] + "..."
        print(f'  - "{preview}"  pos=({line.get("x")},{line.get("y")})')

    print(f"\nLeave a field blank to leave that axis unchanged on all {speaker} lines.")
    raw_x = input("New X position for all these lines: ").strip()
    raw_y = input("New Y position for all these lines: ").strip()

    new_x = None
    new_y = None
    if raw_x != "":
        try:
            new_x = int(raw_x)
        except ValueError:
            print("  Invalid X value, leaving X unchanged.")
    if raw_y != "":
        try:
            new_y = int(raw_y)
        except ValueError:
            print("  Invalid Y value, leaving Y unchanged.")

    if new_x is None and new_y is None:
        print("Nothing entered -- no changes made.")
        return

    for i in matching:
        if new_x is not None:
            script[i]["x"] = new_x
        if new_y is not None:
            script[i]["y"] = new_y

    save_script(script_path, script)
    print(f"Saved. Updated position for {len(matching)} line(s) spoken by {speaker}.")


def edit_line_menu(script, script_path, idx):
    """Sub-menu: keep asking which parameter to change for this one line
    until the user chooses to go back to the line list."""
    while True:
        line = script[idx]
        print_param_menu(line)
        choice = input("Which parameter do you want to change? ").strip().lower()

        if choice == "b":
            return

        param_choices = {str(i): key for i, (key, _) in enumerate(PARAM_MENU, start=1)}
        if choice not in param_choices:
            print(f"  Please enter a number 1-{len(PARAM_MENU)}, or 'b' to go back.")
            continue

        key = param_choices[choice]
        script[idx] = edit_param(line, key)
        save_script(script_path, script)
        print(f"Saved. {key} updated -> {script[idx][key]}")


def main():
    parser = argparse.ArgumentParser(
        description="Interactively edit x/y/start/duration/speaker for lines in a "
                    "chat_bubble_video.py JSON script."
    )
    parser.add_argument("--script", required=True, help="Path to the script JSON file to edit.")
    args = parser.parse_args()

    script_path = Path(args.script)
    script = load_script(script_path)

    if not script:
        print("Script file is empty -- nothing to edit.")
        return

    print(f"Loaded {len(script)} line(s) from {script_path}")

    while True:
        print_line_menu(script)
        choice = input(
            f"Enter a line number (1-{len(script)}) to edit, "
            "'s' to bulk-edit a speaker's position, or 'q' to quit: "
        ).strip().lower()

        if choice == "q":
            print("Done. All changes were already saved as you made them.")
            break

        if choice == "s":
            bulk_edit_speaker_position(script, script_path)
            continue

        try:
            idx = int(choice)
        except ValueError:
            print("Please enter a valid line number, 's', or 'q'.")
            continue

        if not (1 <= idx <= len(script)):
            print(f"Please enter a number between 1 and {len(script)}.")
            continue

        edit_line_menu(script, script_path, idx - 1)


if __name__ == "__main__":
    main()

