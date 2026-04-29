<template>
  <div class="gallery-container">
    <n-layout has-sider>
      <n-layout-sider
        class="desktop-sider"
        bordered
        :collapsed="appStore.sidebarCollapsed"
        collapse-mode="width"
        :collapsed-width="64"
        :width="240"
        show-trigger
        @collapse="appStore.toggleSidebar"
        @expand="appStore.toggleSidebar"
      >
        <n-menu
          :collapsed="appStore.sidebarCollapsed"
          :collapsed-width="64"
          :collapsed-icon-size="22"
          :options="menuOptions"
          :value="activeMenu"
          @update:value="handleMenuSelect"
        />
      </n-layout-sider>

      <n-layout>
        <n-layout-header bordered class="gallery-header">
          <div class="header-left">
            <n-button class="mobile-menu-btn" quaternary circle @click="showMobileDrawer = true">
              <template #icon>
                <n-icon :component="MenuOutline" />
              </template>
            </n-button>
            <img src="/logo.png" alt="视觉北化" class="gallery-logo" />
            <div class="search-area">
              <n-input
                v-model:value="searchKeyword"
                :placeholder="smartSearchEnabled ? '试试自然语言搜索：秋天的图书馆、春天的樱花...' : '输入关键词搜索照片...'"
                clearable
                class="search-input"
                :class="{ 'search-interpreting': isInterpreting, 'search-pulse': isInterpreting }"
                @update:value="handleSearch"
              >
                <template #prefix>
                  <n-icon :component="SearchOutline" />
                </template>
              </n-input>
              <div class="search-smart-toggle">
                <n-switch
                  v-model:value="smartSearchEnabled"
                  size="small"
                  @update:value="handleSmartToggle"
                />
                <n-text depth="3" class="smart-label" :class="{ 'smart-active': smartSearchEnabled }">
                  {{ smartSearchEnabled ? '✨ 智能搜索' : '普通搜索' }}
                </n-text>
              </div>
              <div v-if="isInterpreting" class="interpreting-dots">
                <span class="dot"></span>
                <span class="dot"></span>
                <span class="dot"></span>
              </div>
              <SearchInterpretation
                :interpretation="currentInterpretation"
                @remove-facet="handleRemoveFacet"
                @remove-keyword="handleRemoveKeyword"
                @dismiss="handleDismissInterpretation"
              />
            </div>
          </div>
          <div class="header-right">
            <n-badge :value="photoStore.total" :max="999" show-zero>
              <n-button tertiary circle>
                <template #icon>
                  <n-icon :component="ImagesOutline" />
                </template>
              </n-button>
            </n-badge>
            <NotificationBell v-if="authStore.isAuthenticated" />
            <n-button v-if="authStore.isAuthenticated" type="primary" @click="router.push('/upload')">
              <template #icon>
                <n-icon :component="CloudUploadOutline" />
              </template>
              上传照片
            </n-button>
            <template v-if="authStore.isAuthenticated">
              <n-dropdown :options="userMenuOptions" @select="handleUserMenuSelect">
                <n-button circle>
                  <template #icon>
                    <n-icon :component="PersonOutline" />
                  </template>
                </n-button>
              </n-dropdown>
            </template>
            <template v-else>
              <n-button type="primary" ghost @click="router.push('/login')">
                <template #icon>
                  <n-icon :component="PersonOutline" />
                </template>
                后台登录
              </n-button>
            </template>
          </div>
        </n-layout-header>

        <n-layout-content content-style="padding: 16px;" class="gallery-content">
          <div class="filters-container">
            <div class="mobile-filter-toggle">
              <n-button @click="showFilters = !showFilters" secondary block>
                <template #icon>
                  <n-icon :component="FunnelOutline" />
                </template>
                {{ showFilters ? '收起筛选' : '展开筛选' }}
              </n-button>
            </div>

            <div class="filters-content" :class="{ 'filters-visible': showFilters }">
              <n-space wrap>
                <n-select
                  v-model:value="photoStore.filters.season"
                  placeholder="季节"
                  clearable
                  style="width: 120px;"
                  :options="facetOptions('season')"
                  @update:value="handleFilterChange"
                />
                <n-select
                  v-model:value="photoStore.filters.campus"
                  placeholder="校区"
                  clearable
                  style="width: 140px;"
                  :options="facetOptions('campus')"
                  @update:value="handleFilterChange"
                />
                <n-select
                  v-model:value="photoStore.filters.building"
                  placeholder="楼宇"
                  clearable
                  style="width: 160px;"
                  :options="facetOptions('building')"
                  @update:value="handleFilterChange"
                />
                <n-select
                  v-model:value="photoStore.filters.gallery_series"
                  placeholder="专题 / 赛事"
                  clearable
                  style="width: 180px;"
                  :options="facetOptions('gallery_series')"
                  @update:value="handleFilterChange"
                />
                <n-select
                  v-model:value="photoStore.filters.gallery_year"
                  placeholder="年份"
                  clearable
                  style="width: 120px;"
                  :options="facetOptions('gallery_year')"
                  @update:value="handleFilterChange"
                />
                <n-select
                  v-model:value="photoStore.filters.photo_type"
                  placeholder="照片类型"
                  clearable
                  style="width: 140px;"
                  :options="facetOptions('photo_type')"
                  @update:value="handleFilterChange"
                />
                <n-select
                  v-model:value="photoStore.filters.tag"
                  placeholder="自由标签"
                  clearable
                  filterable
                  style="width: 160px;"
                  :options="tagOptions"
                  :loading="loadingTags"
                  @update:value="handleFilterChange"
                />
                <n-select
                  v-model:value="photoStore.filters.sortBy"
                  placeholder="排序"
                  style="width: 140px;"
                  :options="sortOptions"
                  @update:value="handleFilterChange"
                />
                <n-button @click="handleClearFilters" secondary size="small">
                  <template #icon>
                    <n-icon :component="RefreshOutline" />
                  </template>
                  清空
                </n-button>
              </n-space>

              <n-space v-if="activeFilters.length" wrap style="margin-top: 12px;">
                <n-tag
                  v-for="filter in activeFilters"
                  :key="filter.key"
                  closable
                  @close="removeFilter(filter.key)"
                >
                  {{ filter.label }}: {{ filter.value }}
                </n-tag>
              </n-space>
            </div>

            <n-text depth="3" class="photo-count">共 {{ photoStore.total }} 张</n-text>
          </div>

          <div class="photos-section">
            <n-spin :show="photoStore.loading">
              <n-grid v-if="photoStore.loading" :cols="gridCols" :x-gap="16" :y-gap="16" responsive="screen">
                <n-grid-item v-for="i in 12" :key="i">
                  <PhotoCardSkeleton />
                </n-grid-item>
              </n-grid>

              <EmptyState
                v-else-if="photoStore.photos.length === 0"
                description="暂无符合条件的照片"
                :icon="ImagesOutline"
                action
                action-text="清空筛选"
                @action="handleClearFilters"
              />

              <MasonryLayout v-else :items="photoStore.photos" :gap="16">
                <template #default="{ item: photo }">
                  <div class="photo-card" @click="handlePhotoClick(photo)">
                    <div
                      class="photo-image"
                      :style="{ aspectRatio: photo.width && photo.height ? `${photo.width} / ${photo.height}` : '4 / 3' }"
                    >
                      <img
                        :src="getImageUrl(photo)"
                        :alt="photo.filename"
                        loading="lazy"
                        class="masonry-img"
                        @error="(e) => handleImageError(e, photo)"
                      />
                      <div class="photo-overlay">
                        <n-icon size="32" color="white" :component="EyeOutline" />
                      </div>
                    </div>
                    <div class="photo-info">
                      <n-space size="small" wrap>
                        <n-tag v-if="photo.classifications?.season" size="small" type="success">
                          {{ photo.classifications.season.node_name }}
                        </n-tag>
                        <n-tag v-if="photo.classifications?.campus" size="small" type="warning">
                          {{ photo.classifications.campus.node_name }}
                        </n-tag>
                        <n-tag v-if="photo.classifications?.photo_type" size="small" type="info">
                          {{ photo.classifications.photo_type.node_name }}
                        </n-tag>
                        <n-tag
                          v-for="tag in (photo.free_tags || photo.tags || []).slice(0, 3)"
                          :key="tag"
                          size="small"
                          class="clickable-tag"
                          @click.stop="handleTagClick(tag)"
                        >
                          {{ tag }}
                        </n-tag>
                      </n-space>
                    </div>
                  </div>
                </template>
              </MasonryLayout>
            </n-spin>
          </div>

          <div v-if="photoStore.total > photoStore.pageSize" class="pagination-container">
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
        </n-layout-content>
      </n-layout>
    </n-layout>

    <PhotoDetail
      v-model:show="showPhotoDetail"
      :photo-id="selectedPhotoId"
      :has-prev="hasPrevPhoto"
      :has-next="hasNextPhoto"
      @prev="handlePrevPhoto"
      @next="handleNextPhoto"
      @deleted="handlePhotoDeleted"
      @updated="handlePhotoUpdated"
    />

    <n-drawer v-model:show="showMobileDrawer" placement="left" :width="280">
      <n-drawer-content title="导航菜单" closable>
        <n-menu
          :options="menuOptions"
          :value="activeMenu"
          @update:value="(val: string) => { handleMenuSelect(val); showMobileDrawer = false }"
        />
      </n-drawer-content>
    </n-drawer>

    <!-- 修改密码对话框 -->
    <ChangePasswordDialog v-model:show="showChangePassword" />
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NIcon, useDialog, useMessage } from 'naive-ui'
import {
  CloudUploadOutline,
  EyeOutline,
  FunnelOutline,
  ImagesOutline,
  LogOutOutline,
  MenuOutline,
  PersonOutline,
  RefreshOutline,
  SearchOutline,
  SettingsOutline,
} from '@vicons/ionicons5'
import { useDebounceFn } from '@vueuse/core'
import type { SelectOption } from 'naive-ui'
import { getPopularTags, type Tag } from '../api/tag'
import { getPublicTaxonomy, type TaxonomyFacet } from '../api/taxonomy'
import { interpretSearch } from '../api/photo'
import EmptyState from '../components/common/EmptyState.vue'
import MasonryLayout from '../components/common/MasonryLayout.vue'
import PhotoCardSkeleton from '../components/common/PhotoCardSkeleton.vue'
import PhotoDetail from '../components/photo/PhotoDetail.vue'
import ChangePasswordDialog from '../components/common/ChangePasswordDialog.vue'
import NotificationBell from '../components/common/NotificationBell.vue'
import SearchInterpretation from '../components/search/SearchInterpretation.vue'
import { useAppStore } from '../stores/app'
import { useAuthStore } from '../stores/auth'
import { usePhotoStore } from '../stores/photo'
import type { Photo, PhotoFilters, SearchInterpretation as SearchInterpretationType } from '../types/photo'
import { getPhotoUrl } from '../utils/format'

const router = useRouter()
const route = useRoute()
const message = useMessage()
const dialog = useDialog()
const authStore = useAuthStore()
const photoStore = usePhotoStore()
const appStore = useAppStore()

const searchKeyword = ref('')
const activeMenu = ref('all')
const showPhotoDetail = ref(false)
const selectedPhotoId = ref<string | null>(null)
const gridCols = ref(4)
const showMobileDrawer = ref(false)
const showFilters = ref(false)
const showChangePassword = ref(false)
const loadingTags = ref(false)
const popularTags = ref<Tag[]>([])
const smartSearchEnabled = ref(true)
const taxonomyFacets = ref<TaxonomyFacet[]>([])
const syncingRoute = ref(false)
const isInterpreting = ref(false)
const currentInterpretation = ref<SearchInterpretationType | null>(null)

const menuOptions = [
  {
    label: '全部照片',
    key: 'all',
    icon: () => h(NIcon, null, { default: () => h(ImagesOutline) }),
  },
]

const userMenuOptions = computed(() => {
  const options: any[] = [
    {
      label: `${authStore.user?.email || '用户'}`,
      key: 'user-info',
      disabled: true,
    },
    {
      label: '我的投稿',
      key: 'submissions',
    },
  ]

  if (authStore.isAuditor) {
    options.push({
      label: '管理后台',
      key: 'admin',
      icon: () => h(NIcon, null, { default: () => h(SettingsOutline) }),
    })
  }

    options.push({
      label: '修改密码',
      key: 'change-password',
    })

    options.push({
      label: '退出登录',
      key: 'logout',
      icon: () => h(NIcon, null, { default: () => h(LogOutOutline) }),
    })

  return options
})

const sortOptions = [
  { label: '最新上传', value: 'created_at' },
  { label: '最热门', value: 'views' },
  { label: '最近发布', value: 'published_at' },
]

const tagOptions = computed<SelectOption[]>(() =>
  popularTags.value.map((tag) => ({ label: tag.name, value: tag.name })),
)

const facetMap = computed(() =>
  Object.fromEntries(taxonomyFacets.value.map((facet) => [facet.key, facet])),
)

const activeFilters = computed(() => {
  const filters = photoStore.filters
  const chips: Array<{ key: keyof PhotoFilters | 'search'; label: string; value: string }> = []
  const labelMap: Record<string, string> = {
    season: '季节',
    campus: '校区',
    building: '楼宇',
    gallery_series: '专题',
    gallery_year: '年份',
    photo_type: '照片类型',
    tag: '自由标签',
    search: '搜索',
  }

  ;(['season', 'campus', 'building', 'gallery_series', 'gallery_year', 'photo_type', 'tag'] as const).forEach((key) => {
    const value = filters[key]
    if (value) {
      chips.push({ key, label: labelMap[key], value })
    }
  })
  if (filters.search) {
    chips.push({ key: 'search', label: labelMap.search, value: filters.search })
  }
  return chips
})

const currentPhotoIndex = computed(() => {
  if (!selectedPhotoId.value) return -1
  return photoStore.photos.findIndex((photo) => photo.id === selectedPhotoId.value)
})

const hasPrevPhoto = computed(() => currentPhotoIndex.value > 0)
const hasNextPhoto = computed(() => currentPhotoIndex.value >= 0 && currentPhotoIndex.value < photoStore.photos.length - 1)

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

function getImageUrl(photo: Photo) {
  return getPhotoUrl(photo.id, 'thumbnail')
}

function getThumbnailUrl(photo: Photo) {
  return getPhotoUrl(photo.id, 'thumbnail')
}

function handleImageError(event: Event, photo: Photo) {
  const img = event.target as HTMLImageElement
  if (img.getAttribute('data-tried-thumb') === 'true') {
    img.src =
      'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect fill="%23f0f0f0" width="200" height="200"/%3E%3Ctext fill="%23999" x="50%25" y="50%25" text-anchor="middle" dy=".3em"%3E图片加载失败%3C/text%3E%3C/svg%3E'
    return
  }
  img.setAttribute('data-tried-thumb', 'true')
  img.src = getThumbnailUrl(photo)
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
  if (filters.sortOrder) query.sort_order = filters.sortOrder
  if (photoStore.currentPage > 1) query.page = String(photoStore.currentPage)
  if (photoStore.pageSize !== 20) query.page_size = String(photoStore.pageSize)
  if (selectedPhotoId.value) query.photo = selectedPhotoId.value
  return query
}

function applyRouteQuery() {
  syncingRoute.value = true
  const query = route.query
  searchKeyword.value = typeof query.search === 'string' ? query.search : ''
  photoStore.filters.season = typeof query.season === 'string' ? query.season : null
  photoStore.filters.campus = typeof query.campus === 'string' ? query.campus : null
  photoStore.filters.building = typeof query.building === 'string' ? query.building : null
  photoStore.filters.gallery_series = typeof query.gallery_series === 'string' ? query.gallery_series : null
  photoStore.filters.gallery_year = typeof query.gallery_year === 'string' ? query.gallery_year : null
  photoStore.filters.photo_type = typeof query.photo_type === 'string' ? query.photo_type : null
  photoStore.filters.tag = typeof query.tag === 'string' ? query.tag : null
  photoStore.filters.search = searchKeyword.value
  photoStore.filters.sortBy = typeof query.sort_by === 'string' ? query.sort_by : 'created_at'
  photoStore.filters.sortOrder = typeof query.sort_order === 'string' ? query.sort_order : 'desc'
  photoStore.currentPage = query.page ? Number(query.page) || 1 : 1
  photoStore.pageSize = query.page_size ? Number(query.page_size) || 20 : 20
  selectedPhotoId.value = typeof query.photo === 'string' ? query.photo : null
  showPhotoDetail.value = !!selectedPhotoId.value
  syncingRoute.value = false
}

async function syncQueryAndFetch() {
  const nextQuery = buildQuery()
  syncingRoute.value = true
  await router.replace({ path: '/', query: nextQuery })
  syncingRoute.value = false
  await photoStore.fetchPublicPhotos()
}

const handleSearch = useDebounceFn(async (value: string) => {
  if (!value.trim()) {
    currentInterpretation.value = null
    photoStore.setFilters({ search: '' })
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
      if (result.keywords.length > 0) {
        filters.search = result.keywords.join(' ')
      } else {
        filters.search = ''
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

function handleSmartToggle(enabled: boolean) {
  smartSearchEnabled.value = enabled
  localStorage.setItem('smart_search_enabled', enabled ? 'true' : 'false')
  if (searchKeyword.value.trim()) {
    handleSearch(searchKeyword.value)
  }
}

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

async function handleFilterChange() {
  await syncQueryAndFetch()
}

async function handleClearFilters() {
  searchKeyword.value = ''
  currentInterpretation.value = null
  photoStore.clearFilters()
  selectedPhotoId.value = null
  showPhotoDetail.value = false
  await syncQueryAndFetch()
}

async function removeFilter(key: keyof PhotoFilters | 'search') {
  if (key === 'search') {
    searchKeyword.value = ''
    photoStore.setFilters({ search: '' })
  } else {
    photoStore.setFilters({ [key]: null } as Partial<PhotoFilters>)
  }
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

function handleMenuSelect(key: string) {
  activeMenu.value = key
}

function handleUserMenuSelect(key: string) {
  if (key === 'admin') {
    router.push('/admin')
    return
  }
  if (key === 'submissions') {
    router.push('/my-submissions')
    return
  }
  if (key === 'change-password') {
    showChangePassword.value = true
    return
  }
  if (key === 'logout') {
    dialog.warning({
      title: '确认退出',
      content: '确定要退出登录吗？',
      positiveText: '确定',
      negativeText: '取消',
      onPositiveClick: () => {
        authStore.logout()
        message.success('已退出登录')
        router.push('/login')
      },
    })
  }
}

async function handlePhotoClick(photo: Photo) {
  selectedPhotoId.value = photo.id
  showPhotoDetail.value = true
  syncingRoute.value = true
  await router.replace({ path: '/', query: buildQuery() })
  syncingRoute.value = false
}

async function handlePrevPhoto() {
  if (!hasPrevPhoto.value) return
  selectedPhotoId.value = photoStore.photos[currentPhotoIndex.value - 1].id
  syncingRoute.value = true
  await router.replace({ path: '/', query: buildQuery() })
  syncingRoute.value = false
}

async function handleNextPhoto() {
  if (!hasNextPhoto.value) return
  selectedPhotoId.value = photoStore.photos[currentPhotoIndex.value + 1].id
  syncingRoute.value = true
  await router.replace({ path: '/', query: buildQuery() })
  syncingRoute.value = false
}

async function handlePhotoDeleted() {
  message.success('照片已删除')
  showPhotoDetail.value = false
  selectedPhotoId.value = null
  await syncQueryAndFetch()
}

async function handlePhotoUpdated() {
  await photoStore.fetchPublicPhotos()
}

async function handleTagClick(tagName: string) {
  photoStore.setFilters({ tag: tagName })
  await syncQueryAndFetch()
}

async function loadPopularTags() {
  loadingTags.value = true
  try {
    popularTags.value = (await getPopularTags(50)) as unknown as Tag[]
  } catch (error) {
    console.error('加载标签失败:', error)
  } finally {
    loadingTags.value = false
  }
}

async function loadTaxonomy() {
  try {
    taxonomyFacets.value = await getPublicTaxonomy()
  } catch (error) {
    console.error('加载 taxonomy 失败:', error)
  }
}

watch(
  () => route.query,
  async () => {
    if (syncingRoute.value) return
    applyRouteQuery()
    await photoStore.fetchPublicPhotos()
  },
)

watch(showPhotoDetail, async (value) => {
  if (!value && selectedPhotoId.value) {
    selectedPhotoId.value = null
    syncingRoute.value = true
    await router.replace({ path: '/', query: buildQuery() })
    syncingRoute.value = false
  }
})

onMounted(async () => {
  const saved = localStorage.getItem('smart_search_enabled')
  smartSearchEnabled.value = saved !== 'false'

  applyRouteQuery()
  try {
    await Promise.all([
      photoStore.fetchPublicPhotos(),
      loadPopularTags(),
      loadTaxonomy(),
    ])
  } catch (error) {
    message.error('加载图库失败')
    console.error(error)
  }
})
</script>

<style scoped>
.gallery-container {
  height: 100vh;
}

.gallery-header {
  height: 64px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
}

.gallery-logo {
  height: 32px;
  width: auto;
  display: block;
}

.search-input {
  width: 320px;
  max-width: 100%;
}

.search-area {
  width: 360px;
  max-width: 100%;
}

.search-smart-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 0 0 4px;
}

.smart-label {
  font-size: 12px;
  transition: color 0.3s ease;
}

.smart-label.smart-active {
  color: #e60012;
  font-weight: 500;
}

.search-interpreting {
  border-color: rgba(230, 0, 18, 0.4) !important;
}

.search-pulse {
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
  padding: 2px 0 0 4px;
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

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filters-container {
  margin-bottom: 24px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 16px;
}

.photos-section {
  min-height: 400px;
}

.photo-card {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid #f0f0f0;
}

.photo-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.15);
}

.photo-image {
  position: relative;
  width: 100%;
  overflow: hidden;
  background: #f5f5f5;
}

.masonry-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.3s ease;
}

.photo-card:hover .photo-image img {
  transform: scale(1.05);
}

.photo-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.photo-card:hover .photo-overlay {
  opacity: 1;
}

.photo-info {
  padding: 12px;
}

.clickable-tag {
  cursor: pointer;
}

.pagination-container {
  margin-top: 32px;
  display: flex;
  justify-content: center;
}

.photo-count {
  font-size: 14px;
  white-space: nowrap;
}

.mobile-filter-toggle {
  display: none;
}

.filters-content {
  display: block;
  flex: 1;
}

.mobile-menu-btn {
  display: none;
}

@media (max-width: 768px) {
  .desktop-sider {
    display: none !important;
  }

  .mobile-menu-btn {
    display: inline-flex;
  }

  .gallery-header {
    height: auto;
    padding: 12px;
    flex-wrap: wrap;
    gap: 8px;
  }

  .header-left {
    width: 100%;
    flex-wrap: wrap;
    gap: 8px;
  }

  .gallery-logo {
    height: 24px;
  }
  }

  .search-input {
    width: 100%;
    order: 3;
  }

  .search-area {
    width: 100%;
    order: 3;
  }

  .header-right {
    flex-wrap: wrap;
    gap: 8px;
  }

  .mobile-filter-toggle {
    display: block;
    width: 100%;
    margin-bottom: 12px;
  }

  .filters-content {
    display: none;
    width: 100%;
  }

  .filters-content.filters-visible {
    display: block;
    margin-bottom: 12px;
  }

  .filters-container {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .photo-count {
    text-align: center;
    width: 100%;
  }

  .gallery-content {
    padding: 12px !important;
  }

  .pagination-container {
    margin-top: 16px;
  }

  .photo-info {
    padding: 8px;
  }
}
</style>
