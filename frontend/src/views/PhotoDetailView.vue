<template>
  <div class="photo-detail-view">
    <n-spin :show="loading">
      <div v-if="photo" class="detail-main">
        <!-- 左侧：图片展示区 -->
        <div class="detail-image-section" @click.self="handleClose">
          <!-- 顶部悬浮工具栏 -->
          <div class="viewer-toolbar">
            <n-button
              quaternary
              circle
              class="toolbar-btn close-btn"
              @click="handleClose"
            >
              <template #icon>
                <n-icon size="22" :component="CloseOutline" />
              </template>
            </n-button>
            <div class="toolbar-center">
              <span class="photo-counter" v-if="contextPhotos.length > 0">
                {{ currentIndex + 1 }} / {{ contextPhotos.length }}
              </span>
            </div>
            <n-button-group class="toolbar-right">
              <n-button
                quaternary
                circle
                class="toolbar-btn"
                :disabled="!hasPrev"
                @click="goPrev"
              >
                <template #icon>
                  <n-icon size="18" :component="ChevronBackOutline" />
                </template>
              </n-button>
              <n-button
                quaternary
                circle
                class="toolbar-btn"
                :disabled="!hasNext"
                @click="goNext"
              >
                <template #icon>
                  <n-icon size="18" :component="ChevronForwardOutline" />
                </template>
              </n-button>
            </n-button-group>
          </div>

          <!-- 图片容器 -->
          <div
            class="image-stage"
            :class="{ 'zoom-mode': zoomMode }"
            @wheel.prevent="handleWheel"
            @mousedown="handleMouseDown"
            @mousemove="handleMouseMove"
            @mouseup="handleMouseUp"
            @mouseleave="handleMouseUp"
            @touchstart.passive="handleTouchStart"
            @touchmove.passive="handleTouchMove"
            @touchend="handleTouchEnd"
            @dblclick="toggleZoom"
          >
            <!-- 渐进式图片加载：缩略图底图 + 高清图叠加 -->
            <img
              v-if="photo"
              :key="'thumb-' + photo.id + '-' + imageKey"
              :src="getPhotoUrl(photo.id, showOriginal ? 'thumbnail' : 'thumbnail')"
              :alt="photo.filename"
              class="stage-image stage-thumb"
              :style="zoomStyle"
            />
            <transition name="fade-img">
              <img
                v-if="photo && hdReady"
                :key="'hd-' + photo.id + '-' + imageKey"
                :src="hdSrc"
                :alt="photo.filename"
                class="stage-image stage-hd"
                :style="zoomStyle"
                @error="handleHdError"
              />
            </transition>
            <!-- 缩放提示 -->
            <div v-if="zoomMode" class="zoom-hint">
              {{ (scale * 100).toFixed(0) }}% · {{ isTouchDevice ? '双指缩放 · 单指拖动 · 双击退出' : '滚轮缩放 · 拖拽平移 · 点击退出' }}
            </div>
          </div>

          <!-- 左右切换大箭头（缩放模式隐藏） -->
          <div
            v-if="hasPrev && !zoomMode"
            class="stage-arrow stage-prev"
            @click="goPrev"
          >
            <n-icon size="32" color="white" :component="ChevronBackOutline" />
          </div>
          <div
            v-if="hasNext && !zoomMode"
            class="stage-arrow stage-next"
            @click="goNext"
          >
            <n-icon size="32" color="white" :component="ChevronForwardOutline" />
          </div>

          <!-- 底部操作栏 -->
          <div class="stage-bottom-bar">
            <n-button-group>
              <n-button tertiary size="small" @click="downloadImage">
                <template #icon>
                  <n-icon :component="DownloadOutline" />
                </template>
                下载
              </n-button>
              <n-button
                tertiary
                size="small"
                :loading="loadingOriginal"
                @click="loadOriginal"
              >
                <template #icon>
                  <n-icon :component="showOriginal ? ExpandOutline : ExpandOutline" />
                </template>
                {{ showOriginal ? '查看压缩图' : '查看原图' }}
              </n-button>
              <n-button tertiary size="small" @click="shareImage">
                <template #icon>
                  <n-icon :component="ShareSocialOutline" />
                </template>
                分享
              </n-button>
            </n-button-group>
          </div>
        </div>

        <!-- 右侧：信息面板 -->
        <div class="detail-info-section">
          <div class="info-panel">
            <!-- 摄影师信息 -->
            <div class="photographer-card">
              <div class="photographer-avatar">
                <n-icon size="36" :component="PersonCircleOutline" />
              </div>
              <div class="photographer-info">
                <div class="photographer-name">{{ photo.uploader_name || '未知摄影师' }}</div>
                <div class="photographer-id">ID: {{ photo.uploader_id.slice(0, 8) }}</div>
              </div>
              <n-button
                type="primary"
                size="small"
                class="follow-btn"
                disabled
              >
                + 关注
              </n-button>
            </div>

            <!-- 操作按钮 -->
            <div class="action-buttons">
              <n-button type="primary" size="large" block class="action-btn-primary">
                <template #icon>
                  <n-icon :component="HeartOutline" />
                </template>
                加入收藏
              </n-button>
              <n-button size="large" block class="action-btn-secondary" @click="downloadImage">
                <template #icon>
                  <n-icon :component="DownloadOutline" />
                </template>
                下载图片
              </n-button>
            </div>

            <!-- 图片信息 -->
            <div class="meta-section">
              <h3 class="meta-title">图片信息</h3>
              <div class="meta-list">
                <div v-if="photo.width && photo.height" class="meta-item">
                  <span class="meta-label">尺寸</span>
                  <span class="meta-value">{{ photo.width }} x {{ photo.height }} px</span>
                </div>
                <div class="meta-item">
                  <span class="meta-label">大小</span>
                  <span class="meta-value">{{ formatFileSize(photo.file_size) }}</span>
                </div>
                <div class="meta-item">
                  <span class="meta-label">格式</span>
                  <span class="meta-value">{{ photo.mime_type?.split('/')[1]?.toUpperCase() || 'JPG' }}</span>
                </div>
                <div class="meta-item">
                  <span class="meta-label">上传时间</span>
                  <span class="meta-value">{{ formatDate(photo.created_at) }}</span>
                </div>
                <div v-if="photo.captured_at" class="meta-item">
                  <span class="meta-label">拍摄时间</span>
                  <span class="meta-value">{{ formatDate(photo.captured_at) }}</span>
                </div>
              </div>
            </div>

            <!-- 分类标签 -->
            <div v-if="photo.classifications && Object.keys(photo.classifications).length" class="meta-section">
              <h3 class="meta-title">分类</h3>
              <div class="class-tags">
                <span
                  v-for="cls in Object.values(photo.classifications)"
                  :key="cls.node_id"
                  class="class-tag"
                >
                  {{ cls.facet_name }}: {{ cls.node_name }}
                </span>
              </div>
            </div>

            <!-- 描述 -->
            <div v-if="photo.description" class="meta-section">
              <h3 class="meta-title">描述</h3>
              <p class="photo-description">{{ photo.description }}</p>
            </div>
          </div>
        </div>
      </div>
    </n-spin>

    <!-- 关键词区域 -->
    <div v-if="photo && allTags.length" class="detail-keywords">
      <div class="keywords-container">
        <h3 class="section-title">关键词</h3>
        <div class="keywords-list">
          <span
            v-for="tag in allTags"
            :key="tag"
            class="keyword-tag"
            @click="handleKeywordClick(tag)"
          >
            {{ tag }}
          </span>
        </div>
      </div>
    </div>

    <!-- 推荐图片 -->
    <div v-if="relatedPhotos.length" class="detail-related">
      <div class="related-container">
        <h3 class="section-title">相关推荐</h3>
        <div class="related-grid">
          <div
            v-for="rp in relatedPhotos"
            :key="rp.id"
            class="related-item"
            @click="goToPhoto(rp.id)"
          >
            <img
              :src="getThumbnailUrl(rp)"
              :alt="rp.filename"
              loading="lazy"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import {
  ChevronBackOutline,
  ChevronForwardOutline,
  CloseOutline,
  DownloadOutline,
  ExpandOutline,
  HeartOutline,
  PersonCircleOutline,
  ShareSocialOutline,
} from '@vicons/ionicons5'
import dayjs from 'dayjs'
import { getPublicPhotos } from '../api/photo'
import { incrementView } from '../api/stats'
import { usePhotoStore } from '../stores/photo'
import type { Photo } from '../types/photo'
import { getPhotoUrl, getPhotoDownloadUrl } from '../utils/format'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const photoStore = usePhotoStore()

const loading = ref(false)
const photo = ref<Photo | null>(null)
const relatedPhotos = ref<Photo[]>([])
const showOriginal = ref(false)
const loadingOriginal = ref(false)
const imageKey = ref(0)

// 渐进式加载：缩略图立即显示，高清图后台预加载
const hdReady = ref(false)
const hdSrc = ref('')

function preloadHd() {
  if (!photo.value) return
  hdReady.value = false
  const type = showOriginal.value ? 'original' : 'compressed'
  const url = getPhotoUrl(photo.value.id, type)
  hdSrc.value = url
  const img = new Image()
  img.onload = () => { hdReady.value = true }
  img.onerror = () => {
    // 高清图加载失败，尝试回退到缩略图（不覆盖，缩略图已在底层）
    console.warn('HD image load failed, thumbnail still visible')
  }
  img.src = url
}

// 独立维护上下文图片列表，不依赖 photoStore（避免与 HomeView 缓存冲突）
const contextPhotos = ref<Photo[]>([])

// 图片缩放状态
const zoomMode = ref(false)
const scale = ref(1)
const translateX = ref(0)
const translateY = ref(0)
const isDragging = ref(false)
const dragStartX = ref(0)
const dragStartY = ref(0)
const dragStartTranslateX = ref(0)
const dragStartTranslateY = ref(0)

const zoomStyle = computed(() => {
  if (!zoomMode.value) return {}
  return {
    transform: `translate(${translateX.value}px, ${translateY.value}px) scale(${scale.value})`,
    cursor: isDragging.value ? 'grabbing' : 'grab',
    transition: isDragging.value ? 'none' : 'transform 0.2s ease',
  }
})

const currentIndex = computed(() => {
  if (!photo.value) return -1
  return contextPhotos.value.findIndex((p) => p.id === photo.value!.id)
})

const hasPrev = computed(() => currentIndex.value > 0)
const hasNext = computed(() => currentIndex.value >= 0 && currentIndex.value < contextPhotos.value.length - 1)

const allTags = computed(() => {
  if (!photo.value) return []
  const tags = new Set<string>()
  photo.value.tags?.forEach((t) => tags.add(t))
  photo.value.free_tags?.forEach((t) => tags.add(t))
  return Array.from(tags)
})

function loadOriginal() {
  showOriginal.value = !showOriginal.value
  imageKey.value++  // 强制重新加载
  loadingOriginal.value = false
  preloadHd()  // 重新预加载高清图
}

function getThumbnailUrl(currentPhoto: Photo) {
  return getPhotoUrl(currentPhoto.id, 'thumbnail')
}

function handleHdError(event: Event) {
  // 高清图加载失败，缩略图仍在底层显示，无需额外处理
  console.warn('HD image error')
  hdReady.value = false
}

function formatFileSize(bytes: number | null): string {
  if (!bytes) return '未知'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  return `${size.toFixed(2)} ${units[unitIndex]}`
}

function formatDate(dateString: string | null): string {
  return dateString ? dayjs(dateString).format('YYYY-MM-DD HH:mm:ss') : '未知'
}

function getStatusType(status: string): 'success' | 'warning' | 'error' | 'info' {
  const map: Record<string, 'success' | 'warning' | 'error' | 'info'> = {
    approved: 'success',
    pending: 'warning',
    rejected: 'error',
  }
  return map[status] || 'info'
}

function getStatusText(status: string): string {
  const map: Record<string, string> = {
    approved: '已上线',
    pending: '待审核',
    rejected: '已拒绝',
  }
  return map[status] || status
}

function handleClose() {
  router.push('/gallery')
}

function toggleZoom(event?: MouseEvent) {
  // 触摸设备用双击，不响应单击
  if (event && isTouchDevice.value) return
  if (zoomMode.value) {
    zoomMode.value = false
    scale.value = 1
    translateX.value = 0
    translateY.value = 0
  } else {
    zoomMode.value = true
    scale.value = 2
  }
}

function handleWheel(event: WheelEvent) {
  if (!zoomMode.value) return
  const delta = event.deltaY > 0 ? -0.15 : 0.15
  scale.value = Math.max(1, Math.min(5, scale.value + delta))
  if (scale.value <= 1) {
    zoomMode.value = false
    translateX.value = 0
    translateY.value = 0
  }
}

function handleMouseDown(event: MouseEvent) {
  if (!zoomMode.value) return
  isDragging.value = true
  dragStartX.value = event.clientX
  dragStartY.value = event.clientY
  dragStartTranslateX.value = translateX.value
  dragStartTranslateY.value = translateY.value
}

function handleMouseMove(event: MouseEvent) {
  if (!isDragging.value || !zoomMode.value) return
  const dx = event.clientX - dragStartX.value
  const dy = event.clientY - dragStartY.value
  translateX.value = dragStartTranslateX.value + dx
  translateY.value = dragStartTranslateY.value + dy
}

function handleMouseUp() {
  isDragging.value = false
}

// ===== 触摸手势支持 =====
const isTouchDevice = ref(false)
const touchStartDistance = ref(0)
const touchStartScale = ref(1)
const touchStartX = ref(0)
const touchStartY = ref(0)
const touchStartTranslateX = ref(0)
const touchStartTranslateY = ref(0)
const lastTapTime = ref(0)

function getTouchDistance(t1: Touch, t2: Touch) {
  return Math.hypot(t1.clientX - t2.clientX, t1.clientY - t2.clientY)
}

function handleTouchStart(event: TouchEvent) {
  isTouchDevice.value = true
  const touches = event.touches

  if (touches.length === 2) {
    // 双指开始：记录初始距离和缩放
    touchStartDistance.value = getTouchDistance(touches[0], touches[1])
    touchStartScale.value = scale.value
    if (!zoomMode.value) {
      zoomMode.value = true
      scale.value = 1.5
      touchStartScale.value = 1.5
    }
  } else if (touches.length === 1) {
    // 单指开始
    if (zoomMode.value) {
      // 缩放模式下：拖拽
      isDragging.value = true
      dragStartX.value = touches[0].clientX
      dragStartY.value = touches[0].clientY
      dragStartTranslateX.value = translateX.value
      dragStartTranslateY.value = translateY.value
    } else {
      // 非缩放模式：记录滑动起点
      touchStartX.value = touches[0].clientX
      touchStartY.value = touches[0].clientY
      touchStartTranslateX.value = translateX.value
      touchStartTranslateY.value = translateY.value
    }
  }
}

function handleTouchMove(event: TouchEvent) {
  const touches = event.touches

  if (touches.length === 2) {
    // 双指缩放
    const currentDistance = getTouchDistance(touches[0], touches[1])
    const ratio = currentDistance / touchStartDistance.value
    scale.value = Math.max(1, Math.min(5, touchStartScale.value * ratio))
  } else if (touches.length === 1 && zoomMode.value && isDragging.value) {
    // 缩放模式下单指拖拽
    const dx = touches[0].clientX - dragStartX.value
    const dy = touches[0].clientY - dragStartY.value
    translateX.value = dragStartTranslateX.value + dx
    translateY.value = dragStartTranslateY.value + dy
  }
}

function handleTouchEnd(event: TouchEvent) {
  if (event.touches.length === 0) {
    isDragging.value = false

    if (!zoomMode.value) {
      // 非缩放模式下检测左右滑动
      const dx = touchStartX.value - (event.changedTouches[0]?.clientX ?? 0)
      const dy = touchStartY.value - (event.changedTouches[0]?.clientY ?? 0)

      // 水平滑动 > 50px 且大于垂直滑动
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) {
        if (dx > 0 && hasNext.value) {
          goNext()
        } else if (dx < 0 && hasPrev.value) {
          goPrev()
        }
      }
    }

    // 缩放倍率 ≤1 时退出缩放
    if (zoomMode.value && scale.value <= 1.05) {
      zoomMode.value = false
      scale.value = 1
      translateX.value = 0
      translateY.value = 0
    }
  }
}

// 双击切换缩放
function handleDoubleClick() {
  const now = Date.now()
  if (now - lastTapTime.value < 300) {
    toggleZoom()
  }
  lastTapTime.value = now
}

function goPrev() {
  if (!hasPrev.value) return
  const prev = contextPhotos.value[currentIndex.value - 1]
  router.push(`/photo/${prev.id}`)
}

function goNext() {
  if (!hasNext.value) return
  const next = contextPhotos.value[currentIndex.value + 1]
  router.push(`/photo/${next.id}`)
}

function goToPhoto(id: string) {
  router.push(`/photo/${id}`)
}

function handleKeywordClick(tag: string) {
  router.push({ path: '/gallery', query: { search: tag } })
}

function downloadImage() {
  if (!photo.value) return
  window.open(getPhotoDownloadUrl(photo.value.id), '_blank')
}

async function shareImage() {
  if (!photo.value) return
  const shareUrl = `${window.location.origin}/photo/${photo.value.id}`
  try {
    await navigator.clipboard.writeText(shareUrl)
    message.success('链接已复制')
  } catch {
    message.error('复制失败')
  }
}

function preloadAdjacent() {
  // 预加载前后图片的压缩版本
  if (!contextPhotos.value.length) return
  const idx = currentIndex.value
  if (idx > 0) {
    const prevImg = new Image()
    prevImg.src = getPhotoUrl(contextPhotos.value[idx - 1].id, 'compressed')
  }
  if (idx < contextPhotos.value.length - 1) {
    const nextImg = new Image()
    nextImg.src = getPhotoUrl(contextPhotos.value[idx + 1].id, 'compressed')
  }
}

async function loadContextPhotos() {
  // 优先从 photoStore 复用（如果从 Gallery 跳转过来）
  if (photoStore.photos.length > 0) {
    contextPhotos.value = [...photoStore.photos]
    return
  }
  // 否则通过 API 加载当前页数据
  try {
    const response = await getPublicPhotos({ limit: 100, sort_by: 'created_at' })
    contextPhotos.value = response.items
  } catch {
    contextPhotos.value = []
  }
}

async function loadPhotoDetail(id: string) {
  loading.value = true
  showOriginal.value = false
  loadingOriginal.value = false
  imageKey.value = 0
  photo.value = null
  hdReady.value = false  // 重置高清图状态
  try {
    // 先确保上下文图片列表已加载
    if (contextPhotos.value.length === 0) {
      await loadContextPhotos()
    }
    photo.value = await photoStore.fetchPublicPhotoDetail(id)
    // 上报浏览量
    incrementView(id).catch(() => {})
    // 推荐图片从上下文列表中过滤
    relatedPhotos.value = contextPhotos.value
      .filter((p) => p.id !== id)
      .slice(0, 8)
    preloadAdjacent()
    preloadHd()  // 后台预加载高清图
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '加载照片详情失败')
    photo.value = null
  } finally {
    loading.value = false
  }
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'ArrowLeft' && hasPrev.value && !zoomMode.value) goPrev()
  if (event.key === 'ArrowRight' && hasNext.value && !zoomMode.value) goNext()
  if (event.key === 'Escape') {
    if (zoomMode.value) {
      zoomMode.value = false
      scale.value = 1
      translateX.value = 0
      translateY.value = 0
    } else {
      handleClose()
    }
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  const id = route.params.id as string
  if (id) loadPhotoDetail(id)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})

watch(
  () => route.params.id,
  (newId) => {
    if (newId && typeof newId === 'string') {
      loadPhotoDetail(newId)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  },
)
</script>

<style scoped>
.photo-detail-view {
  min-height: 100vh;
  /* padding-top 由 PublicLayout 的 .public-main 提供，不重复设置 */
  background: #fff;
}

/* ===== 主体内容 ===== */
.detail-main {
  display: flex;
  min-height: calc(100vh - 56px);
}

/* ===== 左侧图片区 ===== */
.detail-image-section {
  flex: 1;
  background: #0f0f0f;
  position: relative;
  height: calc(100vh - 56px);
  overflow: hidden;
  cursor: zoom-out;
}

/* 顶部悬浮工具栏 */
.viewer-toolbar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
}

.toolbar-btn {
  color: rgba(255, 255, 255, 0.85) !important;
  background: rgba(255, 255, 255, 0.1) !important;
  transition: all 0.2s;
}

.toolbar-btn:hover {
  background: rgba(255, 255, 255, 0.2) !important;
  color: white !important;
}

.close-btn:hover {
  background: rgba(230, 0, 18, 0.8) !important;
}

.toolbar-center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}

.photo-counter {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  letter-spacing: 1px;
}

.toolbar-right {
  display: flex;
  gap: 4px;
}

/* 图片舞台 */
.image-stage {
  position: absolute;
  inset: 48px 0 48px 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-stage.zoom-mode {
  cursor: grab;
}

.image-stage.zoom-mode:active {
  cursor: grabbing;
}

.stage-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  display: block;
}

/* 缩略图底层 */
.stage-thumb {
  position: relative;
  z-index: 1;
  filter: blur(0);
  transition: filter 0.3s ease;
}

/* 高清图叠加层 */
.stage-hd {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  margin: auto;
  z-index: 2;
}

/* 高清图淡入动画 */
.fade-img-enter-active {
  transition: opacity 0.4s ease;
}
.fade-img-enter-from {
  opacity: 0;
}
.fade-img-enter-to {
  opacity: 1;
}

.image-stage.zoom-mode .stage-image {
  max-width: none;
  max-height: none;
  object-fit: none;
}

.zoom-hint {
  position: absolute;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  background: rgba(0, 0, 0, 0.5);
  padding: 6px 14px;
  border-radius: 20px;
  pointer-events: none;
  white-space: nowrap;
  transition: opacity 0.3s;
}

/* 左右切换大箭头 */
.stage-arrow {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.25s ease;
  z-index: 15;
  opacity: 0.5;
}

.stage-arrow:hover {
  background: rgba(255, 255, 255, 0.2);
  opacity: 1;
}

.stage-prev {
  left: 16px;
}

.stage-next {
  right: 16px;
}

/* 底部操作栏 */
.stage-bottom-bar {
  position: absolute;
  bottom: 12px;
  right: 16px;
  z-index: 15;
  opacity: 0.6;
  transition: opacity 0.2s;
}

.detail-image-section:hover .stage-bottom-bar {
  opacity: 1;
}

/* ===== 右侧信息面板 ===== */
.detail-info-section {
  width: 360px;
  flex-shrink: 0;
  background: #fff;
  border-left: 1px solid #f0f0f0;
  overflow-y: auto;
  max-height: calc(100vh - 56px);
}

.info-panel {
  padding: 20px;
}

/* 摄影师卡片 */
.photographer-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 16px;
}

.photographer-avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
}

.photographer-info {
  flex: 1;
}

.photographer-name {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.photographer-id {
  font-size: 12px;
  color: #999;
  margin-top: 2px;
}

.follow-btn {
  background: #e60012 !important;
  border-color: #e60012 !important;
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 20px;
}

.action-btn-primary {
  background: #e60012 !important;
  border-color: #e60012 !important;
}

.action-btn-secondary {
  border-color: #e0e0e0 !important;
}

/* 元信息区 */
.meta-section {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.meta-section:last-child {
  border-bottom: none;
}

.meta-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 10px;
}

.meta-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.meta-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.meta-label {
  color: #999;
}

.meta-value {
  color: #333;
  text-align: right;
}

/* 分类标签 */
.class-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.class-tag {
  font-size: 12px;
  color: #666;
  background: #f5f5f5;
  padding: 4px 10px;
  border-radius: 4px;
}

.photo-description {
  font-size: 13px;
  color: #666;
  line-height: 1.7;
}

/* ===== 关键词区域 ===== */
.detail-keywords {
  background: #fafafa;
  border-top: 1px solid #f0f0f0;
  padding: 28px 24px;
}

.keywords-container {
  max-width: 1440px;
  margin: 0 auto;
}

.keywords-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}

.keyword-tag {
  font-size: 13px;
  color: #666;
  background: #fff;
  border: 1px solid #e0e0e0;
  padding: 6px 14px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.keyword-tag:hover {
  color: #e60012;
  border-color: #e60012;
}

/* ===== 推荐图片 ===== */
.detail-related {
  padding: 28px 24px 64px;
  background: #fff;
}

.related-container {
  max-width: 1440px;
  margin: 0 auto;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.related-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-top: 14px;
}

.related-item {
  aspect-ratio: 4 / 3;
  border-radius: 4px;
  overflow: hidden;
  cursor: pointer;
  background: #f5f5f5;
}

.related-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s;
}

.related-item:hover img {
  transform: scale(1.05);
}

/* ===== 响应式 ===== */
@media (max-width: 1024px) {
  .detail-main {
    flex-direction: column;
  }

  .detail-image-section {
    height: 60vh;
  }

  .image-stage {
    inset: 44px 0 44px 0;
  }

  .detail-info-section {
    width: 100%;
    max-height: none;
    border-left: none;
    border-top: 1px solid #f0f0f0;
  }

  .stage-arrow {
    width: 44px;
    height: 44px;
  }

  .stage-prev {
    left: 8px;
  }

  .stage-next {
    right: 8px;
  }

  .related-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .viewer-toolbar {
    padding: 8px 10px;
  }

  .image-stage {
    inset: 40px 0 40px 0;
  }

  .info-panel {
    padding: 16px;
  }

  .related-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .detail-keywords,
  .detail-related {
    padding: 20px 12px;
  }
}
</style>
