# 视觉北化 运维 SOP

> 最后更新: 2026-04-30

## 服务器信息

| 项目 | 值 |
|------|-----|
| IP | 121.195.148.85 |
| OS | Ubuntu 22.04 LTS |
| SSH | `ssh yanp@121.195.148.85` |
| sudo | 密码 `mt01@buct` |
| 项目路径 | `/opt/visual_buct/BUCT_Media_System/` |

## 架构速览

```
Nginx :80 → 前端静态文件 (/home/wwwroot/visual_buct/)
           /api → proxy_pass http://127.0.0.1:8000
                         └─ Uvicorn (systemd) → PostgreSQL :5432
                                               → MinIO :9000 (Docker)
```

## 日常部署

### 服务器端部署（推荐）

```bash
cd /opt/visual_buct/BUCT_Media_System

# 仅后端
bash deploy/deploy.sh backend

# 仅前端
bash deploy/deploy.sh frontend

# 全部
bash deploy/deploy.sh all
```

### 从 GitHub 不可达时的部署

服务器无法直接访问 GitHub 时，从本机推送代码后 SSH 到服务器手动拉取：

```bash
# 本机：推送代码
git push origin master

# 服务器：拉取 + 部署
ssh yanp@121.195.148.85
cd /opt/visual_buct/BUCT_Media_System
git pull origin master
bash deploy/deploy.sh all
```

## 服务管理

```bash
# 查看后端状态
sudo systemctl status visual-buct

# 重启后端
sudo systemctl restart visual-buct

# 查看后端日志（实时）
sudo journalctl -u visual-buct -f

# 查看最近 50 行日志
sudo journalctl -u visual-buct -n 50 --no-pager
```

## Nginx 管理

```bash
sudo nginx -t              # 测试配置
sudo nginx -s reload       # 重载（不中断服务）
sudo systemctl restart nginx
```

## 数据库

```bash
# 连接 PostgreSQL
echo mt01@buct | sudo -S -u postgres /www/server/pgsql/bin/psql -d visual_buct

# 常用查询
SELECT count(*) FROM photos;
SELECT count(*) FROM photos WHERE thumb_path IS NOT NULL;
SELECT count(*) FROM photo_classifications;
SELECT count(*) FROM ai_analysis_tasks;
SELECT * FROM users;
```

## MinIO 管理

```bash
# 查看 MinIO 状态
sudo docker ps | grep minio

# 重启 MinIO
sudo docker restart minio

# 列出照片/缩略图数量
mc ls local/buctmedia/photos/ | wc -l
mc ls local/buctmedia/thumbnails/ | wc -l
```

## 数据维护脚本

```bash
cd /opt/visual_buct/BUCT_Media_System/backend

# 缩略图生成（新上传照片）
.venv/bin/python scripts/generate_thumbnails.py --dry-run
.venv/bin/python scripts/generate_thumbnails.py

# OSS 去重
.venv/bin/python scripts/dedup_oss.py --dry-run
.venv/bin/python scripts/dedup_oss.py --cleanup-tests

# SQLite → PostgreSQL 迁移
.venv/bin/python scripts/migrate_to_postgres.py \
    --source visual_buct.db \
    --target "postgresql://visual_buct:xxx@127.0.0.1:5432/visual_buct"
```

## 故障排查

| 症状 | 检查项 |
|------|--------|
| 页面 404 | `curl http://127.0.0.1/` 和 `curl http://127.0.0.1/api/v1/photos/public` |
| 图片不加载 | `sudo docker ps \| grep minio` 检查 MinIO |
| 上传失败 | 检查是否 S3 后端（服务器本地才能直连 MinIO） |
| 注册/登录 500 | `sudo journalctl -u visual-buct -n 100 --no-pager` |
| 服务起不来 | 同上，检查日志中的 Python traceback |

## 环境变量 (.env)

关键配置项，修改后需 `sudo systemctl restart visual-buct`：

```env
DATABASE_URL=postgresql+asyncpg://visual_buct:xxx@127.0.0.1:5432/visual_buct
STORAGE_BACKEND=s3
S3_ENDPOINT=http://127.0.0.1:9000
S3_BUCKET=buctmedia
AI_ENABLED=false
SECRET_KEY=...  # 变更会导致 AI Provider API Key 无法解密
ALLOWED_ORIGINS='["http://121.195.148.85"]'
```
