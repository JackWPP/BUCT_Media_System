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
          <div class="smart-search-toggle">
            <n-switch
              v-model:value="smartSearchEnabled"
              size="small"
              @update:value="handleSmartToggle"
            />
            <n-text depth="3" class="smart-label" :class="{ 'smart-active': smartSearchEnabled }">
              {{ smartSearchEnabled ? '✨ 智能搜索' : '普通搜索' }}
            </n-text>
          </div>
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

      <!-- 搜索输入框 -->
      <div class="gallery-search-box">
        <n-input
          v-model:value="searchKeyword"
          :placeholder="smartSearchEnabled ? '试试自然语言搜索：秋天的图书馆、春天的樱花...' : '输入关键词搜索照片...'"
          clearable
          class="gallery-search-input"
          :class="{ 'search-interpreting': isInterpreting }"
          @update:value="handleSearchInput"
        >
          <template #prefix>
            <n-icon :component="SearchOutline" />
          </template>
        </n-input>
        <div v-if="isInterpreting" class="interpreting-dots">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
        </div>
      </div>

      <!-- 筛选区域 -->
      <div v-if="hasAnyFacets || activeFilters.length" class="filter-area">
        <!-- 筛选头部：模式切换 + 清空按钮 -->
        <div class="filter-header">
          <n-button-group size="small">
            <n-button
              :type="filterMode === 'pills' ? 'primary' : 'default'"
              ghost
              @click="filterMode = 'pills'"
            >
              <template #icon>
                <n-icon :component="PricetagsOutline" />
              </template>
              标签
            </n-button>
            <n-button
              :type="filterMode === 'compact' ? 'primary' : 'default'"
              ghost
              @click="filterMode = 'compact'"
            >
              <template #icon>
                <n-icon :component="OptionsOutline" />
              </template>
              下拉
            </n-button>
          </n-button-group>
          <n-button
            v-if="activeFilters.length"
            text
            size="tiny"
            type="error"
            @click="handleClearFilters"
          >
            <template #icon>
              <n-icon :component="CloseOutline" />
            </template>
            清空全部
          </n-button>
        </div>

        <n-spin :show="taxonomyLoading" size="small">
          <!-- Pills 模式 -->
          <div v-if="filterMode === 'pills'" class="filter-pills">
            <!-- 动态渲染有数据的筛选组 -->
            <div
              v-for="facetKey in visibleFacetKeys"
              :key="facetKey"
              class="filter-group"
            >
              <span class="filter-label">{{ facetLabelMap[facetKey] }}</span>
              <div class="pills-row">
                <span
                  v-for="opt in getVisibleOptions(facetKey)"
                  :key="opt.value"
                  class="tag-pill"
                  :class="{ active: photoStore.filters[facetKey] === opt.value }"
                  @click="toggleFilter(facetKey, opt.value as string)"
                >
                  {{ opt.label }}
                </span>
                <n-button
                  v-if="shouldShowMore(facetKey)"
                  text
                  size="tiny"
                  type="primary"
                  @click="toggleExpand(facetKey)"
                >
                  {{ expandedGroups[facetKey] ? '收起' : '更多' }}
                </n-button>
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
              </div>
            </div>
          </div>

          <!-- Compact 模式 -->
          <div v-else class="filter-compact">
            <div class="compact-selects">
              <n-select
                v-for="facetKey in visibleFacetKeys"
                :key="facetKey"
                v-model:value="photoStore.filters[facetKey]"
                :placeholder="facetLabelMap[facetKey]"
                clearable
                size="small"
                style="width: 130px;"
                :options="facetOptions(facetKey)"
                @update:value="handleCompactFilterChange(facetKey)"
              />
            </div>
            <!-- 已选筛选项 -->
            <div v-if="activeFilters.length" class="compact-active-filters">
              <n-tag
                v-for="filter in activeFilters"
                :key="filter.key"
                closable
                size="small"
                @close="removeFilter(filter.key)"
              >
                {{ filter.label }}: {{ filter.value }}
              </n-tag>
            </div>
          </div>
        </n-spin>
      </div>

      <!-- 搜索解释结果展示 -->
      <div v-if="currentInterpretation" class="search-interpretation-area">
        <SearchInterpretation
          :interpretation="currentInterpretation"
          @remove-facet="handleRemoveFacet"
          @remove-keyword="handleRemoveKeyword"
          @dismiss="handleDismissInterpretation"
        />
      </div>

    </div>

    <!-- 图片瀑布流 -->
    <div class="gallery-grid">
      <n-spin :show="photoStore.loading">
        <div v-if="photoStore.photos.length === 0 && !photoStore.loading" class="gallery-empty">
          <n-empty description="暂无符合条件的照片">
            <template #extra>
              <n-button @click="handleClearFilters">清空筛选</n-button>
            </template>
          </n-empty>
        </div>

        <MasonryLayout
          v-else
          :items="photoStore.photos"
          :gap="gridGap"
          :columns-config="masonryColumnsConfig"
        >
          <template #default="{ item: photo }">
            <div class="photo-card-hover" @click="handlePhotoClick(photo)">
              <img
                :src="getImageUrl(photo)"
                :alt="photo.filename"
                loading="lazy"
                class="masonry-img"
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
            </div>
          </template>
        </MasonryLayout>
      </n-spin>
    </div>

    <!-- 分页 -->
    <div v-if="photoStore.total > photoStore.pageSize" class="gallery-pagination">
      <n-pagination
        v-model:page="photoStore.currentPage"
        :item-count="photoStore.total"
        :page-size="photoStore.pageSize"
        show-size-picker
        :page-sizes="masonryPageSizes"
        @update:page="handlePageChange"
        @update:page-size="handlePageSizeChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  CloseOutline,
  GridOutline,
  AppsOutline,
  SearchOutline,
  PricetagsOutline,
  OptionsOutline,
} from '@vicons/ionicons5'
import { useDebounceFn } from '@vueuse/core'
import type { SelectOption } from 'naive-ui'
import MasonryLayout from '../components/common/MasonryLayout.vue'
import { usePhotoStore } from '../stores/photo'
import { getPublicTaxonomy, type TaxonomyFacet } from '../api/taxonomy'
import type { Photo, PhotoFilters, SearchInterpretation as SearchInterpretationType } from '../types/photo'
import { interpretSearch } from '../api/photo'
import SearchInterpretation from '../components/search/SearchInterpretation.vue'
import { getPhotoUrl } from '../utils/format'

const router = useRouter()
const route = useRoute()
const photoStore = usePhotoStore()

const taxonomyFacets = ref<TaxonomyFacet[]>([])
const taxonomyLoading = ref(false)
const taxonomyError = ref(false)
const syncingRoute = ref(false)
const viewMode = ref<'large' | 'small'>('large')
const smartSearchEnabled = ref(true)
const isInterpreting = ref(false)
const currentInterpretation = ref<SearchInterpretationType | null>(null)
const searchKeyword = ref('')
const filterMode = ref<'pills' | 'compact'>('pills')
const expandedGroups = reactive<Record<string, boolean>>({})

const PILL_COLLAPSE_THRESHOLD = 8

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
// 所有筛选字段统一从 taxonomy API 动态获取
const dynamicFacetKeys = ['season', 'campus', 'photo_type', 'building', 'gallery_series', 'gallery_year', 'tag']

const visibleFacetKeys = computed(() => {
  const visible: string[] = []
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

const gridGap = computed(() => viewMode.value === 'large' ? 16 : 10)

const masonryColumnsConfig = computed(() => {
  if (viewMode.value === 'small') {
    return { base: 2, sm: 3, lg: 4, xl: 5, '2xl': 6 }
  }
  return { base: 1, sm: 2, lg: 3, xl: 4, '2xl': 5 }
})

// 获取当前屏幕下的最大列数，用于计算每页数量
const maxColumnCount = computed(() => {
  const config = masonryColumnsConfig.value
  return config['2xl'] ?? config.xl ?? config.lg ?? config.sm ?? config.base ?? 1
})

// 分页选项：确保每页数量是列数的倍数，让瀑布流底部更平整
const masonryPageSizes = computed(() => {
  const cols = maxColumnCount.value
  // 生成 5倍、10倍、15倍 列数的选项
  return [cols * 5, cols * 10, cols * 15]
})

function facetOptions(key: string): SelectOption[] {
  // 优先从 taxonomy API 动态获取
  const facet = facetMap.value[key]
  if (facet && facet.nodes && facet.nodes.length > 0) {
    const flatten = (nodes: TaxonomyFacet['nodes']): SelectOption[] =>
      nodes.flatMap((node) => [
        { label: node.name, value: node.name },
        ...flatten(node.children || []),
      ])
    return flatten(facet.nodes)
  }

  // 降级：taxonomy 未返回时，使用与后端一致的硬编码选项
  if (key === 'season') {
    return [
      { label: '春季', value: '春季' },
      { label: '夏季', value: '夏季' },
      { label: '秋季', value: '秋季' },
      { label: '冬季', value: '冬季' },
    ]
  }
  if (key === 'campus') {
    return [
      { label: '昌平校区', value: '昌平校区' },
      { label: '朝阳校区', value: '朝阳校区' },
    ]
  }
  if (key === 'photo_type') {
    return [
      { label: '风光', value: '风光' },
      { label: '纪实', value: '纪实' },
    ]
  }

  return []
}

function shouldShowMore(key: string): boolean {
  return facetOptions(key).length > PILL_COLLAPSE_THRESHOLD
}

function getVisibleOptions(key: string): SelectOption[] {
  const opts = facetOptions(key)
  if (expandedGroups[key]) return opts
  return opts.slice(0, PILL_COLLAPSE_THRESHOLD)
}

function toggleExpand(key: string) {
  expandedGroups[key] = !expandedGroups[key]
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
  if (filters.search) {
    query.search = filters.search
    if (smartSearchEnabled.value) query.smart = 'true'
  }
  if (filters.sortBy) query.sort_by = filters.sortBy
  if (photoStore.currentPage > 1) query.page = String(photoStore.currentPage)
  if (photoStore.pageSize !== masonryPageSizes.value[0]) query.page_size = String(photoStore.pageSize)
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
  photoStore.pageSize = query.page_size ? Number(query.page_size) || masonryPageSizes.value[0] : masonryPageSizes.value[0]
  searchKeyword.value = photoStore.filters.search
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
  currentInterpretation.value = null
  await syncQueryAndFetch()
}

function handlePhotoClick(photo: Photo) {
  router.push(`/photo/${photo.id}`)
}

function handleSmartToggle(enabled: boolean) {
  smartSearchEnabled.value = enabled
  localStorage.setItem('smart_search_enabled', enabled ? 'true' : 'false')
}

async function handleCompactFilterChange(key: keyof PhotoFilters) {
  photoStore.setPage(1)
  await syncQueryAndFetch()
}

const handleSearchInput = useDebounceFn(async (value: string) => {
  if (!value.trim()) {
    currentInterpretation.value = null
    photoStore.setFilters({ search: '' })
    searchKeyword.value = ''
    await syncQueryAndFetch()
    return
  }

  if (!smartSearchEnabled.value) {
    currentInterpretation.value = null
    photoStore.setFilters({ search: value.trim() })
    await syncQueryAndFetch()
    return
  }

  isInterpreting.value = true
  try {
    const result = await interpretSearch(value.trim())
    currentInterpretation.value = result

    if (result.facet_filters && Object.keys(result.facet_filters).length > 0) {
      const filters: Partial<PhotoFilters> = {}
      for (const [facetKey, nodeValue] of Object.entries(result.facet_filters)) {
        if (facetKey === 'season') filters.season = nodeValue
        else if (facetKey === 'campus') filters.campus = nodeValue
        else if (facetKey === 'landmark') filters.building = nodeValue
        else if (facetKey === 'gallery_series') filters.gallery_series = nodeValue
        else if (facetKey === 'gallery_year') filters.gallery_year = nodeValue
        else if (facetKey === 'photo_type') filters.photo_type = nodeValue
      }
      const genericWords = new Set(['照片', '图片', '摄影', '相片', '图', '的', '了', '是', '在', '和'])
      const meaningfulKeywords = result.keywords.filter(kw => !genericWords.has(kw) && kw.length >= 2)
      if (meaningfulKeywords.length > 0) {
        filters.search = meaningfulKeywords.join(' ')
      }
      photoStore.setFilters(filters)
    } else {
      photoStore.setFilters({ search: value })
    }

    await syncQueryAndFetch()
  } catch {
    currentInterpretation.value = null
    photoStore.setFilters({ search: value })
    await syncQueryAndFetch()
  } finally {
    isInterpreting.value = false
  }
}, 500)

async function handleRemoveFacet(facetKey: string) {
  if (!currentInterpretation.value) return
  const newFilters = { ...currentInterpretation.value.facet_filters }
  delete newFilters[facetKey]
  currentInterpretation.value = {
    ...currentInterpretation.value,
    facet_filters: newFilters,
  }

  const filters: Partial<PhotoFilters> = {}
  for (const [key, value] of Object.entries(newFilters)) {
    if (key === 'season') filters.season = value
    else if (key === 'campus') filters.campus = value
    else if (key === 'landmark') filters.building = value
    else if (key === 'gallery_series') filters.gallery_series = value
    else if (key === 'gallery_year') filters.gallery_year = value
    else if (key === 'photo_type') filters.photo_type = value
  }
  if (currentInterpretation.value.keywords.length > 0) {
    filters.search = currentInterpretation.value.keywords.join(' ')
  }
  photoStore.setFilters(filters)
  await syncQueryAndFetch()
}

async function handleRemoveKeyword(keyword: string) {
  if (!currentInterpretation.value) return
  const newKeywords = currentInterpretation.value.keywords.filter(k => k !== keyword)
  currentInterpretation.value = {
    ...currentInterpretation.value,
    keywords: newKeywords,
  }
  if (newKeywords.length > 0) {
    photoStore.setFilters({ search: newKeywords.join(' ') })
  } else if (Object.keys(currentInterpretation.value.facet_filters).length === 0) {
    photoStore.setFilters({ search: '' })
  } else {
    photoStore.setFilters({ search: '' })
  }
  await syncQueryAndFetch()
}

function handleDismissInterpretation() {
  currentInterpretation.value = null
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

watch(filterMode, (mode) => {
  localStorage.setItem('gallery_filter_mode', mode)
})

onMounted(async () => {
  const saved = localStorage.getItem('smart_search_enabled')
  smartSearchEnabled.value = saved !== 'false'

  const savedFilterMode = localStorage.getItem('gallery_filter_mode')
  if (savedFilterMode === 'compact' || savedFilterMode === 'pills') {
    filterMode.value = savedFilterMode
  }

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

.filter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.filter-pills {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-compact {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.compact-selects {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.compact-active-filters {
  display: flex;
  flex-wrap: wrap;
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

.smart-search-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
}

.smart-label {
  font-size: 12px;
  transition: color 0.3s ease;
}

.smart-label.smart-active {
  color: #e60012;
  font-weight: 500;
}

.search-interpretation-area {
  margin: 8px 0;
}

.gallery-search-box {
  margin: 12px 0;
  position: relative;
}

.gallery-search-input {
  width: 100%;
}

.search-interpreting :deep(.n-input__border) {
  border-color: rgba(230, 0, 18, 0.4) !important;
  animation: search-pulse-border 1.5s ease-in-out infinite;
}

@keyframes search-pulse-border {
  0%, 100% { box-shadow: 0 0 0 0 rgba(230, 0, 18, 0.2); }
  50% { box-shadow: 0 0 0 3px rgba(230, 0, 18, 0.1); }
}

.interpreting-dots {
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 4px 0 0 4px;
}

.interpreting-dots .dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #e60012;
  animation: dot-bounce 1.2s ease-in-out infinite;
}

.interpreting-dots .dot:nth-child(2) {
  animation-delay: 0.15s;
}

.interpreting-dots .dot:nth-child(3) {
  animation-delay: 0.3s;
}

@keyframes dot-bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.3; }
  30% { transform: translateY(-4px); opacity: 1; }
}

/* 图片网格 */
.gallery-grid {
  min-height: 400px;
}

.gallery-empty {
  padding: 120px 0;
}

/* 瀑布流图片卡片 */
.photo-card-hover {
  position: relative;
  cursor: pointer;
  overflow: hidden;
  border-radius: 8px;
  background: #f5f5f5;
}

.masonry-img {
  width: 100%;
  height: auto;
  display: block;
  transition: transform 0.3s ease;
}

.photo-card-hover:hover .masonry-img {
  transform: scale(1.03);
}

.photo-card-hover .photo-overlay {
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

.photo-card-hover:hover .photo-overlay {
  background: rgba(0, 0, 0, 0.4);
}

.photo-card-hover .photo-overlay-content {
  opacity: 0;
  transform: translateY(6px);
  transition: all 0.3s ease;
}

.photo-card-hover:hover .photo-overlay-content {
  opacity: 1;
  transform: translateY(0);
}

.photo-card-hover .photo-title {
  font-size: 13px;
  color: white;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.photo-card-hover .photo-meta {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 6px;
}

.photo-card-hover .meta-tag {
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

  .compact-selects {
    gap: 6px;
  }

  .compact-selects :deep(.n-select) {
    width: calc(50% - 3px) !important;
  }
}
</style>
