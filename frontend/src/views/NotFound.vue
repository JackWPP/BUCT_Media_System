<template>
  <div class="not-found-container">
    <n-result status="404" title="404 页面不存在" description="您访问的页面不存在">
      <template #footer>
        <n-button @click="router.push('/')">返回首页</n-button>
      </template>
    </n-result>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<style scoped>
.not-found-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
}
</style>
