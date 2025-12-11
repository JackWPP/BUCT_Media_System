import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { uploadPhoto } from '../api/photo'
import { useMessage } from 'naive-ui'

export interface FileItem {
    file: File
    preview: string | null
    status: 'pending' | 'uploading' | 'success' | 'error'
    progress: number
    errorMsg?: string
    // UUID for tracking identity if needed
    id: string
}

export const useUploadStore = defineStore('upload', () => {
    // State
    const fileList = ref<FileItem[]>([])
    const uploading = ref(false)
    const metadata = ref({
        season: null as string | null,
        category: null as string | null,
        description: null as string | null,
    })

    // Getters
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

    // Actions
    function addFiles(files: File[]) {
        files.forEach(file => {
            // Create preview
            const reader = new FileReader()
            reader.onload = (e) => {
                const preview = e.target?.result as string
                fileList.value.push({
                    id: Math.random().toString(36).substr(2, 9),
                    file,
                    preview,
                    status: 'pending',
                    progress: 0,
                })
            }
            reader.readAsDataURL(file)
        })
    }

    function removeFile(index: number) {
        fileList.value.splice(index, 1)
    }

    function clearAll() {
        // Revoke object URLs if we used URL.createObjectURL (here we used dataURL so strict cleanup isn't as critical but good memory hygiene to reset)
        fileList.value = []
        metadata.value = {
            season: null,
            category: null,
            description: null,
        }
        uploading.value = false
    }

    async function startUpload(messageApi: any) {
        if (uploading.value) return
        uploading.value = true

        const pendingFiles = fileList.value.filter(item => item.status === 'pending')

        // Upload one by one to avoid overwhelming server/browser
        // Also allows better progress tracking
        for (const item of pendingFiles) {
            // Check if we should stop? (optional feature for later)
            await uploadSingleFile(item)
        }

        uploading.value = false

        if (successCount.value === fileList.value.length) {
            if (messageApi) messageApi.success('全部上传成功！')
        } else {
            if (messageApi) messageApi.warning(`上传完成，成功 ${successCount.value} 张，失败 ${fileList.value.length - successCount.value} 张`)
        }
    }

    async function uploadSingleFile(item: FileItem) {
        item.status = 'uploading'
        item.progress = 0

        try {
            const metadataToSend: any = {}
            if (metadata.value.season) metadataToSend.season = metadata.value.season
            if (metadata.value.category) metadataToSend.category = metadata.value.category
            if (metadata.value.description) metadataToSend.description = metadata.value.description

            // Pass progress callback
            await uploadPhoto(item.file, metadataToSend, (progressEvent: any) => {
                if (progressEvent.total) {
                    const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
                    item.progress = percentCompleted
                }
            })

            item.progress = 100
            item.status = 'success'
        } catch (error: any) {
            item.status = 'error'
            item.progress = 0
            item.errorMsg = error?.response?.data?.detail || '上传失败'
        }
    }

    async function retryUpload(index: number) {
        const item = fileList.value[index]
        if (item && item.status === 'error') {
            item.status = 'pending'
            item.errorMsg = undefined
            // If we are not currently global uploading, just upload this one
            if (!uploading.value) {
                uploading.value = true
                await uploadSingleFile(item)
                uploading.value = false
            } else {
                // If already uploading loop, just mark as pending and the loop (if implemented to pick up new pending) or next start will pick it up
                // Since our loop only picked "pendingFiles" at start, we might need to manually trigger this one.
                // Simple approach: just upload it now.
                await uploadSingleFile(item)
            }
        }
    }

    return {
        fileList,
        uploading,
        metadata,
        pendingCount,
        successCount,
        errorCount,
        canUpload,
        addFiles,
        removeFile,
        clearAll,
        startUpload,
        retryUpload
    }
})
