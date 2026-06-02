ì DuckDNS + Cloudflare Tunnel 

sudo npm install -g localtunnel
lt --port 8080 --subdomain tytytu91

ssh -R tenban-api:80:localhost:8080 serveo.net