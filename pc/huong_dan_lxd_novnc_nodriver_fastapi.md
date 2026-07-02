# ============================================
# HUONG DAN CHUAN - LXD + noVNC + nodriver + FastAPI
# ============================================
# Tao 1 may (pc-1) co:
#   - Desktop Xvfb + Openbox + Tint2
#   - noVNC (xem qua web)
#   - Firefox (thu cong)
#   - nodriver + FastAPI (tu dong)
# ============================================

## PHAN 1: TAO CONTAINER

```bash
sudo lxc launch ubuntu:24.04 pc-1
sleep 15
```

## PHAN 2: CAI DAT BEN TRONG CONTAINER

### 2.1 Vao container
```bash
sudo lxc exec pc-1 -- bash
```

### 2.2 Doi mirror nhanh
```bash
sed -i 's|http://archive.ubuntu.com/ubuntu|http://mirror.viettelcloud.vn/ubuntu|g' /etc/apt/sources.list
sed -i 's|http://security.ubuntu.com/ubuntu|http://mirror.viettelcloud.vn/ubuntu|g' /etc/apt/sources.list
apt update -qq
```

### 2.3 Cai desktop + VNC + noVNC
```bash
export DEBIAN_FRONTEND=noninteractive
apt install -y -qq \
    xvfb x11vnc novnc websockify python3-websockify \
    dbus-x11 openbox tint2 \
    curl wget \
    python3-pip \
    fonts-liberation fonts-noto
```

### 2.4 Cai Firefox ESR (khong snap)
```bash
apt install -y -qq software-properties-common
add-apt-repository -y ppa:mozillateam/ppa
apt update -qq
apt install -y -qq firefox-esr
```

### 2.5 Tat AppArmor cho Firefox
```bash
ln -s /etc/apparmor.d/firefox /etc/apparmor.d/disable/ 2>/dev/null || true
apparmor_parser -R /etc/apparmor.d/firefox 2>/dev/null || true
```

### 2.6 Sua DNS
```bash
rm -f /etc/resolv.conf
echo 'nameserver 8.8.8.8' > /etc/resolv.conf
echo 'nameserver 8.8.4.4' >> /etc/resolv.conf
```

### 2.7 Tao thu muc
```bash
mkdir -p /app/storage/screenshots /app/firefox-profiles
chmod -R 777 /app
```

### 2.8 Tao user chay API
```bash
useradd -m -s /bin/bash automation 2>/dev/null || true
echo 'automation:auto123' | chpasswd
```

## PHAN 3: CAI nodriver + FastAPI

### 3.1 Cai nodriver
```bash
pip3 install --break-system-packages nodriver
```

### 3.2 Cai FastAPI + uvicorn
```bash
pip3 install --break-system-packages --ignore-installed fastapi uvicorn
```

### 3.3 Tao file API
Chay tung lenh:

```bash
cd /app
```

```bash
printf "%s
" "import os" "import asyncio" "from datetime import datetime" "from typing import Optional, Dict, Any" "from fastapi import FastAPI" "from pydantic import BaseModel" "import uvicorn" "import nodriver as uc" "" "STORAGE_DIR = "/app/storage"" "SCREENSHOTS_DIR = os.path.join(STORAGE_DIR, "screenshots")" "os.makedirs(SCREENSHOTS_DIR, exist_ok=True)" "" "_browser = None" "_tab = None" "" "class TaskRequest(BaseModel):" "    task_type: str" "    params: Dict[str, Any] = {}" "" "class TaskResponse(BaseModel):" "    success: bool" "    data: Dict[str, Any] = {}" "    error: Optional[str] = None" "" "app = FastAPI(title="PC-1 Browser API", version="1.0.0")" "" "@app.get("/health")" "def health():" "    return {"status": "ok", "timestamp": datetime.now().isoformat()}" "" "@app.post("/task", response_model=TaskResponse)" "async def execute_task(request: TaskRequest):" "    global _browser, _tab" "    try:" "        data = {}" "        if not _browser:" "            _browser = await uc.start(headless=False, browser_executable_path="/usr/bin/google-chrome-stable", no_sandbox=True)" "        if request.task_type == "navigate":" "            url = request.params.get("url")" "            if not _tab:" "                _tab = await _browser.get(url)" "            else:" "                await _tab.get(url)" "            await asyncio.sleep(2)" "            data = {"url": url}" "        elif request.task_type == "click":" "            selector = request.params.get("selector")" "            elem = await _tab.select(selector)" "            await elem.click()" "            data = {"clicked": selector}" "        elif request.task_type == "type":" "            selector = request.params.get("selector")" "            text = request.params.get("text")" "            elem = await _tab.select(selector)" "            await elem.send_keys(text)" "            data = {"typed": text[:30] + "..." if len(text) > 30 else text}" "        elif request.task_type == "screenshot":" "            filename = request.params.get("filename", "ss_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".png")" "            filepath = os.path.join(SCREENSHOTS_DIR, filename)" "            await _tab.save_screenshot(filepath)" "            data = {"screenshot": filepath}" "        else:" "            return TaskResponse(success=False, error="Unknown: " + request.task_type)" "        return TaskResponse(success=True, data=data)" "    except Exception as e:" "        return TaskResponse(success=False, error=str(e))" "" "@app.post("/shutdown")" "async def shutdown():" "    global _browser" "    if _browser:" "        _browser.stop()" "    return {"status": "shutdown"}" "" "if __name__ == "__main__":" "    uvicorn.run(app, host="0.0.0.0", port=8002)" > /app/pc1_api.py
```

## PHAN 4: TAO SYSTEMD SERVICES

### 4.1 Xvfb service
```bash
cat > /etc/systemd/system/xvfb.service << 'EOF'
[Unit]
Description=Xvfb
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/Xvfb :99 -screen 0 1366x768x24 +extension RANDR
Restart=always

[Install]
WantedBy=multi-user.target
EOF
```

### 4.2 x11vnc service
```bash
cat > /etc/systemd/system/x11vnc.service << 'EOF'
[Unit]
Description=x11vnc
After=xvfb.service

[Service]
Type=simple
ExecStart=/usr/bin/x11vnc -display :99 -nopw -forever -shared -noxdamage -noxfixes
Restart=always

[Install]
WantedBy=multi-user.target
EOF
```

### 4.3 noVNC service
```bash
cat > /etc/systemd/system/novnc.service << 'EOF'
[Unit]
Description=noVNC
After=x11vnc.service

[Service]
Type=simple
ExecStart=/usr/share/novnc/utils/novnc_proxy --vnc localhost:5900 --listen 0.0.0.0:6080
Restart=always

[Install]
WantedBy=multi-user.target
EOF
```

### 4.4 Desktop service
```bash
cat > /etc/systemd/system/desktop.service << 'EOF'
[Unit]
Description=Desktop
After=novnc.service

[Service]
Type=simple
Environment=DISPLAY=:99
ExecStart=/usr/bin/openbox
Restart=always

[Install]
WantedBy=multi-user.target
EOF
```

### 4.5 API service
```bash
cat > /etc/systemd/system/pc1-api.service << 'EOF'
[Unit]
Description=PC-1 Browser API
After=desktop.service

[Service]
Type=simple
User=automation
Environment=DISPLAY=:99
Environment=HOME=/home/automation
WorkingDirectory=/app
ExecStart=/usr/bin/python3 /app/pc1_api.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF
```

### 4.6 Enable va start
```bash
systemctl daemon-reload
systemctl enable xvfb x11vnc novnc desktop pc1-api
systemctl start xvfb x11vnc novnc desktop pc1-api
```

## PHAN 5: FORWARD PORT RA HOST

Tu host chay:
```bash
sudo lxc config device add pc-1 novnc proxy listen=tcp:0.0.0.0:6080 connect=tcp:127.0.0.1:6080
sudo lxc config device add pc-1 api proxy listen=tcp:0.0.0.0:8002 connect=tcp:127.0.0.1:8002
```

## PHAN 6: LAY IP VA TRUY CAP

### 6.1 Lay IP host
```bash
hostname -I | awk '{print $1}'
```

### 6.2 Truy cap noVNC
```
http://<IP_HOST>:6080/vnc.html
```

### 6.3 Truy cap API
```
http://<IP_HOST>:8002/health
```

## PHAN 7: TEST API

### 7.1 Health check
```bash
curl http://localhost:8002/health
```

### 7.2 Navigate
```bash
curl -X POST http://localhost:8002/task \
  -H "Content-Type: application/json" \
  -d '{"task_type": "navigate", "params": {"url": "https://google.com"}}'
```

### 7.3 Click
```bash
curl -X POST http://localhost:8002/task \
  -H "Content-Type: application/json" \
  -d '{"task_type": "click", "params": {"selector": "button"}}'
```

### 7.4 Type
```bash
curl -X POST http://localhost:8002/task \
  -H "Content-Type: application/json" \
  -d '{"task_type": "type", "params": {"selector": "input", "text": "hello"}}'
```

### 7.5 Screenshot
```bash
curl -X POST http://localhost:8002/task \
  -H "Content-Type: application/json" \
  -d '{"task_type": "screenshot"}'
```

### 7.6 Shutdown
```bash
curl -X POST http://localhost:8002/shutdown
```

## PHAN 8: LUU COOKIES

Sau khi dang nhap Facebook thu cong qua noVNC:

```bash
sudo lxc exec pc-1 -- bash -c "cp -r /tmp/firefox-profile /app/firefox-profiles/default; chmod -R 777 /app/firefox-profiles"
```

## PHAN 9: TAO 10 MAY (pc-1 den pc-10)

### 9.1 Snapshot pc-1
```bash
sudo lxc stop pc-1
sudo lxc snapshot pc-1 clean-install
```

### 9.2 Copy ra 9 may
```bash
for i in {2..10}; do
    echo "Tao pc-$i..."
    sudo lxc copy pc-1/clean-install pc-$i
    sudo lxc start pc-$i
    sleep 5

    # Forward port noVNC
    NOVNC_PORT=$((6080 + i - 1))
    sudo lxc config device add pc-$i novnc proxy listen=tcp:0.0.0.0:$NOVNC_PORT connect=tcp:127.0.0.1:6080

    # Forward port API
    API_PORT=$((8002 + i - 1))
    sudo lxc config device add pc-$i api proxy listen=tcp:0.0.0.0:$API_PORT connect=tcp:127.0.0.1:8002

    echo "  pc-$i: noVNC port $NOVNC_PORT, API port $API_PORT"
done

# Start lai pc-1
sudo lxc start pc-1
```

### 9.3 Danh sach may
| May | noVNC Port | API Port |
|-----|-----------|----------|
| pc-1 | 6080 | 8002 |
| pc-2 | 6081 | 8003 |
| pc-3 | 6082 | 8004 |
| ... | ... | ... |
| pc-10 | 6089 | 8011 |

## PHAN 10: LENH KIEM TRA NHANH

```bash
# Xem container dang chay
sudo lxc list

# Kiem tra service
sudo lxc exec pc-1 -- systemctl status xvfb x11vnc novnc desktop pc1-api --no-pager

# Kiem tra process
sudo lxc exec pc-1 -- ps aux | grep -E 'Xvfb|x11vnc|openbox|firefox|python3'

# Kiem tra log API
sudo lxc exec pc-1 -- journalctl -u pc1-api --no-pager -n 20

# Kiem tra mang
sudo lxc exec pc-1 -- curl -I https://google.com

# Kiem tra port
sudo ss -tlnp | grep -E '6080|8002'
```

## PHAN 11: LOI THUONG GAP

| Loi | Nguyen nhan | Cach fix |
|-----|-------------|----------|
| Khong vao duoc noVNC | Port chua forward | `sudo lxc config device add pc-1 novnc proxy ...` |
| Firefox khong co mang | AppArmor chan | `ln -s /etc/apparmor.d/firefox /etc/apparmor.d/disable/` |
| Firefox khong co mang | DNS 127.0.0.53 | `echo 'nameserver 8.8.8.8' > /etc/resolv.conf` |
| API khong chay | Thieu DISPLAY | Them `Environment=DISPLAY=:99` trong service |
| nodriver loi | Chay root | Tao user `automation`, chay API duoi user do |
| apt lock | Process cu | `rm -f /var/cache/debconf/config.dat.lock; dpkg --configure -a` |

## PHAN 12: DON DEP

```bash
# Xoa 1 may
sudo lxc stop pc-1 --force
sudo lxc delete pc-1 --force

# Xoa tat ca
for i in {1..10}; do
    sudo lxc stop pc-$i --force 2>/dev/null || true
    sudo lxc delete pc-$i --force 2>/dev/null || true
done
```

===========================================




sudo lxc exec pc-1 -- bash <<'EOF'
cat >/app/pc1_api.py <<'PY'
import os
import asyncio

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import nodriver as uc

os.environ["DISPLAY"] = ":99"

app = FastAPI(title="PC1 Browser API")

browser = None
tab = None


class NavigateRequest(BaseModel):
    url: str


async def get_browser():
    global browser, tab

    if browser is None:
        browser = await uc.start(
            headless=False,
            browser_executable_path="/usr/bin/google-chrome-stable",
            browser_args=[
                "--user-data-dir=/home/automation/chrome-profile",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )

        tab = await browser.get("about:blank")

    return browser


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/alive")
async def alive():
    global browser, tab

    return {
        "browser": browser is not None,
        "tab": tab is not None,
    }


@app.post("/open")
async def open_browser():
    await get_browser()
    return {"success": True}


@app.post("/navigate")
async def navigate(req: NavigateRequest):
    global tab

    await get_browser()

    await tab.get(req.url)

    await asyncio.sleep(2)

    return {
        "success": True,
        "title": await tab.evaluate("document.title"),
        "url": req.url,
    }


@app.post("/google")
async def google():
    global tab

    await get_browser()

    await tab.get("https://www.google.com")

    await asyncio.sleep(2)

    return {
        "success": True,
        "title": await tab.evaluate("document.title"),
    }


@app.get("/title")
async def title():
    global tab

    if tab is None:
        return {"success": False}

    return {
        "success": True,
        "title": await tab.evaluate("document.title"),
    }


@app.get("/screenshot")
async def screenshot():
    global tab

    if tab is None:
        return {"success": False}

    path = "/tmp/test.png"

    await tab.save_screenshot(path)

    return {
        "success": True,
        "file": path,
    }


# KHÔNG browser.stop()
# KHÔNG endpoint /close

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
PY

systemctl restart pc1-api
EOF





======================

sudo lxc stop pc-1

sudo lxc stop pc-1




























?/////////////////


sudo lxc start pc-1
sudo lxc exec pc-1 -- systemctl start pc1-api



curl -X POST http://10.76.182.206:8002/navigate \
  -H "Content-Type: application/json" \
  -d '{"url":"https://google.com"}'