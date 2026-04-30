#!/usr/bin/env bash
# 服务器端部署脚本 — 在服务器上执行
# 用法: bash deploy/deploy.sh [all|backend|frontend]
set -e

cd "$(dirname "$0")/.."
PROJECT_DIR="$(pwd)"
SUDO_PASS="mt01@buct"

log() { echo -e "\033[0;32m[DEPLOY]\033[0m $1"; }

deploy_backend() {
    log "Pulling latest code..."
    git pull origin master --ff-only

    log "Installing Python dependencies..."
    cd "$PROJECT_DIR/backend"
    .venv/bin/pip install -r requirements.txt -q

    log "Running database migrations..."
    .venv/bin/alembic upgrade head

    log "Restarting service..."
    echo "$SUDO_PASS" | sudo -S systemctl restart visual-buct

    log "Backend deploy complete."
}

deploy_frontend() {
    log "Pulling latest code..."
    git pull origin master --ff-only

    log "Installing npm dependencies..."
    cd "$PROJECT_DIR/frontend"
    npm ci --silent

    log "Building frontend..."
    npm run build

    log "Deploying to /home/wwwroot/visual_buct/..."
    echo "$SUDO_PASS" | sudo -S rm -rf /home/wwwroot/visual_buct
    echo "$SUDO_PASS" | sudo -S mkdir -p /home/wwwroot/visual_buct
    echo "$SUDO_PASS" | sudo -S cp -r dist/* /home/wwwroot/visual_buct/
    echo "$SUDO_PASS" | sudo -S chown -R www-data:www-data /home/wwwroot/visual_buct

    log "Frontend deploy complete."
}

case "${1:-all}" in
    all)      deploy_backend && deploy_frontend ;;
    backend)  deploy_backend ;;
    frontend) deploy_frontend ;;
    *) echo "Usage: $0 [all|backend|frontend]" ;;
esac
