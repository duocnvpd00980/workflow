sudo systemctl is-enabled nginx
sudo systemctl disable nginx
sudo systemctl enable nginx
sudo systemctl status nginx


======================================= 
[fastapi]

Tạo service:

sudo nano /etc/systemd/system/fastapi.service

Dán:

[Unit]
Description=FastAPI Workflow API
After=network-online.target

[Service]
Type=simple

User=duoc
Group=duoc

WorkingDirectory=/home/duoc/workflow/api

ExecStart=/home/duoc/.local/bin/uv run python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

Restart=always
RestartSec=5

Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target