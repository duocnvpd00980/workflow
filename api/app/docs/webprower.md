# Tắt GNOME tiết kiệm điện
sudo systemctl stop gdm

# Chạy virtual display thay thế
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99



import os
os.environ["DISPLAY"] = ":99"

browser = await uc.start(headless=False)