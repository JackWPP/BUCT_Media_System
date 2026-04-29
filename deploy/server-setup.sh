#!/usr/bin/env bash
# 视觉北化 服务器初始化脚本
# 在服务器上执行: bash server-setup.sh
set -euo pipefail

SUDO_PASS="mt01@buct"
PG_HOST="/www/server/pgsql"
APP_DIR="/opt/visual_buct"
WWW_DIR="/home/wwwroot/visual_buct"

RED='\033[0;31m'; GREEN='\033[0;32m'; NC='\033[0m'
log() { echo -e "${GREEN}[INFO]${NC} $1"; }
err() { echo -e "${RED}[ERROR]${NC} $1"; }

# ── Step 1: Stop old app ──
log "Stopping old multi_media_system..."
echo "$SUDO_PASS" | sudo -S supervisorctl stop multi_media_system 2>/dev/null || true

# ── Step 2: PostgreSQL setup ──
log "Setting up PostgreSQL..."
echo "$SUDO_PASS" | sudo -S -u postgres $PG_HOST/bin/psql <<SQL
CREATE USER visual_buct WITH PASSWORD 'visual_buct_pwd_2026';
CREATE DATABASE visual_buct OWNER visual_buct;
GRANT ALL PRIVILEGES ON DATABASE visual_buct TO visual_buct;
\c visual_buct
GRANT ALL ON SCHEMA public TO visual_buct;
SQL
log "PostgreSQL database and user created."

# ── Step 3: Clone and setup backend ──
if [ ! -d "$APP_DIR/.git" ]; then
    log "Cloning repository..."
    echo "$SUDO_PASS" | sudo -S rm -rf $APP_DIR
    echo "$SUDO_PASS" | sudo -S mkdir -p $APP_DIR
    echo "$SUDO_PASS" | sudo -S chown yanp:yanp $APP_DIR
    git clone https://github.com/JackWPP/BUCT_Media_System.git $APP_DIR
else
    log "Repository exists, pulling..."
    cd $APP_DIR && git pull origin master
fi

# Setup backend
cd $APP_DIR/backend
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
.venv/bin/pip install -r requirements.txt -q

# Copy production env if not exists
if [ ! -f ".env" ]; then
    cp ../deploy/.env.production .env
    log ".env created from production template."
fi

# Run migrations
log "Running database migrations..."
.venv/bin/alembic upgrade head

# ── Step 4: Build frontend ──
log "Building frontend..."
cd $APP_DIR/frontend
npm ci
npm run build

echo "$SUDO_PASS" | sudo -S rm -rf $WWW_DIR
echo "$SUDO_PASS" | sudo -S mkdir -p $WWW_DIR
echo "$SUDO_PASS" | sudo -S cp -r dist/* $WWW_DIR/
echo "$SUDO_PASS" | sudo -S chown -R www-data:www-data $WWW_DIR
log "Frontend deployed to $WWW_DIR"

# ── Step 5: Systemd service ──
log "Setting up systemd service..."
echo "$SUDO_PASS" | sudo -S cp $APP_DIR/deploy/visual-buct.service /etc/systemd/system/
echo "$SUDO_PASS" | sudo -S systemctl daemon-reload
echo "$SUDO_PASS" | sudo -S systemctl enable visual-buct
echo "$SUDO_PASS" | sudo -S systemctl restart visual-buct
sleep 3
echo "$SUDO_PASS" | sudo -S systemctl status visual-buct --no-pager

# ── Step 6: Nginx config update ──
log "Updating Nginx config..."
NGINX_CONF="/etc/nginx/sites-enabled/cpmz.buct.edu.cn.conf"
if [ -f "$NGINX_CONF" ]; then
    echo "$SUDO_PASS" | sudo -S cp $NGINX_CONF ${NGINX_CONF}.backup.$(date +%Y%m%d_%H%M%S)
    echo "$SUDO_PASS" | sudo -S sed -i 's|root /home/wwwroot/default;|root /home/wwwroot/visual_buct;|g' $NGINX_CONF

    # Add SPA fallback if not present
    if ! grep -q "try_files" $NGINX_CONF; then
        echo "$SUDO_PASS" | sudo -S sed -i '/root \/home\/wwwroot\/visual_buct;/a\        try_files $uri $uri/ /index.html;' $NGINX_CONF
    fi

    echo "$SUDO_PASS" | sudo -S nginx -t && echo "$SUDO_PASS" | sudo -S nginx -s reload
    log "Nginx configured and reloaded."
else
    err "Nginx config not found at $NGINX_CONF"
fi

# ── Step 7: SSL ──
log "Checking SSL certificate..."
CERT_FILE="/etc/nginx/ssl/certificate.pem"
if [ -f "$CERT_FILE" ]; then
    EXPIRY=$(echo "$SUDO_PASS" | sudo -S openssl x509 -enddate -noout -in $CERT_FILE 2>/dev/null | cut -d= -f2)
    echo "  Current cert expires: $EXPIRY"
fi

if command -v certbot &>/dev/null; then
    log "certbot found, attempting renew..."
    echo "$SUDO_PASS" | sudo -S certbot renew --nginx --non-interactive 2>&1 || log "certbot renew skipped (may need manual intervention)"
else
    log "certbot not installed. To setup SSL:"
    echo "  sudo apt install certbot python3-certbot-nginx -y"
    echo "  sudo certbot --nginx -d cpmz.buct.edu.cn"
fi

log "Server setup complete!"
