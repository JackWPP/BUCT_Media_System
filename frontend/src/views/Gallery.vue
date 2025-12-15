<template>
  <div class="gallery-container">
    <n-layout has-sider>
      <!-- 侧边栏 -->
      <n-layout-sider
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

      <!-- 主内容区 -->
      <n-layout>
        <!-- 头部 -->
        <n-layout-header bordered class="gallery-header">
          <div class="header-left">
            <h2 class="header-title">BUCT Media HUB</h2>
            <n-input
              v-model:value="searchKeyword"
              placeholder="搜索照片..."
              clearable
              class="search-input"
              @update:value="handleSearch"
            >
              <template #prefix>
                <n-icon :component="SearchOutline" />
              </template>
            </n-input>
          </div>
          <div class="header-right">
            <n-badge :value="photoStore.total" :max="999" show-zero>
              <n-button tertiary circle>
                <template #icon>
                  <n-icon :component="ImagesOutline" />
                </template>
              </n-button>
            </n-badge>
            <!-- 只有登录用户才能上传 -->
            <n-button v-if="authStore.isAuthenticated" type="primary" @click="router.push('/upload')">
              <template #icon>
                <n-icon :component="CloudUploadOutline" />
              </template>
              上传照片
            </n-button>
            <!-- 未登录显示登录按钮，已登录显示用户菜单 -->
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

        <!-- 内容 -->
        <n-layout-content content-style="padding: 24px;">
          <!-- 筛选器 -->
          <div class="filters-container">
            <n-space>
              <n-select
                v-model:value="photoStore.filters.season"
                placeholder="选择季节"
                clearable
                style="width: 150px;"
                :options="seasonOptions"
                @update:value="handleFilterChange"
              />
              <n-select
                v-model:value="photoStore.filters.category"
                placeholder="选择类别"
                clearable
                style="width: 150px;"
                :options="categoryOptions"
                @update:value="handleFilterChange"
              />
              <n-select
                v-model:value="photoStore.filters.tag"
                placeholder="按标签筛选"
                clearable
                filterable
                style="width: 180px;"
                :options="tagOptions"
                :loading="loadingTags"
                @update:value="handleFilterChange"
              />
              <n-button @click="handleClearFilters" secondary>
                <template #icon>
                  <n-icon :component="RefreshOutline" />
                </template>
                清除筛选
              </n-button>
            </n-space>
            <n-text depth="3" style="font-size: 14px;">
              共 {{ photoStore.total }} 张照片
            </n-text>
          </div>

          <!-- 照片网格 -->
          <div class="photos-section">
            <n-spin :show="photoStore.loading">
              <!-- 加载中显示骨架屏 -->
              <n-grid v-if="photoStore.loading" :cols="gridCols" :x-gap="16" :y-gap="16" responsive="screen">
                <n-grid-item v-for="i in 12" :key="i">
                  <PhotoCardSkeleton />
                </n-grid-item>
              </n-grid>
              <!-- 空状态 -->
              <EmptyState
                v-else-if="photoStore.photos.length === 0"
                description="暂无照片"
                :icon="ImagesOutline"
                action
                action-text="上传照片"
                @action="router.push('/upload')"
              />
              <!-- 照片列表 -->
              <MasonryLayout
                v-else
                :items="photoStore.photos"
                :gap="16"
              >
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
                      <n-space size="small" style="margin-top: 8px;" wrap>
                        <n-tag v-if="photo.season" size="small" type="success">
                          {{ SEASON_MAP[photo.season] || photo.season }}
                        </n-tag>
                        <n-tag v-if="photo.category" size="small" type="info">
                          {{ CATEGORY_MAP[photo.category] || photo.category }}
                        </n-tag>
                        <n-tag 
                          v-for="tag in photo.tags?.slice(0, 3)" 
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

          <!-- 分页 -->
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

    <!-- 照片详情模态框 -->
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h, computed } from 'vue'
import { useRouter } from 'vue-router'
import { NIcon, useMessage, useDialog } from 'naive-ui'
import { SearchOutline, CloudUploadOutline, PersonOutline, ImagesOutline, LogOutOutline, EyeOutline, RefreshOutline, SettingsOutline } from '@vicons/ionicons5'
import { useAuthStore } from '../stores/auth'
import { usePhotoStore } from '../stores/photo'
import { useAppStore } from '../stores/app'
import { useDebounceFn } from '@vueuse/core'
import type { Photo } from '../types/photo'
import { getPopularTags, type Tag } from '../api/tag'
import PhotoDetail from '../components/photo/PhotoDetail.vue'
import EmptyState from '../components/common/EmptyState.vue'
import PhotoCardSkeleton from '../components/common/PhotoCardSkeleton.vue'
import MasonryLayout from '../components/common/MasonryLayout.vue'

const router = useRouter()
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

// 标签相关
const loadingTags = ref(false)
const popularTags = ref<Tag[]>([])

// 标签选项
const tagOptions = computed(() =>
  popularTags.value.map(tag => ({ label: tag.name, value: tag.name }))
)

// 菜单选项
const menuOptions = [
  {
    label: '全部照片',
    key: 'all',
    icon: () => h(NIcon, null, { default: () => h(ImagesOutline) }),
  },
]

// 用户菜单选项
const userMenuOptions = computed(() => {
  const options: any[] = [
    {
      label: `${authStore.user?.email || '用户'}`,
      key: 'user-info',
      disabled: true,
    },
    {
      type: 'divider',
      key: 'd1',
    },
  ]

  // 如果是管理员，添加管理后台入口
  if (authStore.user?.role === 'admin') {
    options.push({
      label: '管理后台',
      key: 'admin',
      icon: () => h(NIcon, null, { default: () => h(SettingsOutline) }),
    })
    options.push({
      type: 'divider',
      key: 'd2',
    })
  }

  options.push({
    label: '退出登录',
    key: 'logout',
    icon: () => h(NIcon, null, { default: () => h(LogOutOutline) }),
  })

  return options
})

// 季节选项
import { SEASON_OPTIONS, CATEGORY_OPTIONS, SEASON_MAP, CATEGORY_MAP } from '../constants/options'

const seasonOptions = SEASON_OPTIONS

// 类别选项
const categoryOptions = CATEGORY_OPTIONS

// 获取图片URL - 增强兼容性处理
function getImageUrl(photo: Photo) {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
  
  // 1. 尝试使用原图 (清晰度高)，但前提是路径必须安全 (在 uploads/ 下)
  let path = (photo.original_path || '').replace(/\\/g, '/')
  let isSafeOriginal = false
  
  const uploadsIndex = path.indexOf('uploads/')
  if (uploadsIndex !== -1) {
    path = path.substring(uploadsIndex)
    isSafeOriginal = true
  }
  
  // 2. 如果原图路径看似不安全 (例如旧数据的 F:/...), 则回退到缩略图
  if (!isSafeOriginal && photo.thumb_path) {
    path = photo.thumb_path.replace(/\\/g, '/')
    // 缩略图通常都在 uploads/ 下，但也做一下处理
    const thumbIndex = path.indexOf('uploads/')
    if (thumbIndex !== -1) {
      path = path.substring(thumbIndex)
    }
  }
  
  if (!path) return ''
  
  // 3. 构造最终 URL
  if (path.startsWith('http')) return path
  if (path.startsWith('/')) path = path.substring(1)
  
  return `${baseUrl}/${path}`
}

function getThumbnailUrl(photo: Photo) {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
  let path = (photo.thumb_path || '').replace(/\\/g, '/')
  const uploadsIndex = path.indexOf('uploads/')
  if (uploadsIndex !== -1) {
    path = path.substring(uploadsIndex)
  }
  if (path.startsWith('/')) path = path.substring(1)
  return path ? `${baseUrl}/${path}` : ''
}

// 图片加载错误处理
function handleImageError(e: Event, photo: Photo) {
  const img = e.target as HTMLImageElement
  
  const thumbUrl = getThumbnailUrl(photo)
  // 如果当前显示的不是缩略图，且缩略图存在，尝试降级
  // 注意：需要构建完整的URL进行比较，或者简单判断 src 是否包含 thumbUrl 的关键部分
  // 这里简化判断: 如果 src 已经是 data URL，或者已经是缩略图路径，则停止
  
  if (thumbUrl && !img.src.includes('data:image')) {
     // 检查是否已经是缩略图 (防止无限循环，尽管 getThumbnailUrl 返回的不同)
     // 简单起见，如果 load error 了，且之前尝试的是 getImageUrl 的结果(原图)，那么尝试缩略图
     // 但为了避免判断 src 的复杂性，我们只尝试一次降级
     // 更好的方式是设置一个属性标记
     
     if (img.getAttribute('data-tried-thumb') === 'true') {
        img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect fill="%23f0f0f0" width="200" height="200"/%3E%3Ctext fill="%23999" x="50%25" y="50%25" text-anchor="middle" dy=".3em"%3E图片加载失败%3C/text%3E%3C/svg%3E'
     } else {
        img.setAttribute('data-tried-thumb', 'true')
        img.src = thumbUrl
     }
  } else {
    img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect fill="%23f0f0f0" width="200" height="200"/%3E%3Ctext fill="%23999" x="50%25" y="50%25" text-anchor="middle" dy=".3em"%3E图片加载失败%3C/text%3E%3C/svg%3E'
  }
}

// 防抖搜索
const handleSearch = useDebounceFn((value: string) => {
  photoStore.setFilters({ search: value })
  photoStore.fetchPhotos()
}, 500)

// 筛选变更
function handleFilterChange() {
  photoStore.fetchPublicPhotos()
}

// 清除筛选
function handleClearFilters() {
  searchKeyword.value = ''
  photoStore.clearFilters()
  photoStore.fetchPublicPhotos()
}

// 分页变更
function handlePageChange(page: number) {
  photoStore.setPage(page)
  photoStore.fetchPublicPhotos()
}

// 分页大小变更
function handlePageSizeChange(pageSize: number) {
  photoStore.pageSize = pageSize
  photoStore.setPage(1)
  photoStore.fetchPublicPhotos()
}

// 菜单选择
function handleMenuSelect(key: string) {
  activeMenu.value = key
}

// 用户菜单选择
function handleUserMenuSelect(key: string) {
  if (key === 'admin') {
    router.push('/admin')
  } else if (key === 'logout') {
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

// 照片点击
function handlePhotoClick(photo: Photo) {
  selectedPhotoId.value = photo.id
  showPhotoDetail.value = true
}

// 导航逻辑
const currentPhotoIndex = computed(() => {
  if (!selectedPhotoId.value) return -1
  return photoStore.photos.findIndex(p => p.id === selectedPhotoId.value)
})

const hasPrevPhoto = computed(() => currentPhotoIndex.value > 0)
const hasNextPhoto = computed(() => currentPhotoIndex.value !== -1 && currentPhotoIndex.value < photoStore.photos.length - 1)

function handlePrevPhoto() {
  if (hasPrevPhoto.value) {
    const prevPhoto = photoStore.photos[currentPhotoIndex.value - 1]
    selectedPhotoId.value = prevPhoto.id
  }
}

function handleNextPhoto() {
  if (hasNextPhoto.value) {
    const nextPhoto = photoStore.photos[currentPhotoIndex.value + 1]
    selectedPhotoId.value = nextPhoto.id
  }
}

// 照片删除后
function handlePhotoDeleted() {
  message.success('照片已删除')
  showPhotoDetail.value = false
  photoStore.fetchPublicPhotos()
}

// 照片更新后
function handlePhotoUpdated() {
  photoStore.fetchPublicPhotos()
}

// 点击标签进行筛选
function handleTagClick(tagName: string) {
  photoStore.setFilters({ tag: tagName })
  photoStore.fetchPublicPhotos()
}

// 加载热门标签
async function loadPopularTags() {
  loadingTags.value = true
  try {
    popularTags.value = await getPopularTags(50) as unknown as Tag[]
  } catch (error) {
    console.error('加载标签失败:', error)
  } finally {
    loadingTags.value = false
  }
}

// 加载照片
onMounted(() => {
  photoStore.fetchPublicPhotos().catch((error) => {
    message.error('加载照片失败')
    console.error(error)
  })
  loadPopularTags()
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

.header-title {
  margin: 0;
  white-space: nowrap;
}

.search-input {
  width: 300px;
  max-width: 100%;
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
  align-items: center;
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

/* Remove old absolute positioning if any */
.photo-image img {
  /* Inherit transition from masonry-img or keep here if not using class everywhere */
  transition: transform 0.3s ease;
}

.photo-card:hover .photo-image img {
  transform: scale(1.05);
}

.photo-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
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

.photo-name {
  font-weight: 500;
  font-size: 14px;
}

.clickable-tag {
  cursor: pointer;
  transition: all 0.2s ease;
}

.clickable-tag:hover {
  transform: scale(1.05);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.pagination-container {
  margin-top: 32px;
  display: flex;
  justify-content: center;
}

@media (max-width: 768px) {
  .header-left {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .search-input {
    width: 100%;
  }
  
  .filters-container {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
