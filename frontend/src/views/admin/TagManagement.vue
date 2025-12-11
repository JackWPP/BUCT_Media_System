<template>
  <div class="tag-management">
    <n-space vertical size="large">
      <!-- 标题和操作 -->
      <n-space justify="space-between">
        <n-text strong style="font-size: 24px;">标签管理</n-text>
        <n-button type="primary" @click="showCreateModal = true">
          创建标签
        </n-button>
      </n-space>

      <!-- 搜索和筛选 -->
      <n-space>
        <n-input
          v-model:value="searchQuery"
          placeholder="搜索标签..."
          clearable
          style="width: 300px;"
          @update:value="handleSearch"
        >
          <template #prefix>
            <n-icon :component="SearchOutline" />
          </template>
        </n-input>
        <n-select
          v-model:value="categoryFilter"
          :options="categoryOptions"
          placeholder="筛选分类"
          clearable
          style="width: 200px;"
          @update:value="loadTags"
        />
      </n-space>

      <!-- 标签表格 -->
      <n-data-table
        :columns="columns"
        :data="tags"
        :loading="loading"
        :pagination="pagination"
        :bordered="false"
      />
    </n-space>

    <!-- 创建/编辑标签对话框 -->
    <n-modal
      v-model:show="showCreateModal"
      preset="dialog"
      :title="editingTag ? '编辑标签' : '创建标签'"
      :positive-text="editingTag ? '保存' : '创建'"
      :negative-text="'取消'"
      @positive-click="handleSubmit"
    >
      <n-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-placement="left"
        label-width="80px"
      >
        <n-form-item label="标签名称" path="name">
          <n-input v-model:value="formData.name" placeholder="输入标签名称" />
        </n-form-item>
        <n-form-item label="分类" path="category">
          <n-select
            v-model:value="formData.category"
            :options="categoryOptions"
            placeholder="选择分类"
            clearable
          />
        </n-form-item>
        <n-form-item label="颜色" path="color">
          <n-color-picker v-model:value="formData.color" :modes="['hex']" />
        </n-form-item>
      </n-form>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, h, onMounted } from 'vue'
import { NButton, NTag, NPopconfirm, NIcon, useMessage, type DataTableColumns } from 'naive-ui'
import { SearchOutline, CreateOutline, TrashOutline } from '@vicons/ionicons5'
import { getTags, createTag, updateTag, deleteTag, type Tag, type TagCreate } from '@/api/tag'

const message = useMessage()

const loading = ref(false)
const tags = ref<Tag[]>([])
const totalTags = ref(0)
const searchQuery = ref('')
const categoryFilter = ref<string | null>(null)
const showCreateModal = ref(false)
const editingTag = ref<Tag | null>(null)

const pagination = reactive({
  page: 1,
  pageSize: 20,
  pageCount: 1,
  itemCount: 0,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
  onChange: (page: number) => {
    pagination.page = page
    loadTags()
  },
  onUpdatePageSize: (pageSize: number) => {
    pagination.pageSize = pageSize
    pagination.page = 1
    loadTags()
  },
})

const categoryOptions = [
  { label: 'Object (物体)', value: 'object' },
  { label: 'Scene (场景)', value: 'scene' },
  { label: 'Color (颜色)', value: 'color' },
  { label: 'Mood (情绪)', value: 'mood' },
]

const formData = reactive<TagCreate>({
  name: '',
  category: undefined,
  color: '#18a058',
})

const formRules = {
  name: {
    required: true,
    message: '请输入标签名称',
    trigger: 'blur',
  },
}

const columns: DataTableColumns<Tag> = [
  {
    title: 'ID',
    key: 'id',
    width: 80,
  },
  {
    title: '标签名称',
    key: 'name',
    render(row) {
      return h(
        NTag,
        { type: 'info', color: { color: row.color || '#18a058', textColor: '#fff' } },
        { default: () => row.name }
      )
    },
  },
  {
    title: '分类',
    key: 'category',
    width: 150,
    render(row) {
      return row.category || '-'
    },
  },
  {
    title: '使用次数',
    key: 'usage_count',
    width: 120,
  },
  {
    title: '创建时间',
    key: 'created_at',
    width: 180,
    render(row) {
      return new Date(row.created_at).toLocaleString('zh-CN')
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 200,
    render(row) {
      return h(
        'div',
        { style: 'display: flex; gap: 8px;' },
        [
          h(
            NButton,
            {
              size: 'small',
              onClick: () => handleEdit(row),
            },
            { default: () => '编辑', icon: () => h(NIcon, null, { default: () => h(CreateOutline) }) }
          ),
          h(
            NPopconfirm,
            {
              onPositiveClick: () => handleDelete(row.id),
            },
            {
              trigger: () => h(
                NButton,
                { size: 'small', type: 'error' },
                { default: () => '删除', icon: () => h(NIcon, null, { default: () => h(TrashOutline) }) }
              ),
              default: () => '确定要删除这个标签吗？这将删除所有照片中的此标签。',
            }
          ),
        ]
      )
    },
  },
]

onMounted(() => {
  loadTags()
})

async function loadTags() {
  loading.value = true
  try {
    const skip = (pagination.page - 1) * pagination.pageSize
    const response = await getTags({
      skip,
      limit: pagination.pageSize,
      search: searchQuery.value || undefined,
      category: categoryFilter.value || undefined,
    })
    
    tags.value = response.items
    totalTags.value = response.total
    pagination.itemCount = response.total
    pagination.pageCount = Math.ceil(response.total / pagination.pageSize)
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '加载标签失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  loadTags()
}

function handleEdit(tag: Tag) {
  editingTag.value = tag
  formData.name = tag.name
  formData.category = tag.category || undefined
  formData.color = tag.color || '#18a058'
  showCreateModal.value = true
}

async function handleSubmit() {
  try {
    if (editingTag.value) {
      // 编辑
      await updateTag(editingTag.value.id, {
        name: formData.name,
        category: formData.category,
        color: formData.color,
      })
      message.success('标签已更新')
    } else {
      // 创建
      await createTag(formData)
      message.success('标签已创建')
    }
    
    showCreateModal.value = false
    resetForm()
    loadTags()
    return true
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '操作失败')
    return false
  }
}

async function handleDelete(tagId: number) {
  try {
    await deleteTag(tagId)
    message.success('标签已删除')
    loadTags()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '删除失败')
  }
}

function resetForm() {
  editingTag.value = null
  formData.name = ''
  formData.category = undefined
  formData.color = '#18a058'
}
</script>

<style scoped>
.tag-management {
  max-width: 1400px;
  margin: 0 auto;
}
</style>
