# 视觉北化 - 前端开发手册

> 面向在校园网内开发前端、连接远程后端 API 的开发者

---

## 📋 目录

- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [开发流程](#开发流程)
- [API 连接](#api-连接)
- [常见问题](#常见问题)

---

## 🛠️ 环境要求

| 工具 | 版本 | 说明 |
|------|------|------|
| Node.js | >= 18.x | 推荐 20.x LTS |
| npm | >= 9.x | 或 pnpm / yarn |
| Git | 任意 | 用于版本控制 |

**不需要**：
- ❌ Python 环境
- ❌ PostgreSQL 数据库
- ❌ MinIO 对象存储
- ❌ Milvus 向量数据库

---

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/JackWPP/BUCT_Media_System.git
cd BUCT_Media_System/frontend
```

### 2. 安装依赖

```bash
npm install
```

### 3. 启动开发服务器

```bash
# 方式一：连接本地后端（推荐）
# .env.development 中 VITE_API_BASE_URL 保持为空，Vite 会把 /api 代理到 http://localhost:8000
npm run dev

# 方式二：显式连接远程后端（只用于排查线上数据，不推荐日常开发）
cp .env.development .env.development.local
# 编辑 .env.development.local，修改 VITE_API_BASE_URL
npm run dev
```

### 4. 访问应用

打开浏览器访问：`http://localhost:5173`

---

## ⚙️ 配置说明

### 环境变量

前端通过 `.env` 文件配置环境变量：

| 变量 | 说明 | 示例 |
|------|------|------|
| `VITE_API_BASE_URL` | API 基础 URL；留空时使用同源 `/api` | 空值 |
| `VITE_APP_TITLE` | 应用标题 | `视觉北化 - Dev` |

### 环境文件优先级

```
.env.development.local  >  .env.development  >  .env
```

### 推荐的本地后端配置

默认 `.env.development`：

```bash
VITE_API_BASE_URL=
VITE_APP_TITLE=视觉北化 - Dev
```

这种方式和生产环境一致：浏览器请求同源 `/api/...`，开发时由 Vite proxy 转发到 `http://localhost:8000`，生产时由 Nginx 转发到 `127.0.0.1:8000`。

### 连接远程后端配置

创建 `.env.development.local` 文件：

```bash
# 仅用于排查线上数据；日常开发优先使用本地后端 + Vite proxy
VITE_API_BASE_URL=http://121.195.148.85
VITE_APP_TITLE=视觉北化 - 本地开发
```

或者使用域名（如果 DNS 已配置）：

```bash
VITE_API_BASE_URL=https://tkjs.buct.edu.cn
```

---

## 🔄 开发流程

### 日常开发

```bash
# 1. 拉取最新代码
git pull origin master

# 2. 安装依赖（如果有更新）
npm install

# 3. 启动开发服务器
npm run dev

# 4. 开发...

# 5. 提交代码
git add .
git commit -m "feat: 你的改动说明"
git push origin master
```

### 构建测试

```bash
# 本地构建测试
npm run build

# 预览构建产物
npm run preview
```

### 部署到生产环境

```bash
# 方式一：在服务器上构建（推荐）
ssh yanp@121.195.148.85
cd /opt/visual_buct/BUCT_Media_System
git pull origin master
cd frontend
npm install
npm run build
echo mt01@buct | sudo -S cp -r dist/* /home/wwwroot/visual_buct/

# 方式二：本地构建后上传
npm run build
scp -r dist/* yanp@121.195.148.85:/tmp/frontend/
ssh yanp@121.195.148.85 "echo mt01@buct | sudo -S cp -r /tmp/frontend/* /home/wwwroot/visual_buct/"
```

---

## 🔌 API 连接

### 后端服务器信息

| 环境 | 地址 | 说明 |
|------|------|------|
| **生产环境** | `https://tkjs.buct.edu.cn` | 域名访问 |
| **生产环境** | `http://121.195.148.85` | IP 直接访问 |
| **本地后端** | `http://localhost:8000` | 本地开发后端 |

### API 可用性检查

在校园网内，打开终端测试：

```bash
# 测试公开接口
curl http://121.195.148.85/api/v1/photos/public?page_size=1

# 测试搜索接口
curl -G "http://121.195.148.85/api/v1/search" --data-urlencode "q=秋天"

# 测试缩略图
curl -I "http://121.195.148.85/api/v1/photos/b3000f79-1795-51a1-a9d9-b237c352a1e7/image/thumbnail"
```

### CORS 配置

后端已配置允许以下来源的跨域请求：

- `https://tkjs.buct.edu.cn`
- `http://tkjs.buct.edu.cn`
- `http://121.195.148.85`
- `http://localhost:5173` (Vite 开发服务器)
- `http://localhost:5174`
- `http://localhost:5175`
- `http://localhost:3000`

如果你的开发端口不在以上列表中，需要联系后端管理员添加。

---

## 📁 项目结构

```
frontend/
├── src/
│   ├── api/              # API 请求封装
│   │   ├── index.ts      # Axios 实例配置
│   │   ├── photo.ts      # 照片相关 API
│   │   ├── search.ts     # 搜索 API ⭐ 新增
│   │   └── ...
│   ├── components/       # 组件
│   ├── views/            # 页面
│   │   ├── GalleryView.vue   # 照片墙（含搜索集成）
│   │   ├── SearchView.vue    # 独立搜索页
│   │   └── ...
│   ├── stores/           # Pinia 状态管理
│   ├── router/           # 路由配置
│   └── utils/            # 工具函数
├── public/               # 静态资源
├── .env.development      # 开发环境配置
├── .env.production       # 生产环境配置
├── vite.config.ts        # Vite 配置
└── package.json
```

---

## 🔍 搜索功能开发

### 使用的 API

```typescript
// 向量搜索
GET /api/v1/search?q={query}&limit={limit}

// 响应格式
{
  results: [
    {
      photo_id: string,
      score: number,        // 0-1 相关度
      tags: string[],
      classifications: Record<string, string>
    }
  ],
  total: number,
  query_time_ms: number
}
```

### 前端调用示例

```typescript
import { searchPhotos } from '@/api/search'

const results = await searchPhotos({
  q: '秋天的校园',
  limit: 20,
  season: '秋季',  // 可选过滤
  campus: '昌平校区'
})
```

### 缩略图 URL

```
/api/v1/photos/{photo_id}/image/thumbnail
```

---

## ❓ 常见问题

### 1. CORS 错误

**症状**：浏览器控制台报 `Access-Control-Allow-Origin` 错误

**解决**：
1. 确认你的开发端口在 CORS 允许列表中
2. 或使用 Vite 代理（见下方）

### 2. 使用 Vite 代理避免 CORS

修改 `vite.config.ts`：

```typescript
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://121.195.148.85',  // 远程后端
        changeOrigin: true,
      },
    },
  },
})
```

然后将 `VITE_API_BASE_URL` 设为空。不要设为 `/api`，因为代码中的接口路径已经以 `/api/v1/...` 开头。

### 3. 图片加载失败

**症状**：缩略图 404

**检查**：
```bash
curl -I "http://121.195.148.85/api/v1/photos/{photo_id}/image/thumbnail"
```

**注意**：URL 是 `/image/thumbnail`，不是 `/thumbnail`

### 4. 登录后 401

**原因**：Token 过期或无效

**解决**：清除 localStorage/sessionStorage，重新登录

### 5. 网络不通

**检查**：
```bash
ping 121.195.148.85
curl http://121.195.148.85/api/v1/photos/public?page_size=1
```

**注意**：必须在校园网内才能访问

---

## 📞 联系方式

- **后端/运维**：yanp
- **项目地址**：https://github.com/JackWPP/BUCT_Media_System
- **API 文档**：[docs/API.md](./API.md)

---

## 📝 更新日志

### 2026-05-31
- ✅ 添加向量语义搜索功能
- ✅ CORS 配置支持本地开发
- ✅ 新增 API 手册

---

*本文档由 Hermes Agent 生成*
