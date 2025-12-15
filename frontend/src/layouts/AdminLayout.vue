<template>
  <n-layout class="admin-layout" has-sider>
    <n-layout-sider
      bordered
      :width="240"
      :collapsed="collapsed"
      :collapsed-width="64"
      show-trigger
      @collapse="collapsed = true"
      @expand="collapsed = false"
    >
      <n-menu
        v-model:value="activeKey"
        :collapsed="collapsed"
        :collapsed-width="64"
        :options="menuOptions"
        @update:value="handleMenuSelect"
      />
    </n-layout-sider>
    
    <n-layout>
      <n-layout-header bordered class="admin-header">
        <n-space justify="space-between" align="center">
          <n-text strong style="font-size: 18px;">后台管理</n-text>
          <n-space>
            <n-text>{{ user?.full_name || user?.email }}</n-text>
            <n-button @click="handleLogout" secondary>退出登录</n-button>
          </n-space>
        </n-space>
      </n-layout-header>
      
      <n-layout-content class="admin-content" content-style="padding: 24px;">
        <router-view />
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<script setup lang="ts">
import { ref, computed, h } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { NIcon } from 'naive-ui'
import { 
  ImagesOutline, 
  PricetagsOutline, 
  CloudUploadOutline,
  CheckmarkCircleOutline,
  BarChartOutline
} from '@vicons/ionicons5'
import type { MenuOption } from 'naive-ui'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const collapsed = ref(false)
const activeKey = ref(route.name?.toString() || 'PhotoReview')

const user = computed(() => authStore.user)

function renderMenuIcon(icon: any) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const menuOptions: MenuOption[] = [
  {
    label: '仪表盘',
    key: 'Dashboard',
    icon: renderMenuIcon(BarChartOutline),
  },
  {
    label: '照片审核',
    key: 'PhotoReview',
    icon: renderMenuIcon(CheckmarkCircleOutline),
  },
  {
    label: '标签管理',
    key: 'TagManagement',
    icon: renderMenuIcon(PricetagsOutline),
  },
  {
    label: '批量导入',
    key: 'PhotoImport',
    icon: renderMenuIcon(CloudUploadOutline),
  },
  {
    label: '返回前台',
    key: 'Gallery',
    icon: renderMenuIcon(ImagesOutline),
  },
]

function handleMenuSelect(key: string) {
  activeKey.value = key
  router.push({ name: key })
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.admin-layout {
  height: 100vh;
}

.admin-header {
  padding: 0 24px;
  height: 64px;
  display: flex;
  align-items: center;
}

.admin-content {
  height: calc(100vh - 64px);
  overflow-y: auto;
}
</style>
