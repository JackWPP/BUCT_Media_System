<template>
  <div class="masonry-container" :style="{ gap: gap + 'px' }">
    <div 
      v-for="(col, index) in columns" 
      :key="index" 
      class="masonry-column" 
      :style="{ gap: gap + 'px' }"
    >
      <div v-for="item in col" :key="item.id || index" class="masonry-item">
        <slot :item="item"></slot>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'

export interface ColumnsConfig {
  base?: number
  sm?: number
  lg?: number
  xl?: number
  '2xl'?: number
}

const props = defineProps<{
  items: any[]
  gap?: number
  // Optional fixed columns (deprecated, use columnsConfig instead)
  cols?: number
  // Responsive columns config
  columnsConfig?: ColumnsConfig
}>()

const windowWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1200)

let resizeTimer: ReturnType<typeof setTimeout> | null = null
const updateWidth = () => {
  if (resizeTimer) clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => {
    windowWidth.value = window.innerWidth
  }, 100)
}

onMounted(() => {
  if (typeof window !== 'undefined') {
    window.addEventListener('resize', updateWidth)
    updateWidth()
  }
})

onUnmounted(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', updateWidth)
  }
  if (resizeTimer) clearTimeout(resizeTimer)
})

const defaultColumnsConfig: ColumnsConfig = {
  base: 1,
  sm: 2,
  lg: 3,
  xl: 4,
  '2xl': 5,
}

const columnCount = computed(() => {
  if (props.cols) return props.cols
  const config = props.columnsConfig || defaultColumnsConfig
  const w = windowWidth.value
  if (w >= 1536) return config['2xl'] ?? config.xl ?? config.lg ?? config.sm ?? config.base ?? 1
  if (w >= 1280) return config.xl ?? config.lg ?? config.sm ?? config.base ?? 1
  if (w >= 1024) return config.lg ?? config.sm ?? config.base ?? 1
  if (w >= 640) return config.sm ?? config.base ?? 1
  return config.base ?? 1
})

const columns = computed(() => {
  const count = columnCount.value
  const res = Array.from({ length: count }, () => [] as any[])
  const colHeights = new Array(count).fill(0)

  props.items.forEach((item) => {
    // 找到当前高度最小的列
    let minHeight = colHeights[0]
    let minIndex = 0

    for (let i = 1; i < count; i++) {
      if (colHeights[i] < minHeight) {
        minHeight = colHeights[i]
        minIndex = i
      }
    }

    // 将图片添加到该列
    res[minIndex].push(item)

    // 更新列高度
    // 使用更合理的默认宽高比 3:4 (1.33) 竖图更常见
    // 同时限制极端比例，避免某列过高/过低
    let aspectRatio = 1.0
    if (item.width && item.height) {
      const rawRatio = item.height / item.width
      // 限制比例在 0.5 (2:1 宽图) 到 2.0 (1:2 高图) 之间
      aspectRatio = Math.max(0.5, Math.min(2.0, rawRatio))
    }
    colHeights[minIndex] += aspectRatio
  })

  return res
})
</script>

<style scoped>
.masonry-container {
  display: flex;
  align-items: flex-start;
  width: 100%;
}

.masonry-column {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0; /* Prevent flex overflow */
}

.masonry-item {
  width: 100%;
}
</style>
