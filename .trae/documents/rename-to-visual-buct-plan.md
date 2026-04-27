# 恢复筛选功能修复计划

## 背景

GalleryView 的筛选区域目前使用 `visibleFacetKeys` 计算属性，该属性**只有后端 taxonomy 分类表有数据时才显示**。由于数据库中 taxonomy 数据为空，所有筛选组（季节、校区、照片类型等）默认隐藏——这就是"完全失去了筛选功能"的原因。

实际上，**前 3 个筛选字段（season/campus/photo\_type）是** **`Photo`** **模型的直接数据库列**，不需要 taxonomy 分类系统也能工作。本计划将恢复筛选功能并改进实现。

***

## 根因分析

### 为什么筛选不可见？

GalleryView\.vue 第 199-202 行：

```typescript
const visibleFacetKeys = computed(() => {
  const keys = Object.keys(facetLabelMap)
  return keys.filter((key) => facetOptions(key).length > 0)
})
```

`facetLabelMap` 定义了 7 个筛选组：`season`、`campus`、`building`、`gallery_series`、`gallery_year`、`photo_type`、`tag`。

`facetOptions(key)` 从 `getPublicTaxonomy()` API 返回的数据中提取节点选项。如果 API 返回空数组（或返回的分类中没有节点），所有筛选组不显示。

### 数据列 vs 分类系统

| 筛选字段             | 数据来源                   | 依赖 taxonomy 数据？ |
| ---------------- | ---------------------- | --------------- |
| `season`         | `Photo.season` 直接列     | ❌ 不需要           |
| `campus`         | `Photo.campus` 直接列     | ❌ 不需要           |
| `photo_type`     | Taxonomy 分类关联表         | ✅ 需要            |
| `building`       | Taxonomy 分类关联表         | ✅ 需要            |
| `gallery_series` | Taxonomy 分类关联表         | ✅ 需要            |
| `gallery_year`   | Taxonomy 分类关联表         | ✅ 需要            |
| `tag`            | `Tag.name` 标签表（独立 API） | ❌ 不需要           |

***

## 修复方案

### 核心思路：硬编码常用筛选选项 + 动态加载分类选项

对于 `season`、`campus`、`photo_type` 三个字段，由于它们是常见的固定分类，且后端 CRUD 直接支持，**不需要等待 taxonomy API 返回数据**，直接硬编码常用选项。

对于 `building`、`gallery_series`、`gallery_year` 等走 taxonomy 关联表的字段，继续从 `getPublicTaxonomy()` 动态加载。

### 方案 A（推荐）：混合模式 — 静态选项 + 动态分类

将筛选组分为两类：

**第一类：固定选项（静态硬编码，always show）**

* `season`：春、夏、秋、冬

* `campus`：东校区、西校区、北校区、昌平校区（按实际校区名）

* `photo_type`：校园风光、建筑、人物、活动、实验室、运动（按实际类型）

**第二类：动态分类（从 taxonomy API 加载，有数据才显示）**

* `building`：楼宇

* `gallery_series`：专题（如摄影大赛）

* `gallery_year`：年份

***

### 具体实施步骤

### Step 1：修改 GalleryView\.vue — 加入静态选项

将 `facetOptions()` 函数改为混合模式：

```typescript
function facetOptions(key: string): SelectOption[] {
  // 静态选项（直接硬编码，不需要 taxonomy 数据）
  if (key === 'season') {
    return [
      { label: '春季', value: 'spring' },
      { label: '夏季', value: 'summer' },
      { label: '秋季', value: 'autumn' },
      { label: '冬季', value: 'winter' },
    ]
  }
  if (key === 'campus') {
    return [
      { label: '东校区', value: 'east' },
      { label: '西校区', value: 'west' },
      { label: '北校区', value: 'north' },
      { label: '昌平校区', value: 'changping' },
    ]
  }
  if (key === 'photo_type') {
    return [
      { label: '校园风光', value: 'campus_scenery' },
      { label: '建筑', value: 'architecture' },
      { label: '人物', value: 'people' },
      { label: '活动', value: 'event' },
      { label: '实验室', value: 'laboratory' },
      { label: '运动', value: 'sports' },
    ]
  }

  // 动态分类（从 taxonomy API 加载）
  const facet = facetMap.value[key]
  if (!facet) return []
  const flatten = (nodes: TaxonomyFacet['nodes']): SelectOption[] =>
    nodes.flatMap((node) => [
      { label: node.name, value: node.name },
      ...flatten(node.children || []),
    ])
  return flatten(facet.nodes || [])
}
```

### Step 2：修改 visibleFacetKeys — 始终显示静态字段

```typescript
const staticFacetKeys = ['season', 'campus', 'photo_type']

const visibleFacetKeys = computed(() => {
  // 始终显示静态筛选
  const visible = [...staticFacetKeys]
  // 动态筛选有数据才显示
  const dynamicKeys = ['building', 'gallery_series', 'gallery_year', 'tag']
  dynamicKeys.forEach((key) => {
    if (facetOptions(key).length > 0) {
      visible.push(key)
    }
  })
  return visible
})
```

### Step 3：确认后端支持

不需要改后端。`season`、`campus`、`photo_type` 在后端 `list_public_photos` 参数和 CRUD `get_photos` 中均已支持。

后端 CRUD 处理逻辑：

* `season`：`Photo.season == value`

* `campus`：`Photo.campus == value`

* `photo_type`：通过 `PhotoClassification` 关联 `TaxonomyNode.name` 匹配

### Step 4：确认前端 API 传参

`store.buildQueryParams` 已有对 `season`、`campus`、`photo_type` 的参数传递。GalleryView\.vue 的 `buildQuery()` 函数也把这几个字段拼入 URL 查询参数。不需要改 store 和 API。

### Step 5：确保筛选点击后刷新数据

现有 `toggleFilter(key, value)` 函数正确：

1. 切换筛选值
2. `setFilters` 重置到第一页
3. `syncQueryAndFetch()` 更新 URL + 调用 API 获取数据

不需要改。

***

## 文件修改清单

### 修改文件

* `frontend/src/views/GalleryView.vue` — 修改 `facetOptions()` 和 `visibleFacetKeys`

### 无需修改的文件

* `frontend/src/stores/photo.ts` — 已有完整筛选字段支持

* `frontend/src/types/photo.ts` — 已有完整筛选类型定义

* `frontend/src/api/photo.ts` — 已有完整 API 参数

* `backend/app/api/v1/endpoints/photos.py` — 已有完整后端参数支持

* `backend/app/crud/photo.py` — 已有完整 CRUD 逻辑

***

## 验收标准

1. 打开 GalleryView，**筛选区域始终可见**（不依赖 taxonomy 数据库数据）
2. 点击"季节"的 pills（春/夏/秋/冬），结果正确过滤
3. 点击"校区"的 pills（东校区/西校区等），结果正确过滤
4. 如果后端 taxonomy 有数据，"楼宇/专题/年份"动态显示
5. 已选筛选条件可清除，支持多选筛选组合
6. 筛选后 URL 同步更新（可分享/可刷新）

