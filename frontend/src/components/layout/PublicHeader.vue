<template>
  <header
    class="public-header"
    :class="{
      'header-home': isHome && !isScrolled,
      'header-scrolled': isScrolled || !isHome,
    }"
  >
    <div class="header-container">
      <!-- Logo -->
      <div class="header-logo" @click="handleLogoClick">
        <img src="/logo.png" alt="视觉北化" class="logo-image" />
      </div>

      <!-- 搜索框 - 仅在非首页或滚动后显示 -->
      <div
        v-if="!hideSearch && (!isHome || isScrolled)"
        class="header-search-mini"
      >
        <n-input
          v-model:value="localKeyword"
          placeholder="搜索照片、描述或标签"
          clearable
          size="small"
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <n-icon :component="SearchOutline" />
          </template>
          <template #suffix>
            <n-button
              type="primary"
              size="tiny"
              class="search-btn-red"
              @click="handleSearch"
            >
              <n-icon :component="SearchOutline" />
            </n-button>
          </template>
        </n-input>
      </div>

      <!-- 右侧操作区 -->
      <div class="header-actions">
        <n-button
          v-if="authStore.isAuthenticated"
          quaternary
          size="small"
          @click="router.push('/upload')"
        >
          <template #icon>
            <n-icon :component="CloudUploadOutline" />
          </template>
          <span class="action-text">上传</span>
        </n-button>

        <NotificationBell v-if="authStore.isAuthenticated" />

        <template v-if="authStore.isAuthenticated">
          <n-dropdown :options="userMenuOptions" @select="handleUserMenuSelect">
            <n-button circle size="small">
              <template #icon>
                <n-icon :component="PersonOutline" />
              </template>
            </n-button>
          </n-dropdown>
        </template>
        <template v-else>
          <n-button
            type="primary"
            size="small"
            class="login-btn"
            @click="router.push('/login')"
          >
            登录
          </n-button>
        </template>

        <!-- 手机端搜索按钮 -->
        <n-button
          class="mobile-search-btn"
          quaternary
          circle
          size="small"
          @click="openMobileSearch"
        >
          <template #icon>
            <n-icon :component="SearchOutline" />
          </template>
        </n-button>
      </div>

      <!-- 手机端全屏搜索层 -->
      <Transition name="mobile-search-slide">
        <div v-if="showMobileSearch" class="mobile-search-overlay">
          <div class="mobile-search-bar">
            <n-input
              ref="mobileSearchInput"
              v-model:value="localKeyword"
              placeholder="搜索照片、描述或标签"
              clearable
              size="large"
              autofocus
              @keyup.enter="handleMobileSearch"
            >
              <template #prefix>
                <n-icon :component="SearchOutline" />
              </template>
            </n-input>
            <n-button quaternary @click="closeMobileSearch">取消</n-button>
          </div>
        </div>
      </Transition>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NIcon, useDialog, useMessage } from 'naive-ui'
import {
  CloseOutline,
  CloudUploadOutline,
  LogOutOutline,
  PersonOutline,
  SearchOutline,
  SettingsOutline,
} from '@vicons/ionicons5'
import { useWindowScroll } from '@vueuse/core'
import NotificationBell from '../common/NotificationBell.vue'
import { useAuthStore } from '../../stores/auth'

interface Props {
  isHome?: boolean
  searchKeyword?: string
  hideSearch?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isHome: false,
  searchKeyword: '',
  hideSearch: false,
})

const emit = defineEmits<{
  search: [keyword: string, smart: boolean]
  openChangePassword: []
}>()

const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const authStore = useAuthStore()
const { y: scrollY } = useWindowScroll()

const isScrolled = computed(() => scrollY.value > 60)
const localKeyword = ref(props.searchKeyword)
const smartSearchEnabled = ref(false)
const showMobileSearch = ref(false)

onMounted(() => {
  const saved = localStorage.getItem('smart_search_enabled')
  smartSearchEnabled.value = saved !== 'false'
})

const route = useRoute()

function handleSmartToggle(enabled: boolean) {
  smartSearchEnabled.value = enabled
  localStorage.setItem('smart_search_enabled', enabled ? 'true' : 'false')
}

function openMobileSearch() {
  showMobileSearch.value = true
  localKeyword.value = props.searchKeyword
}

function closeMobileSearch() {
  showMobileSearch.value = false
}

function handleMobileSearch() {
  if (localKeyword.value.trim()) {
    emit('search', localKeyword.value.trim(), smartSearchEnabled.value)
    showMobileSearch.value = false
  }
}

function handleLogoClick() {
  if (route.path === '/') {
    router.push('/gallery')
  } else {
    router.push('/')
  }
}

const userMenuOptions = computed(() => {
  const options: any[] = [
    { label: authStore.user?.email || '用户', key: 'user-info', disabled: true },
    { label: '我的投稿', key: 'submissions' },
  ]
  if (authStore.isAuditor) {
    options.push({
      label: '管理后台',
      key: 'admin',
      icon: () => h(NIcon, null, { default: () => h(SettingsOutline) }),
    })
  }
  options.push(
    { label: '个人中心', key: 'profile' },
    { label: '修改密码', key: 'change-password' },
    {
      label: '退出登录',
      key: 'logout',
      icon: () => h(NIcon, null, { default: () => h(LogOutOutline) }),
    },
  )
  return options
})

function handleSearch() {
  emit('search', localKeyword.value, smartSearchEnabled.value)
}

function handleUserMenuSelect(key: string) {
  if (key === 'admin') router.push('/admin')
  else if (key === 'submissions') router.push('/my-submissions')
  else if (key === 'profile') router.push('/profile')
  else if (key === 'change-password') {
    emit('openChangePassword')
  }
  else if (key === 'logout') {
    dialog.warning({
      title: '确认退出',
      content: '确定要退出登录吗？',
      positiveText: '确定',
      negativeText: '取消',
      onPositiveClick: () => {
        authStore.logout()
        message.success('已退出登录')
        router.push('/login')
      },
    })
  }
}
</script>

<style scoped>
.public-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  height: 80px;
  transition: all 0.3s ease;
}

.header-home {
  background: transparent;
}

.header-scrolled {
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(12px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.header-container {
  max-width: 1440px;
  margin: 0 auto;
  height: 100%;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.header-logo {
  display: flex;
  align-items: center;
  cursor: pointer;
  flex-shrink: 0;
  user-select: none;
}

.logo-image {
  height: 120px;
  width: auto;
  display: block;
}

.header-search-mini {
  flex: 1;
  max-width: 480px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-smart-toggle {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.smart-label {
  font-size: 11px;
  transition: color 0.3s ease;
  white-space: nowrap;
}

.smart-label.smart-active {
  color: #e60012;
  font-weight: 500;
}

.header-search-mini :deep(.n-input) {
  background: #f5f5f5;
  border-radius: 20px;
}

.header-search-mini :deep(.n-input__border) {
  border: none;
}

.header-search-mini :deep(.n-input__state-border) {
  border: none;
}

.header-search-mini :deep(.n-input__suffix) {
  padding-right: 4px;
}

.search-btn-red {
  background: #e60012 !important;
  border-radius: 50% !important;
  width: 28px;
  height: 28px;
  padding: 0 !important;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.login-btn {
  background: #e60012 !important;
  border-color: #e60012 !important;
}

.login-btn:hover {
  background: #c4000f !important;
  border-color: #c4000f !important;
}

/* 手机端搜索按钮 - 默认隐藏 */
.mobile-search-btn {
  display: none;
}

/* 手机端全屏搜索层 */
.mobile-search-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background: #fff;
  padding: 8px 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
}

.mobile-search-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mobile-search-slide-enter-active,
.mobile-search-slide-leave-active {
  transition: all 0.2s ease;
}

.mobile-search-slide-enter-from,
.mobile-search-slide-leave-to {
  transform: translateY(-100%);
  opacity: 0;
}

@media (max-width: 768px) {
  .header-container {
    padding: 0 12px;
  }

  .logo-image {
    height: 80px;
  }

  .action-text {
    display: none;
  }

  .header-search-mini {
    max-width: 200px;
  }
}

@media (max-width: 480px) {
  .header-search-mini {
    display: none;
  }

  .mobile-search-btn {
    display: flex;
  }
}
</style>
