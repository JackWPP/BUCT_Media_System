# 视觉北化 — 后端更新文档

> 本文档供前端对接参考，汇总本次所有后端变更、新增字段、API 端点及数据模型变化。

---

## 一、数据库变更

### 1.1 照片表 (photos)

当前 495 张照片，全部来自 OSS 摄影大赛作品（2018-2024），AI 预处理完成。

| 字段 | 类型 | 说明 | 状态 |
|------|------|------|------|
| `season` | String(20) | 季节：春季/夏季/秋季/冬季/None | AI 已填充（61% 有值） |
| `campus` | String(50) | 校区：昌平校区/朝阳校区 | AI 已填充（100%） |
| `category` | String(50) | 类型：Landscape/Documentary | 导入时填充 |
| `status` | String(20) | 审核状态：**approved** | 全量已审批 |
| `processing_status` | String(20) | AI 处理状态：**completed** | 全量已完成 |
| `original_path` | Text | S3 对象键，如 `photos/2018_xxx.jpg` | OSS 直连 |
| `thumb_path` | Text | 缩略图路径（暂为 NULL） | 暂无缩略图 |
| `views` | Integer | 浏览计数 | 可用于热门排序 |

### 1.2 分类体系 (taxonomy)

AI 分析结果已写入受控分类表 `photo_classifications`，共 **2205 条**记录，覆盖全部 495 张照片。

| 分类面 (facet key) | 说明 | 常见值 |
|------|------|------|
| `season` | 季节 | 夏季(115) / 秋季(55) / 冬季(47) / 春季(30) |
| `campus` | 校区 | 昌平校区(495) |
| `landmark` | 地标 | 学生活动中心(65) / 柳湖(53) / 图书馆(41) / 科技大厦(20) |
| `gallery_series` | 图库系列 | 摄影大赛(495) |
| `gallery_year` | 年份 | 2024(40) / 2020(38) / 2019(31) / 2023(19) |
| `photo_type` | 照片类型 | 风光(228) / 纪实(177) |

**前端获取方式**：通过分类 API 或直接查 `photo_classifications` 关联表。

### 1.3 标签 (tags)

AI 生成 **839 个**自由标签，已关联到对应照片（`photo_tags` 表）。

Top 标签：红砖建筑(62) / 远山(60) / 学生(60) / 夏季(59) / 建筑(53) / 倒影(40) / 室内(40) / 雪景(26) / 秋叶(25) / 夜景(24)

### 1.4 AI 分析任务 (ai_analysis_tasks)

405 条记录，status=completed。`result_json` 字段包含完整 AI 输出：

```json
{
  "summary": "一句话中文描述（15-30字）",
  "classifications": {
    "season": "夏季",
    "campus": "昌平校区",
    "landmark": "柳湖",
    "gallery_series": "摄影大赛",
    "gallery_year": null,
    "photo_type": "风光"
  },
  "free_tags": ["柳湖", "倒影", "绿树", "夏季"],
  "quality_flags": [],
  "risk_flags": [],
  "confidence": 0.91,
  "provider": "openai_compatible",
  "model_id": "qwen3-vl-8b-instruct-abliterated-v2.0"
}
```

---

## 二、API 端点变更

### 2.1 新增端点

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| `GET` | `/api/v1/admin/database/export` | 下载 SQLite 数据库文件（用于迁移到 PostgreSQL） | admin |

### 2.2 行为变更

| 端点 | 变更 |
|------|------|
| `GET /photos/{id}/image/thumbnail` | 缩略图不存在时自动降级返回原图，不再返回 404 |
| `GET /photos/{id}/image/original` | 图片通过后端流式传输（StreamingResponse），浏览器不再被重定向到外部 URL |

### 2.3 现有 AI 相关端点（无变更，供参考）

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/photos/{id}/ai-analysis` | 获取最新 AI 分析结果 |
| `POST` | `/photos/{id}/ai-analysis` | 触发单张 AI 分析 |
| `POST` | `/photos/batch-ai-analysis` | 批量触发 AI 分析（admin） |
| `POST` | `/photos/{id}/ai-analysis/{task_id}/apply` | 应用 AI 结果到照片 |
| `POST` | `/photos/{id}/ai-analysis/{task_id}/ignore` | 忽略 AI 建议 |
| `GET` | `/taxonomy/public` | 获取分类体系（公开） |
| `GET` | `/taxonomy/facets` | 获取分类面详情（审核人） |

---

## 三、存储架构

```
浏览器 ──→ localhost:8000 (FastAPI StreamingResponse)
                │
                └──→ 121.195.148.85:9000 (MinIO S3, bucket: buctmedia)
```

- 图片通过后端流式传输，前端 `<img>` 标签直接指向 `/api/v1/photos/{id}/image/original` 或 `/thumbnail`
- 对象键格式：`photos/{year}_{filename}`
- 无需关心 S3 端点地址

---

## 四、数据统计（当前快照）

| 指标 | 数值 |
|------|------|
| 照片总数 | 495 |
| 已审批 | 495 |
| AI 处理完成 | 495 |
| 标签总数 | 839 |
| 分类记录 | 2205 |
| 照片类型分布 | 风光 228 / 纪实 177 |
| 年份跨度 | 2018-2024 |

---

## 五、环境配置要点

后端 `.env` 关键配置：

```env
STORAGE_BACKEND=s3
S3_ENDPOINT=http://121.195.148.85:9000
S3_BUCKET=buctmedia
AI_ENABLED=true
AI_PROVIDER=openai_compatible
```

前端无需特殊配置，API 地址保持指向后端即可（默认 `http://localhost:8000`）。

---

## 六、前端建议

1. **分类筛选**：利用 `photo_classifications` + `taxonomy_facets` 做侧边栏筛选（按季节/地标/类型/年份）
2. **标签展示**：照片详情页展示 `tags`，标签可点击搜索
3. **AI 摘要**：照片卡片 hover 时展示 AI 生成的 `summary`
4. **热门排序**：用 `views` 字段排序
5. **缩略图**：当前 `thumb_path` 为 NULL，`/thumbnail` 端点返回原图。后续若需缩略图可批量生成
6. **上传功能**：若开启 AI (`enable_ai=true`)，上传后会自动排队 AI 分析

---

*文档生成于 2026-04-29，基于 backend 当前代码状态*
