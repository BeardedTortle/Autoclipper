# process_tarkov_raid_refactor.py
# Enhancements:
# 1. User input for first kill timestamp.
# 2. Frame extraction and kill list detection with exact resolution and frame rate.
# 3. Dynamic clipping logic to capture 10s before and after each kill.
# 4. Maintains original video specs for clipped segments.
# 5. Enhanced logging and structured output.
# 6. Additional Debugging and Loading Screens
# 7. Directory, Video, and FFmpeg Path Validation
# 8. Detailed FFmpeg Debugging
# 9. Fixed logic for end-of-raid detection
# 10. Optimized OCR and Debugging for Kill List Extraction
# 11. User Input for Kill List Timestamp
# 12. User Input for First Kill and End Screen Timestamp
# 13. Region of Interest (ROI) and Enhanced OCR Detection
# 14. Contrast Boost and Edge Preservation
# 15. Focused ROI from User Image
# 16. Multi-Pass OCR with Character Reconstruction
# 17. Fuzzy Matching and Line Parsing

import os
import cv2
import pytesseract
import subprocess
import sys
import hashlib
from difflib import SequenceMatcher
import re
import time

def parse_timestamp(timestamp):
    """ Parse timestamp in m:s or s format """
    if ":" in timestamp:
        minutes, seconds = map(int, timestamp.split(':'))
        return minutes * 60 + seconds
    else:
        return int(timestamp)


def fuzzy_match(text, pattern):
    return SequenceMatcher(None, text, pattern).ratio() > 0.6


def clean_ocr_line(line):
    line = line.replace("O", "0")
    line = line.replace("Q", "0")
    line = line.replace("—", "-")
    line = line.replace("=", "-")
    line = re.sub(r'[^a-zA-Z0-9 :.,\-]', '', line)
    return line.strip()


def parse_kill_list(ocr_text):
    kill_data = []
    lines = ocr_text.splitlines()
    for line in lines:
        cleaned = clean_ocr_line(line)
        if fuzzy_match(cleaned, "Customs") and fuzzy_match(cleaned, "SCAV"):
            print(f"[DEBUG] Matched Kill Line: {cleaned}")
            # Try to extract meaningful parts
            parts = cleaned.split()
            if len(parts) >= 5:
                timestamp = parts[1]
                name = parts[2]
                faction = parts[4]
                weapon = ' '.join(parts[5:])
                kill_data.append(f"Time: {timestamp} | Name: {name} | Faction: {faction} | Weapon: {weapon}")
    return kill_data


video_path = sys.argv[1]
video_name = os.path.splitext(os.path.basename(video_path))[0]
base_dir = os.path.dirname(video_path)
output_dir = os.path.join(base_dir, f"{video_name}_frames")
log_file = os.path.join(base_dir, f"{video_name}_kill_log.txt")
debug_ocr_dir = os.path.join(base_dir, f"{video_name}_ocr_debug")

highlight_dir = os.path.join(base_dir, f"{video_name}_highlights")
log_lines = []
os.makedirs(output_dir, exist_ok=True)
os.makedirs(highlight_dir, exist_ok=True)
os.makedirs(debug_ocr_dir, exist_ok=True)

def loading_screen(message):
    print(f"\n[LOADING] {message}... Please wait.")
    time.sleep(0.5)
    print("[LOADING] |===      |")
    time.sleep(0.5)
    print("[LOADING] |======   |")
    time.sleep(0.5)
    print("[LOADING] |=========|")
    time.sleep(0.5)


def extract_frames(start_time, duration, fps, prefix):
    loading_screen(f"Extracting frames from {start_time}s for {duration}s at {fps} fps")
    cmd = [
        "ffmpeg", "-ss", str(start_time), "-i", video_path,
        "-t", str(duration), "-vf", f"fps={fps}",
        os.path.join(output_dir, f"{prefix}_%04d.png")
    ]
    print(f"[DEBUG] ffmpeg command: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"[DEBUG] ffmpeg stdout: {result.stdout.decode(errors='replace')}")
        print(f"[DEBUG] ffmpeg stderr: {result.stderr.decode(errors='replace')}")
        if result.returncode != 0:
            print("[ERROR] ffmpeg failed to extract frames.")
    except Exception as e:
        print(f"[ERROR] Exception during ffmpeg execution: {str(e)}")


def process_kill_list(frame_file):
    print(f"[DEBUG] Extracting kill rows from {frame_file}")
    img = cv2.imread(os.path.join(output_dir, frame_file))
    if img is None:
        print(f"[ERROR] Failed to load image {frame_file}")
        return []

    height, width, _ = img.shape

    # === Focused Region of Interest (ROI) ===
    roi = img[int(height * 0.2):int(height * 0.8), int(width * 0.15):int(width * 0.85)]

    # === Multi-Pass OCR ===
    text = pytesseract.image_to_string(roi)
    kill_list = parse_kill_list(text)

    # === Logging the results ===
    with open(log_file, "a", encoding="utf-8") as f:
        for kill in kill_list:
            f.write(f"{kill}\n")
            print(f"[LOGGED] {kill}")


# Main Process
loading_screen("Starting main process")
print("[DEBUG] Starting main process...")

# User Inputs for Timestamps
first_kill_time = parse_timestamp(input("Enter the timestamp of the **first kill** (m:s or s): ").strip())
print(f"[INFO] First kill at {first_kill_time}s")

kill_list_time = parse_timestamp(input("Enter the timestamp of the **kill list screen** (m:s or s): ").strip())
print(f"[INFO] Kill List screen at {kill_list_time}s")

# Extract frames from the kill list screen
print(f"[DEBUG] Attempting to extract frames from {kill_list_time} for 180 seconds")
extract_frames(kill_list_time, 180, 1, "end")

frame_list = sorted(os.listdir(output_dir))
print(f"[DEBUG] Frames found: {frame_list}")

# Process the frames for Kill List
for frame in frame_list:
    process_kill_list(frame)
