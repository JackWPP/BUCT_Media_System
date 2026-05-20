<template>
  <div class="home-view">
    <!-- Hero 区域 -->
    <section class="hero-section">
      <div class="hero-bg">
        <!-- 首图 -->
        <img src="/hero-banner.jpg" alt="视觉北化" class="hero-bg-image" />
        <!-- 半透明遮罩，让文字更清晰 -->
        <div class="hero-bg-overlay"></div>
      </div>
      <div class="hero-content" :style="{ opacity: heroOpacity, transform: heroTranslate }">
        <h1 class="hero-slogan">北化之美 美在四季<br>北化育人 育在全面</h1>

        <!-- 搜索框 -->
        <div class="hero-search">
          <div class="search-box">
            <input
              v-model="searchKeyword"
              type="text"
              class="search-input"
              placeholder="输入关键词搜索照片..."
              @keyup.enter="handleSearch"
            />
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
        <MasonryLayout v-else :items="photos" :gap="16" :columns-config="homeColumnsConfig" :get-item-ratio="getItemRatio">
          <template #default="{ item: photo }">
            <div class="photo-card-hover" :class="{ 'photo-card-portrait': photo.height > photo.width }" @click="handlePhotoClick(photo)">
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
// 根据图片方向返回高度/宽度比（与 CSS aspect-ratio 对齐）
const getItemRatio = (photo: any) => {
  return photo.height > photo.width ? 3 / 2 : 2 / 3
}

// 首页瀑布流列数配置：手机端 2 列
const homeColumnsConfig = { base: 2, sm: 2, lg: 3, xl: 4, '2xl': 4 }

const photos = ref<Photo[]>([])
const loading = ref(false)
const hotTags = ref<string[]>(['春天', '天空', '风景', '校园', '建筑', '人物', '运动', '实验室'])
const smartSearchEnabled = ref(false)

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
  }
  if (Object.keys(query).length > 0) {
    router.push({ path: '/gallery', query })
  } else {
    router.push('/gallery')
  }
}

function handleTagClick(tag: string) {
  const query: Record<string, string> = { search: tag }
  router.push({ path: '/gallery', query })
}

function handleSmartToggle(enabled: boolean) {
  smartSearchEnabled.value = enabled
  localStorage.setItem('smart_search_enabled', enabled ? 'true' : 'false')
}

function handlePhotoClick(photo: Photo) {
  router.push(`/photo/${photo.id}`)
}

// 奖项等级排序权重（数字越小越靠前）
const AWARD_ORDER: Record<string, number> = {
  '特等奖': 1,
  '一等奖': 2,
  '二等奖': 3,
  '优秀奖': 4,
}

function getAwardOrder(photo: Photo): number {
  const award = photo.classifications?.award_level?.node_name
  return award ? (AWARD_ORDER[award] ?? 99) : 99
}

async function loadPhotos() {
  loading.value = true
  try {
    const response = await getPublicPhotos({
      limit: 100,
      gallery_year: '2025年第八届获奖作品',
      photo_type: '风光类',
    })
    // 按奖项等级排序：特等奖 → 一等奖 → 二等奖 → 优秀奖 → 无奖项
    photos.value = response.items.sort((a, b) => getAwardOrder(a) - getAwardOrder(b))
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
  margin-top: -80px;
}

/* ===== Hero 区域 ===== */
.hero-section {
  position: relative;
  min-height: 520px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 160px 24px 48px;
  overflow: hidden;
}

.hero-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
}

/* 底层：首图 */
.hero-bg-image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
}

/* 半透明遮罩 */
.hero-bg-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    rgba(0, 0, 0, 0.55) 0%,
    rgba(0, 0, 0, 0.35) 30%,
    rgba(0, 0, 0, 0.45) 60%,
    rgba(0, 0, 0, 0.65) 100%
  );
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
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 12px;
  letter-spacing: 4px;
  text-shadow: 0 2px 20px rgba(0, 0, 0, 0.5), 0 1px 4px rgba(0, 0, 0, 0.3);
}

.hero-subtitle {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 40px;
  letter-spacing: 2px;
  text-shadow: 0 1px 8px rgba(0, 0, 0, 0.4);
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
    padding: 112px 16px 32px;
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
    padding: 24px 8px 48px;
  }

  .section-title {
    font-size: 18px;
  }
}
</style>
