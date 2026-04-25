<template>
  <div class="gallery-view">
    <!-- 筛选栏 -->
    <div class="gallery-toolbar">
      <div class="toolbar-main">
        <div class="result-count">
          <span v-if="photoStore.filters.search" class="search-term">
            "{{ photoStore.filters.search }}"
          </span>
          <span class="count-text">共 <strong>{{ photoStore.total.toLocaleString() }}</strong> 张</span>
        </div>

        <div class="toolbar-actions">
          <n-button-group size="small">
            <n-button
              :type="viewMode === 'large' ? 'primary' : 'default'"
              ghost
              @click="viewMode = 'large'"
            >
              <template #icon>
                <n-icon :component="GridOutline" />
              </template>
            </n-button>
            <n-button
              :type="viewMode === 'small' ? 'primary' : 'default'"
              ghost
              @click="viewMode = 'small'"
            >
              <template #icon>
                <n-icon :component="AppsOutline" />
              </template>
            </n-button>
          </n-button-group>
          <n-select
            v-model:value="photoStore.filters.sortBy"
            size="small"
            style="width: 110px;"
            :options="sortOptions"
            @update:value="handleSortChange"
          />
        </div>
      </div>

      <!-- 筛选标签 pills -->
      <div v-if="hasAnyFacets || activeFilters.length" class="filter-area">
        <n-spin :show="taxonomyLoading" size="small">
          <div class="filter-pills">
            <!-- 动态渲染有数据的筛选组 -->
            <div
              v-for="facetKey in visibleFacetKeys"
              :key="facetKey"
              class="filter-group"
            >
              <span class="filter-label">{{ facetLabelMap[facetKey] }}</span>
              <div class="pills-row">
                <span
                  v-for="opt in facetOptions(facetKey)"
                  :key="opt.value"
                  class="tag-pill"
                  :class="{ active: photoStore.filters[facetKey] === opt.value }"
                  @click="toggleFilter(facetKey, opt.value as string)"
                >
                  {{ opt.label }}
                </span>
              </div>
            </div>

            <!-- 已选筛选项 -->
            <div v-if="activeFilters.length" class="filter-group">
              <span class="filter-label">已选</span>
              <div class="pills-row">
                <span
                  v-for="filter in activeFilters"
                  :key="filter.key"
                  class="tag-pill active"
                  @click="removeFilter(filter.key)"
                >
                  {{ filter.label }}: {{ filter.value }}
                  <n-icon :component="CloseOutline" size="12" style="margin-left: 4px;" />
                </span>
                <n-button text size="tiny" type="error" @click="handleClearFilters">
                  清空全部
                </n-button>
              </div>
            </div>
          </div>
        </n-spin>
      </div>

      <!-- 无分类数据提示 -->
      <div v-else-if="!taxonomyLoading && !taxonomyError" class="filter-empty-hint">
        <n-text depth="3" style="font-size: 13px;">
          暂无分类数据，筛选功能将在管理员添加分类后自动显示
        </n-text>
      </div>
    </div>

    <!-- 图片网格 -->
    <div class="gallery-grid">
      <n-spin :show="photoStore.loading">
        <div v-if="photoStore.photos.length === 0 && !photoStore.loading" class="gallery-empty">
          <n-empty description="暂无符合条件的照片">
            <template #extra>
              <n-button @click="handleClearFilters">清空筛选</n-button>
            </template>
          </n-empty>
        </div>

        <UniformGrid
          v-else
          :items="photoStore.photos"
          :columns="gridColumns"
          :gap="gridGap"
          aspect-ratio="4 / 3"
          @item-click="handlePhotoClick"
        >
          <template #default="{ item: photo }">
            <img
              :src="getImageUrl(photo)"
              :alt="photo.filename"
              loading="lazy"
              @error="(e) => handleImageError(e, photo)"
            />
            <div class="photo-overlay">
              <div class="photo-overlay-content">
                <div class="photo-title">{{ photo.filename }}</div>
                <div class="photo-meta">
                  <span v-if="photo.classifications?.season" class="meta-tag">
                    {{ photo.classifications.season.node_name }}
                  </span>
                  <span v-if="photo.classifications?.campus" class="meta-tag">
                    {{ photo.classifications.campus.node_name }}
                  </span>
                </div>
              </div>
            </div>
          </template>
        </UniformGrid>
      </n-spin>
    </div>

    <!-- 分页 -->
    <div v-if="photoStore.total > photoStore.pageSize" class="gallery-pagination">
      <n-pagination
        v-model:page="photoStore.currentPage"
        :item-count="photoStore.total"
        :page-size="photoStore.pageSize"
        show-size-picker
        :page-sizes="[20, 50, 100]"
        @update:page="handlePageChange"
        @update:page-size="handlePageSizeChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { CloseOutline, GridOutline, AppsOutline } from '@vicons/ionicons5'
import type { SelectOption } from 'naive-ui'
import UniformGrid from '../components/common/UniformGrid.vue'
import { usePhotoStore } from '../stores/photo'
import { getPublicTaxonomy, type TaxonomyFacet } from '../api/taxonomy'
import type { Photo, PhotoFilters } from '../types/photo'
import { getPhotoUrl } from '../utils/format'

const router = useRouter()
const route = useRoute()
const photoStore = usePhotoStore()

const taxonomyFacets = ref<TaxonomyFacet[]>([])
const taxonomyLoading = ref(false)
const taxonomyError = ref(false)
const syncingRoute = ref(false)
const viewMode = ref<'large' | 'small'>('large')

const sortOptions = [
  { label: '最新上传', value: 'created_at' },
  { label: '最热门', value: 'views' },
  { label: '最近发布', value: 'published_at' },
]

const facetLabelMap: Record<string, string> = {
  season: '季节',
  campus: '校区',
  building: '楼宇',
  gallery_series: '专题',
  gallery_year: '年份',
  photo_type: '照片类型',
  tag: '标签',
}

const facetMap = computed(() =>
  Object.fromEntries(taxonomyFacets.value.map((facet) => [facet.key, facet])),
)

// 静态筛选字段（始终显示，不需要 taxonomy 数据）
const staticFacetKeys = ['season', 'campus', 'photo_type']
// 动态筛选字段（从 taxonomy API 加载，有数据才显示）
const dynamicFacetKeys = ['building', 'gallery_series', 'gallery_year', 'tag']

const visibleFacetKeys = computed(() => {
  const visible = [...staticFacetKeys]
  dynamicFacetKeys.forEach((key) => {
    if (facetOptions(key).length > 0) {
      visible.push(key)
    }
  })
  return visible
})

const hasAnyFacets = computed(() => visibleFacetKeys.value.length > 0)

const activeFilters = computed(() => {
  const filters = photoStore.filters
  const chips: Array<{ key: keyof PhotoFilters; label: string; value: string }> = []
  ;(['season', 'campus', 'building', 'gallery_series', 'gallery_year', 'photo_type', 'tag'] as const).forEach((key) => {
    const value = filters[key]
    if (value) {
      chips.push({ key, label: facetLabelMap[key], value })
    }
  })
  return chips
})

const gridColumns = computed(() => viewMode.value === 'large' ? 4 : 6)
const gridGap = computed(() => viewMode.value === 'large' ? 16 : 10)

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

function getImageUrl(photo: Photo) {
  return getPhotoUrl(photo.id, 'thumbnail')
}

function handleImageError(event: Event, photo: Photo) {
  const img = event.target as HTMLImageElement
  if (img.getAttribute('data-tried') === 'true') {
    img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect fill="%23f0f0f0" width="200" height="200"/%3E%3Ctext fill="%23999" x="50%25" y="50%25" text-anchor="middle" dy=".3em"%3E图片加载失败%3C/text%3E%3C/svg%3E'
    return
  }
  img.setAttribute('data-tried', 'true')
  img.src = getPhotoUrl(photo.id, 'thumbnail')
}

function buildQuery() {
  const query: Record<string, string> = {}
  const filters = photoStore.filters
  ;(['season', 'campus', 'building', 'gallery_series', 'gallery_year', 'photo_type', 'tag'] as const).forEach((key) => {
    const value = filters[key]
    if (value) query[key] = value
  })
  if (filters.search) query.search = filters.search
  if (filters.sortBy) query.sort_by = filters.sortBy
  if (photoStore.currentPage > 1) query.page = String(photoStore.currentPage)
  if (photoStore.pageSize !== 20) query.page_size = String(photoStore.pageSize)
  return query
}

async function syncQueryAndFetch() {
  const nextQuery = buildQuery()
  syncingRoute.value = true
  await router.replace({ path: '/gallery', query: nextQuery })
  await nextTick()
  await photoStore.fetchPublicPhotos()
  syncingRoute.value = false
}

function applyRouteQuery() {
  syncingRoute.value = true
  const query = route.query
  photoStore.filters.season = typeof query.season === 'string' ? query.season : null
  photoStore.filters.campus = typeof query.campus === 'string' ? query.campus : null
  photoStore.filters.building = typeof query.building === 'string' ? query.building : null
  photoStore.filters.gallery_series = typeof query.gallery_series === 'string' ? query.gallery_series : null
  photoStore.filters.gallery_year = typeof query.gallery_year === 'string' ? query.gallery_year : null
  photoStore.filters.photo_type = typeof query.photo_type === 'string' ? query.photo_type : null
  photoStore.filters.tag = typeof query.tag === 'string' ? query.tag : null
  photoStore.filters.search = typeof query.search === 'string' ? query.search : ''
  photoStore.filters.sortBy = typeof query.sort_by === 'string' ? query.sort_by : 'created_at'
  photoStore.currentPage = query.page ? Number(query.page) || 1 : 1
  photoStore.pageSize = query.page_size ? Number(query.page_size) || 20 : 20
  syncingRoute.value = false
}

async function toggleFilter(key: keyof PhotoFilters, value: string) {
  const current = photoStore.filters[key]
  photoStore.setFilters({ [key]: current === value ? null : value } as Partial<PhotoFilters>)
  await syncQueryAndFetch()
}

async function removeFilter(key: keyof PhotoFilters) {
  photoStore.setFilters({ [key]: null } as Partial<PhotoFilters>)
  await syncQueryAndFetch()
}

async function handleSortChange() {
  await syncQueryAndFetch()
}

async function handlePageChange(page: number) {
  photoStore.setPage(page)
  await syncQueryAndFetch()
}

async function handlePageSizeChange(pageSize: number) {
  photoStore.pageSize = pageSize
  photoStore.setPage(1)
  await syncQueryAndFetch()
}

async function handleClearFilters() {
  photoStore.clearFilters()
  await syncQueryAndFetch()
}

function handlePhotoClick(photo: Photo) {
  router.push(`/photo/${photo.id}`)
}

async function loadTaxonomy() {
  taxonomyLoading.value = true
  taxonomyError.value = false
  try {
    taxonomyFacets.value = await getPublicTaxonomy()
  } catch (error) {
    console.error('加载分类失败:', error)
    taxonomyError.value = true
  } finally {
    taxonomyLoading.value = false
  }
}

watch(
  () => route.query,
  async () => {
    if (syncingRoute.value) return
    applyRouteQuery()
    await photoStore.fetchPublicPhotos()
  },
  { deep: true },
)

onMounted(async () => {
  applyRouteQuery()
  await Promise.all([photoStore.fetchPublicPhotos(), loadTaxonomy()])
})
</script>

<style scoped>
.gallery-view {
  padding: 72px 24px 48px;
  max-width: 1440px;
  margin: 0 auto;
  min-height: 100vh;
}

/* 工具栏 */
.gallery-toolbar {
  margin-bottom: 20px;
}

.toolbar-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.result-count {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #666;
}

.search-term {
  font-weight: 600;
  color: #333;
}

.count-text strong {
  color: #e60012;
  font-weight: 600;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 筛选区域 */
.filter-area {
  min-height: 36px;
}

.filter-pills {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-group {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.filter-label {
  font-size: 13px;
  color: #999;
  white-space: nowrap;
  padding-top: 4px;
  min-width: 48px;
}

.pills-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.filter-empty-hint {
  padding: 8px 0;
}

/* 图片网格 */
.gallery-grid {
  min-height: 400px;
}

.gallery-empty {
  padding: 120px 0;
}

/* hover 遮罩 - 用于 UniformGrid 内部 */
:deep(.grid-cell) {
  position: relative;
}

:deep(.grid-cell .photo-overlay) {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0);
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: 12px;
  transition: background 0.3s ease;
  pointer-events: none;
}

:deep(.grid-cell:hover .photo-overlay) {
  background: rgba(0, 0, 0, 0.4);
}

:deep(.grid-cell .photo-overlay-content) {
  opacity: 0;
  transform: translateY(6px);
  transition: all 0.3s ease;
}

:deep(.grid-cell:hover .photo-overlay-content) {
  opacity: 1;
  transform: translateY(0);
}

:deep(.grid-cell .photo-title) {
  font-size: 13px;
  color: white;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:deep(.grid-cell .photo-meta) {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 6px;
}

:deep(.grid-cell .meta-tag) {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.85);
  background: rgba(255, 255, 255, 0.15);
  padding: 2px 8px;
  border-radius: 10px;
  backdrop-filter: blur(4px);
}

/* 分页 */
.gallery-pagination {
  margin-top: 40px;
  display: flex;
  justify-content: center;
}

/* 响应式 */
@media (max-width: 768px) {
  .gallery-view {
    padding: 64px 12px 32px;
  }

  .toolbar-main {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .filter-group {
    flex-direction: column;
    gap: 6px;
  }

  .filter-label {
    padding-top: 0;
  }
}
</style>
