<template>
  <div class="upload-container">
    <n-layout has-sider>
      <!-- 侧边栏 -->
      <n-layout-sider
        bordered
        :width="240"
        class="upload-sidebar"
      >
        <div class="sidebar-content">
          <n-button text size="large" @click="router.push('/')" class="back-button">
            <template #icon>
              <n-icon :component="ArrowBackOutline" />
            </template>
            返回图库
          </n-button>
          <n-divider />
          <div class="upload-stats">
            <n-statistic label="待上传" :value="pendingCount" />
            <n-statistic label="成功" :value="successCount" />
            <n-statistic label="失败" :value="errorCount" />
          </div>
        </div>
      </n-layout-sider>

      <!-- 主内容区 -->
      <n-layout>
        <n-layout-header bordered class="upload-header">
          <h2 style="margin: 0;">上传照片</h2>
          <n-text depth="3">支持批量上传，最多20张</n-text>
        </n-layout-header>

        <n-layout-content class="upload-main-content" content-style="padding: 24px;">
          <div class="upload-content">
            <n-card title="选择照片" :bordered="false">
              <!-- 上传区域 -->
              <n-upload
                ref="uploadRef"
                :multiple="true"
                :max="20"
                :accept="'image/*'"
                :show-file-list="false"
                :custom-request="handleUploadRequest"
                @before-upload="handleBeforeUpload"
                @change="handleFileChange"
              >
                <n-upload-dragger>
                  <div class="upload-dragger-content">
                    <n-icon size="64" :depth="3" color="#18a058">
                      <CloudUploadOutline />
                    </n-icon>
                    <n-text class="upload-text">
                      点击或拖拽文件到此区域上传
                    </n-text>
                    <n-p depth="3" class="upload-hint">
                      支持单张或批量上传，最多 20 张，每张最大 20MB
                    </n-p>
                  </div>
                </n-upload-dragger>
              </n-upload>

              <!-- 文件列表 -->
              <div v-if="fileList.length > 0" class="file-list-section">
                <n-divider />
                <div class="file-list-header">
                  <n-text strong>待上传文件 ({{ fileList.length }})</n-text>
                  <n-button text @click="clearAll" type="error" size="small">
                    清空列表
                  </n-button>
                </div>
                
                <n-list bordered class="file-list">
                  <n-list-item v-for="(item, index) in fileList" :key="index" class="file-item">
                    <n-thing>
                      <template #avatar>
                        <div class="file-avatar">
                          <img v-if="item.preview" :src="item.preview" alt="preview" />
                          <n-icon v-else size="32"><ImageOutline /></n-icon>
                        </div>
                      </template>
                      <template #header>
                        <n-ellipsis style="max-width: 300px;">
                          {{ item.file.name }}
                        </n-ellipsis>
                      </template>
                      <template #description>
                        {{ formatFileSize(item.file.size) }}
                      </template>
                      <template #header-extra>
                        <n-tag v-if="item.status === 'pending'" type="default">等待上传</n-tag>
                        <n-tag v-else-if="item.status === 'uploading'" type="info">
                          <template #icon>
                            <n-icon><SyncOutline /></n-icon>
                          </template>
                          上传中 {{ item.progress }}%
                        </n-tag>
                        <n-tag v-else-if="item.status === 'success'" type="success">
                          <template #icon>
                            <n-icon><CheckmarkOutline /></n-icon>
                          </template>
                          上传成功
                        </n-tag>
                        <n-tag v-else-if="item.status === 'error'" type="error">
                          <template #icon>
                            <n-icon><CloseOutline /></n-icon>
                          </template>
                          上传失败
                        </n-tag>
                      </template>
                      <template #action>
                        <n-space>
                          <n-button
                            v-if="item.status === 'pending' || item.status === 'error'"
                            text
                            type="error"
                            @click="removeFile(index)"
                          >
                            移除
                          </n-button>
                          <n-button
                            v-if="item.status === 'error'"
                            text
                            type="primary"
                            @click="retryUpload(index)"
                          >
                            重试
                          </n-button>
                        </n-space>
                      </template>
                    </n-thing>
                    <n-progress
                      v-if="item.status === 'uploading'"
                      type="line"
                      :percentage="item.progress"
                      :show-indicator="false"
                      status="success"
                      class="file-progress"
                    />
                  </n-list-item>
                </n-list>
              </div>
            </n-card>

            <!-- 元数据设置 -->
            <n-card v-if="fileList.length > 0" title="批量设置" class="metadata-card" :bordered="false">
              <n-form
                ref="metadataFormRef"
                :model="metadata"
                label-placement="left"
                label-width="100"
              >
                <n-form-item label="季节">
                  <n-select
                    v-model:value="metadata.season"
                    :options="seasonOptions"
                    clearable
                    placeholder="为所有照片设置季节"
                  />
                </n-form-item>
                <n-form-item label="类别">
                  <n-select
                    v-model:value="metadata.category"
                    :options="categoryOptions"
                    clearable
                    placeholder="为所有照片设置类别"
                  />
                </n-form-item>
                <n-form-item label="描述">
                  <n-input
                    v-model:value="metadata.description"
                    type="textarea"
                    :rows="2"
                    placeholder="为所有照片设置描述"
                  />
                </n-form-item>
              </n-form>
            </n-card>

            <!-- 操作按钮 -->
            <div v-if="fileList.length > 0" class="action-buttons">
              <n-button @click="clearAll" size="large">清空列表</n-button>
              <n-button
                type="primary"
                size="large"
                :loading="uploading"
                :disabled="!canUpload"
                @click="startUpload"
              >
                <template #icon>
                  <n-icon :component="CloudUploadOutline" />
                </template>
                开始上传 ({{ pendingCount }}/{{ fileList.length }})
              </n-button>
            </div>

            <!-- 上传完成提示 -->
            <n-result
              v-if="allUploaded"
              status="success"
              title="上传完成"
              :description="`成功上传 ${successCount} 张照片`"
              class="upload-result"
            >
              <template #footer>
                <n-space>
                  <n-button @click="clearAll" size="large">继续上传</n-button>
                  <n-button type="primary" @click="router.push('/')" size="large">
                    <template #icon>
                      <n-icon :component="ImagesOutline" />
                    </template>
                    查看照片
                  </n-button>
                </n-space>
              </template>
            </n-result>
          </div>
        </n-layout-content>
      </n-layout>
    </n-layout>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { CloudUploadOutline, ImageOutline, SyncOutline, CheckmarkOutline, CloseOutline, ArrowBackOutline, ImagesOutline } from '@vicons/ionicons5'
import { uploadPhoto } from '../api/photo'
import type { UploadCustomRequestOptions } from 'naive-ui'

const router = useRouter()
const message = useMessage()

interface FileItem {
  file: File
  preview: string | null
  status: 'pending' | 'uploading' | 'success' | 'error'
  progress: number
  errorMsg?: string
}

const fileList = ref<FileItem[]>([])
const uploading = ref(false)
const metadata = ref({
  season: null as string | null,
  category: null as string | null,
  description: null as string | null,
})

const seasonOptions = [
  { label: 'Spring', value: 'Spring' },
  { label: 'Summer', value: 'Summer' },
  { label: 'Autumn', value: 'Autumn' },
  { label: 'Winter', value: 'Winter' },
]

const categoryOptions = [
  { label: 'Landscape', value: 'Landscape' },
  { label: 'Portrait', value: 'Portrait' },
  { label: 'Activity', value: 'Activity' },
  { label: 'Documentary', value: 'Documentary' },
]

const pendingCount = computed(() => {
  return fileList.value.filter(item => item.status === 'pending').length
})

const successCount = computed(() => {
  return fileList.value.filter(item => item.status === 'success').length
})

const errorCount = computed(() => {
  return fileList.value.filter(item => item.status === 'error').length
})

const canUpload = computed(() => {
  return pendingCount.value > 0 && !uploading.value
})

const allUploaded = computed(() => {
  return fileList.value.length > 0 && 
         pendingCount.value === 0 && 
         !uploading.value &&
         successCount.value > 0
})

function handleBeforeUpload(options: { file: File; fileList: File[] }) {
  const { file } = options
  
  // 检查文件类型
  if (!file.type.startsWith('image/')) {
    message.error(`${file.name} 不是图片文件`)
    return false
  }
  
  // 检查文件大小 (20MB)
  if (file.size > 20 * 1024 * 1024) {
    message.error(`${file.name} 大小超过 20MB`)
    return false
  }
  
  return true
}

function handleFileChange(options: { fileList: Array<{ file: File }> }) {
  // 这个方法在使用 custom-request 时不会被调用文件到列表
  // 我们在 handleUploadRequest 中手动处理
}

function handleUploadRequest(options: UploadCustomRequestOptions) {
  const { file } = options
  
  // 创建预览
  const reader = new FileReader()
  reader.onload = (e) => {
    const preview = e.target?.result as string
    fileList.value.push({
      file: file.file as File,
      preview,
      status: 'pending',
      progress: 0,
    })
  }
  reader.readAsDataURL(file.file as File)
  
  // 不实际上传，等待用户点击"开始上传"
  return
}

function removeFile(index: number) {
  fileList.value.splice(index, 1)
}

function clearAll() {
  fileList.value = []
  metadata.value = {
    season: null,
    category: null,
    description: null,
  }
}

async function startUpload() {
  uploading.value = true
  
  const pendingFiles = fileList.value.filter(item => item.status === 'pending')
  
  for (const item of pendingFiles) {
    await uploadSingleFile(item)
  }
  
  uploading.value = false
  
  if (successCount.value === fileList.value.length) {
    message.success('全部上传成功！')
  } else {
    message.warning(`上传完成，成功 ${successCount.value} 张，失败 ${fileList.value.length - successCount.value} 张`)
  }
}

async function uploadSingleFile(item: FileItem) {
  item.status = 'uploading'
  item.progress = 0
  
  try {
    // 模拟进度
    const progressInterval = setInterval(() => {
      if (item.progress < 90) {
        item.progress += 10
      }
    }, 200)
    
    const metadataToSend: any = {}
    if (metadata.value.season) metadataToSend.season = metadata.value.season
    if (metadata.value.category) metadataToSend.category = metadata.value.category
    if (metadata.value.description) metadataToSend.description = metadata.value.description
    
    await uploadPhoto(item.file, metadataToSend)
    
    clearInterval(progressInterval)
    item.progress = 100
    item.status = 'success'
  } catch (error: any) {
    item.status = 'error'
    item.errorMsg = error?.response?.data?.detail || '上传失败'
    message.error(`${item.file.name} 上传失败: ${item.errorMsg}`)
  }
}

async function retryUpload(index: number) {
  const item = fileList.value[index]
  if (item) {
    item.status = 'pending'
    item.progress = 0
    item.errorMsg = undefined
    await uploadSingleFile(item)
  }
}

function formatFileSize(bytes: number): string {
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  return `${size.toFixed(2)} ${units[unitIndex]}`
}
</script>

<style scoped>
.upload-container {
  height: 100vh;
  overflow: hidden;
}

.upload-sidebar {
  height: 100vh;
  overflow-y: auto;
}

.sidebar-content {
  padding: 24px;
}

.back-button {
  width: 100%;
  justify-content: flex-start;
}

.upload-stats {
  margin-top: 24px;
}

.upload-stats .n-statistic {
  margin-bottom: 16px;
}

.upload-header {
  height: 64px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.upload-main-content {
  height: calc(100vh - 64px);
  overflow-y: auto;
}

.upload-content {
  max-width: 1000px;
  margin: 0 auto;
}

.upload-dragger-content {
  text-align: center;
  padding: 40px 20px;
}

.upload-text {
  display: block;
  font-size: 16px;
  font-weight: 500;
  margin: 16px 0 8px;
}

.upload-hint {
  margin: 0;
}

.file-list-section {
  margin-top: 24px;
}

.file-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.file-list {
  margin-top: 16px;
}

.file-item {
  transition: background 0.3s ease;
}

.file-item:hover {
  background: #fafafa;
}

.file-avatar {
  width: 64px;
  height: 64px;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
}

.file-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.file-progress {
  margin-top: 8px;
}

.metadata-card {
  margin-top: 24px;
}

.action-buttons {
  margin-top: 32px;
  display: flex;
  justify-content: center;
  gap: 16px;
}

.upload-result {
  margin-top: 48px;
}

@media (max-width: 768px) {
  .upload-sidebar {
    display: none;
  }
  
  .action-buttons {
    flex-direction: column;
  }
}
</style>
