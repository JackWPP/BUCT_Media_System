<template>
  <div class="public-layout">
    <PublicHeader
      :is-home="isHome"
      :search-keyword="searchKeyword"
      :hide-search="hideHeaderSearch"
      @search="handleHeaderSearch"
      @open-change-password="showChangePassword = true"
    />
    <main class="public-main">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
    <ChangePasswordDialog v-model:show="showChangePassword" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PublicHeader from '../components/layout/PublicHeader.vue'
import ChangePasswordDialog from '../components/common/ChangePasswordDialog.vue'

const route = useRoute()
const router = useRouter()

const isHome = computed(() => route.path === '/')
const hideHeaderSearch = computed(() => route.path === '/gallery')
const searchKeyword = ref('')
const showChangePassword = ref(false)

watch(() => route.query.search, (val) => {
  searchKeyword.value = typeof val === 'string' ? val : ''
}, { immediate: true })

function handleHeaderSearch(keyword: string, smart: boolean) {
  const query: Record<string, string> = {}
  if (keyword.trim()) {
    query.search = keyword.trim()
    if (smart) query.smart = 'true'
  }
  if (Object.keys(query).length > 0) {
    router.push({ path: '/gallery', query })
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
