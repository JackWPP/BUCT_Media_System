<template>
  <div class="empty-state">
    <n-empty
      :description="description"
      :size="size"
    >
      <template v-if="icon" #icon>
        <n-icon :size="iconSize">
          <component :is="icon" />
        </n-icon>
      </template>
      <template v-if="action" #extra>
        <slot name="action">
          <n-button v-if="actionText" :type="actionType" @click="handleAction">
            {{ actionText }}
          </n-button>
        </slot>
      </template>
    </n-empty>
  </div>
</template>

<script setup lang="ts">
import type { Component } from 'vue'

interface Props {
  description?: string
  icon?: Component
  iconSize?: number
  size?: 'small' | 'medium' | 'large' | 'huge'
  action?: boolean
  actionText?: string
  actionType?: 'default' | 'primary' | 'info' | 'success' | 'warning' | 'error'
}

withDefaults(defineProps<Props>(), {
  description: '暂无数据',
  iconSize: 60,
  size: 'medium',
  action: false,
  actionType: 'primary',
})

const emit = defineEmits<{
  action: []
}>()

function handleAction() {
  emit('action')
}
</script>

<style scoped>
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
  padding: 40px 20px;
}
</style>
