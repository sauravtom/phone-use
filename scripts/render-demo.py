#!/usr/bin/env python3
"""Frame the real capture for sharing. Never synthesizes or replaces phone content."""

import argparse
import json
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--directory", type=Path, default=Path("artifacts/recorded-demo"))
args = parser.parse_args()
root = args.directory.resolve()
report = json.loads((root / "report.json").read_text())
if not report.get("passed") or not report.get("video_pulled"):
    raise SystemExit("A successful recorded MCP workflow is required")
raw = root / "android-raw.mp4"
probe = json.loads(
    subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(raw)],
        text=True,
    )
)
duration = float(probe["format"]["duration"])
if duration < 5:
    raise SystemExit("The recording is too short to verify")
font = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
labels = [
    ("phone-use", 110, 140, 88, "white"),
    ("Control Android through MCP", 114, 255, 39, "0xb3d7d6"),
    ("01  Observe the screen", 114, 430, 36, "white"),
    ("02  Enter text and press Apply", 114, 520, 36, "white"),
    ("03  Read back the verified result", 114, 610, 36, "white"),
    ("Real Android capture / scripted MCP client", 114, 785, 27, "0xb3d7d6"),
    ("Production HTTPS relay / no model API key", 114, 835, 27, "0xb3d7d6"),
    ("Continuous capture shown at 2x speed", 114, 925, 25, "0x56d3bb"),
    ("github.com/sauravtom/phone-use", 114, 970, 25, "0x56d3bb"),
]
filters = ["drawbox=x=110:y=365:w=780:h=3:color=0x29bda4:t=fill"]
for i, (text, x, y, size, color) in enumerate(labels):
    label = root / f"video-label-{i}.txt"
    label.write_text(text)
    filters.append(
        f"drawtext=fontfile={font}:textfile={label}:x={x}:y={y}:fontsize={size}:fontcolor={color}"
    )
graph = (
    "[0:v]setpts=(PTS-STARTPTS)/2,scale=-2:880,fps=30[phone];[1:v]"
    + ",".join(filters)
    + "[bg];[bg][phone]overlay=x=W-w-100:y=100:shortest=1[v]"
)
output = root / "phone-use-demo.mp4"
subprocess.run(
    [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(raw),
        "-f",
        "lavfi",
        "-i",
        "color=c=0x081f24:s=1920x1080:r=30",
        "-filter_complex",
        graph,
        "-map",
        "[v]",
        "-an",
        "-t",
        str(duration / 2),
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output),
    ],
    check=True,
)
print(
    json.dumps(
        {
            "video": str(output),
            "raw_seconds": duration,
            "playback_speed": 2,
            "phone_content": "actual screen capture, scaled for layout",
        }
    )
)
