<template>
  <div class="public-layout">
    <PublicHeader
      :is-home="isHome"
      :search-keyword="searchKeyword"
      @search="handleHeaderSearch"
    />
    <main class="public-main">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PublicHeader from '../components/layout/PublicHeader.vue'

const route = useRoute()
const router = useRouter()

const isHome = computed(() => route.path === '/')
const searchKeyword = ref('')

watch(() => route.query.search, (val) => {
  searchKeyword.value = typeof val === 'string' ? val : ''
}, { immediate: true })

function handleHeaderSearch(keyword: string) {
  if (keyword.trim()) {
    router.push({ path: '/gallery', query: { search: keyword.trim() } })
  } else {
    router.push('/gallery')
  }
}
</script>

<style scoped>
.public-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.public-main {
  flex: 1;
}
</style>
