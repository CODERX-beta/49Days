Usage:

.txt to script format(json):
    python3 txt_to_script.py --input conversation.txt --output script.json

edit script:
    python3 edit_script.py --script script.json

generate: 
    python3 chat_bubble_video_p5.py --video input.mp4 --script script.json --out output.mp4 \\
        [--font /path/to/font.ttf] [--font-size 48] [--screen-width 1080] [--screen-height 1920] \\
        [--duration 20] \\
        [--box] [--box-color 20,20,20] [--box-opacity 200] [--box-padding 16] [--box-radius 18]

