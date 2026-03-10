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
            <NotificationBell />
            <n-button secondary size="small" @click="showChangePassword = true">修改密码</n-button>
            <n-button secondary @click="handleLogout">退出登录</n-button>
          </n-space>
        </n-space>
      </n-layout-header>

      <n-layout-content class="admin-content" content-style="padding: 24px;">
        <router-view />
      </n-layout-content>
    </n-layout>
  </n-layout>

  <ChangePasswordDialog v-model:show="showChangePassword" />
</template>

<script setup lang="ts">
import { computed, h, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NIcon } from 'naive-ui'
import {
  BarChartOutline,
  CheckmarkCircleOutline,
  CloudUploadOutline,
  DocumentTextOutline,
  GitNetworkOutline,
  ImagesOutline,
  PeopleOutline,
  PricetagsOutline,
  SettingsOutline,
} from '@vicons/ionicons5'
import type { MenuOption } from 'naive-ui'
import { useAuthStore } from '../stores/auth'
import ChangePasswordDialog from '../components/common/ChangePasswordDialog.vue'
import NotificationBell from '../components/common/NotificationBell.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const collapsed = ref(false)
const activeKey = ref(route.name?.toString() || 'PhotoReview')
const user = computed(() => authStore.user)
const showChangePassword = ref(false)

const roleLabel = computed(() => {
  const roleMap: Record<string, string> = {
    admin: '管理员',
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

const baseMenuOptions: MenuOption[] = [
  { label: '仪表盘', key: 'Dashboard', icon: renderMenuIcon(BarChartOutline) },
  { label: '照片审核', key: 'PhotoReview', icon: renderMenuIcon(CheckmarkCircleOutline) },
  { label: '自由标签', key: 'TagManagement', icon: renderMenuIcon(PricetagsOutline) },
  { label: '分类治理', key: 'TaxonomyManagement', icon: renderMenuIcon(GitNetworkOutline) },
]

const adminOnlyMenuOptions: MenuOption[] = [
  { type: 'divider', key: 'divider-admin' },
  { label: '批量导入', key: 'PhotoImport', icon: renderMenuIcon(CloudUploadOutline) },
  { label: '用户管理', key: 'UserManagement', icon: renderMenuIcon(PeopleOutline) },
  { label: '系统设置', key: 'SystemSettings', icon: renderMenuIcon(SettingsOutline) },
  { label: '审计日志', key: 'AuditLog', icon: renderMenuIcon(DocumentTextOutline) },
]

const bottomMenuOptions: MenuOption[] = [
  { type: 'divider', key: 'divider-bottom' },
  { label: '返回前台', key: 'Gallery', icon: renderMenuIcon(ImagesOutline) },
]

const filteredMenuOptions = computed(() => {
  const options = [...baseMenuOptions]
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
