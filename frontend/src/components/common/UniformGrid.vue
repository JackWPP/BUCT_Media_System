<template>
  <div class="uniform-grid" :style="gridStyle">
    <div
      v-for="item in items"
      :key="itemKey(item)"
      class="grid-cell"
      :style="cellStyle"
      @click="$emit('itemClick', item)"
    >
      <div class="cell-inner">
        <slot :item="item" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts" generic="T extends Record<string, any>">
import { computed } from 'vue'

interface Props {
  items: T[]
  columns?: number
  gap?: number
  aspectRatio?: string
  itemKey?: (item: T) => string
}

const props = withDefaults(defineProps<Props>(), {
  columns: 4,
  gap: 12,
  aspectRatio: '4 / 3',
  itemKey: (item: T) => item.id || String(Math.random()),
})

defineEmits<{
  itemClick: [item: T]
}>()

const gridStyle = computed(() => ({
  display: 'grid',
  gridTemplateColumns: `repeat(${props.columns}, 1fr)`,
  gap: `${props.gap}px`,
}))

const cellStyle = computed(() => ({
  aspectRatio: props.aspectRatio,
}))
</script>

<style scoped>
.uniform-grid {
  width: 100%;
}

.grid-cell {
  position: relative;
  overflow: hidden;
  border-radius: 4px;
  cursor: pointer;
}

.cell-inner {
  position: absolute;
  inset: 0;
}

.cell-inner :deep(img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

.grid-cell:hover .cell-inner :deep(img) {
  transform: scale(1.06);
}

/* 响应式 */
@media (max-width: 1200px) {
  .uniform-grid {
    grid-template-columns: repeat(3, 1fr) !important;
  }
}

@media (max-width: 768px) {
  .uniform-grid {
    grid-template-columns: repeat(2, 1fr) !important;
  }
}
</style>
