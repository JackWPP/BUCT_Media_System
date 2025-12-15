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

const props = defineProps<{
  items: any[]
  gap?: number
  // Optional fixed columns
  cols?: number
}>()

const windowWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1200)

const updateWidth = () => {
  windowWidth.value = window.innerWidth
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
})

const columnCount = computed(() => {
  if (props.cols) return props.cols
  const w = windowWidth.value
  if (w >= 1536) return 5 // 2xl
  if (w >= 1280) return 4 // xl
  if (w >= 1024) return 3 // lg
  if (w >= 640) return 2  // sm
  return 1                // base
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
    // 默认假设宽高比为 4:3 (0.75)
    let aspectRatio = 0.75
    if (item.width && item.height) {
      aspectRatio = item.height / item.width
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
