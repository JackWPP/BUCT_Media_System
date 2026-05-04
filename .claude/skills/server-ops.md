---
name: server-ops
description: Production server operations for 视觉北化 — health checks, deployment, log analysis, database queries, bug diagnosis, and hotfixes.
---

# 视觉北化 服务器运维 Agent

## 服务器访问

```
SSH:  ssh yanp@121.195.148.85
sudo: 密码 mt01@buct (通过 echo mt01@buct | sudo -S <cmd> 传递)
OS:    Ubuntu 22.04 LTS, x86_64
```

所有运维操作通过 SSH 在服务器上执行。当前服务均以 yanp 用户运行，sudo 用于 systemd / nginx / postgres 操作。

## 项目概况

这是一个北化校园媒体系统，用于展示和管理校园摄影照片。

| 层 | 技术栈 | 端口 | 管理 |
|----|--------|------|------|
| 前端 | Vue 3 + Naive UI + Vite 7 | Nginx 80 | 静态文件 |
| 后端 | FastAPI + SQLAlchemy 2.0 + asyncpg | Uvicorn 8000 | systemd |
| 数据库 | PostgreSQL 18 (Baota) | 5432 | Baota |
| 存储 | MinIO (Docker) | 9000 / 9001 | Docker |
| 反向代理 | Nginx 1.18 | 80 | systemd |

数据规模: 494 张照片, 839 个标签, 2205 条分类, 898 条 AI 分析记录。

## 关键路径

```
项目根:   /opt/visual_buct/BUCT_Media_System/
后端:     /opt/visual_buct/BUCT_Media_System/backend/
前端:     /opt/visual_buct/BUCT_Media_System/frontend/
.env:     /opt/visual_buct/BUCT_Media_System/backend/.env
前端产物: /home/wwwroot/visual_buct/
Nginx:    /etc/nginx/sites-available/default
Systemd:  /etc/systemd/system/visual-buct.service
PG 客户端: /www/server/pgsql/bin/psql
MinIO:    sudo docker ps | grep minio
mc:       /usr/local/bin/mc (alias: local → http://127.0.0.1:9000)
```

## 环境变量要点

服务器 `.env` 中的关键配置:

```
DATABASE_URL=postgresql+asyncpg://visual_buct:visual_buct_pwd_2026@127.0.0.1:5432/visual_buct
STORAGE_BACKEND=s3
S3_ENDPOINT=http://127.0.0.1:9000
S3_BUCKET=buctmedia
S3_ACCESS_KEY=admin
S3_SECRET_KEY=jt20030613
SECRET_KEY=Bf06CKSORn2XCZ8WdQBiLbNlXO3Zf9Frg9WiVhyNDDk
AI_ENABLED=false
ALLOWED_ORIGINS='["http://121.195.148.85"]'
```

⚠️ `SECRET_KEY` 用于 Fernet 加密 AI Provider 的 API Key。**绝对不能随意修改**，否则已存的 API Key 无法解密，系统设置页会 500 错误。

## 服务管理

### 查看状态

```bash
# 后端服务
sudo systemctl status visual-buct

# Nginx
sudo systemctl status nginx

# MinIO
sudo docker ps | grep minio

# PostgreSQL (通过 Baota 管理，无 systemd 服务)
echo mt01@buct | sudo -S -u postgres /www/server/pgsql/bin/psql -c "SELECT 1"
```

### 重启服务

```bash
# 重启后端 (最常用)
echo mt01@buct | sudo -S systemctl restart visual-buct

# 重启 Nginx
echo mt01@buct | sudo -S nginx -s reload

# 重启 MinIO
sudo docker restart minio
```

### 查看日志

```bash
# 后端实时日志
sudo journalctl -u visual-buct -f

# 后端最近 100 行
sudo journalctl -u visual-buct -n 100 --no-pager

# 搜索错误
sudo journalctl -u visual-buct --no-pager | grep -i error

# Nginx 日志
sudo tail -100 /var/log/nginx/access.log
sudo tail -100 /var/log/nginx/error.log
```

## 部署流程

### 标准部署 (服务器端执行)

```bash
cd /opt/visual_buct/BUCT_Media_System
bash deploy/deploy.sh all       # 全部
bash deploy/deploy.sh backend   # 仅后端
bash deploy/deploy.sh frontend  # 仅前端
```

部署脚本会: git pull → pip install → alembic upgrade → systemctl restart (后端) 或 npm ci → npm build → 拷贝到 /home/wwwroot/visual_buct/ (前端)。

### 服务器无法访问 GitHub 时

先从本机 push 代码，然后服务器拉取:

```bash
# 本机: git push origin master
# 服务器:
cd /opt/visual_buct/BUCT_Media_System
git pull origin master
bash deploy/deploy.sh all
```

## 健康检查

### 快速诊断

```bash
# 1. 后端 API
curl -s http://127.0.0.1:8000/api/v1/photos/public | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Photos: {d[\"total\"]}')"

# 2. 管理员 API (先获取 token)
TOKEN=$(curl -s http://127.0.0.1/api/v1/auth/login -H "Content-Type: application/json" -d '{"identifier":"admin","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -s http://127.0.0.1/api/v1/admin/settings -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# 3. 前端
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/

# 4. Nginx 到后端连通性
curl -s http://127.0.0.1/api/v1/photos/public | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'OK: {d[\"total\"]} photos')"
```

### 检查各组件

```bash
# 后端进程
sudo systemctl is-active visual-buct

# Nginx
sudo systemctl is-active nginx

# PostgreSQL
echo mt01@buct | sudo -S -u postgres /www/server/pgsql/bin/psql -c "SELECT 1" 2>&1 | grep -q "1" && echo "PG OK"

# MinIO
sudo docker ps | grep -q minio && echo "MinIO OK"

# 磁盘
df -h / | tail -1
```

## 数据库操作

### 连接

```bash
echo mt01@buct | sudo -S -u postgres /www/server/pgsql/bin/psql -d visual_buct
```

### 常用查询

```sql
-- 统计
SELECT count(*) FROM photos;
SELECT count(*) FROM photos WHERE thumb_path IS NOT NULL;
SELECT count(*) FROM photos WHERE status = 'approved';
SELECT count(*) FROM photo_tags;
SELECT count(*) FROM photo_classifications;
SELECT count(*) FROM ai_analysis_tasks;

-- 用户列表
SELECT id, student_id, email, role, is_active FROM users;

-- 最近上传
SELECT id, filename, status, created_at FROM photos ORDER BY created_at DESC LIMIT 10;

-- 照片详情 (带标签)
SELECT p.filename, p.status, p.thumb_path, string_agg(t.name, ', ') as tags
FROM photos p
LEFT JOIN photo_tags pt ON p.id = pt.photo_id
LEFT JOIN tags t ON pt.tag_id = t.id
GROUP BY p.id
LIMIT 10;

-- AI provider 配置
SELECT id, provider_type, display_name, enabled, is_default, base_url, model_id FROM ai_provider_configs;
```

### 直接操作数据

```bash
# 通过 Python (推荐)
cd /opt/visual_buct/BUCT_Media_System/backend
.venv/bin/python3 -c "
import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as db:
        r = await db.execute(text('SELECT count(*) FROM photos'))
        print(f'Photos: {r.scalar()}')

asyncio.run(main())
"
```

## MinIO 操作

```bash
# 列出
mc ls local/buctmedia/photos/ | wc -l
mc ls local/buctmedia/thumbnails/ | wc -l

# 删除对象
mc rm local/buctmedia/photos/<key>

# 查看存储用量
mc du local/buctmedia
```

## 缩略图维护

```bash
cd /opt/visual_buct/BUCT_Media_System/backend

# 检查有多少照片缺少缩略图
.venv/bin/python3 -c "
import asyncio; from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.photo import Photo
async def m():
    async with AsyncSessionLocal() as d:
        r = await d.execute(select(func.count()).where(Photo.thumb_path == None))
        print(f'Missing thumbnails: {r.scalar()}')
asyncio.run(m())
"

# 生成缺失的缩略图
.venv/bin/python scripts/generate_thumbnails.py --dry-run
.venv/bin/python scripts/generate_thumbnails.py
```

## 常见 Bug 及修复

### 1. 注册/创建用户 500 错误

**症状**: POST /api/v1/auth/register 返回 500 Internal Error

**原因**: 模型 `created_at` 使用 `datetime.now(timezone.utc)` 产生 aware datetime，PG `TIMESTAMP WITHOUT TIME ZONE` 列不兼容

**修复**: 已在 `app/models/user.py` 改为 `datetime.utcnow`。如果复发，检查是否有其他模型同样问题:

```bash
cd /opt/visual_buct/BUCT_Media_System/backend
grep -rn "timezone.utc" app/models/
```

如果仍有引用，改为 `datetime.utcnow` 并去掉 `from datetime import timezone`。

### 2. AI Provider 解密失败

**症状**: 系统设置页 500，日志显示 `ValueError: Stored secret cannot be decrypted with current SECRET_KEY`

**原因**: `.env` 中的 `SECRET_KEY` 与加密 AI Provider API Key 时使用的密钥不一致

**修复**:
```bash
# 1. 确认当前密钥
grep SECRET_KEY /opt/visual_buct/BUCT_Media_System/backend/.env

# 2. 如果密钥被修改过，恢复部署时的原始密钥:
#    Bf06CKSORn2XCZ8WdQBiLbNlXO3Zf9Frg9WiVhyNDDk

# 3. 或者删除无法解密的 provider 重建:
cd /opt/visual_buct/BUCT_Media_System/backend
.venv/bin/python3 -c "
import asyncio; from sqlalchemy import select, delete
from app.core.database import AsyncSessionLocal
from app.models.ai_provider import AIProviderConfig
from app.core.secrets import decrypt_secret
async def m():
    async with AsyncSessionLocal() as d:
        r = await d.execute(select(AIProviderConfig))
        for p in r.scalars().all():
            try:
                k = decrypt_secret(p.api_key_encrypted) if p.api_key_encrypted else None
            except:
                print(f'Deleting broken provider {p.id[:8]}...')
                await d.delete(p)
        await d.commit()
asyncio.run(m())
"
```

### 3. 图片无法显示

**症状**: 前端图片加载失败

**排查**:
```bash
# 1. MinIO 是否运行
sudo docker ps | grep minio

# 2. 缩略图是否存在
mc ls local/buctmedia/thumbnails/ | wc -l

# 3. 直接测试图片 API
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/v1/photos/public
```

### 4. 服务启动失败

**排查**:
```bash
# 查看启动日志
sudo journalctl -u visual-buct -n 50 --no-pager

# 常见原因:
# - Python 依赖缺失: cd backend && .venv/bin/pip install -r requirements.txt
# - 数据库连接失败: 确认 .env 中 DATABASE_URL
# - 端口被占用: sudo ss -tlnp | grep 8000
# - 导入错误: 检查 git pull 是否完整
```

### 5. API 返回 404 (Nginx)

**症状**: curl 后端 8000 正常，但通过 Nginx 80 返回 404

**排查**:
```bash
# 测试 Nginx 代理
curl -s http://127.0.0.1/api/v1/photos/public

# 检查 Nginx 配置
grep -A 5 "location /api" /etc/nginx/sites-available/default
# proxy_pass 末尾不能有 / (会剥离 /api 前缀)
# 正确: proxy_pass http://127.0.0.1:8000;
# 错误: proxy_pass http://127.0.0.1:8000/;
```

## 文件结构速查

```
/opt/visual_buct/BUCT_Media_System/
├── backend/
│   ├── .env                          # 环境配置 (PG + S3 + 密钥)
│   ├── .venv/                        # Python 虚拟环境
│   ├── app/
│   │   ├── main.py                   # FastAPI 入口
│   │   ├── api/v1/endpoints/         # API 端点
│   │   │   ├── photos.py             # 照片 CRUD + 上传
│   │   │   ├── auth.py               # 登录/注册
│   │   │   ├── admin_config.py       # 系统设置 + 数据库管理
│   │   │   └── ...
│   │   ├── models/                   # SQLAlchemy 模型
│   │   ├── crud/                     # 数据库操作
│   │   ├── services/
│   │   │   ├── storage.py            # S3/MinIO 存储后端
│   │   │   ├── ai_providers.py       # AI 供应商管理
│   │   │   ├── ai_tasks.py           # AI 分析任务
│   │   │   └── image_processing.py   # 缩略图生成
│   │   ├── core/
│   │   │   ├── config.py             # 配置类 (Settings)
│   │   │   ├── database.py           # 数据库引擎 + 会话
│   │   │   └── secrets.py            # Fernet 加密
│   │   └── schemas/                  # Pydantic 模型
│   ├── scripts/
│   │   ├── generate_thumbnails.py    # 缩略图批量生成
│   │   ├── dedup_oss.py              # OSS 去重
│   │   └── migrate_to_postgres.py    # SQLite→PG 迁移
│   ├── alembic/                      # 数据库迁移
│   └── requirements.txt
├── frontend/                          # Vue 3 + Vite 前端
├── deploy/
│   ├── deploy.sh                     # 服务器端部署脚本
│   ├── deploy-from-local.sh          # 本机部署脚本 (Windows)
│   ├── visual-buct.service           # systemd 服务定义
│   ├── nginx-ip.sh                   # Nginx 纯 IP 配置
│   ├── .env.production               # 生产环境配置模板
│   └── server-setup.sh               # 初始服务器配置
├── docs/
│   └── SOP.md                        # 运维 SOP
└── CLAUDE.md                         # 项目指南
```

## 应急操作

### 回滚代码

```bash
cd /opt/visual_buct/BUCT_Media_System
git log --oneline -10                    # 查看历史
git revert <commit-hash> --no-edit       # 回滚某个提交
bash deploy/deploy.sh all
```

### 紧急重启

```bash
echo mt01@buct | sudo -S systemctl restart visual-buct
echo mt01@buct | sudo -S nginx -s reload
```

### 查看谁在线

```bash
# 查看活跃 SSH 连接
sudo ss -tnp | grep :22

# 查看系统负载
uptime && free -h
```

## Agent 工作原则

1. **先诊断，再动手**：修改前先查日志、测 API、确认根因
2. **最小变更**：优先用脚本和命令，不随意改代码
3. **记录操作**：重要变更说明原因和结果
4. **保持一致性**：.env 中的 SECRET_KEY 绝对不要改
5. **前端构建在服务器**：用 `bash deploy/deploy.sh frontend`，不需要本地 Node 环境
