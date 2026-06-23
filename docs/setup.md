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


==================================================

sudo nano /etc/nginx/sites-enabled/nginx_gateway.conf

duoc@duoc-MS-7A70:~$ cat /etc/nginx/sites-enabled/nginx_gateway.conf
server {
    listen 80;
    server_name localhost;

    # 1. Đường dẫn đến thư mục chứa UI tĩnh (Frontend)
    location / {
        root /home/duoc/workflow/ui/dist;
        index index.html index.htm;
        try_files $uri $uri/ /index.html;
    }

    # 2. Đường dẫn Reverse Proxy sang API (FastAPI cổng 8000)
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
	proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
duoc@duoc-MS-7A70:~$ 







sudo systemctl daemon-reload
sudo systemctl restart fastapi
sudo systemctl status fastapi
sudo systemctl enable fastapi
sudo journalctl -u fastapi.service -f
sudo systemctl stop fastapi



comfyui
python main.py --listen 127.0.0.1 --port 8188





https://developers.buffer.com/
https://publish.buffer.com/settings/api
mLsaw1srstOY_V-WP2GdVpNwdPdybSfKC2fBhVUz8jR



https://www.canva.dev/docs/?utm_source=chatgpt.com



setup: 306x306 - thay đổi kích thước-
https://scontent.fdad3-6.fna.fbcdn.net/v/t51.82787-15/728156190_18174092326418097_4814652062547422421_n.jpg?stp=dst-jpg_tt6&cstp=mx3125x3125&ctp=s306x306&_nc_cat=104&ccb=1-7&_nc_sid=714c7a&_nc_ohc=iISA281JIQgQ7kNvwFbugTC&_nc_oc=AdpD3fZF8vMVSQ4Fwava-AV8Ew9ywk_UrAFpIG9g42MtY5nPI48q8aXqeQpmXMuWbaA&_nc_zt=23&_nc_ht=scontent.fdad3-6.fna&_nc_gid=wpWvPWoHhBBMOX6iapJelA&_nc_ss=7b289&oh=00_Af9Ms3OuXAcIxyehVDrtP7hnx2cwUYYV-1T81dRaFlhVJg&oe=6A400DD5