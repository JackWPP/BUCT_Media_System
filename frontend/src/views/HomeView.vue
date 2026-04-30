<template>
  <div class="home-view">
    <!-- Hero 区域 -->
    <section class="hero-section">
      <div class="hero-bg">
        <!-- 底层：深蓝主色 -->
        <div class="hero-bg-layer"></div>
        <!-- 动态渐变网格 -->
        <div class="hero-grid-overlay"></div>
        <!-- 浮动光球 -->
        <div class="gradient-circle circle-1"></div>
        <div class="gradient-circle circle-2"></div>
        <div class="gradient-circle circle-3"></div>
        <div class="gradient-circle circle-4"></div>
        <!-- 顶部高光 -->
        <div class="hero-top-light"></div>
      </div>
      <div class="hero-content" :style="{ opacity: heroOpacity, transform: heroTranslate }">
        <h1 class="hero-slogan">视觉之美  触动世界</h1>
        <p class="hero-subtitle">探索北化校园精彩瞬间</p>

        <!-- 搜索框 -->
        <div class="hero-search">
          <div class="search-box">
            <div class="search-type">
              <span>图片</span>
              <n-icon :component="ChevronDownOutline" size="14" />
            </div>
            <div class="search-divider"></div>
            <input
              v-model="searchKeyword"
              type="text"
              class="search-input"
              :placeholder="smartSearchEnabled ? '试试自然语言搜索：秋天的图书馆、春天的樱花...' : '输入关键词搜索照片...'"
              @keyup.enter="handleSearch"
            />
            <n-button
              class="search-camera-btn"
              quaternary
              circle
              @click="handleSearch"
            >
              <template #icon>
                <n-icon :component="CameraOutline" size="20" />
              </template>
            </n-button>
            <n-button
              class="search-submit-btn"
              type="primary"
              @click="handleSearch"
            >
              <template #icon>
                <n-icon :component="SearchOutline" size="18" />
              </template>
            </n-button>
          </div>
          <div class="home-smart-toggle">
            <n-switch
              v-model:value="smartSearchEnabled"
              size="small"
              @update:value="handleSmartToggle"
            />
            <n-text depth="3" class="smart-label" :class="{ 'smart-active': smartSearchEnabled }">
              {{ smartSearchEnabled ? '✨ 智能搜索' : '普通搜索' }}
            </n-text>
          </div>
        </div>

        <!-- 热搜推荐 -->
        <div class="hot-tags">
          <span class="hot-label">图片热搜推荐</span>
          <div class="hot-tags-list">
            <span
              v-for="tag in hotTags"
              :key="tag"
              class="hot-tag"
              @click="handleTagClick(tag)"
            >
              {{ tag }}
            </span>
          </div>
        </div>
      </div>
    </section>

    <!-- 精选图片区域 -->
    <section class="featured-section">
      <div class="section-header">
        <h2 class="section-title">精选图片</h2>
        <n-button text type="primary" @click="router.push('/gallery')">
          查看更多
          <template #icon>
            <n-icon :component="ChevronForwardOutline" />
          </template>
        </n-button>
      </div>

      <n-spin :show="loading">
        <div v-if="photos.length === 0 && !loading" class="empty-featured">
          <n-empty description="暂无精选图片" />
        </div>
        <MasonryLayout v-else :items="photos" :gap="16">
          <template #default="{ item: photo }">
            <div class="photo-card-hover" @click="handlePhotoClick(photo)">
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
                    <span v-if="photo.classifications?.season">
                      {{ photo.classifications.season.node_name }}
                    </span>
                    <span v-if="photo.classifications?.campus">
                      {{ photo.classifications.campus.node_name }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </MasonryLayout>
      </n-spin>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useWindowScroll } from '@vueuse/core'
import {
  CameraOutline,
  ChevronDownOutline,
  ChevronForwardOutline,
  SearchOutline,
} from '@vicons/ionicons5'
import MasonryLayout from '../components/common/MasonryLayout.vue'
import { getPublicPhotos } from '../api/photo'
import { getPopularTags } from '../api/tag'
import type { Photo } from '../types/photo'
import { getPhotoUrl } from '../utils/format'

const router = useRouter()
const { y: scrollY } = useWindowScroll()

const searchKeyword = ref('')
const photos = ref<Photo[]>([])
const loading = ref(false)
const hotTags = ref<string[]>(['春天', '天空', '风景', '校园', '建筑', '人物', '运动', '实验室'])
const smartSearchEnabled = ref(true)

// Hero 区域滚动动效
const heroOpacity = computed(() => {
  const threshold = 200
  return Math.max(0, 1 - scrollY.value / threshold)
})
const heroTranslate = computed(() => {
  const threshold = 200
  const offset = Math.min(scrollY.value / 2, 80)
  return `translateY(-${offset}px)`
})

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

function handleSearch() {
  const query: Record<string, string> = {}
  if (searchKeyword.value.trim()) {
    query.search = searchKeyword.value.trim()
    if (smartSearchEnabled.value) query.smart = 'true'
  }
  if (Object.keys(query).length > 0) {
    router.push({ path: '/gallery', query })
  } else {
    router.push('/gallery')
  }
}

function handleTagClick(tag: string) {
  const query: Record<string, string> = { search: tag }
  if (smartSearchEnabled.value) query.smart = 'true'
  router.push({ path: '/gallery', query })
}

function handleSmartToggle(enabled: boolean) {
  smartSearchEnabled.value = enabled
  localStorage.setItem('smart_search_enabled', enabled ? 'true' : 'false')
}

function handlePhotoClick(photo: Photo) {
  router.push(`/photo/${photo.id}`)
}

async function loadPhotos() {
  loading.value = true
  try {
    const response = await getPublicPhotos({ limit: 12, sort_by: 'created_at' })
    photos.value = response.items.slice(0, 12)
  } catch (error) {
    console.error('加载图片失败:', error)
  } finally {
    loading.value = false
  }
}

async function loadHotTags() {
  try {
    const tags = await getPopularTags(12) as any
    if (Array.isArray(tags) && tags.length > 0) {
      hotTags.value = tags.map((t: any) => t.name).slice(0, 12)
    }
  } catch (error) {
    console.error('加载热门标签失败:', error)
  }
}

onMounted(() => {
  const saved = localStorage.getItem('smart_search_enabled')
  smartSearchEnabled.value = saved !== 'false'

  loadPhotos()
  loadHotTags()
})
</script>

<style scoped>
.home-view {
  min-height: 100vh;
}

/* ===== Hero 区域 ===== */
.hero-section {
  position: relative;
  min-height: 520px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 120px 24px 48px;
  overflow: hidden;
}

.hero-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
}

/* 底层：深蓝主色 + 微妙渐变 */
.hero-bg-layer {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse at 20% 80%, rgba(0, 80, 160, 0.6) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 20%, rgba(0, 100, 180, 0.4) 0%, transparent 40%),
    linear-gradient(160deg, #0a2540 0%, #003d7a 30%, #0056a6 60%, #004b8d 100%);
}

/* 动态渐变网格 */
.hero-grid-overlay {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
  background-size: 60px 60px;
  mask-image: radial-gradient(ellipse at center, black 30%, transparent 70%);
  -webkit-mask-image: radial-gradient(ellipse at center, black 30%, transparent 70%);
}

/* 顶部高光 */
.hero-top-light {
  position: absolute;
  top: -30%;
  left: 50%;
  transform: translateX(-50%);
  width: 80%;
  height: 60%;
  background: radial-gradient(ellipse at center, rgba(100, 180, 255, 0.15) 0%, transparent 60%);
  pointer-events: none;
}

.gradient-circle {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
}

.circle-1 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(80, 160, 255, 0.2), transparent 70%);
  top: -120px;
  left: 5%;
  animation: float-1 12s ease-in-out infinite;
}

.circle-2 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(0, 100, 200, 0.15), transparent 70%);
  top: 30%;
  right: 10%;
  animation: float-2 10s ease-in-out infinite;
}

.circle-3 {
  width: 350px;
  height: 350px;
  background: radial-gradient(circle, rgba(60, 140, 220, 0.12), transparent 70%);
  bottom: 5%;
  left: 20%;
  animation: float-3 14s ease-in-out infinite;
}

.circle-4 {
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(0, 80, 160, 0.18), transparent 70%);
  bottom: 15%;
  right: 25%;
  animation: float-4 11s ease-in-out infinite;
}

@keyframes float-1 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(30px, 20px) scale(1.05); }
}

@keyframes float-2 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(-20px, 30px) scale(1.08); }
}

@keyframes float-3 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(25px, -15px) scale(1.06); }
}

@keyframes float-4 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(-15px, -25px) scale(1.04); }
}

.hero-content {
  position: relative;
  z-index: 1;
  text-align: center;
  max-width: 720px;
  width: 100%;
  transition: opacity 0.15s linear;
  will-change: opacity, transform;
}

.hero-slogan {
  font-size: 42px;
  font-weight: 500;
  color: #ffffff;
  margin-bottom: 12px;
  letter-spacing: 4px;
  text-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
}

.hero-subtitle {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.75);
  margin-bottom: 40px;
  letter-spacing: 2px;
}

/* 搜索框 */
.hero-search {
  margin-bottom: 24px;
}

.home-smart-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 10px;
}

.home-smart-toggle .smart-label {
  font-size: 12px;
  transition: color 0.3s ease;
}

.home-smart-toggle .smart-label.smart-active {
  color: #64b4ff;
  font-weight: 500;
}

.search-box {
  display: flex;
  align-items: center;
  background: white;
  border-radius: 4px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  height: 52px;
  overflow: hidden;
  border: 1px solid #eee;
}

.search-type {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 16px;
  font-size: 14px;
  color: #666;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
}

.search-type:hover {
  color: #0056a6;
}

.search-divider {
  width: 1px;
  height: 24px;
  background: #e8e8e8;
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  border: none;
  outline: none;
  padding: 0 16px;
  font-size: 14px;
  color: #333;
  background: transparent;
  min-width: 0;
}

.search-input::placeholder {
  color: #bbb;
}

.search-camera-btn {
  flex-shrink: 0;
  color: #999;
}

.search-camera-btn:hover {
  color: #0056a6;
}

.search-submit-btn {
  width: 52px;
  height: 52px;
  border-radius: 0;
  background: #0056a6 !important;
  border: none !important;
  flex-shrink: 0;
}

.search-submit-btn:hover {
  background: #004080 !important;
}

/* 热搜标签 */
.hot-tags {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 8px;
}

.hot-label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  margin-right: 4px;
}

.hot-tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.hot-tag {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
  cursor: pointer;
  transition: color 0.2s;
}

.hot-tag:hover {
  color: #ffffff;
}

.hot-tag:not(:last-child)::after {
  content: '|';
  margin-left: 8px;
  color: rgba(255, 255, 255, 0.4);
}

/* ===== 精选图片区域 ===== */
.featured-section {
  max-width: 1440px;
  margin: 0 auto;
  padding: 48px 24px 64px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.section-title {
  font-size: 22px;
  font-weight: 600;
  color: #333;
}

.empty-featured {
  padding: 80px 0;
}

/* 响应式 */
@media (max-width: 768px) {
  .hero-section {
    min-height: 400px;
    padding: 72px 16px 32px;
  }

  .hero-slogan {
    font-size: 28px;
    letter-spacing: 2px;
  }

  .hero-subtitle {
    font-size: 14px;
  }

  .search-box {
    height: 46px;
  }

  .search-type {
    padding: 0 10px;
    font-size: 13px;
  }

  .search-input {
    padding: 0 10px;
    font-size: 13px;
  }

  .search-submit-btn {
    width: 46px;
    height: 46px;
  }

  .hot-tags {
    flex-direction: column;
    align-items: flex-start;
  }

  .featured-section {
    padding: 32px 16px 48px;
  }

  .section-title {
    font-size: 18px;
  }
}
</style>
