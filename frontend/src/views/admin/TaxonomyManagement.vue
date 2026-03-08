<template>
  <div class="taxonomy-page">
    <n-space vertical size="large">
      <n-space justify="space-between" align="center">
        <n-text strong style="font-size: 24px;">分类治理</n-text>
        <n-space>
          <n-button @click="loadFacets" :loading="loading">刷新</n-button>
          <n-button type="primary" @click="showFacetModal = true">新增分面</n-button>
        </n-space>
      </n-space>

      <n-alert type="info" title="受控分类">
        这里维护季节、校区、楼宇、专题/赛事、年份和照片类型等标准词表。自由标签继续在“自由标签”页维护。
      </n-alert>

      <n-collapse>
        <n-collapse-item v-for="facet in facets" :key="facet.id" :title="facet.name" :name="facet.key">
          <template #header-extra>
            <n-tag size="small" :type="facet.is_system ? 'warning' : 'default'">{{ facet.key }}</n-tag>
          </template>

          <n-space vertical>
            <n-space justify="space-between">
              <n-space>
                <n-text depth="3">选择模式：{{ facet.selection_mode }}</n-text>
                <n-text depth="3">状态：{{ facet.is_active ? '启用' : '停用' }}</n-text>
              </n-space>
              <n-button size="small" @click="openNodeModal(facet)">新增节点</n-button>
            </n-space>

            <n-data-table
              :columns="columnsForFacet(facet)"
              :data="flattenNodes(facet.nodes)"
              :bordered="false"
              size="small"
            />
          </n-space>
        </n-collapse-item>
      </n-collapse>
    </n-space>

    <n-modal
      v-model:show="showFacetModal"
      preset="dialog"
      title="新增分面"
      positive-text="保存"
      negative-text="取消"
      @positive-click="handleCreateFacet"
    >
      <n-form :model="facetForm" label-placement="left" label-width="90">
        <n-form-item label="键名">
          <n-input v-model:value="facetForm.key" placeholder="building" />
        </n-form-item>
        <n-form-item label="名称">
          <n-input v-model:value="facetForm.name" placeholder="楼宇" />
        </n-form-item>
        <n-form-item label="说明">
          <n-input v-model:value="facetForm.description" type="textarea" :rows="2" />
        </n-form-item>
      </n-form>
    </n-modal>

    <n-modal
      v-model:show="showNodeModal"
      preset="dialog"
      :title="`新增节点 - ${selectedFacet?.name || ''}`"
      positive-text="保存"
      negative-text="取消"
      @positive-click="handleCreateNode"
    >
      <n-form :model="nodeForm" label-placement="left" label-width="90">
        <n-form-item label="键名">
          <n-input v-model:value="nodeForm.key" placeholder="library" />
        </n-form-item>
        <n-form-item label="名称">
          <n-input v-model:value="nodeForm.name" placeholder="图书馆" />
        </n-form-item>
        <n-form-item label="别名">
          <n-dynamic-tags v-model:value="nodeForm.aliases" />
        </n-form-item>
      </n-form>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue'
import { NButton, NPopconfirm, NTag, useMessage, type DataTableColumns } from 'naive-ui'
import {
  createTaxonomyFacet,
  createTaxonomyNode,
  deleteTaxonomyNode,
  getTaxonomyFacets,
  type TaxonomyFacet,
  type TaxonomyNode,
} from '@/api/taxonomy'

const message = useMessage()
const loading = ref(false)
const facets = ref<TaxonomyFacet[]>([])
const showFacetModal = ref(false)
const showNodeModal = ref(false)
const selectedFacet = ref<TaxonomyFacet | null>(null)

const facetForm = reactive({
  key: '',
  name: '',
  description: '',
})

const nodeForm = reactive({
  key: '',
  name: '',
  aliases: [] as string[],
})

onMounted(() => {
  loadFacets()
})

async function loadFacets() {
  loading.value = true
  try {
    facets.value = await getTaxonomyFacets()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '加载分类失败')
  } finally {
    loading.value = false
  }
}

function flattenNodes(nodes: TaxonomyNode[], depth = 0): Array<TaxonomyNode & { depth: number }> {
  return nodes.flatMap((node) => [
    { ...node, depth },
    ...flattenNodes(node.children || [], depth + 1),
  ])
}

function columnsForFacet(facet: TaxonomyFacet): DataTableColumns<TaxonomyNode & { depth: number }> {
  return [
    {
      title: '名称',
      key: 'name',
      render(row) {
        return h('div', { style: `padding-left: ${row.depth * 20}px;` }, row.name)
      },
    },
    {
      title: '键名',
      key: 'key',
    },
    {
      title: '别名',
      key: 'aliases',
      render(row) {
        return (row.aliases || []).map((alias) => alias.alias).join('，') || '-'
      },
    },
    {
      title: '状态',
      key: 'is_active',
      width: 100,
      render(row) {
        return h(NTag, { type: row.is_active ? 'success' : 'default', size: 'small' }, { default: () => (row.is_active ? '启用' : '停用') })
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render(row) {
        return h(
          NPopconfirm,
          {
            onPositiveClick: () => handleDeleteNode(row.id),
          },
          {
            trigger: () => h(NButton, { size: 'small', type: 'error', disabled: facet.is_system && ['season', 'campus', 'photo_type', 'gallery_year'].includes(facet.key) }, { default: () => '删除' }),
            default: () => '确定删除该节点吗？',
          },
        )
      },
    },
  ]
}

function openNodeModal(facet: TaxonomyFacet) {
  selectedFacet.value = facet
  nodeForm.key = ''
  nodeForm.name = ''
  nodeForm.aliases = []
  showNodeModal.value = true
}

async function handleCreateFacet() {
  try {
    await createTaxonomyFacet({
      key: facetForm.key,
      name: facetForm.name,
      description: facetForm.description,
      selection_mode: 'single',
    })
    message.success('分面已创建')
    facetForm.key = ''
    facetForm.name = ''
    facetForm.description = ''
    await loadFacets()
    return true
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '创建失败')
    return false
  }
}

async function handleCreateNode() {
  if (!selectedFacet.value) return false
  try {
    await createTaxonomyNode(selectedFacet.value.id, {
      key: nodeForm.key,
      name: nodeForm.name,
      aliases: nodeForm.aliases,
    })
    message.success('节点已创建')
    await loadFacets()
    return true
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '创建失败')
    return false
  }
}

async function handleDeleteNode(nodeId: number) {
  try {
    await deleteTaxonomyNode(nodeId)
    message.success('节点已删除')
    await loadFacets()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '删除失败')
  }
}
</script>

<style scoped>
.taxonomy-page {
  max-width: 1400px;
  margin: 0 auto;
}
</style>
