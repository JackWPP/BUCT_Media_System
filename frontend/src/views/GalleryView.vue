<template>
  <div class="gallery-view">
    <!-- 搜索结果头部 -->
    <div v-if="isVectorSearch && vectorSearchResults.length > 0" class="search-results-header">
      <div class="search-info">
        <div class="search-query">
          <n-icon :component="SearchOutline" size="20" />
          <span class="query-text">"{{ searchQuery }}"</span>
        </div>
        <div class="search-meta">
          <n-tag type="success" size="small" :bordered="false">
            ✨ 语义搜索
          </n-tag>
          <span class="result-count">找到 {{ vectorSearchResults.length }} 张相关照片</span>
          <span class="query-time">{{ vectorQueryTime }}ms</span>
        </div>
      </div>
      <n-button text size="small" @click="clearVectorSearch">
        清除搜索
      </n-button>
    </div>

    <!-- 筛选栏 -->
    <div class="gallery-toolbar">
      <div class="toolbar-main">
        <div class="result-count">
          <span v-if="photoStore.filters.search && !isVectorSearch" class="search-term">
            "{{ photoStore.filters.search }}"
          </span>
        </div>

        <div class="toolbar-actions">
          <!-- 智能搜索开关已隐藏 -->
          <div class="smart-search-toggle" style="display:none;">
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
            class="sort-select"
            :options="sortOptions"
            @update:value="handleSortChange"
          />
        </div>
      </div>

      <!-- 筛选区域 -->
      <div v-if="hasAnyFacets || activeFilters.length" class="filter-area">
        <div v-if="activeFilters.length" class="filter-header">
          <n-button
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
              v-for="facetKey in guideVisibleFacetKeys"
              :key="facetKey"
              class="filter-group"
              :class="{ 'filter-group-child': !primaryFacetKeys.includes(facetKey) }"
            >
              <span class="filter-label">{{ facetLabelMap[facetKey] }}</span>
              <div class="pills-row">
                <span
                  v-for="opt in getVisibleOptions(facetKey)"
                  :key="opt.value"
                  class="tag-pill"
                  :class="{ active: photoStore.filters[facetKey] === opt.value, disabled: opt.disabled }"
                  @click="!opt.disabled && toggleFilter(facetKey as keyof PhotoFilters, opt.value as string)"
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
                v-for="facetKey in guideVisibleFacetKeys"
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
      <n-spin :show="photoStore.loading || vectorSearchLoading">
        <!-- 向量搜索结果为空 -->
        <div v-if="isVectorSearch && vectorSearchResults.length === 0 && !vectorSearchLoading" class="gallery-empty">
          <n-empty description="没有找到匹配的照片">
            <template #extra>
              <n-button @click="clearVectorSearch">清除搜索</n-button>
            </template>
          </n-empty>
        </div>

        <!-- 普通浏览为空 -->
        <div v-else-if="!isVectorSearch && photoStore.photos.length === 0 && !photoStore.loading" class="gallery-empty">
          <n-empty description="暂无符合条件的照片">
            <template #extra>
              <n-button @click="handleClearFilters">清空筛选</n-button>
            </template>
          </n-empty>
        </div>

        <!-- 向量搜索结果展示 -->
        <MasonryLayout
          v-else-if="isVectorSearch && vectorSearchResults.length > 0"
          :items="vectorSearchResults"
          :gap="gridGap"
          :columns-config="masonryColumnsConfig"
          :get-item-ratio="getVectorItemRatio"
        >
          <template #default="{ item: result }">
            <div class="photo-card-hover vector-search-card" @click="handlePhotoClick({ id: result.photo_id } as Photo)">
              <img
                :src="getVectorThumbUrl(result.photo_id)"
                :alt="result.tags.join(', ')"
                loading="lazy"
                class="masonry-img"
                @load="(e) => handleVectorImageLoad(e, result)"
                @error="(e) => handleVectorImageError(e, result)"
              />
              <div class="photo-overlay vector-overlay">
                <div class="photo-overlay-content">
                  <div class="vector-score-badge">
                    <n-tag :type="getScoreType(result.score)" size="small" :bordered="false">
                      {{ (result.score * 100).toFixed(0) }}%
                    </n-tag>
                  </div>
                  <div class="vector-tags">
                    <n-tag
                      v-for="tag in result.tags.slice(0, 3)"
                      :key="tag"
                      size="tiny"
                      :bordered="false"
                      type="info"
                    >
                      {{ tag }}
                    </n-tag>
                  </div>
                  <div class="vector-classifications" v-if="result.classifications">
                    <span v-if="result.classifications.season" class="meta-tag">
                      {{ result.classifications.season }}
                    </span>
                    <span v-if="result.classifications.campus" class="meta-tag">
                      {{ result.classifications.campus }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </MasonryLayout>

        <!-- 普通照片展示 -->
        <MasonryLayout
          v-else
          :items="photoStore.photos"
          :gap="gridGap"
          :columns-config="masonryColumnsConfig"
          :get-item-ratio="getItemRatio"
        >
          <template #default="{ item: photo }">
            <div class="photo-card-hover" :class="{ 'photo-card-portrait': photo.height > photo.width }" @click="handlePhotoClick(photo)">
              <img
                :src="getImageUrl(photo)"
                :alt="photo.filename"
                loading="lazy"
                class="masonry-img"
                @load="(e) => handleImageLoad(e, photo)"
                @error="(e) => handleImageError(e, photo)"
              />
              <div class="photo-overlay">
                <div class="photo-overlay-content">
                  <div class="photo-title">{{ photo.filename }}</div>
                  <div class="photo-meta">
                    <span v-if="taxonomyValueName(photo.classifications?.season)" class="meta-tag">
                      {{ taxonomyValueName(photo.classifications?.season) }}
                    </span>
                    <span v-if="taxonomyValueName(photo.classifications?.campus)" class="meta-tag">
                      {{ taxonomyValueName(photo.classifications?.campus) }}
                    </span>
                  </div>
                </div>
                <n-button
                  v-if="authStore.isAuditor"
                  class="photo-edit-btn"
                  circle
                  size="tiny"
                  :color="'rgba(255,255,255,0.9)'"
                  @click.stop="openEditModal(photo)"
                >
                  <template #icon>
                    <n-icon :component="CreateOutline" />
                  </template>
                </n-button>
              </div>
            </div>
          </template>
        </MasonryLayout>
      </n-spin>
    </div>

    <!-- 无限滚动加载更多 -->
    <div ref="loadMoreSentinel" class="load-more-sentinel" v-if="photoStore.hasMore">
      <n-spin size="small" />
      <span class="load-more-text">加载更多…</span>
    </div>
    <div v-else-if="photoStore.photos.length > 0" class="load-more-end">
      — 已加载全部 {{ photoStore.total }} 张 —
    </div>

    <!-- 管理员编辑模态框 -->
    <PhotoDetail
      v-model:show="showEditModal"
      :photo-id="editingPhotoId"
      admin-mode
      @updated="syncQueryAndFetch"
      @deleted="syncQueryAndFetch"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  CloseOutline,
  GridOutline,
  AppsOutline,
  CreateOutline,
  SearchOutline,
} from '@vicons/ionicons5'
import { useDebounceFn } from '@vueuse/core'
import type { SelectOption } from 'naive-ui'
import MasonryLayout from '../components/common/MasonryLayout.vue'
import { usePhotoStore } from '../stores/photo'
import { getPublicTaxonomy, getPublicTaxonomyGuide, type TaxonomyFacet, type TaxonomyGuide } from '../api/taxonomy'
import { getPublicTags } from '../api/tag'
import type { Photo, PhotoFilters, SearchInterpretation as SearchInterpretationType } from '../types/photo'
import { taxonomyValueName } from '../types/photo'
import { interpretSearch } from '../api/photo'
import SearchInterpretation from '../components/search/SearchInterpretation.vue'
import PhotoDetail from '../components/photo/PhotoDetail.vue'
import { getPhotoUrl } from '../utils/format'
import { useAuthStore } from '../stores/auth'
import { searchPhotos, type SearchResult } from '../api/search'
import {
  FACET_LABELS,
  GALLERY_FILTER_KEYS,
  flattenTaxonomyOptions,
} from '../utils/taxonomy'

const router = useRouter()
const route = useRoute()
const photoStore = usePhotoStore()
const authStore = useAuthStore()

const taxonomyFacets = ref<TaxonomyFacet[]>([])
const taxonomyGuide = ref<TaxonomyGuide | null>(null)
const publicTagOptions = ref<SelectOption[]>([])
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
const showEditModal = ref(false)
const editingPhotoId = ref<string | null>(null)

// 向量搜索状态
const isVectorSearch = ref(false)
const vectorSearchResults = ref<SearchResult[]>([])
const vectorQueryTime = ref(0)
const searchQuery = ref('')
const vectorSearchLoading = ref(false)

const PILL_COLLAPSE_THRESHOLD = 8

// 需要隐藏的标签（红框标注要删除的）
const hiddenTags: Record<string, string[]> = {}

const sortOptions = [
  { label: '最新上传', value: 'created_at' },
  { label: '最热门', value: 'views' },
  { label: '最近发布', value: 'published_at' },
]

const facetLabelMap: Record<string, string> = FACET_LABELS

const facetMap = computed(() =>
  Object.fromEntries(taxonomyFacets.value.map((facet) => [facet.key, facet])),
)

// 静态筛选字段（始终显示，不需要 taxonomy 数据）
// 所有筛选字段统一从 taxonomy API 动态获取
const dynamicFacetKeys = GALLERY_FILTER_KEYS

const primaryFacetKeys = computed(() => taxonomyGuide.value?.primary || ['gallery_series', 'campus', 'photo_type'])

const dependentFacetKeys = computed(() => {
  const keys: string[] = []
  const dependencies = taxonomyGuide.value?.dependencies || {}
  Object.entries(dependencies).forEach(([parentKey, byValue]) => {
    const selected = photoStore.filters[parentKey as keyof PhotoFilters]
    if (!selected) return
    const children = byValue[selected as string] || []
    children.forEach((key) => keys.push(key))
  })
  return keys
})

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

const guideVisibleFacetKeys = computed(() => {
  const keys = [...primaryFacetKeys.value, ...dependentFacetKeys.value, 'tag']
  return [...new Set(keys)].filter((key) => visibleFacetKeys.value.includes(key))
})

const activeFilters = computed(() => {
  const filters = photoStore.filters
  const chips: Array<{ key: keyof PhotoFilters; label: string; value: string }> = []
  GALLERY_FILTER_KEYS.forEach((key) => {
    const value = filters[key]
    if (value) {
      chips.push({ key, label: facetLabelMap[key], value: filterValueLabel(key, value) })
    }
  })
  return chips
})

const gridGap = computed(() => viewMode.value === 'large' ? 16 : 10)

const masonryColumnsConfig = computed(() => {
  if (viewMode.value === 'small') {
    return { base: 2, sm: 3, lg: 4, xl: 5, '2xl': 6 }
  }
  return { base: 2, sm: 2, lg: 3, xl: 4, '2xl': 5 }
})

// 根据图片方向返回高度/宽度比。缺少尺寸时用原图加载后的比例回填，避免本地元数据缺失时全部显示为横屏。
const getItemRatio = (photo: any) => {
  if (photo.width && photo.height) {
    return photo.height / photo.width
  }
  return photo._displayRatio || 2 / 3
}

// 获取当前屏幕下的最大列数，用于计算每页数量
const maxColumnCount = computed(() => {
  const config = masonryColumnsConfig.value
  return config['2xl'] ?? config.xl ?? config.lg ?? config.sm ?? config.base ?? 1
})

// 分页选项：确保每页数量是列数的倍数，让瀑布流底部更平整
const masonryPageSizes = computed(() => {
  const cols = maxColumnCount.value
  // 默认至少30张或列数×8（取较大值），确保首屏填满
  const defaultSize = Math.max(30, cols * 8)
  return [defaultSize, cols * 15, cols * 25]
})

function facetOptions(key: string): SelectOption[] {
  let options: SelectOption[] = []

  if (key === 'tag') {
    return publicTagOptions.value
  }

  // 优先从 taxonomy API 动态获取
  const taxonomyKey = key
  const facet = facetMap.value[taxonomyKey]
  if (facet && facet.nodes && facet.nodes.length > 0) {
    options = flattenTaxonomyOptions(facet.nodes, (node) => node.name)
  } else {
    // 降级：taxonomy 未返回时，使用与后端一致的硬编码选项
    if (key === 'season') {
      options = [
        { label: '春季', value: '春季' },
        { label: '夏季', value: '夏季' },
        { label: '秋季', value: '秋季' },
        { label: '冬季', value: '冬季' },
      ]
    }
    if (key === 'campus') {
      options = [
        { label: '朝阳校区', value: '朝阳校区' },
        { label: '昌平校区', value: '昌平校区' },
        { label: '海淀校区', value: '海淀校区' },
      ]
    }
    if (key === 'photo_type') {
      options = [
        { label: '校园风光', value: '校园风光' },
        { label: '人文纪实', value: '人文纪实' },
        { label: '自然生态', value: '自然生态' },
      ]
    }
  }

  // 过滤掉需要隐藏的标签
  const hidden = hiddenTags[key] || []
  return options.filter((opt) => !hidden.includes(opt.value as string))
}

function filterValueLabel(key: string, value: string) {
  return facetOptions(key).find((option) => option.value === value)?.label || value
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

// 向量搜索相关函数
function getVectorThumbUrl(photoId: string): string {
  return getPhotoUrl(photoId, 'thumbnail')
}

function getVectorItemRatio(result: SearchResult): number {
  // 搜索结果卡片统一 1:1 裁切。
  return 1
}

function handleVectorImageLoad(event: Event, result: SearchResult) {
  const img = event.target as HTMLImageElement
  if (img.naturalWidth > 0 && img.naturalHeight > 0) {
    // 可以在这里更新结果的宽高信息
  }
}

function handleVectorImageError(event: Event, result: SearchResult) {
  const img = event.target as HTMLImageElement
  if (img.getAttribute('data-tried') === 'true') {
    img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect fill="%23f0f0f0" width="200" height="200"/%3E%3Ctext fill="%23999" x="50%25" y="50%25" text-anchor="middle" dy=".3em"%3E图片加载失败%3C/text%3E%3C/svg%3E'
    return
  }
  img.setAttribute('data-tried', 'true')
  img.src = getVectorThumbUrl(result.photo_id)
}

function getScoreType(score: number): 'success' | 'warning' | 'error' {
  if (score >= 0.8) return 'success'
  if (score >= 0.6) return 'warning'
  return 'error'
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

function handleImageLoad(event: Event, photo: Photo) {
  const img = event.target as HTMLImageElement
  if (img.naturalWidth > 0 && img.naturalHeight > 0) {
    ;(photo as Photo & { _displayRatio?: number })._displayRatio = img.naturalHeight / img.naturalWidth
  }
}

function buildQuery() {
  const query: Record<string, string> = {}
  const filters = photoStore.filters
  GALLERY_FILTER_KEYS.forEach((key) => {
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
  await nextTick()
  setupInfiniteScroll()
}

function applyRouteQuery() {
  syncingRoute.value = true
  const query = route.query
  photoStore.filters.season = typeof query.season === 'string' ? query.season : null
  photoStore.filters.campus = typeof query.campus === 'string' ? query.campus : null
  photoStore.filters.building = typeof query.building === 'string' ? query.building : null
  photoStore.filters.facility = typeof query.facility === 'string' ? query.facility : null
  photoStore.filters.landscape = typeof query.landscape === 'string' ? query.landscape : null
  photoStore.filters.natural_phenomenon = typeof query.natural_phenomenon === 'string' ? query.natural_phenomenon : null
  photoStore.filters.technique = typeof query.technique === 'string' ? query.technique : null
  photoStore.filters.animal = typeof query.animal === 'string' ? query.animal : null
  photoStore.filters.plant = typeof query.plant === 'string' ? query.plant : null
  photoStore.filters.source_type = typeof query.source_type === 'string' ? query.source_type : null
  photoStore.filters.gallery_series = typeof query.gallery_series === 'string' ? query.gallery_series : null
  photoStore.filters.gallery_year = typeof query.gallery_year === 'string' ? query.gallery_year : null
  photoStore.filters.award_level = typeof query.award_level === 'string' ? query.award_level : null
  photoStore.filters.photo_type = typeof query.photo_type === 'string' ? query.photo_type : null
  photoStore.filters.documentary_topic = typeof query.documentary_topic === 'string' ? query.documentary_topic : null
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
  clearVectorSearch()
  await syncQueryAndFetch()
}

// 向量搜索函数
async function performVectorSearch(query: string) {
  console.log('🔍 performVectorSearch called with:', query)
  
  if (!query.trim()) {
    console.log('❌ Empty query, clearing search')
    clearVectorSearch()
    return
  }

  // 清除之前的搜索结果
  clearVectorSearch()
  vectorSearchLoading.value = true
  searchQuery.value = query.trim()

  try {
    console.log('📡 Calling searchPhotos API...')
    const response = await searchPhotos({
      q: query.trim(),
      limit: 50,
      ...(photoStore.filters.season ? { season: photoStore.filters.season } : {}),
      ...(photoStore.filters.campus ? { campus: photoStore.filters.campus } : {}),
    })

    console.log('✅ API response:', response)
    isVectorSearch.value = true
    vectorSearchResults.value = response.results
    vectorQueryTime.value = response.query_time_ms

    // 将向量搜索结果转换为照片格式显示
    const photoIds = response.results.map(r => r.photo_id)
    if (photoIds.length > 0) {
      // 这里需要批量获取照片详情，暂时使用搜索结果
      // TODO: 后续优化为批量获取照片详情
    }
  } catch (err) {
    console.error('❌ Vector search failed:', err)
    // 降级到普通搜索
    isVectorSearch.value = false
    photoStore.setFilters({ search: query.trim() })
    await syncQueryAndFetch()
  } finally {
    vectorSearchLoading.value = false
  }
}

function clearVectorSearch() {
  isVectorSearch.value = false
  vectorSearchResults.value = []
  vectorQueryTime.value = 0
  searchQuery.value = ''
}

function handlePhotoClick(photo: Photo) {
  router.push(`/photo/${photo.id}`)
}

function openEditModal(photo: Photo) {
  editingPhotoId.value = photo.id
  showEditModal.value = true
}

async function handleSmartToggle(enabled: boolean) {
  smartSearchEnabled.value = enabled
  localStorage.setItem('smart_search_enabled', enabled ? 'true' : 'false')
  if (!enabled) {
    currentInterpretation.value = null
    if (searchKeyword.value.trim()) {
      photoStore.setFilters({ search: searchKeyword.value.trim() })
      await syncQueryAndFetch()
    }
  } else if (searchKeyword.value.trim()) {
    // Re-trigger interpretation with current search text
    await handleSearchInput(searchKeyword.value)
  }
}

async function handleCompactFilterChange(key: keyof PhotoFilters) {
  photoStore.setPage(1)
  await syncQueryAndFetch()
}

function applyInterpretation(interpretation: SearchInterpretationType) {
  currentInterpretation.value = interpretation

  if (interpretation.facet_filters && Object.keys(interpretation.facet_filters).length > 0) {
    const filters: Partial<PhotoFilters> = {}
    for (const [facetKey, nodeValue] of Object.entries(interpretation.facet_filters)) {
      if (facetKey === 'season') filters.season = nodeValue
      else if (facetKey === 'campus') filters.campus = nodeValue
      else if (facetKey === 'building' || facetKey === 'landmark') filters.building = nodeValue
      else if (facetKey === 'source_type') filters.source_type = nodeValue
      else if (facetKey === 'facility') filters.facility = nodeValue
      else if (facetKey === 'landscape') filters.landscape = nodeValue
      else if (facetKey === 'natural_phenomenon') filters.natural_phenomenon = nodeValue
      else if (facetKey === 'technique') filters.technique = nodeValue
      else if (facetKey === 'animal') filters.animal = nodeValue
      else if (facetKey === 'plant') filters.plant = nodeValue
      else if (facetKey === 'gallery_series') filters.gallery_series = nodeValue
      else if (facetKey === 'gallery_year') filters.gallery_year = nodeValue
      else if (facetKey === 'award_level') filters.award_level = nodeValue
      else if (facetKey === 'photo_type') filters.photo_type = nodeValue
      else if (facetKey === 'documentary_topic') filters.documentary_topic = nodeValue
    }
    const genericWords = new Set(['照片', '图片', '摄影', '相片', '图', '的', '了', '是', '在', '和'])
    const meaningfulKeywords = interpretation.keywords.filter(kw => !genericWords.has(kw) && kw.length >= 2)
    if (meaningfulKeywords.length > 0) {
      filters.search = meaningfulKeywords.join(' ')
    } else {
      filters.search = interpretation.original_query
    }
    photoStore.setFilters(filters)
  }
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
    applyInterpretation(result)
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
    else if (key === 'building' || key === 'landmark') filters.building = value
    else if (key === 'source_type') filters.source_type = value
    else if (key === 'facility') filters.facility = value
    else if (key === 'landscape') filters.landscape = value
    else if (key === 'natural_phenomenon') filters.natural_phenomenon = value
    else if (key === 'technique') filters.technique = value
    else if (key === 'animal') filters.animal = value
    else if (key === 'plant') filters.plant = value
    else if (key === 'gallery_series') filters.gallery_series = value
    else if (key === 'gallery_year') filters.gallery_year = value
    else if (key === 'award_level') filters.award_level = value
    else if (key === 'photo_type') filters.photo_type = value
    else if (key === 'documentary_topic') filters.documentary_topic = value
  }
  const genericWords = new Set(['照片', '图片', '摄影', '相片', '图', '的', '了', '是', '在', '和'])
  const meaningfulKeywords = currentInterpretation.value.keywords.filter(kw => !genericWords.has(kw) && kw.length >= 2)
  if (meaningfulKeywords.length > 0) {
    filters.search = meaningfulKeywords.join(' ')
  } else {
    filters.search = currentInterpretation.value.original_query
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
  } else {
    photoStore.setFilters({ search: currentInterpretation.value.original_query })
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
    const [facets, guide, tags] = await Promise.all([
      getPublicTaxonomy(),
      getPublicTaxonomyGuide(),
      getPublicTags({ limit: 60 }),
    ])
    taxonomyFacets.value = facets
    taxonomyGuide.value = guide
    publicTagOptions.value = tags.items.map((tag) => ({
      label: tag.name,
      value: tag.name,
      disabled: false,
    }))
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
    
    clearVectorSearch()
    await photoStore.fetchPublicPhotos()
    
    // Display interpretation when navigating to gallery with search (e.g., browser back/forward)
    if (photoStore.searchInterpretation && smartSearchEnabled.value) {
      applyInterpretation(photoStore.searchInterpretation)
    }
  },
  { deep: true },
)

watch(filterMode, (mode) => {
  localStorage.setItem('gallery_filter_mode', mode)
})

const loadMoreSentinel = ref<HTMLElement | null>(null)
let scrollObserver: IntersectionObserver | null = null

function setupInfiniteScroll() {
  if (scrollObserver) scrollObserver.disconnect()
  scrollObserver = new IntersectionObserver(
    (entries) => {
      if (entries[0].isIntersecting && photoStore.hasMore && !photoStore.loading) {
        photoStore.loadMorePublicPhotos()
      }
    },
    { rootMargin: '300px' },
  )
  // nextTick 确保 sentinel 已渲染
  nextTick(() => {
    if (loadMoreSentinel.value) {
      scrollObserver!.observe(loadMoreSentinel.value)
    }
  })
}

onMounted(async () => {
  const saved = localStorage.getItem('smart_search_enabled')
  smartSearchEnabled.value = saved !== 'false'

  const savedFilterMode = localStorage.getItem('gallery_filter_mode')
  if (savedFilterMode === 'compact' || savedFilterMode === 'pills') {
    filterMode.value = savedFilterMode
  }

  applyRouteQuery()
  clearVectorSearch()
  await Promise.all([photoStore.fetchPublicPhotos(), loadTaxonomy()])

  if (photoStore.searchInterpretation && smartSearchEnabled.value) {
    applyInterpretation(photoStore.searchInterpretation)
  }

  setupInfiniteScroll()
})

onUnmounted(() => {
  if (scrollObserver) {
    scrollObserver.disconnect()
    scrollObserver = null
  }
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
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}

.result-count {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  min-height: 32px;
  flex: 1 1 240px;
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
  justify-content: flex-end;
  gap: 8px;
  flex: 0 1 auto;
  min-width: 0;
  max-width: 100%;
  flex-wrap: wrap;
}

.toolbar-actions :deep(.n-button-group) {
  flex: 0 0 auto;
}

.sort-select {
  width: 128px;
  min-width: 112px;
  flex: 0 0 128px;
}

/* 筛选区域 */
.filter-area {
  min-height: 36px;
}

.filter-header {
  display: flex;
  justify-content: flex-end;
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

.filter-group-child {
  padding-left: 18px;
  border-left: 2px solid #e5e7eb;
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

.tag-pill.disabled {
  cursor: not-allowed;
  opacity: 0.52;
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
  aspect-ratio: 3 / 2;
}

.photo-card-hover.photo-card-portrait {
  aspect-ratio: 2 / 3;
}

.masonry-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
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

.photo-edit-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  opacity: 0;
  transform: translateY(-4px);
  transition: all 0.3s ease;
  pointer-events: auto;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.photo-card-hover:hover .photo-edit-btn {
  opacity: 1;
  transform: translateY(0);
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
    padding: 64px 8px 32px;
  }

  .toolbar-main {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .result-count {
    display: none;
  }

  .toolbar-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .sort-select {
    width: min(160px, calc(100vw - 132px));
    flex-basis: min(160px, calc(100vw - 132px));
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
.load-more-sentinel {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 32px 0;
  color: #999;
  font-size: 14px;
}

.load-more-end {
  text-align: center;
  padding: 32px 0;
  color: #bbb;
  font-size: 13px;
}

/* 向量搜索结果头部 */
.search-results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  margin-bottom: 16px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.search-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.search-query {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #1e293b;
  font-size: 16px;
  font-weight: 600;
}

.query-text {
  color: #3b82f6;
}

.search-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  color: #64748b;
}

.result-count {
  font-weight: 500;
}

.query-time {
  color: #94a3b8;
}

/* 向量搜索卡片样式 */
.vector-search-card {
  position: relative;
}

.vector-overlay {
  background: linear-gradient(to top, rgba(0, 0, 0, 0.8) 0%, rgba(0, 0, 0, 0.4) 50%, transparent 100%) !important;
}

.vector-score-badge {
  position: absolute;
  top: 8px;
  right: 8px;
}

.vector-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 8px;
}

.vector-classifications {
  display: flex;
  gap: 6px;
  margin-top: 6px;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .search-results-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
    padding: 12px 16px;
  }
  
  .search-meta {
    flex-wrap: wrap;
  }
}

</style>
