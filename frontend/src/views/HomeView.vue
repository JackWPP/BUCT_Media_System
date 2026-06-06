<template>
  <div class="home-view">
    <!-- Hero 区域 -->
    <section class="hero-section">
      <div class="hero-bg">
        <img src="/hero-banner.jpg" alt="视觉北化" class="hero-bg-image" />
      </div>
      <div class="hero-search-panel">
        <h1>视觉北化</h1>
        <div class="hero-search">
          <n-input
            v-model:value="heroSearch"
            size="large"
            placeholder="搜索四季校园、建筑地点、摄影作品"
            clearable
            @keyup.enter="submitHeroSearch"
          >
            <template #prefix>
              <n-icon :component="SearchOutline" />
            </template>
          </n-input>
          <n-button type="primary" size="large" class="hero-search-button" @click="submitHeroSearch">
            搜索
          </n-button>
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
        <div v-else class="featured-grid">
          <div
            v-for="photo in photos"
            :key="photo.id"
            class="featured-card photo-card-hover"
            @click="handlePhotoClick(photo)"
          >
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
                  <span v-if="taxonomyValueName(photo.classifications?.season)">
                    {{ taxonomyValueName(photo.classifications?.season) }}
                  </span>
                  <span v-if="taxonomyValueName(photo.classifications?.campus)">
                    {{ taxonomyValueName(photo.classifications?.campus) }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </n-spin>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ChevronForwardOutline,
  SearchOutline,
} from '@vicons/ionicons5'
import { getPublicPhotos } from '../api/photo'
import type { Photo } from '../types/photo'
import { taxonomyValueName } from '../types/photo'
import { getPhotoUrl } from '../utils/format'

const router = useRouter()

const photos = ref<Photo[]>([])
const loading = ref(false)
const heroSearch = ref('')

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

function handlePhotoClick(photo: Photo) {
  router.push(`/photo/${photo.id}`)
}

function submitHeroSearch() {
  const keyword = heroSearch.value.trim()
  if (!keyword) {
    router.push('/gallery')
    return
  }
  router.push({ path: '/gallery', query: { search: keyword, smart: 'true' } })
}

// 奖项等级排序权重（数字越小越靠前）
const AWARD_ORDER: Record<string, number> = {
  '特等奖': 1,
  '一等奖': 2,
  '二等奖': 3,
  '优秀奖': 4,
}

function getAwardOrder(photo: Photo): number {
  const award = taxonomyValueName(photo.classifications?.award_level)
  return award ? (AWARD_ORDER[award] ?? 99) : 99
}

async function loadPhotos() {
  loading.value = true
  try {
    const response = await getPublicPhotos({
      limit: 100,
      gallery_year: '第八届获奖作品（2025年）',
      photo_type: '校园风光',
    })
    // 按奖项等级排序：特等奖 → 一等奖 → 二等奖 → 优秀奖 → 无奖项
    photos.value = response.items.sort((a, b) => getAwardOrder(a) - getAwardOrder(b))
  } catch (error) {
    console.error('加载图片失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadPhotos()
})
</script>

<style scoped>
.home-view {
  min-height: 100vh;
}

/* ===== Hero 区域 ===== */
.hero-section {
  position: relative;
  min-height: 430px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  overflow: hidden;
}

.hero-search-panel {
  position: relative;
  z-index: 2;
  width: min(720px, calc(100% - 32px));
  margin-top: 120px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 18px;
}

.hero-search-panel h1 {
  margin: 0;
  font-size: 38px;
  font-weight: 700;
  color: #fff;
  text-shadow: 0 3px 14px rgba(0, 0, 0, 0.48), 0 1px 2px rgba(0, 0, 0, 0.36);
}

.hero-search {
  width: 100%;
  display: flex;
  gap: 10px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  box-shadow: 0 16px 42px rgba(5, 18, 44, 0.34);
  backdrop-filter: blur(10px);
}

.hero-search :deep(.n-input) {
  flex: 1;
  background: #fff;
}

.hero-search-button {
  min-width: 96px;
  background: #0056a6 !important;
  border-color: #0056a6 !important;
}

.hero-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
}

.hero-bg::after {
  content: '';
  position: absolute;
  inset: 0;
  background:
    linear-gradient(180deg, rgba(8, 22, 52, 0.08) 0%, rgba(8, 22, 52, 0.42) 50%, rgba(8, 22, 52, 0.14) 100%),
    linear-gradient(90deg, rgba(8, 22, 52, 0.08) 0%, rgba(8, 22, 52, 0.24) 42%, rgba(8, 22, 52, 0.24) 58%, rgba(8, 22, 52, 0.08) 100%);
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

.featured-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.featured-card {
  aspect-ratio: 1 / 1;
}

/* 响应式 */
@media (max-width: 768px) {
  .hero-section {
    min-height: 280px;
  }

  .hero-search-panel {
    margin-top: 64px;
    gap: 12px;
  }

  .hero-search-panel h1 {
    font-size: 28px;
  }

  .hero-search {
    flex-direction: column;
    padding: 8px;
  }

  .hero-search-button {
    width: 100%;
  }

  .featured-section {
    padding: 24px 8px 48px;
  }

  .section-title {
    font-size: 18px;
  }

  .featured-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }
}

@media (min-width: 769px) and (max-width: 1180px) {
  .featured-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
