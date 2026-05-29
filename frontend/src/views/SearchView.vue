<template>
  <div class="search-view">
    <!-- 搜索栏 -->
    <div class="search-header">
      <n-input
        v-model:value="query"
        placeholder="搜索照片... 例如：秋天的校园、星空夜景、银杏落叶"
        size="large"
        clearable
        @update:value="onInput"
      >
        <template #prefix>
          <n-icon :component="SearchOutline" />
        </template>
      </n-input>
      <div class="search-meta" v-if="searched">
        <n-text depth="3">
          找到 {{ total }} 张照片，用时 {{ queryTime }}ms
        </n-text>
      </div>
    </div>

    <!-- 筛选器 -->
    <div class="search-filters">
      <n-space>
        <n-select
          v-model:value="filters.season"
          :options="seasonOptions"
          placeholder="季节"
          clearable
          style="width: 120px;"
          @update:value="doSearch"
        />
        <n-select
          v-model:value="filters.campus"
          :options="campusOptions"
          placeholder="校区"
          clearable
          style="width: 140px;"
          @update:value="doSearch"
        />
      </n-space>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="search-loading">
      <n-spin size="large" />
      <n-text>搜索中...</n-text>
    </div>

    <!-- 空状态 -->
    <n-empty v-else-if="searched && results.length === 0" description="没有找到匹配的照片" />

    <!-- 搜索结果 -->
    <div v-else-if="results.length > 0" class="search-results">
      <div
        v-for="result in results"
        :key="result.photo_id"
        class="result-card"
        @click="goToPhoto(result.photo_id)"
      >
        <div class="result-image">
          <img
            :src="getThumbUrl(result.photo_id)"
            :alt="result.tags.join(', ')"
            loading="lazy"
          />
          <div class="result-score">
            <n-tag size="small" :bordered="false" :color="{ color: 'rgba(0,0,0,0.6)', textColor: '#fff' }">
              {{ (result.score * 100).toFixed(0) }}%
            </n-tag>
          </div>
        </div>
        <div class="result-info">
          <div class="result-tags">
            <n-tag
              v-for="tag in result.tags.slice(0, 5)"
              :key="tag"
              size="small"
              :bordered="false"
              type="info"
            >
              {{ tag }}
            </n-tag>
          </div>
          <div class="result-classifications">
            <n-text depth="3" style="font-size: 12px;">
              <span v-if="result.classifications.season">{{ result.classifications.season }}</span>
              <span v-if="result.classifications.campus"> · {{ result.classifications.campus }}</span>
              <span v-if="result.classifications.landmark"> · {{ result.classifications.landmark }}</span>
            </n-text>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NInput, NIcon, NSelect, NTag, NSpin, NEmpty, NText } from 'naive-ui'
import { SearchOutline } from '@vicons/ionicons5'
import { searchPhotos, type SearchResult } from '@/api/search'

const route = useRoute()
const router = useRouter()

const query = ref((route.query.q as string) || '')
const loading = ref(false)
const searched = ref(false)
const results = ref<SearchResult[]>([])
const total = ref(0)
const queryTime = ref(0)

const filters = reactive({
  season: (route.query.season as string) || null,
  campus: (route.query.campus as string) || null,
})

const seasonOptions = [
  { label: '春季', value: '春季' },
  { label: '夏季', value: '夏季' },
  { label: '秋季', value: '秋季' },
  { label: '冬季', value: '冬季' },
]

const campusOptions = [
  { label: '昌平校区', value: '昌平校区' },
  { label: '朝阳校区', value: '朝阳校区' },
  { label: '海淀校区', value: '海淀校区' },
]

let debounceTimer: ReturnType<typeof setTimeout> | null = null

function onInput(val: string) {
  if (debounceTimer) clearTimeout(debounceTimer)
  if (!val.trim()) {
    results.value = []
    searched.value = false
    total.value = 0
    return
  }
  debounceTimer = setTimeout(() => doSearch(), 300)
}

async function doSearch() {
  const q = query.value.trim()
  if (!q) return

  loading.value = true
  searched.value = true

  // Update URL
  router.replace({
    query: {
      q,
      ...(filters.season ? { season: filters.season } : {}),
      ...(filters.campus ? { campus: filters.campus } : {}),
    },
  })

  try {
    const resp = await searchPhotos({
      q,
      limit: 30,
      ...(filters.season ? { season: filters.season } : {}),
      ...(filters.campus ? { campus: filters.campus } : {}),
    })
    results.value = resp.results
    total.value = resp.total
    queryTime.value = resp.query_time_ms
  } catch (err: any) {
    console.error('Search failed:', err)
    results.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function getThumbUrl(photoId: string): string {
  return `/api/v1/photos/${photoId}/thumbnail`
}

function goToPhoto(photoId: string) {
  router.push({ name: 'PhotoDetail', params: { id: photoId } })
}

onMounted(() => {
  if (query.value.trim()) {
    doSearch()
  }
})
</script>

<style scoped>
.search-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.search-header {
  margin-bottom: 20px;
}

.search-meta {
  margin-top: 8px;
}

.search-filters {
  margin-bottom: 20px;
}

.search-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 60px 0;
}

.search-results {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}

.result-card {
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.result-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.result-image {
  position: relative;
  aspect-ratio: 4/3;
  overflow: hidden;
}

.result-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.result-score {
  position: absolute;
  top: 8px;
  right: 8px;
}

.result-info {
  padding: 10px;
}

.result-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 6px;
}

.result-classifications {
  font-size: 12px;
}
</style>
