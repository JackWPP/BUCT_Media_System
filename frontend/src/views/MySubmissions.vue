<template>
  <div class="my-submissions-container">
    <n-card title="我的投稿">
      <template #header-extra>
        <n-button type="primary" @click="goToUpload">
          <template #icon>
            <n-icon><CloudUploadOutline /></n-icon>
          </template>
          上传新照片
        </n-button>
      </template>

      <!-- 筛选栏 -->
      <n-space class="mb-4">
        <n-select
          v-model:value="statusFilter"
          placeholder="状态筛选"
          :options="statusOptions"
          clearable
          style="width: 140px"
          @update:value="fetchPhotos"
        />
        <n-input
          v-model:value="searchQuery"
          placeholder="搜索文件名..."
          clearable
          style="width: 200px"
          @keyup.enter="fetchPhotos"
        >
          <template #prefix>
            <n-icon><SearchIcon /></n-icon>
          </template>
        </n-input>
      </n-space>

      <n-spin :show="loading">
        <n-data-table
          :columns="columns"
          :data="photos"
          :bordered="false"
          :pagination="pagination"
          remote
          @update:page="handlePageChange"
        />
      </n-spin>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, h, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, NTag, NButton, NSpace, NImage } from 'naive-ui'
import { CloudUploadOutline, Search as SearchIcon } from '@vicons/ionicons5'
import type { DataTableColumns } from 'naive-ui'
import type { Photo } from '../types/photo'
import * as photoApi from '../api/photo'

const router = useRouter()
const message = useMessage()

// 状态
const loading = ref(false)
const photos = ref<Photo[]>([])
const statusFilter = ref<string | null>(null)
const searchQuery = ref('')
const total = ref(0)

const statusOptions = [
  { label: '审核中', value: 'pending' },
  { label: '已发布', value: 'approved' },
  { label: '已驳回', value: 'rejected' },
]

const pagination = reactive({
  page: 1,
  pageSize: 10,
  pageCount: 1,
  showSizePicker: true,
  pageSizes: [10, 20, 50],
  onUpdatePageSize: (pageSize: number) => {
    pagination.pageSize = pageSize
    pagination.page = 1
    fetchPhotos()
  }
})

// 表格列定义
const columns: DataTableColumns<Photo> = [
  {
    title: '预览',
    key: 'thumb_path',
    width: 100,
    render(row) {
      if (!row.thumb_path) return '无'
      return h(NImage, {
        src: getImageUrl(row.thumb_path),
        width: 80,
        height: 60,
        objectFit: 'cover',
        style: { borderRadius: '4px' }
      })
    }
  },
  { title: '文件名', key: 'filename', ellipsis: { tooltip: true } },
  { title: '描述', key: 'description', ellipsis: { tooltip: true } },
  { 
    title: '分类', 
    key: 'category', 
    width: 100,
    render(row) {
      return row.category || '-'
    }
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render(row) {
      let type: 'default' | 'success' | 'warning' | 'error' = 'default'
      let label = '未知'
      
      switch (row.status) {
        case 'approved':
          type = 'success'
          label = '已发布'
          break
        case 'pending':
          type = 'warning'
          label = '审核中'
          break
        case 'rejected':
          type = 'error'
          label = '已驳回'
          break
      }
      return h(NTag, { type, size: 'small' }, { default: () => label })
    }
  },
  {
    title: '提交时间',
    key: 'created_at',
    width: 180,
    render(row) {
      return new Date(row.created_at).toLocaleString()
    }
  }
]

// 方法
function getImageUrl(path: string) {
  if (!path) return ''
  // 简单处理路径，实际应根据后端配置
  return `/api/v1/static/${path.split('/').pop()}`
}

async function fetchPhotos() {
  loading.value = true
  try {
    const res = await photoApi.getMySubmissions({
      skip: (pagination.page - 1) * pagination.pageSize,
      limit: pagination.pageSize,
      status: statusFilter.value || undefined,
      search: searchQuery.value || undefined
    })
    
    photos.value = res.items
    total.value = res.total
    pagination.pageCount = Math.ceil(res.total / pagination.pageSize)
  } catch (error) {
    message.error('加载投稿列表失败')
  } finally {
    loading.value = false
  }
}

function handlePageChange(page: number) {
  pagination.page = page
  fetchPhotos()
}

function goToUpload() {
  router.push('/upload')
}

onMounted(() => {
  fetchPhotos()
})
</script>

<style scoped>
.my-submissions-container {
  padding: 24px;
}
.mb-4 {
  margin-bottom: 16px;
}
</style>
