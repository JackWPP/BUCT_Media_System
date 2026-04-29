#!/usr/bin/env bash
# 纯 IP 访问 Nginx 配置
# 在服务器上执行: sudo bash nginx-ip.sh
set -e

cat > /etc/nginx/sites-available/default << 'NGINX'
server {
    listen 80 default_server;
    server_name _;

    root /home/wwwroot/visual_buct;
    index index.html;

    client_max_body_size 25M;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_connect_timeout 60s;
        proxy_read_timeout 60s;
    }
}
NGINX

rm -f /etc/nginx/sites-enabled/cpmz.buct.edu.cn.conf
ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default
nginx -t && nginx -s reload

echo ""
echo "Done! Access at http://121.195.148.85"
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://127.0.0.1/
