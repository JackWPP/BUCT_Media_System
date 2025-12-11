<template>
  <div class="photo-card-skeleton">
    <n-card>
      <template #cover>
        <n-skeleton height="200px" />
      </template>
      <n-skeleton text :repeat="2" />
      <n-skeleton text style="width: 60%; margin-top: 8px;" />
    </n-card>
  </div>
</template>

<script setup lang="ts">
// 照片卡片骨架屏组件
</script>

<style scoped>
.photo-card-skeleton {
  width: 100%;
}
</style>
