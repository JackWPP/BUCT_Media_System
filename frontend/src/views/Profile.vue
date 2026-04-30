<template>
  <div class="profile-container">
    <n-card title="个人中心" class="profile-card">
      <n-tabs type="line" animated>
        <n-tab-pane name="info" tab="基本资料">
          <n-form
            ref="formRef"
            :model="formData"
            :rules="formRules"
            label-placement="left"
            label-width="100px"
            class="profile-form"
          >
            <n-form-item label="学号/工号">
              <n-input :value="authStore.user?.student_id" disabled />
            </n-form-item>
            <n-form-item label="角色">
              <n-tag :type="roleTagType">{{ roleLabel }}</n-tag>
            </n-form-item>
            <n-form-item label="邮箱" path="email">
              <n-input v-model:value="formData.email" placeholder="请输入邮箱" />
            </n-form-item>
            <n-form-item label="姓名" path="full_name">
              <n-input v-model:value="formData.full_name" placeholder="请输入姓名" />
            </n-form-item>
            <n-form-item label="注册时间">
              <n-text depth="3">{{ formatDate(authStore.user?.created_at) }}</n-text>
            </n-form-item>
            <n-form-item>
              <n-space>
                <n-button type="primary" :loading="saving" @click="handleSave">
                  保存修改
                </n-button>
                <n-button @click="showChangePassword = true">
                  修改密码
                </n-button>
              </n-space>
            </n-form-item>
          </n-form>
        </n-tab-pane>

        <n-tab-pane name="stats" tab="我的统计">
          <n-grid :cols="3" :x-gap="16" :y-gap="16">
            <n-gi>
              <n-statistic label="总投稿" :value="stats.total" />
            </n-gi>
            <n-gi>
              <n-statistic label="已发布" :value="stats.approved">
                <template #suffix>
                  <n-tag type="success" size="small">通过</n-tag>
                </template>
              </n-statistic>
            </n-gi>
            <n-gi>
              <n-statistic label="审核中" :value="stats.pending">
                <template #suffix>
                  <n-tag type="warning" size="small">待审</n-tag>
                </template>
              </n-statistic>
            </n-gi>
            <n-gi>
              <n-statistic label="已驳回" :value="stats.rejected">
                <template #suffix>
                  <n-tag type="error" size="small">驳回</n-tag>
                </template>
              </n-statistic>
            </n-gi>
            <n-gi>
              <n-statistic label="收藏数" :value="stats.favorites" />
            </n-gi>
          </n-grid>
        </n-tab-pane>
      </n-tabs>
    </n-card>

    <ChangePasswordDialog v-model:show="showChangePassword" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { useMessage, type FormInst, type FormRules } from 'naive-ui'
import { useAuthStore } from '../stores/auth'
import ChangePasswordDialog from '../components/common/ChangePasswordDialog.vue'
import * as photoApi from '../api/photo'
import * as authApi from '../api/auth'

const message = useMessage()
const authStore = useAuthStore()

const formRef = ref<FormInst | null>(null)
const saving = ref(false)
const showChangePassword = ref(false)

const formData = reactive({
  email: authStore.user?.email || '',
  full_name: authStore.user?.full_name || '',
})

const formRules: FormRules = {
  email: [
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
}

const roleLabel = computed(() => {
  const map: Record<string, string> = {
    admin: '超级管理员',
    auditor: '审核员',
    dept_user: '部门用户',
    user: '普通用户',
  }
  return map[authStore.user?.role || 'user'] || '普通用户'
})

const roleTagType = computed(() => {
  const map: Record<string, 'success' | 'warning' | 'info' | 'default'> = {
    admin: 'success',
    auditor: 'warning',
    dept_user: 'info',
    user: 'default',
  }
  return map[authStore.user?.role || 'user'] || 'default'
})

const stats = reactive({
  total: 0,
  approved: 0,
  pending: 0,
  rejected: 0,
  favorites: 0,
})

function formatDate(dateStr: string | undefined) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

async function handleSave() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  saving.value = true
  try {
    await authApi.updateProfile({
      email: formData.email || undefined,
      full_name: formData.full_name || undefined,
    })
    message.success('资料更新成功')
    await authStore.fetchCurrentUser()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '更新失败')
  } finally {
    saving.value = false
  }
}

async function loadStats() {
  try {
    const res = await photoApi.getMySubmissions({ limit: 1000 })
    const items = res.items || []
    stats.total = items.length
    stats.approved = items.filter((p) => p.status === 'approved').length
    stats.pending = items.filter((p) => p.status === 'pending').length
    stats.rejected = items.filter((p) => p.status === 'rejected').length
  } catch {
    // 静默失败
  }
}

onMounted(() => {
  loadStats()
})
</script>

<style scoped>
.profile-container {
  max-width: 800px;
  margin: 80px auto 24px;
  padding: 0 24px;
}

.profile-form {
  max-width: 480px;
  margin-top: 16px;
}
</style>
