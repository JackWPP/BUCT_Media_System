<template>
  <div class="tagging-workspace">
    <n-page-header title="标注工作台" subtitle="补全作品信息，选择专区、校区、类别和明显可见的标准标签">
      <template #extra>
        <n-space align="center">
          <n-tag v-if="draftState" size="small" :type="draftState === '已保存' ? 'success' : 'warning'">
            {{ draftState }}
          </n-tag>
          <n-button @click="loadTasks" :loading="loading">刷新</n-button>
        </n-space>
      </template>
    </n-page-header>

    <div class="workspace-grid">
      <aside class="task-column">
        <n-card title="任务" size="small">
          <n-list v-if="tasks.length">
            <n-list-item
              v-for="task in tasks"
              :key="task.id"
              class="task-item"
              :class="{ active: selectedTask?.id === task.id }"
              @click="selectTask(task)"
            >
              <n-space vertical size="small">
                <n-space justify="space-between" align="center">
                  <n-text strong>{{ task.title }}</n-text>
                  <n-tag size="small">{{ statusLabel(task.status) }}</n-tag>
                </n-space>
                <n-progress
                  type="line"
                  :percentage="task.stats?.completion_rate || 0"
                  :height="6"
                  :show-indicator="false"
                />
                <n-text depth="3" class="small-text">
                  {{ task.stats?.approved || 0 }} 已通过 / {{ task.stats?.submitted || 0 }} 待审核 / {{ task.stats?.pending || 0 }} 待标注
                </n-text>
              </n-space>
            </n-list-item>
          </n-list>
          <n-empty v-else description="暂无标注任务" />
        </n-card>

        <n-card v-if="selectedTask" title="照片队列" size="small">
          <n-radio-group v-model:value="queueFilter" size="small">
            <n-radio-button value="all">全部</n-radio-button>
            <n-radio-button value="pending">待标</n-radio-button>
            <n-radio-button value="submitted">待审</n-radio-button>
            <n-radio-button value="rejected">驳回</n-radio-button>
          </n-radio-group>
          <div class="queue-list">
            <button
              v-for="(item, index) in filteredItems"
              :key="item.id"
              class="queue-item"
              :class="{ active: selectedItem?.id === item.id }"
              type="button"
              @click="selectItem(item.id)"
            >
              <span>{{ index + 1 }}</span>
              <img v-if="item.photo" :src="getPhotoUrl(item.photo.id, 'thumbnail')" :alt="item.photo.filename" />
              <div>
                <strong>{{ item.photo?.filename || item.photo_id }}</strong>
                <small>{{ statusLabel(item.status) }}</small>
              </div>
            </button>
          </div>
        </n-card>
      </aside>

      <main v-if="selectedItem?.photo" class="photo-column">
        <section class="photo-toolbar">
          <n-space vertical size="small">
            <n-text strong>{{ selectedItem.photo.filename }}</n-text>
            <n-text depth="3">
              {{ currentIndex + 1 }} / {{ selectedTask?.items.length || 0 }}
            </n-text>
          </n-space>
          <n-space>
            <n-button :disabled="!previousItem" @click="goRelative(-1)">上一张</n-button>
            <n-button :disabled="!nextItem" @click="goRelative(1)">下一张</n-button>
          </n-space>
        </section>

        <section class="image-panel">
          <img :src="getPhotoUrl(selectedItem.photo.id, 'compressed')" :alt="selectedItem.photo.filename" />
        </section>

        <section class="metadata-panel">
          <div>
            <span>导入描述</span>
            <p>{{ selectedItem.photo.description || '暂无描述' }}</p>
          </div>
          <div>
            <span>已有分类</span>
            <p>{{ existingClassificationSummary || '暂无' }}</p>
          </div>
        </section>
      </main>

      <aside v-if="selectedItem?.photo" class="question-column">
        <n-card size="small" title="选择题">
          <n-space vertical size="large">
            <section class="question-section">
              <div class="section-head">
                <strong>1. 作品信息</strong>
                <n-tag size="small">建议填写</n-tag>
              </div>
              <n-form label-placement="top">
                <n-form-item label="作品名称">
                  <n-input v-model:value="titleDraft" clearable placeholder="可从作品名、描述或文件名中整理" />
                </n-form-item>
                <n-form-item label="作者">
                  <n-input v-model:value="authorDraft" clearable placeholder="填写作者姓名；不确定可暂留空" />
                </n-form-item>
              </n-form>
            </section>

            <section class="question-section">
              <div class="section-head">
                <strong>2. 核心分类</strong>
                <n-tag size="small" type="error">必填</n-tag>
              </div>
              <n-form label-placement="top">
                <n-form-item label="专区">
                  <n-radio-group v-model:value="classificationDraft.gallery_series">
                    <n-space vertical size="small">
                      <n-radio
                        v-for="option in optionsFor('gallery_series')"
                        :key="option.value"
                        :value="option.value"
                        :disabled="option.disabled"
                      >
                        {{ option.label }}
                      </n-radio>
                    </n-space>
                  </n-radio-group>
                </n-form-item>
                <n-form-item v-if="selectedSeriesName === '昌平校区摄影大赛'" label="届次/年份">
                  <n-select
                    v-model:value="classificationDraft.gallery_year"
                    :options="optionsFor('gallery_year')"
                    filterable
                    clearable
                    placeholder="选择摄影大赛届次"
                  />
                </n-form-item>
                <n-form-item label="校区">
                  <n-radio-group v-model:value="classificationDraft.campus">
                    <n-space>
                      <n-radio
                        v-for="option in optionsFor('campus')"
                        :key="option.value"
                        :value="option.value"
                        :disabled="option.disabled"
                      >
                        {{ option.label }}
                      </n-radio>
                    </n-space>
                  </n-radio-group>
                </n-form-item>
                <n-form-item label="类别">
                  <n-radio-group v-model:value="classificationDraft.photo_type">
                    <n-space vertical size="small">
                      <n-radio
                        v-for="option in optionsFor('photo_type')"
                        :key="option.value"
                        :value="option.value"
                        :disabled="option.disabled"
                      >
                        {{ option.label }}
                      </n-radio>
                    </n-space>
                  </n-radio-group>
                </n-form-item>
              </n-form>
              <n-alert v-if="validationMessage" type="warning" :show-icon="false">
                {{ validationMessage }}
              </n-alert>
            </section>

            <section class="question-section">
              <div class="section-head">
                <strong>3. 季节</strong>
                <n-tag size="small">明显时填写</n-tag>
              </div>
              <n-radio-group v-model:value="classificationDraft.season">
                <n-space wrap>
                  <n-radio-button :value="null">不填写</n-radio-button>
                  <n-radio-button
                    v-for="option in optionsFor('season')"
                    :key="option.value"
                    :value="option.value"
                  >
                    {{ option.label }}
                  </n-radio-button>
                </n-space>
              </n-radio-group>
            </section>

            <section class="question-section">
              <div class="section-head">
                <strong>4. 标准细分标签</strong>
                <n-tag size="small">只选明显可见项</n-tag>
              </div>
              <n-input v-model:value="fineSearch" clearable placeholder="在当前校区和类别下搜索标准标签" />
              <n-empty
                v-if="classificationDraft.campus && classificationDraft.photo_type && !visibleFineFacets.length"
                description="当前校区和类别暂无可选细分标签"
              />
              <n-alert v-else-if="!classificationDraft.campus || !classificationDraft.photo_type" type="info" :show-icon="false">
                先选择校区和类别，再补充对应的具体标签。
              </n-alert>
              <n-collapse v-else :default-expanded-names="visibleFineFacets.map((facet) => facet.key)">
                <n-collapse-item
                  v-for="facet in visibleFineFacets"
                  :key="facet.key"
                  :title="facet.name"
                  :name="facet.key"
                >
                  <n-checkbox-group v-model:value="multiClassificationDraft[facet.key]">
                    <div class="check-grid">
                      <n-checkbox
                        v-for="option in filteredOptionsFor(facet.key)"
                        :key="option.value"
                        :value="option.value"
                        :disabled="option.disabled"
                      >
                        {{ option.label }}
                      </n-checkbox>
                    </div>
                  </n-checkbox-group>
                </n-collapse-item>
              </n-collapse>
              <n-space v-if="selectedFineLabels.length" wrap>
                <n-tag
                  v-for="label in selectedFineLabels"
                  :key="label.key"
                  closable
                  @close="removeFineLabel(label.facetKey, label.value)"
                >
                  {{ label.label }}
                </n-tag>
              </n-space>
            </section>

            <section class="question-section">
              <div class="section-head">
                <strong>5. 纪实补充</strong>
                <n-tag size="small">需要时补充</n-tag>
              </div>
              <n-select
                v-model:value="classificationDraft.documentary_topic"
                :options="optionsFor('documentary_topic')"
                clearable
                filterable
                placeholder="选择纪实主题"
              />
            </section>

            <section class="question-section muted">
              <div class="section-head">
                <strong>元数据参考</strong>
                <n-tag size="small">不强制</n-tag>
              </div>
              <div class="reference-grid">
                <span>奖项</span><b>{{ referenceValue('award_level') }}</b>
                <span>原楼宇</span><b>{{ referenceValue('landmark') }}</b>
              </div>
            </section>

            <n-input v-model:value="note" type="textarea" :rows="3" placeholder="备注（可选）" />

            <n-button
              type="primary"
              block
              size="large"
              :loading="submitting"
              :disabled="!canSubmit"
              @click="submitCurrent"
            >
              提交并下一张
            </n-button>
          </n-space>
        </n-card>
      </aside>

      <n-empty v-if="!selectedItem?.photo" class="empty-state" description="请选择一个标注任务" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useMessage } from 'naive-ui'
import { getPublicTaxonomy, getPublicTaxonomyGuide, type TaxonomyFacet, type TaxonomyGuide, type TaxonomyGuideGroup, type TaxonomyNode } from '../api/taxonomy'
import {
  getTaggingTasks,
  saveTaggingItemDraft,
  submitTaggingItem,
  type TaggingTask,
  type TaggingTaskItem,
} from '../api/taggingTasks'
import { getPhotoUrl } from '../utils/format'
import {
  findTaxonomyNode,
  flattenTaxonomyOptions,
  isNodeSelectable,
  sanitizeTaxonomySelection,
  type TaxonomyOption,
} from '../utils/taxonomy'

type SelectOption = TaxonomyOption<number>

const FINE_FACETS = ['building', 'facility', 'landscape', 'natural_phenomenon', 'technique', 'animal', 'plant']
const REFERENCE_FACETS = ['award_level']

const message = useMessage()
const loading = ref(false)
const submitting = ref(false)
const tasks = ref<TaggingTask[]>([])
const selectedTask = ref<TaggingTask | null>(null)
const selectedItemId = ref<string | null>(null)
const taxonomyFacets = ref<TaxonomyFacet[]>([])
const taxonomyGuide = ref<TaxonomyGuide | null>(null)
const titleDraft = ref('')
const authorDraft = ref('')
const classificationDraft = reactive<Record<string, number | null>>({})
const multiClassificationDraft = reactive<Record<string, number[]>>({})
const note = ref('')
const fineSearch = ref('')
const queueFilter = ref<'all' | 'pending' | 'submitted' | 'rejected'>('all')
const draftState = ref('')
let draftTimer: number | undefined
let hydrating = false

const selectedItem = computed(() =>
  selectedTask.value?.items.find((item) => item.id === selectedItemId.value) || null,
)

const currentIndex = computed(() =>
  selectedTask.value?.items.findIndex((item) => item.id === selectedItemId.value) ?? -1,
)

const previousItem = computed(() => {
  if (!selectedTask.value || currentIndex.value <= 0) return null
  return selectedTask.value.items[currentIndex.value - 1]
})

const nextItem = computed(() => {
  if (!selectedTask.value || currentIndex.value < 0) return null
  return selectedTask.value.items[currentIndex.value + 1] || null
})

const filteredItems = computed(() => {
  const items = selectedTask.value?.items || []
  if (queueFilter.value === 'all') return items
  return items.filter((item) => item.status === queueFilter.value)
})

const canSubmit = computed(() =>
  !!selectedItem.value && ['pending', 'submitted', 'rejected'].includes(selectedItem.value.status) && !validationMessage.value,
)

const validationMessage = computed(() => {
  if (!classificationDraft.gallery_series) return '请选择专区'
  if (selectedSeriesName.value === '昌平校区摄影大赛' && !classificationDraft.gallery_year) return '请选择摄影大赛届次'
  if (!classificationDraft.campus) return '请选择校区'
  if (!classificationDraft.photo_type) return '请选择类别'
  return ''
})

const selectedSeriesName = computed(() => optionLabel('gallery_series', classificationDraft.gallery_series))

const guideFineGroups = computed(() => {
  const campusName = optionLabel('campus', classificationDraft.campus)
  const categoryName = optionLabel('photo_type', classificationDraft.photo_type)
  if (!campusName || !categoryName) return []
  return collectGuideGroups(taxonomyGuide.value?.campus_category_tree?.[campusName]?.[categoryName])
})

const guideFineFacetKeys = computed(() =>
  new Set(guideFineGroups.value.map((group) => group.facetKey).filter((key) => FINE_FACETS.includes(key))),
)

const visibleFineFacets = computed(() => {
  const keys = guideFineFacetKeys.value
  if (keys.size) return taxonomyFacets.value.filter((facet) => keys.has(facet.key))
  if (!classificationDraft.campus || !classificationDraft.photo_type) return []
  return taxonomyFacets.value.filter((facet) => FINE_FACETS.includes(facet.key))
})

const existingClassificationSummary = computed(() => {
  const values = selectedItem.value?.photo?.classifications || {}
  return Object.entries(values)
    .map(([key, value]) => {
      const facet = taxonomyFacets.value.find((item) => item.key === key)
      const names = Array.isArray(value)
        ? value.map((item) => item.node_name).join('、')
        : value?.node_name
      return names ? `${facet?.name || key}：${names}` : ''
    })
    .filter(Boolean)
    .join('；')
})

const selectedFineLabels = computed(() =>
  Object.entries(multiClassificationDraft).flatMap(([facetKey, values]) =>
    values.map((value) => ({
      key: `${facetKey}-${value}`,
      facetKey,
      value,
      label: optionLabel(facetKey, value),
    })),
  ),
)

onMounted(async () => {
  await Promise.all([loadTaxonomy(), loadTasks()])
})

onBeforeUnmount(() => {
  if (draftTimer) window.clearTimeout(draftTimer)
})

watch(
  [titleDraft, authorDraft, () => ({ ...classificationDraft }), () => ({ ...multiClassificationDraft }), note],
  () => {
    if (!hydrating) scheduleDraftSave()
  },
  { deep: true },
)

async function loadTaxonomy() {
  const [facets, guide] = await Promise.all([getPublicTaxonomy(), getPublicTaxonomyGuide()])
  taxonomyFacets.value = facets
  taxonomyGuide.value = guide
}

async function loadTasks() {
  loading.value = true
  try {
    const response = await getTaggingTasks({ limit: 100 })
    tasks.value = response.items
    if (!selectedTask.value && tasks.value.length) await selectTask(tasks.value[0])
    else if (selectedTask.value) {
      selectedTask.value = tasks.value.find((task) => task.id === selectedTask.value?.id) || selectedTask.value
      hydrateDraft()
    }
  } finally {
    loading.value = false
  }
}

async function selectTask(task: TaggingTask) {
  await saveDraftNow()
  selectedTask.value = task
  selectedItemId.value = task.items[0]?.id || null
  hydrateDraft()
}

async function selectItem(itemId: string) {
  await saveDraftNow()
  selectedItemId.value = itemId
  hydrateDraft()
}

async function goRelative(offset: number) {
  const target = offset < 0 ? previousItem.value : nextItem.value
  if (target) await selectItem(target.id)
}

function hydrateDraft() {
  hydrating = true
  const item = selectedItem.value
  titleDraft.value = item?.submitted_title || item?.draft_title || item?.photo?.title || parsedTitleFromPhoto() || ''
  authorDraft.value = item?.submitted_author || item?.draft_author || item?.photo?.author || parsedAuthorFromPhoto() || ''
  Object.keys(classificationDraft).forEach((key) => delete classificationDraft[key])
  Object.keys(multiClassificationDraft).forEach((key) => delete multiClassificationDraft[key])

  taxonomyFacets.value.forEach((facet) => {
    if (facet.selection_mode === 'multiple') multiClassificationDraft[facet.key] = []
    else classificationDraft[facet.key] = null
  })

  const source = item?.submitted_classifications || item?.draft_classifications || item?.photo?.classifications || {}
  Object.entries(source).forEach(([facetKey, value]) => {
    const facet = taxonomyFacets.value.find((item) => item.key === facetKey)
    if (!facet || !value) return
    if (facet.selection_mode === 'multiple') {
      multiClassificationDraft[facetKey] = extractNodeIds(value)
        .filter((nodeId) => {
          const node = findTaxonomyNode(facet, nodeId)
          return node ? isNodeSelectable(node) : false
        })
    } else {
      const nodeId = extractNodeIds(value).find((item) => {
        const node = findTaxonomyNode(facet, item)
        return node ? isNodeSelectable(node) : false
      })
      classificationDraft[facetKey] = nodeId || null
    }
  })
  note.value = item?.submitter_note || item?.draft_note || ''
  draftState.value = item?.draft_saved_at ? `已保存 ${formatTime(item.draft_saved_at)}` : ''
  nextTick(() => {
    hydrating = false
  })
}

interface FineGuideGroup {
  title: string
  facetKey: string
  nodeNames: string[]
}

function collectGuideGroups(groups: TaxonomyGuideGroup[] | undefined): FineGuideGroup[] {
  if (!groups?.length) return []
  return groups.flatMap((group) => [
    {
      title: group.title,
      facetKey: group.facet_key,
      nodeNames: group.nodes || [],
    },
    ...collectGuideGroups(group.groups),
  ])
}

function optionsFor(facetKey: string): SelectOption[] {
  const facet = taxonomyFacets.value.find((item) => item.key === facetKey)
  return facet ? flattenOptions(facet.nodes) : []
}

function filteredOptionsFor(facetKey: string): SelectOption[] {
  const query = fineSearch.value.trim().toLowerCase()
  const allowed = guideFineGroups.value
    .filter((group) => group.facetKey === facetKey)
    .flatMap((group) => group.nodeNames)
  const options = optionsFor(facetKey).filter((option) => {
    if (!allowed.length) return true
    return allowed.includes(option.label) || allowed.includes(option.node.name)
  })
  if (!query) return options
  return options.filter((option) => option.searchText.includes(query))
}

function flattenOptions(nodes: TaxonomyNode[], prefix = ''): SelectOption[] {
  const parentPath = prefix ? prefix.split(' / ') : []
  return flattenTaxonomyOptions(nodes, (node) => node.id, parentPath)
}

function extractNodeIds(value: any): number[] {
  if (!value) return []
  if (Array.isArray(value)) return value.map((item) => item.node_id).filter(Boolean)
  if (Array.isArray(value.node_ids)) return value.node_ids
  if (Array.isArray(value.nodes)) return value.nodes.map((item: any) => item.node_id).filter(Boolean)
  return value.node_id ? [value.node_id] : []
}

function optionLabel(facetKey: string, value: number | null | undefined) {
  if (!value) return ''
  return optionsFor(facetKey).find((option) => option.value === value)?.label || ''
}

function referenceValue(facetKey: string) {
  const value = classificationDraft[facetKey]
  if (value) return optionLabel(facetKey, value)
  const source = selectedItem.value?.photo?.classifications?.[facetKey]
  const names = Array.isArray(source) ? source.map((item) => item.node_name).join('、') : source?.node_name
  return names || '暂无'
}

function buildClassifications() {
  const classifications: Record<string, number | number[]> = {}
  Object.entries(classificationDraft).forEach(([key, value]) => {
    if (value) classifications[key] = value
  })
  Object.entries(multiClassificationDraft).forEach(([key, values]) => {
    if (values.length) classifications[key] = values
  })
  return sanitizeTaxonomySelection(taxonomyFacets.value, classifications)
}

function scheduleDraftSave() {
  if (!selectedItem.value || selectedItem.value.status === 'approved') return
  draftState.value = '保存中'
  if (draftTimer) window.clearTimeout(draftTimer)
  draftTimer = window.setTimeout(() => {
    saveDraftNow()
  }, 700)
}

async function saveDraftNow() {
  if (draftTimer) {
    window.clearTimeout(draftTimer)
    draftTimer = undefined
  }
  if (!selectedItem.value || selectedItem.value.status === 'approved') return
  try {
    const updated = await saveTaggingItemDraft(selectedItem.value.id, {
      tags: [],
      classifications: buildClassifications(),
      title: titleDraft.value.trim() || undefined,
      author: authorDraft.value.trim() || undefined,
      note: note.value || undefined,
    })
    replaceItem(updated)
    draftState.value = `已保存 ${formatTime(updated.draft_saved_at)}`
  } catch (error: any) {
    draftState.value = '保存失败'
  }
}

function removeFineLabel(facetKey: string, value: number) {
  multiClassificationDraft[facetKey] = (multiClassificationDraft[facetKey] || []).filter((item) => item !== value)
}

async function submitCurrent() {
  if (!selectedItem.value || validationMessage.value) {
    message.warning(validationMessage.value || '当前照片不能提交')
    return
  }
  submitting.value = true
  try {
    const updated = await submitTaggingItem(selectedItem.value.id, {
      tags: [],
      classifications: buildClassifications(),
      title: titleDraft.value.trim() || undefined,
      author: authorDraft.value.trim() || undefined,
      note: note.value || undefined,
    })
    replaceItem(updated)
    message.success('已提交审核')
    if (nextItem.value) await selectItem(nextItem.value.id)
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '提交失败')
  } finally {
    submitting.value = false
  }
}

function parsedDescriptionParts() {
  return (selectedItem.value?.photo?.description || '')
    .split('|')
    .map((part) => part.trim())
    .filter(Boolean)
}

function parsedTitleFromPhoto() {
  return parsedDescriptionParts().find((part) => !part.includes('作者') && !part.includes('序号')) || ''
}

function parsedAuthorFromPhoto() {
  const authorPart = parsedDescriptionParts().find((part) => part.includes('作者'))
  const match = authorPart?.match(/作者[：:]\s*(.+)$/)
  return match?.[1]?.trim() || ''
}

function replaceItem(updated: TaggingTaskItem) {
  const task = tasks.value.find((task) => task.id === updated.task_id)
  if (!task) return
  const index = task.items.findIndex((item) => item.id === updated.id)
  if (index !== -1) task.items[index] = updated
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    pending: '待标注',
    in_progress: '进行中',
    reviewing: '审核中',
    submitted: '待审核',
    approved: '已通过',
    rejected: '已驳回',
    completed: '已完成',
  }
  return labels[status] || status
}

function formatTime(value: string | null | undefined) {
  if (!value) return ''
  return new Date(value).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

REFERENCE_FACETS.forEach((key) => {
  classificationDraft[key] = null
})
</script>

<style scoped>
.tagging-workspace {
  padding: 20px;
  background: #f6f7f9;
  min-height: calc(100vh - 64px);
}

.workspace-grid {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr) 400px;
  gap: 16px;
  margin-top: 16px;
  align-items: start;
}

.task-column,
.question-column {
  display: flex;
  flex-direction: column;
  gap: 12px;
  position: sticky;
  top: 16px;
}

.task-item {
  cursor: pointer;
  padding: 8px;
  border-radius: 6px;
}

.task-item.active,
.queue-item.active {
  background: #eef6f0;
}

.small-text {
  font-size: 12px;
}

.queue-list {
  margin-top: 12px;
  max-height: 520px;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.queue-item {
  display: grid;
  grid-template-columns: 24px 52px minmax(0, 1fr);
  gap: 8px;
  align-items: center;
  border: 0;
  border-radius: 6px;
  background: transparent;
  padding: 6px;
  cursor: pointer;
  text-align: left;
}

.queue-item img {
  width: 52px;
  height: 40px;
  object-fit: cover;
  border-radius: 4px;
}

.queue-item strong,
.queue-item small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.queue-item small {
  color: #6b7280;
}

.photo-column {
  min-width: 0;
}

.photo-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  background: #fff;
  border-radius: 8px;
  padding: 12px 14px;
}

.image-panel {
  min-height: 560px;
  background: #111827;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  overflow: hidden;
}

.image-panel img {
  max-width: 100%;
  max-height: 760px;
  object-fit: contain;
}

.metadata-panel {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.metadata-panel div {
  background: #fff;
  border-radius: 8px;
  padding: 10px 12px;
}

.metadata-panel span {
  display: block;
  color: #6b7280;
  font-size: 12px;
  margin-bottom: 4px;
}

.metadata-panel p {
  margin: 0;
  line-height: 1.5;
}

.question-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.question-section.muted {
  background: #f8fafc;
  border-radius: 8px;
  padding: 10px;
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.check-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 12px;
}

.reference-grid {
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr);
  gap: 6px 10px;
  font-size: 13px;
}

.reference-grid span {
  color: #6b7280;
}

.reference-grid b {
  font-weight: 500;
}

.candidate-tag {
  cursor: pointer;
}

.empty-state {
  grid-column: 2 / 4;
  min-height: 400px;
  background: #fff;
  border-radius: 8px;
}

@media (max-width: 1200px) {
  .workspace-grid {
    grid-template-columns: 240px minmax(0, 1fr);
  }

  .question-column {
    grid-column: 1 / -1;
    position: static;
  }
}

@media (max-width: 820px) {
  .workspace-grid,
  .metadata-panel {
    grid-template-columns: 1fr;
  }

  .task-column {
    position: static;
  }
}
</style>
