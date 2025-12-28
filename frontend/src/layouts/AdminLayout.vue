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
        :options="filteredMenuOptions"
        @update:value="handleMenuSelect"
      />
    </n-layout-sider>
    
    <n-layout>
      <n-layout-header bordered class="admin-header">
        <n-space justify="space-between" align="center">
          <n-text strong style="font-size: 18px;">后台管理</n-text>
          <n-space>
            <n-tag :type="roleTagType" size="small">{{ roleLabel }}</n-tag>
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
  BarChartOutline,
  PeopleOutline,
  SettingsOutline
} from '@vicons/ionicons5'
import type { MenuOption } from 'naive-ui'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const collapsed = ref(false)
const activeKey = ref(route.name?.toString() || 'PhotoReview')

const user = computed(() => authStore.user)

// 角色显示
const roleLabel = computed(() => {
  const roleMap: Record<string, string> = {
    admin: '超级管理员',
    auditor: '审核员',
    dept_user: '部门用户',
    user: '普通用户',
  }
  return roleMap[user.value?.role || 'user'] || '未知'
})

const roleTagType = computed(() => {
  const typeMap: Record<string, 'success' | 'warning' | 'info' | 'default'> = {
    admin: 'success',
    auditor: 'warning',
    dept_user: 'info',
    user: 'default',
  }
  return typeMap[user.value?.role || 'user'] || 'default'
})

function renderMenuIcon(icon: any) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

// 基础菜单（审核员可见）
const baseMenuOptions: MenuOption[] = [
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
]

// 仅管理员可见的菜单
const adminOnlyMenuOptions: MenuOption[] = [
  {
    type: 'divider',
    key: 'd1',
  },
  {
    label: '用户管理',
    key: 'UserManagement',
    icon: renderMenuIcon(PeopleOutline),
  },
  {
    label: '系统设置',
    key: 'SystemSettings',
    icon: renderMenuIcon(SettingsOutline),
  },
]

// 底部通用菜单
const bottomMenuOptions: MenuOption[] = [
  {
    type: 'divider',
    key: 'd2',
  },
  {
    label: '返回前台',
    key: 'Gallery',
    icon: renderMenuIcon(ImagesOutline),
  },
]

// 根据权限过滤菜单
const filteredMenuOptions = computed(() => {
  const options = [...baseMenuOptions]
  
  // 仅管理员可以看到用户管理和系统设置
  if (authStore.isAdmin) {
    options.push(...adminOnlyMenuOptions)
  }
  
  options.push(...bottomMenuOptions)
  return options
})

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

