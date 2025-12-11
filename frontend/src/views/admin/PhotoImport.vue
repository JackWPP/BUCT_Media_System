<template>
  <div class="photo-import">
    <n-space vertical size="large">
      <!-- 标题 -->
      <n-text strong style="font-size: 24px;">批量导入照片</n-text>

      <!-- 使用说明 -->
      <n-alert type="info" title="使用说明">
        <n-text>
          此功能用于从 JSON 文件批量导入照片元数据。支持以下两种方式：
        </n-text>
        <ul style="margin: 8px 0; padding-left: 20px;">
          <li>单个 JSON 文件：直接指定 JSON 文件路径</li>
          <li>目录：指定包含多个 JSON 文件的目录，系统会递归扫描</li>
        </ul>
        <n-text depth="3" style="font-size: 12px;">
          JSON 文件格式请参考系统文档。导入的照片默认状态为"待审核"。
        </n-text>
      </n-alert>

      <!-- 导入表单 -->
      <n-card title="导入配置">
        <n-form
          ref="formRef"
          :model="formData"
          :rules="formRules"
          label-placement="left"
          label-width="140px"
        >
          <n-form-item label="JSON 路径" path="json_path">
            <n-input
              v-model:value="formData.json_path"
              placeholder="输入 JSON 文件或目录的完整路径"
              @blur="handlePathValidate"
            />
          </n-form-item>
          
          <n-form-item label="图片文件夹" path="image_folder">
            <n-input
              v-model:value="formData.image_folder"
              placeholder="可选：图片文件所在目录（留空则从 JSON 同目录查找）"
            />
          </n-form-item>

          <!-- 路径验证结果 -->
          <n-form-item v-if="validateResult" label="路径验证">
            <n-space vertical>
              <n-text v-if="validateResult.exists" type="success">
                ✓ 路径有效
              </n-text>
              <n-text v-else type="error">
                ✗ 路径不存在
              </n-text>
              
              <n-descriptions v-if="validateResult.exists" :column="2" size="small">
                <n-descriptions-item label="类型">
                  {{ validateResult.is_file ? '文件' : '目录' }}
                </n-descriptions-item>
                <n-descriptions-item label="JSON 文件数">
                  {{ validateResult.json_files_count }}
                </n-descriptions-item>
              </n-descriptions>

              <n-collapse v-if="validateResult.json_files && validateResult.json_files.length > 0">
                <n-collapse-item title="JSON 文件列表（前 10 个）">
                  <n-list>
                    <n-list-item v-for="file in validateResult.json_files" :key="file">
                      {{ file }}
                    </n-list-item>
                  </n-list>
                </n-collapse-item>
              </n-collapse>
            </n-space>
          </n-form-item>

          <n-form-item>
            <n-space>
              <n-button
                type="primary"
                :loading="importing"
                :disabled="!formData.json_path || !validateResult?.exists"
                @click="handleImport"
              >
                开始导入
              </n-button>
              <n-button @click="handleReset">
                重置
              </n-button>
            </n-space>
          </n-form-item>
        </n-form>
      </n-card>

      <!-- 导入结果 -->
      <n-card v-if="importResult" title="导入结果">
        <n-space vertical>
          <n-text>{{ importResult.message }}</n-text>
          
          <n-descriptions :column="4" bordered size="small">
            <n-descriptions-item label="总计">
              {{ importResult.total_count }}
            </n-descriptions-item>
            <n-descriptions-item label="成功">
              <n-text type="success">{{ importResult.imported_count }}</n-text>
            </n-descriptions-item>
            <n-descriptions-item label="跳过">
              <n-text type="warning">{{ importResult.skipped_count }}</n-text>
            </n-descriptions-item>
            <n-descriptions-item label="失败">
              <n-text type="error">{{ importResult.error_count }}</n-text>
            </n-descriptions-item>
          </n-descriptions>

          <!-- 错误列表 -->
          <n-collapse v-if="importResult.errors && importResult.errors.length > 0">
            <n-collapse-item title="错误详情">
              <n-list>
                <n-list-item v-for="(error, index) in importResult.errors" :key="index">
                  <n-text type="error">{{ error }}</n-text>
                </n-list-item>
              </n-list>
            </n-collapse-item>
          </n-collapse>

          <n-space>
            <n-button type="primary" @click="goToReview">
              前往审核页面
            </n-button>
            <n-button @click="handleReset">
              继续导入
            </n-button>
          </n-space>
        </n-space>
      </n-card>

      <!-- 导入历史 -->
      <n-card title="最近导入记录">
        <n-empty v-if="importHistory.length === 0" description="暂无导入记录" />
        <n-timeline v-else>
          <n-timeline-item
            v-for="(record, index) in importHistory"
            :key="index"
            :type="record.error_count > 0 ? 'warning' : 'success'"
            :title="record.timestamp"
          >
            <n-text>{{ record.message }}</n-text>
            <n-text depth="3" style="display: block; margin-top: 4px; font-size: 12px;">
              成功: {{ record.imported_count }} | 跳过: {{ record.skipped_count }} | 失败: {{ record.error_count }}
            </n-text>
          </n-timeline-item>
        </n-timeline>
      </n-card>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { importPhotos, validateImportPath, type ImportResponse, type ValidateResponse } from '@/api/import'

const router = useRouter()
const message = useMessage()

const importing = ref(false)
const validateResult = ref<ValidateResponse | null>(null)
const importResult = ref<ImportResponse | null>(null)

const formData = reactive({
  json_path: '',
  image_folder: '',
})

const formRules = {
  json_path: {
    required: true,
    message: '请输入 JSON 路径',
    trigger: 'blur',
  },
}

interface ImportHistoryRecord extends ImportResponse {
  timestamp: string
}

const importHistory = ref<ImportHistoryRecord[]>([])

// 从 localStorage 加载历史记录
const loadHistory = () => {
  const stored = localStorage.getItem('import_history')
  if (stored) {
    try {
      importHistory.value = JSON.parse(stored)
    } catch (e) {
      console.error('Failed to load import history:', e)
    }
  }
}

// 保存历史记录
const saveHistory = (result: ImportResponse) => {
  const record: ImportHistoryRecord = {
    ...result,
    timestamp: new Date().toLocaleString('zh-CN'),
  }
  
  importHistory.value.unshift(record)
  
  // 只保留最近 10 条
  if (importHistory.value.length > 10) {
    importHistory.value = importHistory.value.slice(0, 10)
  }
  
  localStorage.setItem('import_history', JSON.stringify(importHistory.value))
}

loadHistory()

async function handlePathValidate() {
  if (!formData.json_path) {
    validateResult.value = null
    return
  }

  try {
    const result = await validateImportPath(formData.json_path)
    validateResult.value = result
    
    if (!result.exists) {
      message.warning('路径不存在')
    } else if (result.json_files_count === 0) {
      message.warning('未找到 JSON 文件')
    } else {
      message.success(`找到 ${result.json_files_count} 个 JSON 文件`)
    }
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '验证路径失败')
    validateResult.value = null
  }
}

async function handleImport() {
  if (!formData.json_path) {
    message.warning('请输入 JSON 路径')
    return
  }

  importing.value = true
  importResult.value = null
  
  try {
    const result = await importPhotos({
      json_path: formData.json_path,
      image_folder: formData.image_folder || undefined,
    })
    
    importResult.value = result
    saveHistory(result)
    
    if (result.error_count === 0) {
      message.success(result.message)
    } else {
      message.warning(result.message)
    }
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '导入失败')
  } finally {
    importing.value = false
  }
}

function handleReset() {
  formData.json_path = ''
  formData.image_folder = ''
  validateResult.value = null
  importResult.value = null
}

function goToReview() {
  router.push({ name: 'PhotoReview' })
}
</script>

<style scoped>
.photo-import {
  max-width: 1000px;
  margin: 0 auto;
}
</style>
