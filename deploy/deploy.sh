#!/bin/bash
# ============================================================
# BUCT Media System 部署脚本
# ============================================================
# 
# 使用方法:
#   chmod +x deploy.sh
#   sudo ./deploy.sh
#
# 此脚本会:
# 1. 安装系统依赖
# 2. 创建目录结构
# 3. 配置 Python 虚拟环境
# 4. 构建前端
# 5. 配置 Nginx
# 6. 配置 Systemd 服务
# ============================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置变量 (根据需要修改)
APP_NAME="buct_media"
APP_DIR="/var/www/${APP_NAME}"
DOMAIN="your-domain.com"  # 修改为你的域名或IP
PYTHON_VERSION="python3"

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否以 root 运行
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用 sudo 运行此脚本"
        exit 1
    fi
}

# 安装系统依赖
install_dependencies() {
    log_info "安装系统依赖..."
    apt update
    apt install -y python3 python3-pip python3-venv nginx curl
    
    # 安装 Node.js (如果需要构建前端)
    if ! command -v node &> /dev/null; then
        log_info "安装 Node.js..."
        curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
        apt install -y nodejs
    fi
}

# 创建目录结构
create_directories() {
    log_info "创建目录结构..."
    mkdir -p ${APP_DIR}/{backend,frontend,uploads,logs}
    chown -R www-data:www-data ${APP_DIR}
}

# 部署后端
deploy_backend() {
    log_info "部署后端..."
    
    # 复制后端代码 (假设当前目录是项目根目录)
    cp -r backend/* ${APP_DIR}/backend/
    
    # 创建虚拟环境
    ${PYTHON_VERSION} -m venv ${APP_DIR}/venv
    
    # 安装依赖
    ${APP_DIR}/venv/bin/pip install --upgrade pip
    ${APP_DIR}/venv/bin/pip install -r ${APP_DIR}/backend/requirements.txt
    
    # 复制生产环境配置
    if [ -f "deploy/.env.production" ]; then
        cp deploy/.env.production ${APP_DIR}/backend/.env
        log_warn "请编辑 ${APP_DIR}/backend/.env 修改密钥!"
    fi
    
    # 初始化数据库
    cd ${APP_DIR}/backend
    ${APP_DIR}/venv/bin/python -c "from app.core.database import init_db; import asyncio; asyncio.run(init_db())"
    
    chown -R www-data:www-data ${APP_DIR}/backend
}

# 构建并部署前端
deploy_frontend() {
    log_info "构建前端..."
    
    cd frontend
    
    # 安装依赖
    npm ci
    
    # 修改 API 地址 (生产环境使用相对路径)
    echo "VITE_API_BASE_URL=" > .env.production.local
    
    # 构建
    npm run build
    
    # 复制构建产物
    cp -r dist/* ${APP_DIR}/frontend/
    
    chown -R www-data:www-data ${APP_DIR}/frontend
}

# 配置 Nginx
configure_nginx() {
    log_info "配置 Nginx..."
    
    # 复制配置文件
    cp deploy/nginx.conf /etc/nginx/sites-available/${APP_NAME}
    
    # 替换域名
    sed -i "s/your-domain.com/${DOMAIN}/g" /etc/nginx/sites-available/${APP_NAME}
    
    # 启用站点
    ln -sf /etc/nginx/sites-available/${APP_NAME} /etc/nginx/sites-enabled/
    
    # 删除默认站点
    rm -f /etc/nginx/sites-enabled/default
    
    # 测试配置
    nginx -t
    
    # 重新加载
    systemctl reload nginx
}

# 配置 Systemd 服务
configure_systemd() {
    log_info "配置 Systemd 服务..."
    
    # 复制服务文件
    cp deploy/buct_media.service /etc/systemd/system/
    
    # 重新加载 systemd
    systemctl daemon-reload
    
    # 启用并启动服务
    systemctl enable ${APP_NAME}
    systemctl start ${APP_NAME}
    
    log_info "服务状态:"
    systemctl status ${APP_NAME} --no-pager
}

# 打印完成信息
print_success() {
    echo ""
    echo "============================================================"
    echo -e "${GREEN}部署完成!${NC}"
    echo "============================================================"
    echo ""
    echo "访问地址: http://${DOMAIN}"
    echo ""
    echo "管理命令:"
    echo "  查看后端日志:    journalctl -u ${APP_NAME} -f"
    echo "  重启后端:        systemctl restart ${APP_NAME}"
    echo "  查看 Nginx 日志: tail -f /var/log/nginx/buct_media_*.log"
    echo ""
    echo "重要提醒:"
    echo "  1. 请修改 ${APP_DIR}/backend/.env 中的 SECRET_KEY"
    echo "  2. 建议配置 HTTPS: certbot --nginx -d ${DOMAIN}"
    echo ""
}

# 主函数
main() {
    check_root
    
    log_info "开始部署 BUCT Media System..."
    
    install_dependencies
    create_directories
    deploy_backend
    deploy_frontend
    configure_nginx
    configure_systemd
    
    print_success
}

# 运行
main "$@"
