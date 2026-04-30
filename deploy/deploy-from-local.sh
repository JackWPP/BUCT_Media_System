#!/usr/bin/env bash
# 本机一键部署脚本 (Windows Git Bash 兼容)
# 用法: bash deploy/deploy-from-local.sh [deploy|backend|frontend|restart]
set -e

SERVER="yanp@121.195.148.85"
PROJECT="/opt/visual_buct/BUCT_Media_System"
SUDO_PASS="mt01@buct"

# 使用 Windows 原生 OpenSSH（避免 Git Bash 自带 SSH 的加密套件不匹配）
if [ -f "/c/Windows/System32/OpenSSH/ssh.exe" ]; then
    SSH="/c/Windows/System32/OpenSSH/ssh.exe"
elif [ -f "/mnt/c/Windows/System32/OpenSSH/ssh.exe" ]; then
    SSH="/mnt/c/Windows/System32/OpenSSH/ssh.exe"
else
    SSH="ssh"
fi

log() { echo -e "\033[0;32m[DEPLOY]\033[0m $1"; }
err()  { echo -e "\033[0;31m[ERROR]\033[0m $1"; }

push_code() {
    log "Pushing to GitHub..."
    git push origin master
}

deploy_backend() {
    log "Uploading backend to server..."
    tar czf - --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' --exclude='visual_buct.db' --exclude='uploads' --exclude='.env' backend/ | $SSH $SERVER "tar xzf - -C $PROJECT/"

    log "Installing dependencies..."
    $SSH $SERVER "cd $PROJECT/backend && .venv/bin/pip install -r requirements.txt -q"

    log "Running migrations..."
    $SSH $SERVER "cd $PROJECT/backend && .venv/bin/alembic upgrade head"

    log "Restarting service..."
    $SSH $SERVER "echo $SUDO_PASS | sudo -S systemctl restart visual-buct"
}

deploy_frontend() {
    log "Building frontend..."
    (cd frontend && npm run build)

    log "Uploading frontend to server..."
    tar czf - -C frontend/ dist/ | $SSH $SERVER "tar xzf - -C /home/wwwroot/visual_buct/"
    $SSH $SERVER "echo $SUDO_PASS | sudo -S chown -R www-data:www-data /home/wwwroot/visual_buct"
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
    restart)         $SSH $SERVER "echo $SUDO_PASS | sudo -S systemctl restart visual-buct" ;;
    *) echo "Usage: $0 [deploy|backend|frontend|restart]" ;;
esac
