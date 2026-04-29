<template>
  <div>
    <n-space justify="space-between" align="center" style="margin-bottom: 16px;">
      <n-h3 style="margin: 0;">操作审计日志</n-h3>
      <n-button @click="fetchLogs" :loading="loading" secondary size="small">
        <template #icon>
          <n-icon :component="RefreshOutline" />
        </template>
        刷新
      </n-button>
    </n-space>

    <n-space style="margin-bottom: 16px;" wrap>
      <n-select v-model:value="filters.action" placeholder="操作类型" clearable style="width: 160px;"
        :options="actionOptions" @update:value="fetchLogs" />
      <n-select v-model:value="filters.resource_type" placeholder="资源类型" clearable style="width: 140px;"
        :options="resourceTypeOptions" @update:value="fetchLogs" />
      <n-input v-model:value="filters.user_id" placeholder="用户 ID" clearable style="width: 200px;"
        @update:value="handleSearch" />
    </n-space>

    <n-data-table :columns="columns" :data="logs" :loading="loading" :pagination="pagination" remote
      @update:page="handlePageChange" @update:page-size="handlePageSizeChange" />
  </div>
</template>

<script setup lang="ts">
import { h, onMounted, reactive, ref } from 'vue'
import { NTag, NText } from 'naive-ui'
import { RefreshOutline } from '@vicons/ionicons5'
import { useDebounceFn } from '@vueuse/core'
import { getAuditLogs, type AuditLogItem } from '../../api/audit'

const loading = ref(false)
const logs = ref<AuditLogItem[]>([])
const total = ref(0)

const filters = reactive({
  action: null as string | null,
  resource_type: null as string | null,
  user_id: '',
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  pageCount: 1,
  itemCount: 0,
  showSizePicker: true,
  pageSizes: [20, 50, 100],
})

const actionOptions = [
  { label: '照片通过', value: 'photo.approve' },
  { label: '照片拒绝', value: 'photo.reject' },
  { label: '照片删除', value: 'photo.delete' },
  { label: '批量通过', value: 'photo.batch_approve' },
  { label: '批量拒绝', value: 'photo.batch_reject' },
  { label: '用户创建', value: 'user.create' },
  { label: '用户删除', value: 'user.delete' },
  { label: '密码重置', value: 'user.password_reset' },
  { label: '权限变更', value: 'permission.grant' },
  { label: '批量删除', value: 'photo.batch_delete' },
  { label: '照片导入', value: 'import.photos' },
]

const resourceTypeOptions = [
  { label: '照片', value: 'photo' },
  { label: '用户', value: 'user' },
  { label: '权限', value: 'permission' },
]

function getActionTag(action: string) {
  const map: Record<string, { type: 'success' | 'warning' | 'error' | 'info'; label: string }> = {
    'photo.approve': { type: 'success', label: '通过' },
    'photo.reject': { type: 'warning', label: '拒绝' },
    'photo.delete': { type: 'error', label: '删除' },
    'photo.batch_approve': { type: 'success', label: '批量通过' },
    'photo.batch_reject': { type: 'warning', label: '批量拒绝' },
    'user.create': { type: 'info', label: '创建用户' },
    'user.delete': { type: 'error', label: '删除用户' },
    'user.password_reset': { type: 'warning', label: '密码重置' },
    'permission.grant': { type: 'info', label: '授权' },
    'photo.batch_delete': { type: 'error', label: '批量删除' },
    'import.photos': { type: 'info', label: '导入' },
  }
  const info = map[action]
  return info || { type: 'info' as const, label: action }
}

const columns = [
  {
    title: '时间',
    key: 'created_at',
    width: 180,
    render: (row: AuditLogItem) => {
      const d = new Date(row.created_at)
      return h(NText, { depth: 3 }, { default: () => d.toLocaleString('zh-CN') })
    },
  },
  {
    title: '操作人',
    key: 'user_name',
    width: 140,
    render: (row: AuditLogItem) => {
      return row.user_name || row.user_student_id || '-'
    },
  },
  {
    title: '操作',
    key: 'action',
    width: 120,
    render: (row: AuditLogItem) => {
      const tag = getActionTag(row.action)
      return h(NTag, { type: tag.type, size: 'small' }, { default: () => tag.label })
    },
  },
  {
    title: '资源类型',
    key: 'resource_type',
    width: 100,
    render: (row: AuditLogItem) => row.resource_type || '-',
  },
  {
    title: '资源 ID',
    key: 'resource_id',
    width: 160,
    ellipsis: { tooltip: true },
    render: (row: AuditLogItem) => row.resource_id || '-',
  },
  {
    title: '详情',
    key: 'detail',
    ellipsis: { tooltip: true },
    render: (row: AuditLogItem) => row.detail || '-',
  },
  {
    title: 'IP',
    key: 'ip_address',
    width: 140,
    render: (row: AuditLogItem) => row.ip_address || '-',
  },
]

async function fetchLogs() {
  loading.value = true
  try {
    const skip = (pagination.page - 1) * pagination.pageSize
    const res = await getAuditLogs({
      skip,
      limit: pagination.pageSize,
      action: filters.action || undefined,
      resource_type: filters.resource_type || undefined,
      user_id: filters.user_id || undefined,
    })
    logs.value = res.logs
    total.value = res.total
    pagination.itemCount = res.total
    pagination.pageCount = Math.ceil(res.total / pagination.pageSize)
  } catch {
    // error handled by global interceptor
  } finally {
    loading.value = false
  }
}

function handlePageChange(page: number) {
  pagination.page = page
  fetchLogs()
}

function handlePageSizeChange(pageSize: number) {
  pagination.pageSize = pageSize
  pagination.page = 1
  fetchLogs()
}

const handleSearch = useDebounceFn(() => {
  pagination.page = 1
  fetchLogs()
}, 500)

onMounted(fetchLogs)
</script>
