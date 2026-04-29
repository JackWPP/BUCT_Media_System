<template>
  <div class="database-management">
    <n-space vertical :size="24">
      <n-text depth="1" style="font-size: 24px; font-weight: 600;">
        数据库管理
      </n-text>

      <!-- Database Info Card -->
      <n-card title="数据库概览">
        <template #header-extra>
          <n-button size="small" @click="fetchInfo" :loading="infoLoading">
            刷新
          </n-button>
        </template>
        <n-spin :show="infoLoading">
          <n-descriptions v-if="dbInfo" bordered :column="2">
            <n-descriptions-item label="数据库类型">
              <n-tag :type="dbInfo.backend === 'sqlite' ? 'info' : 'success'">
                {{ dbInfo.backend }}
              </n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="数据表数">
              {{ dbInfo.table_count }}
            </n-descriptions-item>
            <n-descriptions-item label="文件大小">
              {{ dbInfo.file_size_mb != null ? dbInfo.file_size_mb + ' MB' : 'N/A' }}
            </n-descriptions-item>
            <n-descriptions-item label="Alembic 版本">
              <n-text code v-if="dbInfo.alembic_revision">{{ dbInfo.alembic_revision }}</n-text>
              <n-text depth="3" v-else>无</n-text>
            </n-descriptions-item>
          </n-descriptions>

          <n-divider />

          <n-text strong>各表行数</n-text>
          <n-data-table
            v-if="dbInfo"
            :columns="tableColumns"
            :data="tableRows"
            :size="'small'"
            :bordered="false"
            :max-height="300"
            style="margin-top: 12px;"
          />
        </n-spin>
      </n-card>

      <!-- Export Card -->
      <n-card title="数据导出">
        <n-space>
          <n-button type="primary" @click="handleExportDatabase" :loading="exportLoading">
            <template #icon>
              <n-icon><download-outline /></n-icon>
            </template>
            下载 SQLite 数据库
          </n-button>
          <n-button @click="handleDownloadScript" :loading="scriptLoading">
            <template #icon>
              <n-icon><code-download-outline /></n-icon>
            </template>
            下载迁移脚本
          </n-button>
        </n-space>
      </n-card>

      <!-- PostgreSQL Migration Card -->
      <n-card title="迁移至 PostgreSQL">
        <template #header-extra>
          <n-tag :type="dbInfo?.backend === 'postgresql' ? 'success' : 'warning'" size="small">
            {{ dbInfo?.backend === 'postgresql' ? '已是 PostgreSQL' : '当前 SQLite' }}
          </n-tag>
        </template>

        <n-form
          ref="formRef"
          :model="migrateForm"
          :rules="migrateRules"
          label-placement="top"
          style="max-width: 600px;"
        >
          <n-form-item label="目标 PostgreSQL DSN" path="target_dsn">
            <n-input
              v-model:value="migrateForm.target_dsn"
              placeholder="postgresql://user:password@host:5432/dbname"
              :disabled="migrating"
            />
          </n-form-item>
          <n-form-item label="导入选项" path="truncate">
            <n-checkbox v-model:checked="migrateForm.truncate" :disabled="migrating">
              导入前清空目标表 (TRUNCATE)
            </n-checkbox>
          </n-form-item>
          <n-form-item>
            <n-button
              type="primary"
              @click="handleMigrate"
              :loading="migrating"
              :disabled="dbInfo?.backend === 'postgresql'"
            >
              开始迁移
            </n-button>
          </n-form-item>
        </n-form>

        <n-alert v-if="migrateResult" :type="migrateResult.status === 'started' ? 'success' : 'error'" style="margin-top: 16px;">
          {{ migrateResult.message }}
        </n-alert>
        <n-alert type="info" style="margin-top: 16px;">
          迁移后请手动修改 <n-text code>.env</n-text> 中的 <n-text code>DATABASE_URL</n-text> 为 PostgreSQL DSN，并重启后端。
        </n-alert>
      </n-card>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue'
import {
  NAlert,
  NButton,
  NCard,
  NCheckbox,
  NDataTable,
  NDescriptions,
  NDescriptionsItem,
  NDivider,
  NForm,
  NFormItem,
  NIcon,
  NInput,
  NSpace,
  NSpin,
  NTag,
  NText,
  useMessage,
} from 'naive-ui'
import { CodeDownloadOutline, DownloadOutline } from '@vicons/ionicons5'
import {
  getDatabaseInfo,
  downloadDatabaseExport,
  downloadMigrationScript,
  triggerMigration,
  type DatabaseInfo,
} from '../../api/database'

const message = useMessage()

// ── Database info ──
const dbInfo = ref<DatabaseInfo | null>(null)
const infoLoading = ref(false)
const exportLoading = ref(false)
const scriptLoading = ref(false)

const tableColumns = [
  { title: '表名', key: 'name', width: 200 },
  { title: '行数', key: 'count', width: 120 },
]

const tableRows = computed(() => {
  if (!dbInfo.value) return []
  return Object.entries(dbInfo.value.row_counts).map(([name, count]) => ({
    name,
    count,
  }))
})

async function fetchInfo() {
  infoLoading.value = true
  try {
    dbInfo.value = await getDatabaseInfo()
  } catch (e: any) {
    if (e?.response?.status === 401 || e?.response?.status === 403) {
      message.error('无权限访问，请确认已使用管理员账号登录')
    } else {
      message.error(e?.response?.data?.detail || '获取数据库信息失败')
    }
  } finally {
    infoLoading.value = false
  }
}

// ── Export ──
function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

async function handleExportDatabase() {
  exportLoading.value = true
  try {
    const blob = await downloadDatabaseExport()
    triggerDownload(blob, `visual_buct_backup_${Date.now()}.db`)
    message.success('下载已开始')
  } catch {
    message.error('下载数据库失败')
  } finally {
    exportLoading.value = false
  }
}

async function handleDownloadScript() {
  scriptLoading.value = true
  try {
    const blob = await downloadMigrationScript()
    triggerDownload(blob, 'migrate_to_postgres.py')
    message.success('下载已开始')
  } catch {
    message.error('下载迁移脚本失败')
  } finally {
    scriptLoading.value = false
  }
}

// ── Migration ──
const formRef = ref()
const migrating = ref(false)
const migrateResult = ref<{ status: string; message: string } | null>(null)

const migrateForm = reactive({
  target_dsn: '',
  truncate: false,
})

const migrateRules = {
  target_dsn: [
    { required: true, message: '请输入目标 PostgreSQL DSN', trigger: 'blur' },
    {
      pattern: /^postgresql:\/\/.+/,
      message: 'DSN 应以 postgresql:// 开头',
      trigger: 'blur',
    },
  ],
}

async function handleMigrate() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  migrating.value = true
  migrateResult.value = null
  try {
    const result = await triggerMigration({
      target_dsn: migrateForm.target_dsn,
      truncate: migrateForm.truncate,
    })
    migrateResult.value = result
    message.success(result.message)
  } catch (e: any) {
    const msg = e?.response?.data?.detail || '迁移触发失败'
    migrateResult.value = { status: 'error', message: msg }
    message.error(msg)
  } finally {
    migrating.value = false
  }
}

onMounted(() => {
  fetchInfo()
})
</script>

<style scoped>
.database-management {
  max-width: 900px;
}
</style>
