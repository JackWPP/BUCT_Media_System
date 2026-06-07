#!/usr/bin/env bash
# 服务器端部署脚本 — 在服务器上执行
# 用法: bash deploy/deploy.sh [all|backend|frontend] [--skip-taxonomy|--taxonomy-dry-run|--taxonomy-apply --confirm-taxonomy-apply]
set -e

cd "$(dirname "$0")/.."
PROJECT_DIR="$(pwd)"
SUDO_PASS="mt01@buct"
TARGET="all"
TAXONOMY_MIGRATION_MODE="${TAXONOMY_MIGRATION_MODE:-skip}"
TAXONOMY_APPLY_CONFIRM="${TAXONOMY_APPLY_CONFIRM:-}"

log() { echo -e "\033[0;32m[DEPLOY]\033[0m $1"; }
err() { echo -e "\033[0;31m[ERROR]\033[0m $1"; }

usage() {
    cat <<'EOF'
Usage: bash deploy/deploy.sh [all|backend|frontend] [taxonomy options]

Taxonomy options:
  --skip-taxonomy              Skip taxonomy migration (default)
  --taxonomy-dry-run           Run scripts/migrate_taxonomy_2026.py without --apply
  --taxonomy-apply             Run scripts/migrate_taxonomy_2026.py --apply
  --confirm-taxonomy-apply     Required with --taxonomy-apply

Environment equivalents:
  TAXONOMY_MIGRATION_MODE=skip|dry-run|apply
  TAXONOMY_APPLY_CONFIRM=APPLY_TAXONOMY_2026
EOF
}

parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            all|backend|frontend)
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

pull_latest() {
    if [ "${SKIP_GIT_PULL:-0}" = "1" ]; then
        log "Skipping git pull because SKIP_GIT_PULL=1"
        return
    fi
    git pull origin master --ff-only
}

deploy_backend() {
    log "Pulling latest code..."
    pull_latest

    log "Installing Python dependencies..."
    cd "$PROJECT_DIR/backend"
    .venv/bin/pip install -r requirements.txt -c constraints-prod.txt -q

    log "Running database migrations..."
    .venv/bin/alembic upgrade head

    run_taxonomy_migration

    log "Restarting service..."
    echo "$SUDO_PASS" | sudo -S systemctl restart visual-buct

    log "Backend deploy complete."
}

deploy_frontend() {
    log "Pulling latest code..."
    pull_latest

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

run_taxonomy_migration() {
    case "$TAXONOMY_MIGRATION_MODE" in
        skip|"")
            log "Skipping 2026 taxonomy migration. Set --taxonomy-dry-run or --taxonomy-apply to run it."
            ;;
        dry-run)
            log "Running 2026 taxonomy migration dry-run..."
            .venv/bin/python scripts/migrate_taxonomy_2026.py
            ;;
        apply)
            if [ "$TAXONOMY_APPLY_CONFIRM" != "APPLY_TAXONOMY_2026" ]; then
                err "Refusing taxonomy apply. Pass --confirm-taxonomy-apply or set TAXONOMY_APPLY_CONFIRM=APPLY_TAXONOMY_2026."
                exit 1
            fi
            log "Applying 2026 taxonomy migration..."
            .venv/bin/python scripts/migrate_taxonomy_2026.py --apply
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
    all)      deploy_backend && deploy_frontend ;;
    backend)  deploy_backend ;;
    frontend) deploy_frontend ;;
    *) usage; exit 1 ;;
esac
