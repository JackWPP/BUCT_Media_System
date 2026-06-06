<template>
  <div class="tagging-workspace">
    <n-page-header title="标注工作台" subtitle="处理分配给你的照片标签和分类任务">
      <template #extra>
        <n-button @click="loadTasks" :loading="loading">刷新</n-button>
      </template>
    </n-page-header>

    <n-grid :cols="24" :x-gap="16" responsive="screen" class="workspace-grid">
      <n-grid-item :span="5">
        <n-card title="任务列表" size="small">
          <n-list v-if="tasks.length">
            <n-list-item
              v-for="task in tasks"
              :key="task.id"
              class="task-item"
              :class="{ active: selectedTask?.id === task.id }"
              @click="selectTask(task)"
            >
              <n-space vertical size="small">
                <n-text strong>{{ task.title }}</n-text>
                <n-space>
                  <n-tag size="small">{{ task.status }}</n-tag>
                  <n-text depth="3">{{ task.items.length }} 张</n-text>
                </n-space>
              </n-space>
            </n-list-item>
          </n-list>
          <n-empty v-else description="暂无标注任务" />
        </n-card>
      </n-grid-item>

      <n-grid-item :span="19">
        <n-card v-if="selectedItem?.photo" size="small">
          <template #header>
            <n-space justify="space-between" align="center">
              <span>{{ selectedItem.photo.filename }}</span>
              <n-select
                v-model:value="selectedItemId"
                :options="itemOptions"
                style="width: 220px"
                @update:value="handleItemSelect"
              />
            </n-space>
          </template>

          <div class="editor-layout">
            <div class="image-panel">
              <img :src="getPhotoUrl(selectedItem.photo.id, 'compressed')" :alt="selectedItem.photo.filename" />
            </div>

            <div class="side-panel">
              <n-space vertical size="large">
                <div>
                  <n-text strong>自由标签</n-text>
                  <n-dynamic-tags v-model:value="tagDraft" style="margin-top: 8px" />
                  <n-input
                    v-model:value="tagSearch"
                    placeholder="搜索已有标签候选"
                    clearable
                    style="margin-top: 10px"
                    @update:value="loadTagSuggestions"
                  />
                  <n-space v-if="tagSuggestions.length" wrap style="margin-top: 8px">
                    <n-tag
                      v-for="tag in tagSuggestions"
                      :key="tag.id"
                      class="candidate-tag"
                      @click="addCandidateTag(tag.name)"
                    >
                      {{ tag.name }}
                    </n-tag>
                  </n-space>
                </div>

                <div>
                  <n-text strong>核心分类</n-text>
                  <n-form label-placement="top" style="margin-top: 8px">
                    <n-form-item v-for="facet in singleFacets" :key="facet.key" :label="facet.name">
                      <n-select
                        v-model:value="classificationDraft[facet.key]"
                        :options="facetNodeOptions(facet)"
                        clearable
                        filterable
                      />
                    </n-form-item>
                  </n-form>
                </div>

                <div v-if="multiFacets.length">
                  <n-text strong>细分标签</n-text>
                  <n-collapse style="margin-top: 8px">
                    <n-collapse-item
                      v-for="facet in multiFacets"
                      :key="facet.key"
                      :title="facet.name"
                      :name="facet.key"
                    >
                      <n-select
                        v-model:value="multiClassificationDraft[facet.key]"
                        :options="facetNodeOptions(facet)"
                        multiple
                        clearable
                        filterable
                        placeholder="可多选"
                      />
                    </n-collapse-item>
                  </n-collapse>
                  <div v-if="selectedFineTagCount" class="selected-summary">
                    已选择 {{ selectedFineTagCount }} 个细分标签
                  </div>
                </div>

                <n-input v-model:value="note" type="textarea" :rows="3" placeholder="提交说明（可选）" />

                <n-alert v-if="selectedItem.status !== 'pending' && selectedItem.status !== 'rejected'" type="info">
                  当前状态：{{ selectedItem.status }}。已提交或已审核的条目不会直接修改正式数据，需等待管理员审核。
                </n-alert>

                <n-button
                  type="primary"
                  block
                  :loading="submitting"
                  :disabled="!canSubmit"
                  @click="submitCurrent"
                >
                  提交审核
                </n-button>
              </n-space>
            </div>
          </div>
        </n-card>
        <n-empty v-else description="请选择一个标注任务" />
      </n-grid-item>
    </n-grid>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useMessage } from 'naive-ui'
import { getTagSuggestions, type TagSuggestion } from '../api/tag'
import { getPublicTaxonomy, type TaxonomyFacet } from '../api/taxonomy'
import { getTaggingTasks, submitTaggingItem, type TaggingTask, type TaggingTaskItem } from '../api/taggingTasks'
import { getPhotoUrl } from '../utils/format'

const message = useMessage()
const loading = ref(false)
const submitting = ref(false)
const tasks = ref<TaggingTask[]>([])
const selectedTask = ref<TaggingTask | null>(null)
const selectedItemId = ref<string | null>(null)
const taxonomyFacets = ref<TaxonomyFacet[]>([])
const tagDraft = ref<string[]>([])
const tagSearch = ref('')
const tagSuggestions = ref<TagSuggestion[]>([])
const classificationDraft = reactive<Record<string, number | null>>({})
const multiClassificationDraft = reactive<Record<string, number[]>>({})
const note = ref('')

const selectedItem = computed(() =>
  selectedTask.value?.items.find((item) => item.id === selectedItemId.value) || null,
)

const itemOptions = computed(() =>
  (selectedTask.value?.items || []).map((item, index) => ({
    label: `${index + 1}. ${item.photo?.filename || item.photo_id} (${item.status})`,
    value: item.id,
  })),
)

const canSubmit = computed(() =>
  !!selectedItem.value && ['pending', 'submitted', 'rejected'].includes(selectedItem.value.status),
)

const singleFacets = computed(() =>
  taxonomyFacets.value.filter((facet) => facet.selection_mode !== 'multiple'),
)

const multiFacets = computed(() =>
  taxonomyFacets.value.filter((facet) => facet.selection_mode === 'multiple'),
)

const selectedFineTagCount = computed(() =>
  Object.values(multiClassificationDraft).reduce((sum, values) => sum + values.length, 0),
)

onMounted(async () => {
  await Promise.all([loadTaxonomy(), loadTasks()])
})

async function loadTaxonomy() {
  taxonomyFacets.value = await getPublicTaxonomy()
}

async function loadTasks() {
  loading.value = true
  try {
    const response = await getTaggingTasks({ limit: 100 })
    tasks.value = response.items
    if (!selectedTask.value && tasks.value.length) selectTask(tasks.value[0])
  } finally {
    loading.value = false
  }
}

function selectTask(task: TaggingTask) {
  selectedTask.value = task
  selectedItemId.value = task.items[0]?.id || null
  hydrateDraft()
}

function handleItemSelect() {
  hydrateDraft()
}

function hydrateDraft() {
  const item = selectedItem.value
  tagDraft.value = item?.submitted_tags || item?.photo?.free_tags || item?.photo?.tags || []
  Object.keys(classificationDraft).forEach((key) => delete classificationDraft[key])
  Object.keys(multiClassificationDraft).forEach((key) => delete multiClassificationDraft[key])
  taxonomyFacets.value.forEach((facet) => {
    const submitted = item?.submitted_classifications?.[facet.key]?.node_id
    const current = item?.photo?.classifications?.[facet.key]?.node_id
    const submittedIds = item?.submitted_classifications?.[facet.key]?.node_ids
    const currentValue = item?.photo?.classifications?.[facet.key]
    const currentIds = Array.isArray(currentValue) ? currentValue.map((value) => value.node_id) : []
    if (facet.selection_mode === 'multiple') {
      multiClassificationDraft[facet.key] = submittedIds || currentIds || []
    } else {
      classificationDraft[facet.key] = submitted || current || null
    }
  })
  note.value = item?.submitter_note || ''
}

function facetNodeOptions(facet: TaxonomyFacet) {
  const flatten = (nodes: TaxonomyFacet['nodes']): Array<{ label: string; value: number }> =>
    nodes.flatMap((node) => [
      { label: node.name, value: node.id },
      ...flatten(node.children || []),
    ])
  return flatten(facet.nodes)
}

async function loadTagSuggestions(value: string) {
  if (!value.trim()) {
    tagSuggestions.value = []
    return
  }
  tagSuggestions.value = await getTagSuggestions(value.trim())
}

function addCandidateTag(name: string) {
  if (!tagDraft.value.includes(name)) tagDraft.value.push(name)
}

async function submitCurrent() {
  if (!selectedItem.value) return
  submitting.value = true
  try {
    const classifications: Record<string, number | number[]> = {}
    Object.entries(classificationDraft).forEach(([key, value]) => {
      if (value) classifications[key] = value
    })
    Object.entries(multiClassificationDraft).forEach(([key, values]) => {
      if (values.length) classifications[key] = values
    })
    const updated = await submitTaggingItem(selectedItem.value.id, {
      tags: tagDraft.value,
      classifications,
      note: note.value || undefined,
    })
    replaceItem(updated)
    message.success('已提交审核')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '提交失败')
  } finally {
    submitting.value = false
  }
}

function replaceItem(updated: TaggingTaskItem) {
  if (!selectedTask.value) return
  const index = selectedTask.value.items.findIndex((item) => item.id === updated.id)
  if (index !== -1) selectedTask.value.items[index] = updated
}
</script>

<style scoped>
.tagging-workspace {
  padding: 24px;
}

.workspace-grid {
  margin-top: 16px;
}

.task-item {
  cursor: pointer;
  padding: 8px;
  border-radius: 6px;
}

.task-item.active {
  background: #f3f4f6;
}

.editor-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 20px;
}

.image-panel {
  min-height: 540px;
  background: #111827;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  overflow: hidden;
}

.image-panel img {
  max-width: 100%;
  max-height: 720px;
  object-fit: contain;
}

.side-panel {
  min-width: 0;
}

.candidate-tag {
  cursor: pointer;
}

@media (max-width: 960px) {
  .editor-layout {
    grid-template-columns: 1fr;
  }
}
</style>
