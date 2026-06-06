<template>
  <div class="tagging-admin">
    <n-space vertical size="large">
      <n-space justify="space-between" align="center">
        <n-text strong style="font-size: 24px">标注任务</n-text>
        <n-space>
          <n-button @click="loadData" :loading="loading">刷新</n-button>
          <n-button type="primary" @click="openCreate">新建任务</n-button>
        </n-space>
      </n-space>

      <n-card v-for="task in tasks" :key="task.id" size="small" :title="task.title">
        <template #header-extra>
          <n-space>
            <n-tag>{{ assigneeLabel(task.assignee_id) }}</n-tag>
            <n-tag>{{ task.status }}</n-tag>
          </n-space>
        </template>
        <n-data-table :columns="columns" :data="task.items" :bordered="false" size="small" />
      </n-card>
      <n-empty v-if="!tasks.length && !loading" description="暂无标注任务" />
    </n-space>

    <n-modal v-model:show="showCreate" preset="card" title="批量新建标注任务" class="create-modal">
      <n-space vertical size="large">
        <n-form :model="form" label-placement="left" label-width="90">
          <n-form-item label="任务名称">
            <n-input v-model:value="form.title" placeholder="例如：五月图库标签补充" />
          </n-form-item>
          <n-form-item label="说明">
            <n-input v-model:value="form.description" type="textarea" :rows="2" />
          </n-form-item>
          <n-form-item label="标注学生">
            <n-select
              v-model:value="form.assignee_ids"
              multiple
              :options="taggerOptions"
              filterable
              placeholder="选择一个或多个 tagger 账号"
            />
          </n-form-item>
        </n-form>

        <n-card size="small" title="候选照片">
          <template #header-extra>
            <n-space align="center">
              <n-radio-group v-model:value="candidateMode" size="small" @update:value="reloadCandidates">
                <n-radio-button value="all">全部照片</n-radio-button>
                <n-radio-button value="zero_tags">0 标签照片</n-radio-button>
              </n-radio-group>
              <n-radio-group v-model:value="candidatePhotoType" size="small" @update:value="reloadCandidates">
                <n-radio-button value="">全部题材</n-radio-button>
                <n-radio-button value="校园风光">校园风光</n-radio-button>
                <n-radio-button value="人文纪实">人文纪实</n-radio-button>
                <n-radio-button value="自然生态">自然生态</n-radio-button>
              </n-radio-group>
              <n-input
                v-model:value="candidateSearch"
                placeholder="搜索文件名/描述/标签"
                clearable
                style="width: 220px"
                @keyup.enter="reloadCandidates"
              />
              <n-button size="small" @click="reloadCandidates">筛选</n-button>
            </n-space>
          </template>

          <n-space justify="space-between" align="center" class="candidate-toolbar">
            <n-space>
              <n-button size="small" @click="selectCurrentPage">选中当前页</n-button>
              <n-button size="small" @click="clearSelection">清空选择</n-button>
              <n-checkbox v-model:checked="assignAllMatched">
                分派全部匹配照片（{{ candidateTotal }} 张）
              </n-checkbox>
            </n-space>
            <n-text depth="3">已手动选择 {{ selectedPhotoIds.length }} 张</n-text>
          </n-space>

          <n-spin :show="candidateLoading">
            <div class="photo-grid">
              <div
                v-for="photo in candidates"
                :key="photo.id"
                class="photo-tile"
                :class="{ selected: selectedSet.has(photo.id) }"
                @click="togglePhoto(photo.id)"
              >
                <img :src="getPhotoUrl(photo.id, 'thumbnail')" :alt="photo.filename" />
                <div class="tile-check">
                  <n-checkbox :checked="selectedSet.has(photo.id)" @click.stop @update:checked="() => togglePhoto(photo.id)" />
                </div>
                <div class="tile-meta">
                  <span>{{ photo.filename }}</span>
                  <n-tag size="tiny">{{ (photo.free_tags || photo.tags || []).length }} 标签</n-tag>
                </div>
              </div>
            </div>
          </n-spin>

          <n-pagination
            v-model:page="candidatePage"
            :page-size="candidatePageSize"
            :item-count="candidateTotal"
            style="margin-top: 12px"
            @update:page="loadCandidates"
          />
        </n-card>
      </n-space>

      <template #footer>
        <n-space justify="space-between" align="center">
          <n-text depth="3">
            将按学生数平均分派，生成 {{ form.assignee_ids.length || 0 }} 个任务。
          </n-text>
          <n-space>
            <n-button @click="showCreate = false">取消</n-button>
            <n-button type="primary" :loading="submitting" @click="createBatchTasks">创建并平均分派</n-button>
          </n-space>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue'
import { NButton, NImage, NSpace, NTag, useMessage, type DataTableColumns } from 'naive-ui'
import {
  approveTaggingItem,
  createTaggingTaskBatch,
  getTaggingAssignees,
  getTaggingPhotoCandidates,
  getTaggingTasks,
  rejectTaggingItem,
  type TaggingTask,
  type TaggingTaskItem,
} from '@/api/taggingTasks'
import type { Photo } from '@/types/photo'
import type { User } from '@/types/user'
import { getPhotoUrl } from '@/utils/format'

const message = useMessage()
const loading = ref(false)
const submitting = ref(false)
const showCreate = ref(false)
const tasks = ref<TaggingTask[]>([])
const users = ref<User[]>([])
const candidates = ref<Photo[]>([])
const candidateLoading = ref(false)
const candidateTotal = ref(0)
const candidatePage = ref(1)
const candidatePageSize = 36
const candidateMode = ref<'all' | 'zero_tags'>('zero_tags')
const candidatePhotoType = ref<'' | '校园风光' | '人文纪实' | '自然生态'>('')
const candidateSearch = ref('')
const selectedPhotoIds = ref<string[]>([])
const assignAllMatched = ref(true)

const form = reactive({
  title: '',
  description: '',
  assignee_ids: [] as string[],
})

const selectedSet = computed(() => new Set(selectedPhotoIds.value))

const taggerOptions = computed(() =>
  users.value
    .filter((user) => ['tagger', 'auditor', 'admin'].includes(user.role))
    .map((user) => ({
      label: `${user.full_name || user.student_id || user.email} (${user.role})`,
      value: user.id,
    })),
)

const columns: DataTableColumns<TaggingTaskItem> = [
  {
    title: '照片',
    key: 'photo',
    width: 220,
    render(row) {
      return h(NSpace, { align: 'center' }, {
        default: () => [
          row.photo ? h(NImage, { src: getPhotoUrl(row.photo.id, 'thumbnail'), width: 64, height: 42, objectFit: 'cover' }) : null,
          h('span', row.photo?.filename || row.photo_id),
        ],
      })
    },
  },
  {
    title: '状态',
    key: 'status',
    width: 110,
    render(row) {
      return h(NTag, { size: 'small' }, { default: () => row.status })
    },
  },
  {
    title: '提交标签',
    key: 'submitted_tags',
    render(row) {
      return (row.submitted_tags || []).join('、') || '-'
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 180,
    render(row) {
      return h(NSpace, {}, {
        default: () => [
          h(NButton, { size: 'small', type: 'primary', disabled: row.status !== 'submitted', onClick: () => review(row, true) }, { default: () => '通过' }),
          h(NButton, { size: 'small', type: 'error', disabled: row.status !== 'submitted', onClick: () => review(row, false) }, { default: () => '驳回' }),
        ],
      })
    },
  },
]

onMounted(loadData)

async function loadData() {
  loading.value = true
  try {
    const [taskResponse, userResponse] = await Promise.all([
      getTaggingTasks({ limit: 100 }),
      getTaggingAssignees(),
    ])
    tasks.value = taskResponse.items
    users.value = userResponse
  } finally {
    loading.value = false
  }
}

function openCreate() {
  showCreate.value = true
  if (!candidates.value.length) loadCandidates()
}

function assigneeLabel(id: string) {
  const user = users.value.find((item) => item.id === id)
  return user?.full_name || user?.student_id || user?.email || id
}

async function reloadCandidates() {
  candidatePage.value = 1
  await loadCandidates()
}

async function loadCandidates() {
  candidateLoading.value = true
  try {
    const response = await getTaggingPhotoCandidates({
      selection_mode: candidateMode.value,
      status: 'approved',
      search: candidateSearch.value || undefined,
      photo_type: candidatePhotoType.value || undefined,
      skip: (candidatePage.value - 1) * candidatePageSize,
      limit: candidatePageSize,
    })
    candidates.value = response.items
    candidateTotal.value = response.total
  } finally {
    candidateLoading.value = false
  }
}

function togglePhoto(photoId: string) {
  if (selectedSet.value.has(photoId)) {
    selectedPhotoIds.value = selectedPhotoIds.value.filter((id) => id !== photoId)
  } else {
    selectedPhotoIds.value = [...selectedPhotoIds.value, photoId]
  }
}

function selectCurrentPage() {
  const ids = new Set(selectedPhotoIds.value)
  candidates.value.forEach((photo) => ids.add(photo.id))
  selectedPhotoIds.value = [...ids]
  assignAllMatched.value = false
}

function clearSelection() {
  selectedPhotoIds.value = []
  assignAllMatched.value = false
}

async function createBatchTasks() {
  if (!form.title || !form.assignee_ids.length) {
    message.error('请填写任务名称并选择标注学生')
    return
  }
  if (!assignAllMatched.value && !selectedPhotoIds.value.length) {
    message.error('请选择照片，或勾选分派全部匹配照片')
    return
  }
  submitting.value = true
  try {
    await createTaggingTaskBatch({
      title: form.title,
      description: form.description || undefined,
      assignee_ids: form.assignee_ids,
      selection_mode: assignAllMatched.value ? candidateMode.value : 'manual',
      search: assignAllMatched.value ? candidateSearch.value || undefined : undefined,
      photo_type: assignAllMatched.value ? candidatePhotoType.value || undefined : undefined,
      status: 'approved',
      photo_ids: assignAllMatched.value ? [] : selectedPhotoIds.value,
      max_photos: 20000,
    })
    message.success('任务已创建并平均分派')
    showCreate.value = false
    form.title = ''
    form.description = ''
    form.assignee_ids = []
    selectedPhotoIds.value = []
    assignAllMatched.value = true
    await loadData()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '创建失败')
  } finally {
    submitting.value = false
  }
}

async function review(row: TaggingTaskItem, approved: boolean) {
  try {
    if (approved) await approveTaggingItem(row.id)
    else await rejectTaggingItem(row.id)
    message.success(approved ? '已通过' : '已驳回')
    await loadData()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '审核失败')
  }
}
</script>

<style scoped>
.tagging-admin {
  max-width: 1400px;
  margin: 0 auto;
}

.create-modal {
  width: min(1180px, 92vw);
}

.candidate-toolbar {
  margin-bottom: 12px;
}

.photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(132px, 1fr));
  gap: 10px;
  min-height: 240px;
}

.photo-tile {
  position: relative;
  border: 2px solid transparent;
  border-radius: 8px;
  overflow: hidden;
  background: #f3f4f6;
  cursor: pointer;
}

.photo-tile.selected {
  border-color: #18a058;
}

.photo-tile img {
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
  display: block;
}

.tile-check {
  position: absolute;
  top: 6px;
  right: 6px;
  background: rgba(255, 255, 255, 0.86);
  border-radius: 4px;
  padding: 2px;
}

.tile-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 6px;
  font-size: 12px;
}

.tile-meta span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
