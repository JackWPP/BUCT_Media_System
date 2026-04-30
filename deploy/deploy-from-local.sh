#!/usr/bin/env bash
# 本机一键部署脚本
# 用法: bash deploy/deploy-from-local.sh [deploy|build-frontend|restart]
set -e

SERVER="yanp@121.195.148.85"
PROJECT="/opt/visual_buct/BUCT_Media_System"
SUDO_PASS="mt01@buct"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

log() { echo -e "${GREEN}[DEPLOY]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; }

push_code() {
    log "Pushing to GitHub..."
    git push origin master
}

deploy_backend() {
    log "Syncing backend to server..."
    rsync -avz --delete \
        --exclude '.venv/' --exclude '__pycache__/' --exclude '*.pyc' \
        --exclude 'visual_buct.db' --exclude 'uploads/' --exclude '.env' \
        backend/ $SERVER:$PROJECT/backend/

    log "Installing dependencies..."
    ssh $SERVER "cd $PROJECT/backend && .venv/bin/pip install -r requirements.txt -q"

    log "Running migrations..."
    ssh $SERVER "cd $PROJECT/backend && .venv/bin/alembic upgrade head"

    log "Restarting service..."
    ssh $SERVER "echo $SUDO_PASS | sudo -S systemctl restart visual-buct"
}

deploy_frontend() {
    log "Building frontend..."
    cd frontend && npm run build && cd ..

    log "Uploading frontend to server..."
    rsync -avz --delete frontend/dist/ $SERVER:/home/wwwroot/visual_buct/
    ssh $SERVER "echo $SUDO_PASS | sudo -S chown -R www-data:www-data /home/wwwroot/visual_buct"
}

deploy_all() {
    push_code
    deploy_backend
    deploy_frontend
    log "Deploy complete!"
}

case "${1:-deploy}" in
    deploy)          deploy_all ;;
    backend)         push_code && deploy_backend ;;
    frontend)        push_code && deploy_frontend ;;
    build-frontend)  deploy_frontend ;;
    restart)         ssh $SERVER "echo $SUDO_PASS | sudo -S systemctl restart visual-buct" ;;
    *) echo "Usage: $0 [deploy|backend|frontend|build-frontend|restart]" ;;
esac
