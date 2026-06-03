uv run npm run preview
# Hoặc nếu chạy trực tiếp qua vite:
uv run npx vite preview --host


sudo nano /etc/systemd/system/ngrok.service

sudo nano /etc/systemd/system/ngrok-backend.service


============


sudo nano /etc/ngrok.yml


version: "2"
authtoken: 2dkJ53HSSUbsGGHQCi2F9p1nt63_FXaNseiL64sY7La5QM48

tunnels:
  frontend:
    addr: 4174
    proto: http
    domain: viable-superb-basilisk.ngrok-free.app
    
  backend:
    addr: 8000
    proto: http



sudo nano /etc/systemd/system/ngrok.service


[Unit]
Description=Ngrok Tunnel (Frontend + Backend)
After=network.target

[Service]
User=duoc
Type=simple
ExecStart=/snap/bin/ngrok start --all --config=/etc/ngrok.yml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target





sudo systemctl daemon-reload
sudo systemctl enable ngrok
sudo systemctl restart ngrok
sudo systemctl status ngrok