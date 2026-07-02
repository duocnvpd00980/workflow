

🧹 Bước 0: Xóa container cũ, tạo lại sạch

    lxc delete pc-1 --force 2>/dev/null; lxc launch ubuntu:24.04 pc-1


## Bước 1: Update apt + cài dependencies hệ thống

    sudo lxc exec pc-1 -- bash -c "apt update && apt install -y wget curl gnupg xvfb fonts-liberation fonts-noto fonts-dejavu-core libnss3 libatk-bridge2.0-0t64 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2t64 libpangocairo-1.0-0 libxshmfence1 libcurl4t64 ca-certificates"


## Bước 2: Cài Google Chrome (KHÔNG dùng snap)

    sudo lxc exec pc-1 -- bash -c "
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - 2>/dev/null || true
    echo 'deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main' > /etc/apt/sources.list.d/google-chrome.list
    apt update
    apt install -y google-chrome-stable
    "


## Bước 3: Cài Python + nodriver + fastapi

    sudo lxc exec pc-1 -- bash -c "
    apt install -y python3-pip python3-venv
    pip3 install --break-system-packages nodriver fastapi uvicorn pydantic
    "


## Bước 4: Tạo thư mục + copy code client

    sudo lxc exec pc-1 -- mkdir -p /app/storage/screenshots
    sudo lxc file push ~/fb_automation_stack/lxd-client/client_app.py pc-1/app/client_app.py



## Bước 5: Sửa code client dùng Google Chrome path


sudo lxc exec pc-1 -- bash -c 'cat > /app/client_app.py << "EOF"
#!/usr/bin/env python3
"""LXD Client - Nodriver + Google Chrome"""

import asyncio
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

import nodriver as uc

# ============ CONFIG ============
STORAGE_DIR = "/app/storage"
os.makedirs(STORAGE_DIR, exist_ok=True)

CHROME_PATH = "/usr/bin/google-chrome-stable"

FINGERPRINT = {
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "viewport": {"width": 1366, "height": 768},
    "locale": "vi-VN",
    "timezone": "Asia/Ho_Chi_Minh",
    "lang": "vi,en-US,en",
}

# ============ STATE ============
_browser = None
_tab = None

# ============ MODELS ============
class TaskRequest(BaseModel):
    task_type: str
    params: Dict[str, Any] = {}

class TaskResponse(BaseModel):
    success: bool
    data: Dict[str, Any] = {}
    error: Optional[str] = None

# ============ APP ============
app = FastAPI(title="FB Client - Nodriver", version="1.0.0")

@app.get("/health")
async def health():
    chrome_exists = os.path.exists(CHROME_PATH)
    return {
        "status": "ok",
        "browser": "nodriver+chrome",
        "chrome_path": CHROME_PATH,
        "chrome_exists": chrome_exists,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/fingerprint")
async def get_fingerprint():
    return FINGERPRINT

@app.post("/task", response_model=TaskResponse)
async def execute_task(request: TaskRequest):
    global _browser, _tab
    
    try:
        data = {}
        
        if not _browser:
            _browser = await uc.start(
                headless=True,
                browser_executable_path=CHROME_PATH,
                lang=FINGERPRINT["lang"],
            )
        
        if request.task_type == "navigate":
            url = request.params.get("url")
            if not _tab:
                _tab = await _browser.get(url)
            else:
                await _tab.get(url)
            await asyncio.sleep(2)
            data = {"url": url, "title": await _tab.evaluate("document.title")}
            
        elif request.task_type == "click":
            selector = request.params.get("selector")
            elem = await _tab.select(selector)
            await elem.click()
            await asyncio.sleep(0.5)
            data = {"clicked": selector}
            
        elif request.task_type == "type":
            selector = request.params.get("selector")
            text = request.params.get("text")
            elem = await _tab.select(selector)
            await elem.send_keys(text)
            data = {"typed": text[:30] + "..." if len(text) > 30 else text}
            
        elif request.task_type == "screenshot":
            now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = request.params.get("filename", "ss_" + now_str + ".png")
            filepath = os.path.join(STORAGE_DIR, filename)
            await _tab.save_screenshot(filepath)
            data = {"screenshot": filepath}
            
        elif request.task_type == "get_html":
            html = await _tab.evaluate("document.documentElement.outerHTML")
            data = {"html_length": len(html), "preview": html[:500]}
            
        elif request.task_type == "evaluate":
            script = request.params.get("script")
            result = await _tab.evaluate(script)
            data = {"result": result}
            
        elif request.task_type == "scroll":
            direction = request.params.get("direction", "down")
            amount = request.params.get("amount", 500)
            sign = "-" if direction == "up" else ""
            js = "window.scrollBy(0, " + sign + str(amount) + ")"
            await _tab.evaluate(js)
            await asyncio.sleep(0.5)
            data = {"scrolled": direction}
            
        else:
            return TaskResponse(success=False, error="Unknown: " + request.task_type)
        
        return TaskResponse(success=True, data=data)
        
    except Exception as e:
        return TaskResponse(success=False, error=str(e))

@app.post("/shutdown")
async def shutdown():
    global _browser
    if _browser:
        _browser.stop()
    return {"status": "shutdown"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
EOF'







## Bước 6: Khởi động client

sudo lxc exec pc-1 -- bash -c "cd /app && nohup python3 client_app.py > /app/storage/client.log 2>&1 &"


## Bước 7: Test

sudo lxc list pc-1 --format=json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['state']['network']['eth0']['addresses'][0]['address'])"

sudo lxc exec pc-1 -- bash -c "cd /app && python3 client_app.py"

curl http://<IP_VỪA_LẤY>:8001/health


==================


## Bước 2: Chạy lại ở background

sudo lxc exec pc-1 -- setsid bash -c "cd /app && python3 client_app.py > /app/storage/client.log 2>&1"


## Bước 3: Kiểm tra log

sudo lxc exec pc-1 -- cat /app/storage/client.log


## Bước 4: Test lại health

curl http://10.76.182.112:8001/health


## Tôi sẽ tạo systemd service trong container để chạy persistent:

#### step 1:

sudo lxc exec pc-1 -- bash -c 'cat > /etc/systemd/system/fb-client.service << "EOF"
[Unit]
Description=FB Automation Client
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/app
ExecStart=/usr/bin/python3 /app/client_app.py
Restart=always
RestartSec=5
StandardOutput=append:/app/storage/client.log
StandardError=append:/app/storage/client.log

[Install]
WantedBy=multi-user.target
EOF'



#### step 2:

sudo lxc exec pc-1 -- systemctl daemon-reload
sudo lxc exec pc-1 -- systemctl enable fb-client
sudo lxc exec pc-1 -- systemctl start fb-client


#### step 3:

sudo lxc exec pc-1 -- systemctl status fb-client

curl http://10.76.182.112:8001/health



### step 4:

sudo lxc exec pc-1 -- apt install -y x11vnc xvfb


-----------------

✅ Bước tiếp theo: Test navigate

curl -X POST http://10.76.182.112:8001/task \
  -H "Content-Type: application/json" \
  -d '{"task_type": "navigate", "params": {"url": "https://example.com"}}'


✅ Bước tiếp theo: Test fingerprint detection

curl -X POST http://10.76.182.112:8001/task \
  -H "Content-Type: application/json" \
  -d '{"task_type": "navigate", "params": {"url": "https://pixelscan.net"}}'


======================


Lệnh 1: Chụp màn hình Xvfb trong container

sudo lxc exec pc-1 -- bash -c 'apt install -y imagemagick; DISPLAY=:99 import -window root /app/storage/screenshot_xvfb.png'


Lệnh 2: Copy ảnh ra host để xem

sudo lxc file pull pc-1/app/storage/screenshot_xvfb.png ~/screenshot_xvfb.png



















sudo lxc exec pc-1 -- bash -c "DISPLAY=:99 google-chrome-stable --no-sandbox --disable-setuid-sandbox --disable-gpu --no-first-run https://google.com 2>&1 | head -30"






sudo lxc exec pc-1 -- bash -c "DISPLAY=:99 firefox-esr https://google.com 2>&1 | head -20"



sudo lxc exec pc-1 -- bash -c "
rm -f /etc/resolv.conf
echo 'nameserver 8.8.8.8' > /etc/resolv.conf
echo 'nameserver 8.8.4.4' >> /etc/resolv.conf
cat /etc/resolv.conf
"


-------------------------

sudo lxc exec pc-1 -- bash -c "
add-apt-repository -y ppa:mozillateam/ppa
apt update
apt install -y firefox-esr
"
sudo lxc exec pc-1 -- bash -c "DISPLAY=:99 firefox-esr https://google.com &"





















=================================

uoc@duoc-MS-7A70:~$ sudo lxc exec pc-1 -- bash -c "DISPLAY=:99 firefox-esr https://142.250.198.174 &"
duoc@duoc-MS-7A70:~$ sudo lxc exec pc-1 -- bash -c "aa-disable firefox 2>/dev/null || ln -s /etc/apparmor.d/firefox /etc/apparmor.d/disable/; apparmor_parser -R /etc/apparmor.d/firefox 2>/dev/null || true"
duoc@duoc-MS-7A70:~$ sudo lxc exec pc-1 -- bash -c "pkill -9 firefox; sleep 2; DISPLAY=:99 firefox-esr https://google.com &"
duoc@duoc-MS-7A70:~$ sudo lxc exec pc-1 -- bash -c "systemctl stop apparmor; systemctl disable apparmor"
Warning: The unit file, source configuration file or drop-ins of apparmor.service changed on disk. Run 'systemctl daemon-reload' to reload units.
Synchronizing state of apparmor.service with SysV service script with /usr/lib/systemd/systemd-sysv-install.
Executing: /usr/lib/systemd/systemd-sysv-install disable apparmor
Removed "/etc/systemd/system/sysinit.target.wants/apparmor.service".
duoc@duoc-MS-7A70:~$ sudo lxc exec pc-1 -- bash -c "DISPLAY=:99 firefox-esr https://google.com 2>&1 | head -20"


=================================


duoc@duoc-MS-7A70:~$ sudo lxc exec pc-1 -- bash -c "cat > /etc/systemd/system/pc1-api.service << 'EOF'
[Unit]
Description=PC-1 Browser API
After=network.target

[Service]
Type=simple
WorkingDirectory=/app
ExecStart=/usr/bin/python3 /app/pc1_api.py
Restart=always
StandardOutput=append:/app/storage/api.log
StandardError=append:/app/storage/api.log

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable pc1-api
systemctl start pc1-api
"
Created symlink /etc/systemd/system/multi-user.target.wants/pc1-api.service → /etc/systemd/system/pc1-api.service.
duoc@duoc-MS-7A70:~$ sudo lxc exec pc-1 -- systemctl status pc1-api --no-pager
● pc1-api.service - PC-1 Browser API
     Loaded: loaded (/etc/systemd/system/pc1-api.service; enabled; preset: enabled)
     Active: active (running) since Thu 2026-07-02 11:53:06 UTC; 4s ago
   Main PID: 11710 (python3)
      Tasks: 1 (limit: 38329)
     Memory: 35.5M (peak: 35.6M)
        CPU: 423ms
     CGroup: /system.slice/pc1-api.service
             └─11710 /usr/bin/python3 /app/pc1_api.py

Jul 02 11:53:06 pc-1 systemd[1]: Started pc1-api.service - PC-1 Browser API.
duoc@duoc-MS-7A70:~$ curl http://10.76.182.112:8002/health
curl: (7) Failed to connect to 10.76.182.112 port 8002 after 3109 ms: Couldn't connect to server
duoc@duoc-MS-7A70:~$ sudo lxc exec pc-1 -- systemctl status pc1-api --no-pager
● pc1-api.service - PC-1 Browser API
     Loaded: loaded (/etc/systemd/system/pc1-api.service; enabled; preset: enabled)
     Active: active (running) since Thu 2026-07-02 11:53:06 UTC; 22s ago
   Main PID: 11710 (python3)
      Tasks: 1 (limit: 38329)
     Memory: 35.5M (peak: 35.6M)
        CPU: 445ms
     CGroup: /system.slice/pc1-api.service
             └─11710 /usr/bin/python3 /app/pc1_api.py

Jul 02 11:53:06 pc-1 systemd[1]: Started pc1-api.service - PC-1 Browser API.
duoc@duoc-MS-7A70:~$ sudo lxc exec pc-1 -- cat /app/storage/api.log
INFO:     Started server process [11710]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8002 (Press CTRL+C to quit)
duoc@duoc-MS-7A70:~$ curl http://10.76.182.112:8002/health
curl: (7) Failed to connect to 10.76.182.112 port 8002 after 3104 ms: Couldn't connect to server
duoc@duoc-MS-7A70:~$ sudo lxc list pc-1 --format=json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['state']['network']['eth0']['addresses'][0]['address'])"
10.76.182.206
duoc@duoc-MS-7A70:~$ 



http://10.76.182.206:8002/health

http://192.168.101.18:6080/vnc.html


------------------------------------

# 2. Cài lại nodriver
sudo lxc exec pc-1 -- pip3 install --break-system-packages nodriver

# 3. Tạo user thường để chạy nodriver
sudo lxc exec pc-1 -- bash -c "useradd -m -s /bin/bash automation 2>/dev/null || true; echo 'automation:auto123' | chpasswd"


-------------------------------------------------

sudo lxc exec pc-1 -- bash -c 'printf "%s\n" "import os" "import asyncio" "from datetime import datetime" "from typing import Optional, Dict, Any" "from fastapi import FastAPI" "from pydantic import BaseModel" "import uvicorn" "import nodriver as uc" "" "STORAGE_DIR = \"/app/storage\"" "SCREENSHOTS_DIR = os.path.join(STORAGE_DIR, \"screenshots\")" "os.makedirs(SCREENSHOTS_DIR, exist_ok=True)" "" "_browser = None" "_tab = None" "" "class TaskRequest(BaseModel):" "    task_type: str" "    params: Dict[str, Any] = {}" "" "class TaskResponse(BaseModel):" "    success: bool" "    data: Dict[str, Any] = {}" "    error: Optional[str] = None" "" "app = FastAPI(title=\"PC-1 Browser API\", version=\"1.0.0\")" "" "@app.get(\"/health\")" "def health():" "    return {\"status\": \"ok\", \"timestamp\": datetime.now().isoformat()}" "" "@app.post(\"/task\", response_model=TaskResponse)" "async def execute_task(request: TaskRequest):" "    global _browser, _tab" "    try:" "        data = {}" "        if not _browser:" "            _browser = await uc.start(headless=False, browser_executable_path=\"/usr/bin/google-chrome-stable\", no_sandbox=True)" "        if request.task_type == \"navigate\":" "            url = request.params.get(\"url\")" "            if not _tab:" "                _tab = await _browser.get(url)" "            else:" "                await _tab.get(url)" "            await asyncio.sleep(2)" "            data = {\"url\": url}" "        elif request.task_type == \"click\":" "            selector = request.params.get(\"selector\")" "            elem = await _tab.select(selector)" "            await elem.click()" "            data = {\"clicked\": selector}" "        elif request.task_type == \"type\":" "            selector = request.params.get(\"selector\")" "            text = request.params.get(\"text\")" "            elem = await _tab.select(selector)" "            await elem.send_keys(text)" "            data = {\"typed\": text[:30] + \"...\" if len(text) > 30 else text}" "        elif request.task_type == \"screenshot\":" "            filename = request.params.get(\"filename\", \"ss_\" + datetime.now().strftime(\"%Y%m%d_%H%M%S\") + \".png\")" "            filepath = os.path.join(SCREENSHOTS_DIR, filename)" "            await _tab.save_screenshot(filepath)" "            data = {\"screenshot\": filepath}" "        else:" "            return TaskResponse(success=False, error=\"Unknown: \" + request.task_type)" "        return TaskResponse(success=True, data=data)" "    except Exception as e:" "        return TaskResponse(success=False, error=str(e))" "" "@app.post(\"/shutdown\")" "async def shutdown():" "    global _browser" "    if _browser:" "        _browser.stop()" "    return {\"status\": \"shutdown\"}" "" "if __name__ == \"__main__\":" "    uvicorn.run(app, host=\"0.0.0.0\", port=8002)" > /app/pc1_api.py'



-------------------------------------

sudo lxc list pc-1 --format=json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['state']['network']['eth0']['addresses'][0]['address'])"


curl -X POST http://10.76.182.206:8002/task \
  -H "Content-Type: application/json" \
  -d '{"task_type": "navigate", "params": {"url": "https://google.com"}}'