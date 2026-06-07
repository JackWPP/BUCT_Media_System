# 标签体系统一实施评估与推进计划

更新时间：2026-06-07

## 目标

将视觉北化全系统的标签能力统一为：

- 严格分类：由 `taxonomy_facets`、`taxonomy_nodes`、`photo_classifications` 承载，是网站正式分类、筛选、展示和审核的主数据。
- 标准内容标签：楼宇、设施、景观、自然现象、表现手法、动物、植物、季节、纪实主题等仍属于 taxonomy，不作为自由标签沉淀。
- 补充自由标签：由 `tags`、`photo_tags` 承载，允许用户/标注员补充描述性 tag，并作为公共筛选和搜索召回的一部分，但不替代标准分类。

本轮只做评估和实施方案沉淀，不直接执行代码改动或生产数据迁移。

## 已确认原则

### 1. 标签映射与迁移

- 旧字段、旧 taxonomy、旧自由标签中能确定映射到新体系的内容，迁移到新 taxonomy。
- 无法确定的内容先留空，不强行归类，不制造“其它/无法判断”兜底节点。
- 历史数据迁移以“网站可正常运转 + 后续人工补齐”为目标，不追求一次性自动补全全部细分内容。
- 所有生产迁移默认先 dry-run 出报告，再审查 unresolved 列表，最后单独 apply。

### 2. 自由标签与筛选

- 自由标签保留，并作为公共筛选的一部分。
- 设计上参考图片站常见模式：固定硬性分类用于标准筛选，用户自加 tag 用于补充描述、公共筛选和搜索召回。
- 自由标签不自动升级为标准 taxonomy。若后续发现高频自由标签应标准化，需要单独做管理员归并或 alias 沉淀流程。

### 3. AI 自动打标

- 本轮暂不做 AI 自动打标的功能完善。
- 但后端接口和数据结构要保留兼容空间，后续 AI 输出应能直接对齐新 taxonomy，而不是继续输出旧 `landmark`。
- AI 结果进入正式照片数据前仍应走人工审核或管理员确认流程。

### 4. 父节点/分组节点提交

- 本轮新增 `taxonomy_nodes.is_selectable`，把“分组节点仅用于 UI 分组”固化为后端契约。
- 服务层、标注提交、手动分类编辑和前端提交前清洗都应拒绝 `is_selectable=false` 的节点。
- 数据库仍允许节点结构调整，是否可提交由 `is_selectable` 明确表达。

### 5. 限量搜索与索引重建

- 可以重建搜索索引逻辑，但必须考虑后续标签体系还会继续调整。
- 索引应支持增量重建和全量重建，不能绑定一次性标签快照。
- 在标签重建期间，搜索需要能容忍分类缺失：标准 taxonomy 用于精确筛选，自由标签/标题/描述用于补充召回。

## 当前系统实际情况

### 已经接近目标的部分

- 后端已有 taxonomy 主模型：
  - `taxonomy_facets`
  - `taxonomy_nodes`
  - `photo_classifications`
- 后端已有自由标签模型：
  - `tags`
  - `photo_tags`
  - `tag_aliases`
- 当前 taxonomy seed 已包含新的主要 facet：
  - `gallery_series`
  - `source_type`
  - `gallery_year`
  - `award_level`
  - `campus`
  - `photo_type`
  - `building`
  - `facility`
  - `landscape`
  - `natural_phenomenon`
  - `technique`
  - `animal`
  - `plant`
  - `documentary_topic`
  - `season`
- `building` 已恢复为独立 facet，校区不再作为楼宇节点。
- 标注工作台提交逻辑已经要求核心分类：
  - `gallery_series`
  - 摄影大赛必须有 `gallery_year`
  - 投稿作品必须有 `source_type`
  - `campus`
  - `photo_type`
- 标注提交已经允许多选细分 taxonomy，并拒绝提交有子节点的分组节点。
- 已有 dry-run 迁移脚本可报告旧 `landmark` 到 `building` / `landscape` / unresolved 的迁移情况。

### 尚未完全统一的部分

- `photos` 表仍保留旧字段：
  - `season`
  - `category`
  - `campus`
- taxonomy 写入时会同步回填部分旧字段，因此短期兼容没问题，但长期要明确 taxonomy 才是分类主数据。
- AI 图像分析 prompt 仍在要求模型输出旧 `landmark`，并且把 `free_tags` 描述为语义搜索核心数据。
- AI apply 逻辑目前会把旧 `landmark` 尝试映射到 `building` 或 `landscape`，这是兼容层，不应成为长期主路径。
- 普通 JSON 导入接口仍主要写旧 `season/category` 字段和自由标签，没有完整进入 taxonomy。
- 当前向量搜索主要是“向量化自由标签，再找拥有这些 tag 的照片”，不是对标准 taxonomy、标题、描述、自由标签的统一语义索引。
- taxonomy 管理接口允许管理员创建和修改 facet/node，后续需要治理规则，避免再次出现混合语义。

## 目标数据边界

### 正式分类

正式分类只通过 taxonomy 表达：

- 来源/专区：
  - `gallery_series`
  - `source_type`
  - `gallery_year`
  - `award_level`
- 位置：
  - `campus`
  - `building`
  - `facility`
  - `landscape`
- 内容：
  - `photo_type`
  - `season`
  - `natural_phenomenon`
  - `technique`
  - `animal`
  - `plant`
  - `documentary_topic`

### 自由标签

自由标签用于：

- 补充画面描述，例如“逆光剪影”“红砖外墙”“湖面倒影”。
- 公共 tag 筛选。
- 关键词搜索和语义搜索召回。

自由标签不用于：

- 代替 `campus`、`photo_type`、`building` 等标准分类。
- 自动生成标准 taxonomy 节点。
- 决定详情页中的正式地点、楼宇、来源、题材展示。

## 搜索与限量搜索评估

### 当前搜索结构

当前有两条主要搜索路径：

1. `/api/v1/photos/public`
   - 支持标准 taxonomy 筛选参数，如 `building`、`campus`、`photo_type` 等。
   - 文本搜索会同时查文件名、描述、自由标签、taxonomy node、taxonomy alias。

2. `/api/v1/search`
   - 当前是向量搜索入口。
   - 主要流程是：用户 query 向量化，去 Milvus 找相似自由标签，再回 PostgreSQL 找拥有这些自由标签的照片。

### 对限量搜索的影响

标签重建会影响搜索结果，影响程度取决于搜索路径：

- 标准 taxonomy 筛选：迁移后会更稳定，因为筛选从旧混合语义收口到明确 facet。
- 自由标签筛选：会受清洗、合并、删除影响，需要迁移前保留映射报告。
- 向量搜索：影响最大，因为当前 Milvus 索引主要来自自由标签。自由标签重建后必须重建向量索引，否则搜索会命中旧 tag。
- 限量返回：如果只按向量 tag 命中排序，标签重建期间可能出现结果数量减少、排序波动、部分新分类无法召回。

### 建议方向

搜索索引后续应改为“组合搜索文档”：

- 标准 taxonomy 节点名称。
- taxonomy alias。
- 自由标签。
- 照片标题/文件名。
- 描述/来源信息。
- 必要时加入作者、届次、奖项等导入元数据。

这样即使自由标签正在重建，标准分类仍能参与召回，限量搜索不会完全依赖自由标签质量。

## 分阶段推进

### 阶段 0：生产只读审计

目标：确认真实数据状态，不写生产。

建议检查：

- 当前生产 taxonomy facet/node 列表。
- 是否仍存在 active `landmark` facet。
- `landmark` 分类数量，以及可映射到 `building` / `landscape` / unresolved 的数量。
- 核心分类缺失情况：
  - 缺 `gallery_series`
  - 缺 `campus`
  - 缺 `photo_type`
  - 摄影大赛缺 `gallery_year`
  - 投稿作品缺 `source_type`
- 自由标签中与标准 taxonomy 重复的 tag。
- 当前 Milvus 向量集合数量、来源和更新时间。

输出物：

- `taxonomy_audit_YYYYMMDD.md`
- `landmark_migration_dry_run_YYYYMMDD.txt`
- `free_tag_quality_YYYYMMDD.md`
- `search_index_status_YYYYMMDD.md`

### 阶段 1：后端分类契约统一

目标：统一后端所有正式分类写入口。

需要收口：

- 标注审核通过。
- 后台照片分类编辑。
- 摄影大赛导入。
- 普通 JSON 导入。
- AI apply 兼容层。
- 迁移脚本。

原则：

- 正式分类写入 `photo_classifications`。
- 旧 `photos.season/category/campus` 只作为兼容字段同步，不作为新功能主依据。
- `landmark` 只保留 legacy 查询兼容，不再作为新数据写入目标。

### 阶段 2：历史数据迁移

目标：能确定的先迁移，不能确定的留给人工标注。

迁移策略：

- 旧 `landmark`：
  - 楼宇类迁移到 `building`
  - 柳湖、玉屏山、校名石等迁移到 `landscape`
  - 校区类节点跳过，不迁移为楼宇
  - “其它”跳过
  - 无法判断进入 unresolved
- 旧 `category/photo_type`：
  - `风光类`、`Landscape` 等映射到 `校园风光`
  - `纪实类`、`Documentary`、`Activity` 等映射到 `人文纪实`
  - 不能确定的留空
- 旧自由标签：
  - 明确重复标准分类的，可保留为自由标签但不作为标准筛选依据；是否清理需要另行决策
  - 噪声 tag、重复 tag 可通过质量脚本报告后再处理

### 阶段 3：标注工作台适配最终 taxonomy

目标：让人工补齐高效、清晰、低负担。

核心要求：

- 必填：
  - 来源/专区逻辑
  - 校区
  - 题材
- 可选：
  - 楼宇
  - 设施
  - 景观
  - 季节
  - 自然现象
  - 表现手法
  - 动物
  - 植物
  - 纪实主题
- 自由标签区保留，并明确为“补充说明/可搜索 tag”。
- 已有分类和自由标签预填，标注员主要做确认和修正。

### 阶段 4：搜索索引重建

目标：让搜索同时利用标准分类和自由标签，降低对单一 tag 质量的依赖。

建议：

- 先保留现有搜索接口。
- 增加索引构建脚本的 dry-run/report 模式。
- 重建 Milvus 时使用组合搜索文档，而不是只向量化自由标签。
- 支持全量重建和按照片增量重建。
- 迁移期间前端仍可走 PostgreSQL taxonomy 精确筛选，避免向量索引重建造成不可用。

### 阶段 5：AI 兼容预留

目标：本轮不做 AI 自动打标，但避免未来返工。

建议保留：

- AI analysis task 表和 apply 流程。
- AI 结果 JSON 字段。
- 审核后写入 taxonomy 的路径。

未来需要调整：

- AI prompt 输出新 taxonomy key：
  - `building`
  - `facility`
  - `landscape`
  - `natural_phenomenon`
  - `technique`
  - `animal`
  - `plant`
  - `season`
  - `documentary_topic`
- 不再要求 AI 输出 `landmark`。
- AI 只推荐，不直接覆盖正式数据。

## 需要进一步决策的问题

1. 是否要清理已经重复标准分类的自由标签，例如“昌平校区”“校园风光”“春季”。
2. `is_selectable=false` 的父级分组是否需要更细的管理员权限和变更审计。
3. 旧 `photos.season/category/campus` 字段长期是否保留为缓存，还是未来完全废弃。
4. 自由标签是否需要管理员归并流程，把高频 tag 沉淀为 alias 或标准节点候选。
5. 搜索排序中，标准 taxonomy 命中、自由标签命中、描述命中、向量相似度各自权重如何设定。

## 初步验收标准

- `/api/v1/taxonomy/public` 不再暴露 active `landmark`。
- `building` 中不包含 `朝阳校区 / 昌平校区 / 海淀校区 / 其它`。
- 核心分类缺失照片可以被后台任务识别并分派。
- Gallery 标准筛选读取 taxonomy，自由标签筛选读取 `tags`。
- 详情页地点只显示校区，楼宇和景观独立显示。
- 标注工作台提交不要求楼宇，但要求来源/校区/题材。
- 旧 `landmark=图书馆` 查询仍能兼容到 `building=图书馆`。
- 自由标签重建后，向量索引可以全量重建并生成报告。
- 迁移脚本默认 dry-run，不带显式 apply 不写生产数据。

## 审计与部署安全

### 只读审计

新增审计脚本：

```bash
cd backend
.venv/bin/python scripts/audit_taxonomy_2026.py
```

默认行为：

- 只读查询当前数据库，不调用 taxonomy seed，不写入 `taxonomy_facets` / `taxonomy_nodes` / `photo_classifications`。
- PostgreSQL 下会设置当前事务为 read-only。
- 默认排除 `status=deleted` 的照片；如需包含删除态照片，使用 `--include-deleted`。
- 如需保存报告，使用 `--output taxonomy_audit_YYYYMMDD.md`。

报告覆盖：

- 核心分类缺失：`gallery_series`、`campus`、`photo_type`，以及摄影大赛缺 `gallery_year`、投稿作品缺 `source_type`。
- legacy 字段分布：`photos.season`、`photos.category`、`photos.campus`。
- legacy `landmark` 分布及可映射到 `building` / `landscape` / unresolved 的数量。
- 不可映射 legacy 项。
- 自由标签与 taxonomy node / alias 的重名项。
- 单选 facet 多值冲突。
- `Portrait` / `人像` 保留项。

### 部署 taxonomy 迁移开关

`deploy/deploy.sh` 和 `deploy/deploy-from-local.sh` 不再默认执行 `scripts/migrate_taxonomy_2026.py --apply`。

默认部署行为：

```bash
bash deploy/deploy.sh backend
bash deploy/deploy-from-local.sh backend
```

上述命令会跳过 taxonomy 迁移。

如需在部署中只跑 dry-run：

```bash
bash deploy/deploy.sh backend --taxonomy-dry-run
bash deploy/deploy-from-local.sh backend --taxonomy-dry-run
```

如需正式 apply，必须显式传入 apply 和确认参数：

```bash
bash deploy/deploy.sh backend --taxonomy-apply --confirm-taxonomy-apply
bash deploy/deploy-from-local.sh backend --taxonomy-apply --confirm-taxonomy-apply
```

等价环境变量：

```bash
TAXONOMY_MIGRATION_MODE=apply TAXONOMY_APPLY_CONFIRM=APPLY_TAXONOMY_2026 bash deploy/deploy.sh backend
```

生产执行顺序必须是：先跑 `audit_taxonomy_2026.py`，审查报告和 unresolved 列表，再单独决定是否 apply。

## 推荐下一步

在正式编码前，先执行阶段 0 的生产只读审计。审计完成后，根据真实 unresolved 数量决定：

- 先做最小迁移，保证线上筛选和展示稳定。
- 还是同步推进搜索索引重建。
- 或者先把标注任务分派给人工，等核心缺失补齐后再重建向量索引。
