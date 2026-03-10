<template>
  <n-popover trigger="click" placement="bottom-end" :width="360" @update:show="handlePopoverShow">
    <template #trigger>
      <n-badge :value="unreadCount" :max="99" :show="unreadCount > 0">
        <n-button circle quaternary>
          <template #icon>
            <n-icon :component="NotificationsOutline" />
          </template>
        </n-button>
      </n-badge>
    </template>

    <div class="notification-panel">
      <div class="notification-header">
        <n-text strong>通知</n-text>
        <n-button v-if="unreadCount > 0" text size="small" @click="handleMarkAllRead">
          全部已读
        </n-button>
      </div>

      <n-spin :show="loading">
        <div v-if="notifications.length === 0" class="notification-empty">
          <n-text depth="3">暂无通知</n-text>
        </div>
        <n-list v-else clickable hoverable>
          <n-list-item v-for="item in notifications" :key="item.id"
            :class="{ 'unread': !item.is_read }" @click="handleClick(item)">
            <n-thing>
              <template #header>
                <n-space align="center" :size="4">
                  <n-tag :type="getTypeTag(item.type)" size="small" round>
                    {{ getTypeLabel(item.type) }}
                  </n-tag>
                  <n-text :depth="item.is_read ? 3 : 1" style="font-size: 13px;">
                    {{ item.title }}
                  </n-text>
                </n-space>
              </template>
              <template #description>
                <n-text depth="3" style="font-size: 12px;">
                  {{ formatTime(item.created_at) }}
                </n-text>
              </template>
            </n-thing>
          </n-list-item>
        </n-list>
      </n-spin>
    </div>
  </n-popover>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { NotificationsOutline } from '@vicons/ionicons5'
import {
  getNotifications,
  getUnreadCount,
  markAsRead,
  markAllRead,
  type NotificationItem,
} from '../../api/notification'

const unreadCount = ref(0)
const notifications = ref<NotificationItem[]>([])
const loading = ref(false)
let pollTimer: ReturnType<typeof setInterval> | null = null

function getTypeTag(type: string): 'success' | 'warning' | 'info' | 'error' {
  const map: Record<string, 'success' | 'warning' | 'info' | 'error'> = {
    photo_approved: 'success',
    photo_rejected: 'warning',
    permission_granted: 'info',
    system: 'info',
  }
  return map[type] || 'info'
}

function getTypeLabel(type: string): string {
  const map: Record<string, string> = {
    photo_approved: '通过',
    photo_rejected: '拒绝',
    permission_granted: '授权',
    system: '系统',
  }
  return map[type] || '通知'
}

function formatTime(dateStr: string): string {
  const d = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  return d.toLocaleDateString('zh-CN')
}

async function fetchUnreadCount() {
  try {
    const res = await getUnreadCount()
    unreadCount.value = res.unread_count
  } catch {
    // silent
  }
}

async function fetchNotifications() {
  loading.value = true
  try {
    const res = await getNotifications({ limit: 20 })
    notifications.value = res.notifications
    unreadCount.value = res.unread_count
  } catch {
    // silent
  } finally {
    loading.value = false
  }
}

function handlePopoverShow(show: boolean) {
  if (show) {
    fetchNotifications()
  }
}

async function handleClick(item: NotificationItem) {
  if (!item.is_read) {
    await markAsRead(item.id)
    item.is_read = true
    unreadCount.value = Math.max(0, unreadCount.value - 1)
  }
}

async function handleMarkAllRead() {
  await markAllRead()
  notifications.value.forEach(n => { n.is_read = true })
  unreadCount.value = 0
}

onMounted(() => {
  fetchUnreadCount()
  // 每 60 秒轮询未读数
  pollTimer = setInterval(fetchUnreadCount, 60000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.notification-panel {
  max-height: 400px;
  overflow-y: auto;
}

.notification-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  margin-bottom: 4px;
  border-bottom: 1px solid var(--n-border-color);
}

.notification-empty {
  padding: 32px;
  text-align: center;
}

.unread {
  background: rgba(var(--n-primary-color-hover), 0.05);
}
</style>
