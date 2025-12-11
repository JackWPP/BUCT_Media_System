<template>
  <n-config-provider :theme="appStore.darkMode ? darkTheme : null">
    <n-message-provider>
      <n-dialog-provider>
        <n-notification-provider>
          <router-view />
        </n-notification-provider>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { darkTheme } from 'naive-ui'
import { useAuthStore } from './stores/auth'
import { useAppStore } from './stores/app'
import './assets/styles/main.css'

const authStore = useAuthStore()
const appStore = useAppStore()

onMounted(() => {
  // 初始化应用状态
  appStore.init()
  // 从存储恢复认证状态
  authStore.initFromStorage()
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app {
  width: 100%;
  min-height: 100vh;
}
</style>
