# BUCT Media System 部署指南

本指南详细说明如何将 BUCT Media System 部署到 Ubuntu/Debian 云服务器。

---

## 📋 目录

1. [环境要求](#环境要求)
2. [服务器初始化](#服务器初始化)
3. [上传项目代码](#上传项目代码)
4. [部署后端](#部署后端)
5. [部署前端](#部署前端)
6. [配置 Nginx](#配置-nginx)
7. [配置 Systemd 服务](#配置-systemd-服务)
8. [启动与验证](#启动与验证)
9. [常见问题](#常见问题)
10. [维护命令](#维护命令)

---

## 环境要求

| 组件 | 版本要求 | 说明 |
|------|----------|------|
| 操作系统 | Ubuntu 20.04+ / Debian 11+ | 推荐 Ubuntu 22.04 LTS |
| Python | 3.10+ | 后端运行环境 |
| Node.js | 18+ | 前端构建 |
| Nginx | 1.18+ | 反向代理 |
| RAM | 2GB+ | 建议 4GB |
| 磁盘 | 20GB+ | 取决于照片存储量 |

---

## 服务器初始化

### 1. 连接服务器

```bash
ssh root@your-server-ip
```

### 2. 更新系统

```bash
apt update && apt upgrade -y
```

### 3. 安装基础依赖

```bash
apt install -y python3 python3-pip python3-venv nginx curl git
```

### 4. 安装 Node.js 18

```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt install -y nodejs
```

### 5. 验证安装

```bash
python3 --version   # 应显示 3.10+
node --version      # 应显示 v18+
nginx -v            # 应显示 1.18+
```

---

## 上传项目代码

### 方法一：使用 Git（推荐）

```bash
# 创建目录
mkdir -p /var/www/buct_media
cd /var/www/buct_media

# 克隆代码（替换为你的仓库地址）
git clone https://github.com/your-username/BUCT_Media_System.git .
```

### 方法二：使用 SCP 上传

在**本地电脑**执行：

```bash
# 打包项目（排除 node_modules 和缓存）
cd /path/to/BUCT_Media_System
tar --exclude='node_modules' --exclude='__pycache__' --exclude='.git' \
    --exclude='*.db' --exclude='uploads/*' \
    -czvf buct_media.tar.gz .

# 上传到服务器
scp buct_media.tar.gz root@your-server-ip:/var/www/

# 在服务器上解压
ssh root@your-server-ip
mkdir -p /var/www/buct_media
cd /var/www/buct_media
tar -xzvf /var/www/buct_media.tar.gz
```

---

## 部署后端

### 1. 创建 Python 虚拟环境

```bash
cd /var/www/buct_media
python3 -m venv venv
source venv/bin/activate
```

### 2. 安装依赖

```bash
cd backend
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
# 复制生产环境配置
cp ../deploy/.env.production .env

# 生成安全密钥
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# 复制输出的密钥

# 编辑配置文件
nano .env
```

**必须修改的配置项**：

```env
# 替换为上面生成的密钥
SECRET_KEY=你生成的密钥

# 修改上传目录
UPLOAD_DIR=/var/www/buct_media/uploads

# 如果没有 AI 服务，设置为 false
AI_ENABLED=false
```

### 4. 创建上传目录

```bash
mkdir -p /var/www/buct_media/uploads
chown -R www-data:www-data /var/www/buct_media/uploads
```

### 5. 初始化数据库

```bash
cd /var/www/buct_media/backend
source ../venv/bin/activate
python3 -c "from app.core.database import init_db; import asyncio; asyncio.run(init_db())"
```

### 6. 测试后端启动

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
# Ctrl+C 退出
```

访问 `http://你的服务器IP:8000/docs` 应该能看到 API 文档。

---

## 部署前端

### 1. 安装依赖

```bash
cd /var/www/buct_media/frontend
npm ci
```

### 2. 配置生产环境 API 地址

```bash
# 生产环境使用空地址（相对路径，通过 Nginx 代理）
echo "VITE_API_BASE_URL=" > .env.production.local
```

### 3. 构建生产版本

```bash
npm run build
```

构建完成后，静态文件位于 `dist/` 目录。

### 4. 移动构建产物

```bash
mkdir -p /var/www/buct_media/public
cp -r dist/* /var/www/buct_media/public/
```

---

## 配置 Nginx

### 1. 创建配置文件

```bash
nano /etc/nginx/sites-available/buct_media
```

粘贴以下内容（**修改 server_name**）：

```nginx
upstream backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

server {
    listen 80;
    server_name your-domain.com;  # 改为你的域名或 IP
    
    client_max_body_size 25M;
    
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
    
    # 前端静态文件
    location / {
        root /var/www/buct_media/public;
        try_files $uri $uri/ /index.html;
        
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
            expires 30d;
            add_header Cache-Control "public, immutable";
        }
    }
    
    # API 代理
    location /api {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # 上传的文件
    location /uploads {
        alias /var/www/buct_media/uploads;
        expires 30d;
    }
    
    # API 文档
    location /docs {
        proxy_pass http://backend;
        proxy_set_header Host $host;
    }
    
    location /redoc {
        proxy_pass http://backend;
        proxy_set_header Host $host;
    }
}
```

### 2. 启用站点

```bash
ln -sf /etc/nginx/sites-available/buct_media /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
```

### 3. 测试并重载配置

```bash
nginx -t
systemctl reload nginx
```

---

## 配置 Systemd 服务

### 1. 创建服务文件

```bash
nano /etc/systemd/system/buct_media.service
```

粘贴以下内容：

```ini
[Unit]
Description=BUCT Media System Backend
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/buct_media/backend
Environment="PATH=/var/www/buct_media/venv/bin"
ExecStart=/var/www/buct_media/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 2. 设置目录权限

```bash
chown -R www-data:www-data /var/www/buct_media
```

### 3. 启用并启动服务

```bash
systemctl daemon-reload
systemctl enable buct_media
systemctl start buct_media
```

---

## 启动与验证

### 1. 检查服务状态

```bash
# 后端服务状态
systemctl status buct_media

# Nginx 状态
systemctl status nginx
```

### 2. 查看日志

```bash
# 后端日志
journalctl -u buct_media -f

# Nginx 日志
tail -f /var/log/nginx/error.log
```

### 3. 访问测试

- 打开浏览器访问：`http://你的服务器IP`
- API 文档：`http://你的服务器IP/docs`

---

## 常见问题

### 1. 502 Bad Gateway

**原因**：后端服务未运行

**解决**：
```bash
systemctl status buct_media
systemctl restart buct_media
journalctl -u buct_media -n 50
```

### 2. 静态文件 404

**原因**：前端构建产物路径错误

**解决**：
```bash
ls -la /var/www/buct_media/public/
# 确保 index.html 存在
```

### 3. 上传失败 (413 Request Entity Too Large)

**原因**：Nginx 限制了文件大小

**解决**：检查 `nginx.conf` 中的 `client_max_body_size`

### 4. 文件权限问题

```bash
chown -R www-data:www-data /var/www/buct_media
chmod -R 755 /var/www/buct_media
```

### 5. 数据库锁定错误

SQLite 在高并发时可能出问题：
```bash
# 临时解决
systemctl restart buct_media
```

---

## 维护命令

```bash
# 重启后端
systemctl restart buct_media

# 重载 Nginx 配置
systemctl reload nginx

# 查看后端日志
journalctl -u buct_media -f

# 更新代码后重新部署
cd /var/www/buct_media
git pull
source venv/bin/activate
pip install -r backend/requirements.txt
cd frontend && npm ci && npm run build
cp -r dist/* /var/www/buct_media/public/
systemctl restart buct_media
```

---

## 可选：配置 HTTPS

使用 Let's Encrypt 免费证书：

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d your-domain.com
```

---

## 快速部署（自动脚本）

如果你信任自动化脚本，可以直接运行：

```bash
cd /var/www/buct_media
chmod +x deploy/deploy.sh
sudo ./deploy/deploy.sh
```

**注意**：运行前请修改脚本中的 `DOMAIN` 变量。

---

## 联系支持

如遇到问题，请检查：
1. 服务日志 (`journalctl -u buct_media -n 100`)
2. Nginx 错误日志 (`/var/log/nginx/error.log`)
3. 确保防火墙开放 80/443 端口
