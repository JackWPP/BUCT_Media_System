# AI 自动打标功能使用指南

## 功能概述

BUCT Media HUB 集成了基于视觉语言模型(VLM)的 AI 自动打标功能,可以自动分析上传的照片并生成:
- 季节分类 (Spring/Summer/Autumn/Winter)
- 场景类型 (Landscape/Portrait/Activity/Documentary)
- 关键词标签 (中文,最多5个)

## AI 服务配置

### 选项 1: 使用 Ollama (推荐,本地部署)

**1. 安装 Ollama**

- macOS/Linux:
  ```bash
  curl -fsSL https://ollama.com/install.sh | sh
  ```

- Windows:
  下载安装包: https://ollama.com/download

**2. 拉取 LLaVA 模型**

```bash
ollama pull llava
```

**3. 启动 Ollama 服务**

```bash
ollama serve
```

默认运行在 `http://localhost:11434`

**4. 配置环境变量**

在 `.env` 文件中设置:
```ini
OLLAMA_API_URL=http://localhost:11434
AI_MODEL_NAME=llava
AI_ENABLED=True
```

### 选项 2: 使用阿里云 DashScope (云端 API)

**1. 获取 API Key**

访问: https://dashscope.console.aliyun.com/

**2. 配置环境变量**

在 `.env` 文件中设置:
```ini
DASHSCOPE_API_KEY=your-api-key-here
AI_PROVIDER=dashscope
AI_ENABLED=True
```

### 选项 3: 禁用 AI 功能

如果暂时不需要 AI 自动打标,可以禁用:
```ini
AI_ENABLED=False
```

## 使用方式

### 1. 上传照片时自动打标

上传照片时,如果未手动指定 `season` 或 `category`,AI 会自动分析并填充:

**API 请求示例**:
```bash
curl -X POST "http://localhost:8002/api/v1/photos/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@photo.jpg" \
  -F "enable_ai=true"
```

**处理流程**:
1. 照片上传成功后立即返回
2. 后台异步执行 AI 分析
3. `processing_status` 状态变化:
   - `pending` → `processing` → `completed`
   - 或 `failed` (如果 AI 服务不可用)

### 2. 查询处理状态

查看照片详情时,可以看到 `processing_status`:

```bash
curl -X GET "http://localhost:8002/api/v1/photos/{photo_id}" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

响应示例:
```json
{
  "id": "xxx",
  "filename": "photo.jpg",
  "processing_status": "completed",
  "season": "Winter",
  "category": "Landscape",
  "tags": ["建筑", "雪", "天空"]
}
```

### 3. 禁用某次上传的 AI 分析

如果不希望使用 AI 分析,可以手动指定所有字段:

```bash
curl -X POST "http://localhost:8002/api/v1/photos/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@photo.jpg" \
  -F "season=Spring" \
  -F "category=Landscape" \
  -F "enable_ai=false"
```

## AI 分析结果说明

### Season (季节)
- `Spring` - 春季
- `Summer` - 夏季
- `Autumn` - 秋季
- `Winter` - 冬季

### Category (场景类型)
- `Landscape` - 风景照片
- `Portrait` - 人像照片
- `Activity` - 活动照片
- `Documentary` - 纪实照片

### Objects (关键词标签)
- 自动提取照片中的关键物体
- 使用中文标签
- 最多提取 5 个
- 标签会自动创建并关联到照片

## 测试 AI 服务

运行测试脚本验证 AI 功能:

```bash
python tests/test_ai_tagging.py
```

测试内容:
- ✅ 图片压缩和编码
- ✅ Prompt 构建
- ✅ JSON 响应解析
- ✅ Ollama API 调用 (需要服务运行)

## 常见问题

### Q1: AI 分析一直处于 pending 状态

**原因**: Ollama 服务未运行或不可用

**解决方法**:
1. 检查 Ollama 是否运行: `curl http://localhost:11434/api/tags`
2. 启动 Ollama: `ollama serve`
3. 检查模型是否已安装: `ollama list`

### Q2: AI 分析返回的标签不准确

**原因**: 
- 照片质量问题
- 模型对特定场景识别能力有限

**解决方法**:
- 使用人工微调功能修改标签
- 在照片详情页面添加/删除/修改标签

### Q3: AI 分析速度慢

**原因**: 
- 本地硬件性能限制
- 图片尺寸过大

**优化方法**:
- 系统会自动将图片压缩到 1024px 再分析
- 考虑使用 GPU 加速 (需配置 Ollama GPU 支持)
- 或使用云端 API (DashScope)

### Q4: 如何查看 AI 分析日志

查看后端日志:
```bash
# 启动服务时会输出日志
uvicorn app.main:app --reload --port 8002

# 日志示例:
# INFO:app.api.v1.endpoints.photos:开始 AI 分析照片: xxx
# INFO:app.api.v1.endpoints.photos:AI 分析完成: xxx, season=Winter, category=Landscape, tags=5
```

## 性能指标

- **图片压缩**: < 1 秒
- **AI 分析**: 5-30 秒 (取决于硬件和模型)
- **后台处理**: 不阻塞上传响应

## 技术细节

### Prompt 模板

```
请分析这张图片。

1. 判断季节 (Spring/Summer/Autumn/Winter)。
2. 判断场景类型 (Landscape/Portrait/Activity/Documentary)。
3. 提取画面中的关键物体 (不超过5个) 使用中文标签。

请以纯JSON格式返回，不要包含Markdown格式标记，格式如下:
{
    "season": "...",
    "category": "...",
    "objects": ["...", "..."]
}
```

### 错误处理机制

1. **AI 服务不可用**: 
   - `processing_status` 设为 `failed`
   - 照片仍可正常使用,只是缺少自动标签

2. **JSON 解析失败**:
   - 自动移除 Markdown 格式标记
   - 使用默认值填充缺失字段

3. **无效的分类值**:
   - 自动替换为默认值 (Spring, Landscape)
   - 记录警告日志

## 未来扩展

- [ ] 支持更多 VLM 模型 (Qwen-VL, GPT-4V)
- [ ] 支持批量重新分析已有照片
- [ ] 支持自定义 Prompt 模板
- [ ] 支持人脸识别和聚类
- [ ] 支持语义搜索 (CLIP)

## 相关文档

- [Ollama 官方文档](https://github.com/ollama/ollama)
- [LLaVA 模型介绍](https://llava-vl.github.io/)
- [系统设计文档](../../docs/media-hub-design-and-implementation.md)
