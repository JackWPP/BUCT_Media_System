# VCG 风格重构 Phase2 修复计划

## 背景

Phase1 已完成首页、图库页、详情页的基础重构框架，但存在三个核心问题需要一并修复：
1. **筛选标签无数据**：GalleryView 只显示"季节/校区/照片类型/专题"标题，下方没有实际可点击的筛选选项 pills
2. **缓存冲突**：HomeView（精选图片）和 GalleryView（搜索结果）共用 `photoStore.photos`，数据互相污染
3. **对标 VCG 不够深入**：交互细节（首页滚动动效、搜索过渡、筛选面板、图片 hover、详情页沉浸感等）与视觉中国差距明显

---

## 一、问题定位与根因分析

### 1.1 筛选标签无数据

**根因**：GalleryView 的 `facetOptions(key)` 依赖 `getPublicTaxonomy()` API 返回的数据填充 `taxonomyFacets` 数组。后端 `taxonomy.py` 的 `list_public_taxonomy` 虽然会调用 `ensure_default_taxonomy`，但如果数据库中 taxonomy 表为空，或 API 返回的数据结构（`TaxonomyFacetResponse`）与前端期望的 `{ key, nodes[] }` 不匹配，就会返回空数组。另外前端 `facetOptions` 使用递归 `flatten` 扁平化 node tree，但如果后端返回的 facet 数据缺少 `nodes` 字段或 `nodes` 为空，也会导致 pills 无选项。

**截图现象**：只显示 "季节" "校区" "照片类型" "专题" 四个文字标签，下方没有任何可点击的 pills。

### 1.2 缓存冲突

**根因**：
- HomeView 的 `loadPhotos()` 调用 `photoStore.fetchPublicPhotos()`，将结果写入 `photoStore.photos`
- GalleryView 的搜索也调用 `photoStore.fetchPublicPhotos()`，覆盖 `photoStore.photos`
- 两者共享 `photoStore.photos`、`total`、`currentPage`、`pageSize`、`loading` 等全部状态
- 详情页的 `hasPrev`/`hasNext` 依赖 `photoStore.photos` 数组，如果 Gallery 加载了不同条件下的结果，切换会错乱

**影响场景**：用户先在首页看到12张精选图，再点进 Gallery 搜索"春天"，此时首页的精选图数据被覆盖。如果用户从 Gallery 点进某张图详情页想切换前后页，只有 Gallery 当前页的结果在内存中，首页的精选图已经丢失。

### 1.3 对标 VCG 不够深入

从用户提供的 VCG 截图和之前的观察，VCG 的核心交互细节包括：

**首页（vcg.com/）**：
- Hero 区域背景是柔和的彩色渐变圆形（已实现）
- 搜索框居中，左侧有"图片"下拉选择（已实现）
- **搜索框右侧有 📷 相机图标按钮 + 红色搜索按钮 🔍**（已实现）
- **搜索框下方有"图片热搜推荐"横向排列的热门标签**，带分隔线（已实现）
- **Hero 下方有分类 Tab 导航**：图片、设计、视频、音频、字体（用户说先不用，因只有图片）
- **滚动时 Hero 渐隐，顶部 Header 从透明变为白色并缩小搜索框**（未实现）
- **首页下方内容区有多个区块**：精选专题、热门分类、最新上传等（未实现）

**搜索结果页（vcg.com/search?phrase=xxx）**：
- **顶部有横向筛选 Tab 栏**：全部、照片、插画、矢量、国际 等（类似 pills，但更像 tab）
- **右侧有视图切换按钮**：大图/小图/列表（未实现）
- **筛选条件是可展开/收起的面板**，而非一直显示所有 pills（VCG 的筛选更加紧凑）
- **图片网格是等高分栏（uniform grid）**，不是瀑布流（masonry）。每行高度一致，图片被裁剪填充
- **Hover 效果**：图片微缩放 + 半透明黑色遮罩 + 标题和标签信息浮现（已实现基础，但不够精致）
- **点击图片直接进入详情页**（已实现）

**图片详情页（单张图片页面）**：
- **大图几乎占满整个左侧区域**，深色背景 `#0f0f0f` 或更暗
- **顶部有悬浮工具栏**：返回/关闭按钮 + 图片计数 + 操作按钮（已实现）
- **左右箭头悬浮在图片两侧**，hover 时变亮（已实现）
- **底部有操作按钮栏**：收藏、下载、分享等（已实现）
- **右侧信息面板**：摄影师头像 + 名称 + 关注按钮（已实现）
- **元数据列表**：编号、尺寸、大小、格式、上传时间等（已实现）
- **下方关键词区域**：一行行小标签，点击可搜索（已实现）
- **再下方是相关推荐图片**：横向或网格排列（已实现）
- **VCG 还有一个特点**：大图支持缩放查看，鼠标滚轮可以放大缩小图片（未实现）

---

## 二、修复方案

### Phase 2.1：修复筛选标签无数据

**目标**：GalleryView 的筛选区域要么正确显示可点击的 pills，要么在数据为空时给出友好提示。

**步骤**：

1. **前端增加数据加载状态**
   - GalleryView 增加 `taxonomyLoading` 状态
   - `loadTaxonomy()` 调用时显示 loading，完成后检查返回数据

2. **处理空数据场景**
   - 当 `facetOptions('season')` 等返回空数组时，隐藏该筛选组（不显示"季节"标题）
   - 或者显示占位提示"暂无分类数据，请在管理后台添加"

3. **确保前后端数据格式匹配**
   - 检查后端 `TaxonomyFacetResponse` schema 的 `key` 字段是否为 `"season"`、`"campus"` 等
   - 检查 `nodes` 字段是否为嵌套树形结构，前端 `flatten` 是否能正确解析
   - 增加数据格式容错：如果后端返回的数据没有 `nodes` 但有其他字段，需要兼容处理

4. **增加错误处理**
   - `loadTaxonomy()` 增加 try-catch，API 失败时显示错误提示

### Phase 2.2：分离 HomeView 和 GalleryView 数据状态

**目标**：HomeView 和 GalleryView 使用完全独立的数据状态，互不干扰。

**方案 A（推荐）：HomeView 不使用 Store，直接调用 API**

1. **修改 HomeView 的 `loadPhotos()`**
   - 不再调用 `photoStore.fetchPublicPhotos()`
   - 直接使用 `import { getPublicPhotos } from '../api/photo'` 调用 API
   - 结果存储在 HomeView 本地 `ref<Photo[]>([])` 中

2. **修改 HomeView 的 `loadHotTags()`**
   - 同样改为直接调用 API，不经过 store

3. **GalleryView 继续使用 `photoStore`**
   - 保持不变，但确保 `photoStore` 只被 GalleryView 和 PhotoDetailView 使用

4. **修改 PhotoDetailView**
   - `relatedPhotos` 从 `photoStore.photos` 获取的逻辑保持不变
   - 但 `preloadAdjacent` 需要更加健壮：如果 `photoStore.photos` 为空，自动调用 API 加载当前页数据

**方案 B：创建独立 Store（备选）**

如果未来有更多页面需要独立数据，可以创建 `useHomeStore`，但当前情况方案 A 更简洁。

### Phase 2.3：深入研究并对标 VCG 交互细节

基于 VCG 截图和常见图库设计模式，逐项改进：

#### A. 首页交互增强

1. **Header 滚动动效**
   - 在 HomeView 中监听 `window.scrollY`
   - 滚动超过 80px 时：Hero 区域渐隐（opacity 过渡），顶部 Header 变为白色背景 + 缩小阴影
   - 滚动回到顶部时：Header 恢复透明态
   - 这是一个纯前端视觉效果，不需要后端改动

2. **搜索框聚焦动效**
   - 点击搜索框时，搜索框宽度微扩，阴影加深
   - 输入时 placeholder 平滑消失

3. **首页下方内容区块扩展**
   - "精选图片"区块下方增加 "热门分类" 区块
   - 展示几个大的分类入口（如春天、校园、建筑等），每个分类用一张代表性大图做卡片
   - 用户点击后跳转到 Gallery 并自动应用该分类筛选

#### B. 搜索结果页改进

1. **筛选面板改为可展开/收起**
   - 当前 GalleryView 的筛选 pills 全部平铺显示，占用大量垂直空间
   - 改为 VCG 风格：默认只显示第一行常用筛选（如季节），点击"更多筛选"展开其余条件
   - 或者改为横向 Tab 栏 + 下拉筛选组合的方式

2. **图片网格改为等高分栏（Uniform Grid）**
   - 当前使用 MasonryLayout（瀑布流），图片高度不一
   - VCG 搜索结果页使用的是等高分栏网格，每行高度一致，图片 `object-fit: cover` 填充
   - 这样可以减少布局抖动，视觉更整齐
   - 保留 MasonryLayout 组件，GalleryView 改用新的 `UniformGrid` 组件

3. **Hover 效果优化**
   - 当前 hover 时只有底部浮现信息
   - VCG 的 hover 是整图微缩放 + 全局半透明遮罩 + 信息浮现
   - 增加图片加载时的骨架屏 shimmer 效果

4. **视图切换**
   - 增加大图/小图/列表视图切换按钮
   - 大图：4列网格，图片更大
   - 小图：5-6列网格，紧凑
   - 列表：横向排列，带更多信息
   - 先实现大图/小图两种即可

5. **无限滚动（可选）**
   - 当前使用分页器，VCG 是滚动自动加载更多
   - 可以考虑增加无限滚动模式，但保留分页作为备选
   - 考虑到后端压力，此功能标记为可选，低优先级

#### C. 图片详情页增强

1. **图片缩放查看**
   - 点击图片进入缩放模式
   - 鼠标滚轮放大/缩小
   - 拖拽平移大图
   - ESC 退出缩放
   - 这是 VCG 详情页的核心交互，能大幅提升体验

2. **信息面板优化**
   - 当前信息面板略显冗长
   - 参考 VCG：将元数据（编号、尺寸等）做成更紧凑的表格形式
   - 摄影师信息区域更突出

3. **键盘快捷键完善**
   - 已支持 ← → ESC
   - 增加 F 键收藏、D 键下载

4. **分享功能增强**
   - 当前只支持复制链接
   - 增加社交分享按钮（微信、微博等）
   - 低优先级

#### D. 全局动画与过渡

1. **页面切换过渡**
   - 首页 → Gallery：搜索框从 Hero 中心平滑移动到 Header
   - Gallery → 详情页：点击图片时，图片从网格位置放大到详情页位置（FLIP 动画）
   - 详情页 → Gallery：反向缩小
   - 这些是比较高级的动画，标记为可选

2. **图片加载优化**
   - 缩略图先显示模糊占位，高清图加载完成后清晰化
   - 使用 `loading="lazy"` 已在实现中

---

## 三、实施优先级

| 优先级 | 任务 | 说明 |
|--------|------|------|
| P0（最高） | 修复筛选标签无数据 | 影响 GalleryView 核心功能可用性 |
| P0 | 分离 Home/Gallery 数据状态 | 影响数据一致性和详情页切换体验 |
| P1 | 搜索结果页改为等高分栏网格 | 更对齐 VCG，视觉更整齐 |
| P1 | 筛选面板可展开/收起 | 减少页面垂直占用，更像 VCG |
| P1 | 首页 Header 滚动动效 | 提升首页沉浸感 |
| P2 | 详情页图片缩放查看 | VCG 核心交互，提升体验 |
| P2 | 视图切换（大图/小图） | 增强搜索页交互 |
| P2 | 首页内容区块扩展 | 更丰富，更像内容平台 |
| P3 | 页面切换 FLIP 动画 | 高级动画，可选 |
| P3 | 无限滚动 | 可选，看后端压力 |

---

## 四、文件修改清单

### 新建文件
- `src/components/common/UniformGrid.vue` — 等高分栏图片网格组件
- `src/composables/useScrollHeader.ts` — Header 滚动动效 composable
- `src/composables/useImageZoom.ts` — 图片缩放查看 composable

### 修改文件
- `src/views/GalleryView.vue` — 修复筛选数据 + 改用等分网格 + 筛选面板可展开收起
- `src/views/HomeView.vue` — 改用直接 API 调用 + 增加滚动动效 + 热门分类区块
- `src/views/PhotoDetailView.vue` — 增加图片缩放查看 + 信息面板优化
- `src/components/layout/PublicHeader.vue` — 配合滚动动效
- `src/stores/photo.ts` — 确保只被 Gallery/Detail 使用（可选，看方案 A 还是 B）

---

## 五、验收标准

1. 打开 GalleryView，筛选区域显示实际的分类选项 pills，点击后能正确过滤图片
2. 从首页点进 Gallery，首页的精选图片数据不影响 Gallery 的搜索结果
3. 从 Gallery 点进详情页，前后切换只基于 Gallery 当前页的结果
4. Gallery 图片网格每行高度一致，类似 VCG 的整齐感
5. 首页滚动时 Header 平滑过渡，有沉浸感
6. 详情页点击图片可缩放查看，滚轮放大缩小，ESC 退出
