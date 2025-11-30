import argparse
import subprocess
import sys
import os

parser = argparse.ArgumentParser()
parser.add_argument("--no-gui", action="store_true", help="Run headless")
parser.add_argument("--sound", type=str, default="", help="Engine sound file path")
args = parser.parse_args()

if args.sound:
    os.environ["ENGINE_SOUND_FILE"] = args.sound

subprocess.run([sys.executable, "main.py"])