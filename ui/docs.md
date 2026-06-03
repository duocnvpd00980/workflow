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





sudo systemctl status nginx
sudo systemctl restart nginx
sudo nano /etc/nginx/sites-available/nginx_gateway.conf


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
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}



sudo ln -s /etc/nginx/sites-available/nginx_gateway.conf /etc/nginx/sites-enabled/