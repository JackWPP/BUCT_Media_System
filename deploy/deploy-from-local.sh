#!/usr/bin/env bash
# 本机一键部署脚本 (Windows Git Bash 兼容)
# 用法: bash deploy/deploy-from-local.sh [deploy|backend|frontend|restart] [--skip-taxonomy|--taxonomy-dry-run|--taxonomy-apply --confirm-taxonomy-apply]
set -e

SERVER="yanp@121.195.148.85"
PROJECT="/opt/visual_buct/BUCT_Media_System"
SUDO_PASS="mt01@buct"
TARGET="deploy"
TAXONOMY_MIGRATION_MODE="${TAXONOMY_MIGRATION_MODE:-skip}"
TAXONOMY_APPLY_CONFIRM="${TAXONOMY_APPLY_CONFIRM:-}"

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

usage() {
    cat <<'EOF'
Usage: bash deploy/deploy-from-local.sh [deploy|backend|frontend|restart] [taxonomy options]

Taxonomy options:
  --skip-taxonomy              Skip taxonomy migration (default)
  --taxonomy-dry-run           Run scripts/migrate_taxonomy_2026.py on the server without --apply
  --taxonomy-apply             Run scripts/migrate_taxonomy_2026.py --apply on the server
  --confirm-taxonomy-apply     Required with --taxonomy-apply

Environment equivalents:
  TAXONOMY_MIGRATION_MODE=skip|dry-run|apply
  TAXONOMY_APPLY_CONFIRM=APPLY_TAXONOMY_2026
EOF
}

parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            deploy|backend|frontend|restart)
                TARGET="$1"
                ;;
            --skip-taxonomy)
                TAXONOMY_MIGRATION_MODE="skip"
                ;;
            --taxonomy-dry-run)
                TAXONOMY_MIGRATION_MODE="dry-run"
                ;;
            --taxonomy-apply)
                TAXONOMY_MIGRATION_MODE="apply"
                ;;
            --confirm-taxonomy-apply)
                TAXONOMY_APPLY_CONFIRM="APPLY_TAXONOMY_2026"
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                usage
                exit 1
                ;;
        esac
        shift
    done
}

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

    run_taxonomy_migration

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

run_taxonomy_migration() {
    case "$TAXONOMY_MIGRATION_MODE" in
        skip|"")
            log "Skipping 2026 taxonomy migration. Set --taxonomy-dry-run or --taxonomy-apply to run it."
            ;;
        dry-run)
            log "Running 2026 taxonomy migration dry-run on server..."
            $SSH $SERVER "cd $PROJECT/backend && .venv/bin/python scripts/migrate_taxonomy_2026.py"
            ;;
        apply)
            if [ "$TAXONOMY_APPLY_CONFIRM" != "APPLY_TAXONOMY_2026" ]; then
                err "Refusing taxonomy apply. Pass --confirm-taxonomy-apply or set TAXONOMY_APPLY_CONFIRM=APPLY_TAXONOMY_2026."
                exit 1
            fi
            log "Applying 2026 taxonomy migration on server..."
            $SSH $SERVER "cd $PROJECT/backend && .venv/bin/python scripts/migrate_taxonomy_2026.py --apply"
            ;;
        *)
            err "Invalid TAXONOMY_MIGRATION_MODE=$TAXONOMY_MIGRATION_MODE"
            usage
            exit 1
            ;;
    esac
}

parse_args "$@"

case "$TARGET" in
    deploy)          deploy_all ;;
    backend)         push_code && deploy_backend ;;
    frontend)        push_code && deploy_frontend ;;
    restart)         $SSH $SERVER "echo $SUDO_PASS | sudo -S systemctl restart visual-buct" ;;
    *) usage; exit 1 ;;
esac
