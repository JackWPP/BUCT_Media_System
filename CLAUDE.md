# 视觉北化 — 运维指南

## 项目架构

```
前端 (Vue 3 + Naive UI / Vite)    后端 (FastAPI + SQLAlchemy + asyncpg)
       │                                      │
       └──── Nginx :80 (静态文件 + /api 反代) ── Uvicorn :8000 (systemd)
                         │                          │
                    MinIO :9000 (S3)          PostgreSQL :5432
```

| 组件 | 技术 | 端口 | 管理方式 |
|------|------|------|----------|
| 前端 | Vue 3 + Vite 7 | Nginx :80 | 静态文件 |
| 后端 | FastAPI + Uvicorn | :8000 | systemd |
| 数据库 | PostgreSQL 18 | :5432 | Baota |
| 对象存储 | MinIO (Docker) | :9000 | Docker |
| 反向代理 | Nginx 1.18 | :80 | systemd |

## 服务器信息

- **IP**: 121.195.148.85
- **SSH**: `ssh yanp@121.195.148.85`
- **sudo**: `mt01@buct`
- **OS**: Ubuntu 22.04 LTS
- **项目路径**: `/opt/visual_buct/BUCT_Media_System/`

## 关键文件

```
/opt/visual_buct/BUCT_Media_System/backend/      后端代码
/opt/visual_buct/BUCT_Media_System/backend/.env   环境配置
/opt/visual_buct/BUCT_Media_System/frontend/      前端代码
/home/wwwroot/visual_buct/                        前端构建产物
/etc/systemd/system/visual-buct.service           systemd 服务定义
/etc/nginx/sites-available/default                Nginx 配置
/var/log/nginx/access.log / error.log             Nginx 日志
```

## 常用运维命令

### 后端

```bash
# 查看状态
sudo systemctl status visual-buct

# 重启
sudo systemctl restart visual-buct

# 查看日志
sudo journalctl -u visual-buct -n 50 --no-pager -f

# 手动测试 API
curl http://127.0.0.1:8000/api/v1/photos/public
curl http://127.0.0.1/api/v1/admin/settings
```

### 部署更新

```bash
cd /opt/visual_buct/BUCT_Media_System
bash deploy/deploy.sh all
```

或分别部署：

```bash
bash deploy/deploy.sh backend     # 仅后端
bash deploy/deploy.sh frontend    # 仅前端
```

前端构建在服务器上执行 (`npm run build`)，无需本地 Node 环境。

### Nginx

```bash
sudo nginx -t              # 检查配置
sudo nginx -s reload       # 重载配置
sudo systemctl restart nginx
```

### PostgreSQL

```bash
# 连接数据库
echo mt01@buct | sudo -S -u postgres /www/server/pgsql/bin/psql -d visual_buct

# 常用查询
SELECT count(*) FROM photos;
SELECT count(*) FROM photos WHERE thumb_path IS NOT NULL;
SELECT count(*) FROM photo_classifications;
SELECT count(*) FROM ai_analysis_tasks;
```

### MinIO

```bash
# 通过 mc 客户端
mc ls local/buctmedia/photos/ | wc -l
mc ls local/buctmedia/thumbnails/ | wc -l

# Docker 管理
sudo docker ps | grep minio
sudo docker restart minio
```

### 数据维护

```bash
# 缩略图生成（新上传的照片）
cd /opt/visual_buct/BUCT_Media_System/backend
.venv/bin/python scripts/generate_thumbnails.py --dry-run
.venv/bin/python scripts/generate_thumbnails.py

# OSS 去重
.venv/bin/python scripts/dedup_oss.py --dry-run
.venv/bin/python scripts/dedup_oss.py
```

## 环境变量参考 (.env)

```env
DATABASE_URL=postgresql+asyncpg://visual_buct:xxx@127.0.0.1:5432/visual_buct
STORAGE_BACKEND=s3
S3_ENDPOINT=http://127.0.0.1:9000
S3_BUCKET=buctmedia
S3_ACCESS_KEY=admin
S3_SECRET_KEY=jt20030613
AI_ENABLED=false            # 生产环境无 VLM
SECRET_KEY=...              # 与 API Key 加密绑定，不要随意修改
ALLOWED_ORIGINS='["http://121.195.148.85"]'
```

**注意**: `SECRET_KEY` 变更会导致数据库中已加密的 AI Provider API Key 无法解密。

## 部署流程

服务器无法直接访问 GitHub（被墙），部署通过本机中转：

1. 本机 `git push origin master`
2. SSH 到服务器 `ssh yanp@121.195.148.85`
3. 执行 `cd /opt/visual_buct/BUCT_Media_System && bash deploy/deploy.sh all`

详细 SOP 见 [`docs/SOP.md`](docs/SOP.md)。

## 故障排查

| 症状 | 检查项 |
|------|--------|
| API 404 | `curl http://127.0.0.1:8000/api/v1/photos/public` |
| 图片不显示 | MinIO 是否在运行: `sudo docker ps \| grep minio` |
| 上传失败 | 检查是否 S3 后端（需服务器本地才能写入 MinIO） |
| 注册/登录失败 | 检查 PG 连接: `.venv/bin/python -c "from app.core.database import engine; ..."` |
| 服务起不来 | `sudo journalctl -u visual-buct -n 100 --no-pager` |
