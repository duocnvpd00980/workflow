# app/browser.py
import subprocess
import os

def start_virtual_display():
    subprocess.Popen(
        ["Xvfb", ":99", "-screen", "0", "1920x1080x24"],
        stderr=subprocess.DEVNULL
    )
    os.environ["DISPLAY"] = ":99"