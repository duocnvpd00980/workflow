# ============================================
# HUONG DAN CHUAN - LXD Container + Firefox + noVNC
# ============================================
# May: Ubuntu 24.04 Host
# Muc dich: Tao container co desktop, vao web qua noVNC
# ============================================

## PHAN 1: TAO CONTAINER

### 1.1 Tao container Ubuntu 24.04
```bash
sudo lxc launch ubuntu:24.04 pc-1
sleep 15
```

### 1.2 Vao container
```bash
sudo lxc exec pc-1 -- bash
```

## PHAN 2: CAI DAT BEN TRONG CONTAINER

### 2.1 Doi mirror nhanh (Viettel)
```bash
sed -i 's|http://archive.ubuntu.com/ubuntu|http://mirror.viettelcloud.vn/ubuntu|g' /etc/apt/sources.list
sed -i 's|http://security.ubuntu.com/ubuntu|http://mirror.viettelcloud.vn/ubuntu|g' /etc/apt/sources.list
apt update -qq
```

### 2.2 Cai dependencies
```bash
apt install -y -qq \
    xvfb \
    x11vnc \
    novnc \
    websockify \
    python3-websockify \
    dbus-x11 \
    openbox \
    tint2 \
    curl \
    wget
```

### 2.3 Cai Firefox ESR (khong snap)
```bash
apt install -y -qq software-properties-common
add-apt-repository -y ppa:mozillateam/ppa
apt update -qq
apt install -y -qq firefox-esr
```

### 2.4 Tat AppArmor cho Firefox
```bash
ln -s /etc/apparmor.d/firefox /etc/apparmor.d/disable/ 2>/dev/null || true
apparmor_parser -R /etc/apparmor.d/firefox 2>/dev/null || true
```

### 2.5 Sua DNS (quan trong)
```bash
rm -f /etc/resolv.conf
echo 'nameserver 8.8.8.8' > /etc/resolv.conf
echo 'nameserver 8.8.4.4' >> /etc/resolv.conf
```

### 2.6 Tao thu muc luu tru
```bash
mkdir -p /app/storage /app/firefox-profiles
chmod -R 777 /app
```

## PHAN 3: KHOI DONG DESKTOP + VNC + noVNC

### 3.1 Khoi dong Xvfb
```bash
Xvfb :99 -screen 0 1366x768x24 +extension RANDR &
export DISPLAY=:99
sleep 2
```

### 3.2 Khoi dong Openbox + Tint2
```bash
openbox &
tint2 &
sleep 1
```

### 3.3 Khoi dong x11vnc
```bash
x11vnc -display :99 -nopw -forever -shared -noxdamage -noxfixes -noxrecord &
```

### 3.4 Khoi dong noVNC
```bash
/usr/share/novnc/utils/novnc_proxy --vnc localhost:5900 --listen 0.0.0.0:6080 &
```

### 3.5 Mo Firefox
```bash
firefox-esr https://facebook.com &
```

## PHAN 4: FORWARD PORT RA HOST

### 4.1 Tu host, chay:
```bash
sudo lxc config device add pc-1 novnc proxy listen=tcp:0.0.0.0:6080 connect=tcp:127.0.0.1:6080
```

### 4.2 Lay IP host
```bash
hostname -I | awk '{print $1}'
```

### 4.3 Mo browser
```
http://<IP_HOST>:6080/vnc.html
```

## PHAN 5: TAO SYSTEMD SERVICE (TU DONG KHOI DONG)

### 5.1 Xvfb service
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

### 5.2 x11vnc service
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

### 5.3 noVNC service
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

### 5.4 Desktop service
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

### 5.5 Enable va start tat ca
```bash
systemctl daemon-reload
systemctl enable xvfb x11vnc novnc desktop
systemctl start xvfb x11vnc novnc desktop
```

## PHAN 6: LUU COOKIES

### 6.1 Sau khi dang nhap Facebook, luu profile
```bash
cp -r /tmp/firefox-profile /app/firefox-profiles/default
chmod -R 777 /app/firefox-profiles
```

### 6.2 Mo Firefox voi cookies da luu
```bash
firefox-esr --profile /app/firefox-profiles/default https://facebook.com &
```

## PHAN 7: LOI THUONG GAP VA CACH FIX

| Loi | Nguyen nhan | Cach fix |
|-----|-------------|----------|
| Khong vao duoc noVNC | Port khong forward | `sudo lxc config device add pc-1 novnc proxy listen=tcp:0.0.0.0:6080 connect=tcp:127.0.0.1:6080` |
| Firefox khong co mang | AppArmor chan | `ln -s /etc/apparmor.d/firefox /etc/apparmor.d/disable/` |
| Firefox khong co mang | DNS 127.0.0.53 | `echo 'nameserver 8.8.8.8' > /etc/resolv.conf` |
| Chrome khong chay | La snap | Dung Firefox ESR thay the |
| apt lock | Process cu chua xong | `rm -f /var/cache/debconf/config.dat.lock; dpkg --configure -a` |
| Container khong co internet | LXD bridge loi | `lxc network set lxdbr0 ipv4.nat true` |

## PHAN 8: DON DEP (XOA SACH)

```bash
sudo lxc stop pc-1 --force
sudo lxc delete pc-1 --force
sudo lxc config device remove pc-1 novnc 2>/dev/null || true
```

## PHAN 9: TAO NHIEU MAY (SCALE)

```bash
for i in {2..10}; do
    sudo lxc launch ubuntu:24.04 pc-$i
    # Lap lai cac buoc 2-5 ben tren
    # Moi may co port noVNC khac nhau: 6080 + i
done
```

## PHAN 10: THONG TIN QUAN TRONG

- RAM moi container: ~500MB (Openbox + Tint2 + Firefox)
- 32GB RAM host = chay duoc ~50 container
- Khong dung snap (chromium-browser, firefox snap deu loi)
- Luon tat AppArmor cho Firefox
- Luon sua DNS sang 8.8.8.8
- noVNC port: 6080 (co the doi)
- VNC port: 5900 (noVNC proxy den day)

## PHAN 11: LENH KIEM TRA NHANH

```bash
# Kiem tra container dang chay
sudo lxc list

# Kiem tra service trong container
sudo lxc exec pc-1 -- systemctl status xvfb x11vnc novnc desktop --no-pager

# Kiem tra process
sudo lxc exec pc-1 -- ps aux | grep -E 'Xvfb|x11vnc|openbox|firefox'

# Kiem tra mang trong container
sudo lxc exec pc-1 -- curl -I https://google.com

# Kiem tra port noVNC
sudo ss -tlnp | grep 6080
```

===========================================
EOF



















================[FIX CHORME MẤT MẬNG]=================


sudo lxc exec pc-1 -- bash <<'EOF'

cat >/etc/systemd/system/xvfb.service <<'EOL'
[Unit]
Description=Xvfb
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/Xvfb :99 -screen 0 1920x1080x24
Restart=always

[Install]
WantedBy=multi-user.target
EOL

cat >/etc/systemd/system/desktop.service <<'EOL'
[Unit]
Description=Openbox
After=xvfb.service
Requires=xvfb.service

[Service]
Type=simple
Environment=DISPLAY=:99
ExecStart=/usr/bin/openbox
Restart=always

[Install]
WantedBy=multi-user.target
EOL

cat >/etc/systemd/system/x11vnc.service <<'EOL'
[Unit]
Description=x11vnc
After=xvfb.service desktop.service
Requires=xvfb.service desktop.service

[Service]
Type=simple
Environment=DISPLAY=:99
ExecStart=/usr/bin/x11vnc -display :99 -nopw -forever -shared -noxdamage -noxfixes
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOL

systemctl daemon-reload

systemctl enable xvfb.service
systemctl enable desktop.service
systemctl enable x11vnc.service
systemctl enable novnc.service

systemctl restart xvfb.service
sleep 2
systemctl restart desktop.service
sleep 2
systemctl restart x11vnc.service
sleep 2
systemctl restart novnc.service

systemctl --no-pager --full status xvfb.service desktop.service x11vnc.service novnc.service

EOF

=======================================================

[Unit]
Description=PC1 API
After=desktop.service

[Service]
User=automation
WorkingDirectory=/app
Environment=DISPLAY=:99
Environment=HOME=/home/automation

ExecStart=/usr/bin/python3 /app/pc1_api.py

Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target


================[FIX CHORME MẤT MẬNG]=================

1. Kiểm tra display

sudo lxc exec pc-1 -- ls -l /tmp/.X11-unix

Phải có:

X99

================[FIX CHORME MẤT MẬNG]=================

2. Mở Chrome trên display mới
sudo lxc exec pc-1 -- bash -c '
export DISPLAY=:99
rm -rf /tmp/chrome-test
google-chrome-stable \
  --user-data-dir=/tmp/chrome-test \
  --no-sandbox \
  --disable-gpu \
  https://www.google.com
'


================[FIX CHORME MẤT MẬNG]=================

3. Nếu vẫn ERR_INTERNET_DISCONNECTED, chạy ngay:
sudo lxc exec pc-1 -- bash -c '
export DISPLAY=:99
google-chrome-stable \
  --user-data-dir=/tmp/chrome-test \
  --no-sandbox \
  --headless=new \
  --dump-dom https://www.google.com | head -20
'


================[FIX CHORME MẤT MẬNG]=================

http://192.168.101.18:6080/vnc.html



1. http://10.76.182.206:8002/health
2. POST http://10.76.182.206:8002/open
3. POST http://10.76.182.206:8002/navigate
4. http://10.76.182.206:8002/title
5. http://10.76.182.206:8002/screenshot