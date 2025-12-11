# 智能数字资产管理系统 (IDAMS) 深度架构规划与实施报告

## 1. 项目背景与战略概述

### 1.1 当前数字资产管理的挑战与机遇

在数字化浪潮的推动下，个人与企业积累的非结构化数据——尤其是图像与视频素材——呈指数级增长。传统的本地文件系统管理方式，依赖于层级文件夹和人工重命名，已无法应对数以千计甚至数万张图片的检索需求。与此同时，依赖公有云的SaaS解决方案虽然提供了便捷的检索功能，但往往伴随着隐私泄露风险、高昂的订阅费用以及数据所有权的不可控性。

随着高性能本地硬件（如消费级GPU和高吞吐量NVMe SSD）的普及，以及开源大模型（Large Models）和视觉语言模型（VLMs）的迅猛发展，构建一个私有化、智能化、高性能的数字资产管理系统（Digital Asset Management, DAM）已成为可能且极具价值的方向。本报告旨在详细规划一套基于 **FastAPI** 高性能后端、**MinIO** 对象存储以及 **Vue 3** 现代化前端的智能图片管理系统——智能数字资产管理系统（IDAMS）。

### 1.2 MVP版本目标定义

本项目的核心目标是交付一个最小可行性产品（MVP），该版本需在本地环境中流畅管理数千张高分辨率照片，并具备以下核心能力：

1. **高性能数据流** ：利用异步I/O架构，实现无阻塞的图片上传与元数据处理。
2. **智能打标（Auto-Tagging）** ：集成视觉语言模型，自动识别图片内容并生成语义化标签，彻底解放人工整理的生产力。
3. **现代化交互体验** ：通过瀑布流（Masonry Layout）与虚拟滚动技术，确保在大数据量下的前端渲染性能，并支持拖拽式管理。
4. **云原生架构** ：采用容器化部署（Docker Compose），确保系统具备从单机MVP向集群化生产环境平滑演进的能力。

---

## 2. 技术选型与架构深度解析

### 2.1 后端框架：为何选择 FastAPI

在Python Web框架的生态中，FastAPI 凭借其卓越的性能和现代化的设计理念，已成为构建数据密集型和AI原生应用的首选 ^1^。

#### 2.1.1 异步并发模型与性能优势

传统的同步框架（如Flask或Django）在处理I/O密集型任务（如读取数据库、上传文件到MinIO、等待AI模型推理）时，往往会阻塞工作线程。而在IDAMS系统中，图片上传和AI推理不仅耗时，且并发量大。FastAPI 基于 Python 的 ASGI（Asynchronous Server Gateway Interface）标准，利用 `async/await` 语法原生支持异步编程 ^1^。这使得单个进程能够同时处理成百上千个并发请求，在等待I/O操作完成时释放CPU资源去处理其他请求，极大地提升了系统的吞吐量 ^3^。

#### 2.1.2 数据校验与类型安全

FastAPI 与 **Pydantic V2** 的深度集成是其另一大核心优势 ^1^。Pydantic V2 基于 Rust 重写，数据验证速度提升了5-50倍。在IDAMS中，前端传递的元数据（如拍摄时间、地理位置、自定义标签）往往结构复杂。通过定义强类型的 Pydantic 模型，系统可以在请求进入业务逻辑层之前，自动完成数据格式校验、类型转换和文档生成。这不仅减少了大量的防御性代码，还通过自动生成的 OpenAPI (Swagger) 文档极大地降低了前后端联调的成本 ^5^。

### 2.2 存储层：MinIO 对象存储的战略意义

#### 2.2.1 S3 协议的兼容性与标准化

选择 MinIO 作为文件存储后端，本质上是选择了 **Amazon S3 API** 这一事实上的工业标准 ^1^。MinIO 是一个高性能的分布式对象存储服务器，专为大规模非结构化数据设计。在 MVP 阶段，MinIO 可以在单机 Docker 容器中运行，提供极简的部署体验；而在未来扩展阶段，MinIO 支持纠删码（Erasure Coding）和分布式部署，能够轻松扩展至 PB 级容量而不改变应用层代码。

#### 2.2.2 为什么不直接使用本地文件系统？

虽然直接将图片存储在服务器的本地磁盘（Local FS）看似简单，但在容器化环境中，这种做法会导致数据与应用容器的强耦合，极其不利于迁移和扩展。MinIO 通过将存储抽象为对象（Object）和桶（Bucket），并在应用层通过 HTTP API 访问，实现了计算与存储的彻底解耦。此外，MinIO 提供的预签名 URL（Presigned URL）功能，为减轻后端带宽压力提供了架构上的灵活性 ^8^。

### 2.3 数据库：PostgreSQL 与 JSONB 的力量

对于元数据存储，本方案选用  **PostgreSQL 15+** 。相较于 MySQL，PostgreSQL 在处理复杂查询和非结构化数据（JSONB）方面表现更为优异 ^1^。

* **混合存储能力** ：IDAMS 需要存储图片的结构化信息（如文件名、上传者ID）以及非结构化的AI推理结果（如不确定的标签集合、置信度分数、原始OCR文本）。PostgreSQL 的 JSONB 数据类型允许我们以二进制格式存储 JSON 数据，并支持高效的索引查询，这消除了引入 MongoDB 等 NoSQL 数据库带来的架构复杂性 ^10^。
* **向量检索扩展性** ：未来若需实现“以图搜图”或“语义搜索”功能，PostgreSQL 可通过 `pgvector` 插件无缝支持向量存储与相似度搜索，无需引入专用的向量数据库。

### 2.4 前端框架：Vue 3 生态系统的现代化实践

前端界面是用户与系统交互的窗口，直接决定了产品的可用性。**Vue 3** 配合 **Composition API** 提供了高度的逻辑复用能力和更好的类型推断支持，非常适合构建复杂的单页应用（SPA）^11^。

* **Vite 构建工具** ：利用 ES Modules 实现毫秒级的热更新（HMR），极大提升了开发效率。
* **Tailwind CSS** ：采用原子类（Utility-first）CSS 框架，使得开发者无需在 HTML 和 CSS 文件间频繁切换，即可快速构建出响应式、美观的界面 ^13^。
* **状态管理** ：使用 **Pinia** 替代 Vuex。Pinia 移除了复杂的 mutation 层，API 更加简洁直观，且对 TypeScript 支持更加友好，非常适合管理图片列表、上传队列和用户鉴权状态 ^14^。

---

## 3. 总体架构设计与数据流转

### 3.1 模块化单体架构 (Modular Monolith)

针对“数千张照片”和“本地运行 MVP”的需求，微服务架构带来的服务发现、链路追踪等运维成本过于高昂。因此，本方案采用  **模块化单体架构** 。系统在逻辑上划分为清晰的模块（认证、资产管理、AI处理），但在物理部署上作为一个统一的 API 服务运行。

| **服务组件**              | **技术栈**         | **职责描述**                     |
| ------------------------------- | ------------------------ | -------------------------------------- |
| **API Gateway / Server**  | FastAPI (Uvicorn)        | 处理 HTTP 请求，业务逻辑编排，权限控制 |
| **Database**              | PostgreSQL               | 存储用户数据、资产元数据、标签关系     |
| **Object Storage**        | MinIO                    | 存储原始图片文件、缩略图、预览图       |
| **AI Engine**             | Ollama / Local Inference | 运行视觉语言模型，提供图片分析服务     |
| **Frontend**              | Vue 3 + Nginx            | 提供用户交互界面，静态资源托管         |
| **Task Queue (Optional)** | BackgroundTasks / Redis  | 处理异步耗时任务（如AI推理、图片压缩） |

### 3.2 核心数据流设计

#### 3.2.1 图片上传与存储流程 (The Ingestion Pipeline)

上传流程的设计需要在用户体验与服务器负载之间取得平衡。本方案采用 **后端代理上传 (Proxy Upload)** 模式，以简化 MVP 阶段的鉴权与跨域配置 ^2^。

1. **客户端发起** ：用户在 Vue 前端选择多张图片，前端组件生成本地预览，并构建 `multipart/form-data` 请求，包含文件二进制流及 JSON 元数据（如相册ID）。
2. **API 接收与校验** ：FastAPI 的 `UploadFile` 接口接收数据流。Pydantic 模型对元数据进行校验。此时，文件流暂存于内存缓冲区（SpooledTemporaryFile），超过阈值后自动落盘，防止内存溢出 ^16^。
3. **对象存储写入** ：API 服务调用 MinIO Python SDK，通过流式传输将文件写入 MinIO Bucket。系统根据 UUID 生成唯一的 Object Key，避免文件名冲突，并按日期分层存储（如 `/2024/05/uuid.jpg`）以优化目录性能。
4. **元数据入库** ：文件上传成功后，API 提取文件属性（大小、MIME类型）并结合业务元数据写入 PostgreSQL `assets` 表。初始状态标记为 `processing_status: 'PENDING'`。
5. **异步任务触发** ：API 在返回 HTTP 201 响应给前端之前，将 `analyze_image_task` 函数添加到 FastAPI 的 `BackgroundTasks` 队列中 ^17^。
6. **即时响应** ：前端收到上传成功的确认，界面上的上传进度条完成，图片状态变更为“处理中”。

#### 3.2.2 智能分析与打标流程 (The Intelligence Pipeline)

这是系统的核心增值环节，利用后台任务实现非阻塞的智能化处理。

1. **任务执行** ：后台任务从数据库获取待处理的 Asset ID。
2. **图像预处理** ：从 MinIO读取图片数据。若图片过大（如 20MB 原图），先利用 `Pillow` 库在内存中将其缩放至 AI 模型所需的尺寸（如 1024x1024），以减少显存占用和网络传输时间。
3. **VLM 推理** ：调用本地运行的 Ollama 服务接口（或集成的 ONNX Runtime），发送图片及 Prompt（提示词）。

* *Prompt 示例* ：“分析这张图片，列出其中的主要物体、场景、颜色和氛围，并以 JSON 格式返回关键词列表。”

1. **结果解析与存储** ：解析模型返回的 JSON 数据，提取标签（Tags）。

* **标签去重与归一化** ：检查 `tags` 表，若标签已存在则获取 ID，不存在则创建。
* **建立关联** ：在 `asset_tags` 关联表中写入记录，并标记 `source='ai'` 及置信度分数。

1. **状态更新** ：更新 `assets` 表状态为 `COMPLETED`。前端通过轮询或 WebSocket（进阶功能）检测到状态变化，自动刷新显示新生成的标签。

---

## 4. 后端核心系统详细设计

### 4.1 项目结构规范

为了保证代码的可维护性和可扩展性，项目遵循“基于功能的模块化”结构 ^5^。

idams_backend/

├── app/

│   ├── init.py

│   ├── main.py                 # 应用入口，包含中间件和路由注册

│   ├── core/                   # 核心配置

│   │   ├── config.py           # 环境变量管理 (Pydantic BaseSettings)

│   │   ├── security.py         # JWT 加密与解密工具

│   │   ├── database.py         # SQLAlchemy Engine & SessionLocal

│   │   └── exceptions.py       # 全局异常处理

│   ├── models/                 # 数据库 ORM 模型

│   │   ├── user.py

│   │   ├── asset.py

│   │   └── tag.py

│   ├── schemas/                # Pydantic 数据传输模型 (DTO)

│   │   ├── asset.py

│   │   ├── tag.py

│   │   └── token.py

│   ├── api/                    # API 路由层

│   │   ├── deps.py             # 依赖注入 (Dependency Injection)

│   │   └── v1/

│   │       ├── api.py

│   │       ├── endpoints/

│   │           ├── auth.py

│   │           ├── assets.py

│   │           └── tags.py

│   ├── services/               # 业务逻辑层

│   │   ├── storage.py          # MinIO 操作封装

│   │   └── ai_engine.py        # VLM 模型调用封装

│   └── utils/

├── alembic/                    # 数据库迁移脚本

├── requirements.txt

├── docker-compose.yml

└── Dockerfile

### 4.2 数据库模式设计 (Schema Design)

数据库设计需重点考虑多对多关系（Many-to-Many）的高效查询，特别是在处理标签系统时 ^19^。

#### 4.2.1 实体关系模型 (ERD)

**1. Users 表**

* 用户基础信息，支持多用户隔离（尽管 MVP 可能是单用户，但设计需预留空间）。
* `id` (UUID, PK), `email` (String, Unique), `hashed_password` (String), `is_active` (Bool).

**2. Assets 表**

* 存储图片的核心元数据。
* `id` (UUID, PK)
* `owner_id` (UUID, FK -> Users.id)
* `filename` (String): 原始文件名。
* `object_key` (String): MinIO 中的存储路径，建立 DB 与 OSS 的映射。
* `media_type` (String): MIME 类型 (image/jpeg, image/png)。
* `width`, `height` (Integer): 图片分辨率，用于前端瀑布流布局计算占位。
* `created_at` (Timestamp): 上传时间。
* `captured_at` (Timestamp): 从 EXIF 读取的拍摄时间。
* `meta_data` (JSONB): 存储完整的 EXIF 信息及其他非结构化属性。

**3. Tags 表**

* 标签定义。
* `id` (Integer, PK)
* `name` (String, Unique): 标签文本，建议存储为小写以实现不区分大小写的搜索。
* `category` (String): 标签分类（如：物体、颜色、风格）。

**4. AssetTags 关联表**

* 连接 Assets 与 Tags，支持额外的关系属性 ^22^。
* `asset_id` (UUID, FK -> Assets.id)
* `tag_id` (Integer, FK -> Tags.id)
* `confidence` (Float): AI 预测的置信度 (0.0 - 1.0)。
* `source` (Enum): 'manual' (人工) 或 'ai' (自动)。
* `created_at` (Timestamp)
* **复合主键** : (asset_id, tag_id) 确保同一图片对同一标签不重复关联。

### 4.3 核心 API 实现细节

#### 4.3.1 依赖注入与数据库会话

FastAPI 的依赖注入系统（Dependency Injection）是管理数据库会话生命周期的最佳实践。

**Python**

```
# app/api/deps.py
from typing import Generator
from app.core.database import SessionLocal

def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()
```

#### 4.3.2 异步上传端点实现

在 `assets.py` 中，我们需要同时处理文件流和表单数据。

**Python**

```
# app/api/v1/endpoints/assets.py
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, Form
from sqlalchemy.orm import Session
from app.schemas.asset import AssetCreate
from app.services import storage, ai_engine
from app.api import deps

router = APIRouter()

@router.post("/", response_model=AssetRead, status_code=201)
async def create_asset(
    *,
    db: Session = Depends(deps.get_db),
    file: UploadFile = File(...),
    # 使用 Form 接收 JSON 字符串并解析，因为 multipart/form-data 不支持直接嵌套 JSON
    meta_data_str: str = Form(default="{}"),
    background_tasks: BackgroundTasks
):
    # 1. 上传至 MinIO (同步或异步封装)
    object_key = storage.upload_file(file)
  
    # 2. 创建数据库记录
    asset_in = AssetCreate(
        filename=file.filename,
        object_key=object_key,
        media_type=file.content_type,
        #... 解析 meta_data_str...
    )
    asset = crud.asset.create(db, obj_in=asset_in)
  
    # 3. 添加后台分析任务
    background_tasks.add_task(ai_engine.process_image, asset.id, db)
  
    return asset
```

### 4.4 认证与安全性

采用 **OAuth2 Password Bearer** 流程与 **JWT (JSON Web Tokens)** ^23^。

* 用户登录换取 `access_token`。
* 所有受保护的路由通过 `Depends(get_current_user)` 获取当前用户实例。
* 密码使用 `passlib` 配合 `bcrypt` 算法进行哈希存储，绝不存储明文密码。

---

## 5. 智能引擎与AI集成方案

为了实现“智能打标”，我们需要一个能够理解图像内容的组件。在本地环境中，使用轻量级的视觉语言模型（VLM）是最佳选择。

### 5.1 模型选型：本地化与性能的权衡

考虑到“本地运行 MVP”的要求，我们不能依赖 OpenAI 的 GPT-4V 等在线 API（受限于网络和成本）。

* **LLaVA (Large Language-and-Vision Assistant)** : 基于 Llama 2 或 Vicuna，具备极强的图像描述能力。其 7B 或 13B 版本在 16GB 内存的机器上运行良好。
* **Moondream** : 一个极其轻量级（约 1.6B 参数）的 VLM，专为边缘设备设计，虽然理解深度不如 LLaVA，但推理速度极快，非常适合大批量图片的初步打标。
* **Ollama** : 作为一个本地大模型运行框架，Ollama 支持一键拉取和运行上述模型，并提供标准的 HTTP API，极大地简化了集成难度 ^25^。

 **决策** ：MVP 阶段推荐使用 **Ollama** 运行 **LLaVA v1.5 7b** 或  **Moondream** 。Ollama 封装了复杂的模型加载和量化逻辑，对外提供类似 OpenAI 的接口。

### 5.2 Prompt Engineering (提示词工程)

为了让模型输出结构化的标签而非一段散文，提示词的设计至关重要。

 **Prompt 模板** ：

> "Act as a professional image tagger. Analyze the provided image and extract key entities, colors, scene descriptions, and mood. Output ONLY a JSON object with the following keys: 'objects' (list of strings), 'colors' (list of strings), 'scene' (string). Do not include any conversational text."

### 5.3 AI 服务层实现

在 `app/services/ai_engine.py` 中，我们通过 HTTP 请求调用本地的 Ollama 服务。

**Python**

```
import httpx
import base64
from app.core.config import settings

async def analyze_image_with_ollama(image_path: str):
    # 1. 从 MinIO 获取图片数据
    image_data = storage.get_object(image_path)
    # 2. Base64 编码 [27, 28]
    b64_image = base64.b64encode(image_data).decode('utf-8')
  
    # 3. 构造请求
    payload = {
        "model": "llava",
        "prompt": "List the main objects and descriptive tags for this image as a comma-separated list.",
        "images": [b64_image],
        "stream": False
    }
  
    async with httpx.AsyncClient() as client:
        # 假设 Ollama 运行在 Docker 网络的 host 或专用容器中
        resp = await client.post(f"{settings.OLLAMA_API_URL}/api/generate", json=payload, timeout=60.0)
      
    if resp.status_code == 200:
        return _parse_tags(resp.json().get("response"))
    return

def _parse_tags(raw_text: str) -> list[str]:
    # 清洗数据，去除特殊字符，分割逗号
    return [tag.strip().lower() for tag in raw_text.split(",") if tag.strip()]
```

---

## 6. 前端交互界面设计 (Vue 3)

前端设计不仅仅是展示图片，更是要提供高效的管理工具。

### 6.1 技术栈细节

* **Vue 3 (Script Setup)** : 利用 Composition API 的 `ref` 和 `reactive` 管理复杂的页面状态。
* **Vue Router** : 管理页面路由（画廊视图、详情视图、登录页）。
* **Axios** : 封装 HTTP 请求，处理 JWT Token 的自动注入和 401 刷新逻辑。
* **VueUse** : 一个强大的 Composition API 工具库，利用其 `useInfiniteScroll` 和 `useElementSize` 快速实现响应式功能 ^12^。

### 6.2 瀑布流布局与虚拟滚动 (Virtualized Masonry Grid)

当相册包含数千张照片时，直接渲染所有 DOM 节点会导致浏览器卡顿甚至崩溃。

* **瀑布流 (Masonry)** : 图片等宽不等高，错落排列。这通常通过计算每列的高度，将下一张图片放置在当前高度最小的列中来实现。
* **虚拟滚动 (Virtual Scrolling)** : 仅渲染当前视口（Viewport）内可见的图片及上下少量的缓冲区。随着用户滚动，动态回收不可见的 DOM 节点并创建新节点。
* **实现方案** : 推荐使用现成的成熟库如 `vue-masonry-wall` 或结合 `vue-virtual-scroller`，它们能很好地处理复杂的计算逻辑，保证 60fps 的流畅度 ^11^。

### 6.3 交互式打标组件

用户需要查看 AI 生成的标签，并能方便地添加、删除或修改。

* **标签输入框 (Tag Input)** : 支持输入自动完成（Autocomplete），数据源来自后端已有的标签库。
* **拖拽管理 (Drag and Drop)** : 使用 `vue-draggable-next` ^31^。
* **场景** : 系统可能会显示“AI 推荐标签”区域和“已确认标签”区域。用户可以将标签从“推荐”区拖拽到“确认”区，或者直接拖拽删除。
* **视觉反馈** : AI 生成的标签可以用虚线边框或特定颜色标识（如淡黄色），用户确认（或手动输入）的标签显示为实线深色，直观区分数据来源。

### 6.4 界面布局规划

| **页面区域**   | **功能描述**                                   | **关键组件**                       |
| -------------------- | ---------------------------------------------------- | ---------------------------------------- |
| **顶部导航栏** | 搜索栏（支持标签、时间组合搜索）、上传按钮、用户头像 | `SearchBar`,`UserMenu`               |
| **侧边栏**     | 相册列表、分类浏览（按标签自动分类）、回收站         | `SidebarNav`                           |
| **主内容区**   | 图片瀑布流展示，支持无限滚动加载                     | `MasonryGrid`,`InfiniteLoader`       |
| **详情模态框** | 点击图片弹出，显示大图、EXIF信息、编辑标签           | `Lightbox`,`TagEditor`,`ExifPanel` |

---

## 7. 详细开发文档与实施指南

### 7.1 环境准备与依赖安装

#### 7.1.1 Docker 环境

确保本地安装了 Docker Desktop 或 Docker Engine + Docker Compose。这是运行 MinIO 和 PostgreSQL 的基础。

#### 7.1.2 配置文件 (.env)

在项目根目录创建 `.env` 文件，管理敏感配置。

**Ini, TOML**

```
# Database
POSTGRES_USER=idams_user
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=idams_db
POSTGRES_SERVER=db

# MinIO
MINIO_ROOT_USER=minio_admin
MINIO_ROOT_PASSWORD=minio_secure_password
MINIO_ENDPOINT=minio:9000
MINIO_BUCKET=idams-assets

# Security
SECRET_KEY=generate_a_long_random_string_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI Service
OLLAMA_API_URL=http://host.docker.internal:11434
```

### 7.2 Docker Compose 编排

**YAML**

```
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
    ports:
      - "5432:5432"
    networks:
      - idams_net

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
    environment:
      - MINIO_ROOT_USER=${MINIO_ROOT_USER}
      - MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD}
    ports:
      - "9000:9000"
      - "9001:9001"
    networks:
      - idams_net

  backend:
    build:./idams_backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      -./idams_backend:/app
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db/${POSTGRES_DB}
      - MINIO_ENDPOINT=${MINIO_ENDPOINT}
      - MINIO_ACCESS_KEY=${MINIO_ROOT_USER}
      - MINIO_SECRET_KEY=${MINIO_ROOT_PASSWORD}
    ports:
      - "8000:8000"
    depends_on:
      - db
      - minio
    networks:
      - idams_net
    extra_hosts:
      - "host.docker.internal:host-gateway" # 允许容器访问宿主机的 Ollama

  frontend:
    build:./idams_frontend
    ports:
      - "8080:80"
    depends_on:
      - backend
    networks:
      - idams_net

volumes:
  postgres_data:
  minio_data:

networks:
  idams_net:
```

### 7.3 开发步骤指南

#### 第一步：后端基础搭建

1. 初始化 FastAPI 项目结构。
2. 编写 `app/models` 和 `app/schemas`，定义 Asset 和 Tag 的数据结构。
3. 配置 Alembic，运行 `alembic revision --autogenerate` 生成初始 SQL 迁移脚本，并应用到数据库。

#### 第二步：存储与上传逻辑

1. 集成 `minio` Python SDK。
2. 编写上传 API，测试文件能否成功写入 MinIO Bucket，并确认数据库中生成了记录。
3. **关键点** ：确保处理好文件重命名（UUID），防止上传同名文件导致覆盖。

#### 第三步：AI 服务集成

1. 在本地安装 Ollama 并拉取模型：`ollama run llava`。
2. 编写后端 `ai_engine` 服务，测试通过 HTTP 请求发送一张 Base64 编码的图片给 Ollama，并打印返回的 JSON。
3. 将此逻辑接入 FastAPI 的 `BackgroundTasks`，实现上传后的自动调用。

#### 第四步：前端开发

1. 使用 Vite 创建 Vue 3 + TypeScript 项目。
2. 安装 Tailwind CSS, Axios, Pinia, Vue Router。
3. 开发 `Login` 页面，实现 JWT 存储。
4. 开发 `Gallery` 页面，对接列表 API，调试瀑布流布局。
5. 开发上传组件，对接上传 API，并添加进度条显示。

---

## 8. 部署运维与未来展望

### 8.1 部署策略

对于本地 MVP，直接使用 `docker-compose up -d` 即可一键启动所有服务。

* **数据备份** ：定期备份 PostgreSQL 的数据卷 (`postgres_data`) 和 MinIO 的数据卷 (`minio_data`)。可以使用简单的 Shell 脚本配合 `crontab` 实现每日备份到外部硬盘。

### 8.2 性能优化方向

1. **缩略图生成** ：目前方案可能直接加载原图或由 MinIO 处理。生产环境应在上传后立即生成多种分辨率的缩略图（Thumbnail），前端列表仅加载小图，大幅减少带宽占用。
2. **AI 任务队列升级** ：当图片量达到数万张时，FastAPI 的内存级后台任务将不再适用（重启丢失、无重试机制）。应引入 **Celery** 或 **ARQ** 配合 Redis，构建持久化的任务队列 ^32^。
3. **向量搜索 (Semantic Search)** ：利用 CLIP 等模型将图片和文本转换为向量（Embeddings），存入 PostgreSQL 的 `pgvector` 扩展中。这将支持自然语言搜索，例如输入“雪地里奔跑的狗”，即使没有显式标签也能利用语义相似度找到图片。

### 8.3 总结

本报告详细规划了一个全栈式的智能数字资产管理系统。通过结合 **FastAPI** 的高性能异步处理、**MinIO** 的可扩展存储以及 **Vue 3** 的流畅交互，再加上 **本地 LLM/VLM** 的智能赋能，我们构建了一个既保护隐私又具备强大管理能力的现代化图片管理平台。该架构不仅满足了当前管理数千张照片的 MVP 需求，也为未来向更复杂的 AI 应用和大规模集群演进预留了充足的空间。
