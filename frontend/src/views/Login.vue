<template>
  <div class="login-page">
    <n-card class="login-card" size="large">
      <template #header>
        <div class="card-header">
          <n-icon size="40" color="#18a058">
            <ImagesOutline />
          </n-icon>
          <h2>BUCT Media HUB</h2>
        </div>
      </template>
      
      <n-alert
        v-if="errorMessage"
        type="error"
        :title="errorMessage"
        closable
        @close="errorMessage = ''"
        style="margin-bottom: 16px;"
      />
      
      <n-tabs v-model:value="activeTab" type="line" animated>
        <n-tab-pane name="login" tab="登录">
          <n-form
            ref="loginFormRef"
            :model="loginForm"
            :rules="loginRules"
            size="large"
          >
            <n-form-item label="邮箱" path="email">
              <n-input
                v-model:value="loginForm.email"
                placeholder="请输入邮箱"
                @keydown.enter="handleLogin"
              />
            </n-form-item>
            
            <n-form-item label="密码" path="password">
              <n-input
                v-model:value="loginForm.password"
                type="password"
                show-password-on="click"
                placeholder="请输入密码"
                @keydown.enter="handleLogin"
              />
            </n-form-item>
            
            <n-button
              type="primary"
              block
              size="large"
              :loading="loading"
              @click="handleLogin"
              style="margin-top: 16px;"
            >
              {{ loading ? '登录中...' : '登录' }}
            </n-button>
          </n-form>
        </n-tab-pane>
        
        <n-tab-pane name="register" tab="注册">
          <n-form
            ref="registerFormRef"
            :model="registerForm"
            :rules="registerRules"
            size="large"
          >
            <n-form-item label="邮箱" path="email">
              <n-input
                v-model:value="registerForm.email"
                placeholder="请输入邮箱"
              />
            </n-form-item>
            
            <n-form-item label="姓名" path="full_name">
              <n-input
                v-model:value="registerForm.full_name"
                placeholder="请输入姓名（可选）"
              />
            </n-form-item>
            
            <n-form-item label="密码" path="password">
              <n-input
                v-model:value="registerForm.password"
                type="password"
                show-password-on="click"
                placeholder="请输入密码"
              />
            </n-form-item>
            
            <n-form-item label="确认密码" path="confirmPassword">
              <n-input
                v-model:value="registerForm.confirmPassword"
                type="password"
                show-password-on="click"
                placeholder="请再次输入密码"
                @keydown.enter="handleRegister"
              />
            </n-form-item>
            
            <n-button
              type="primary"
              block
              size="large"
              :loading="registering"
              @click="handleRegister"
              style="margin-top: 16px;"
            >
              {{ registering ? '注册中...' : '注册' }}
            </n-button>
          </n-form>
        </n-tab-pane>
      </n-tabs>
      
      <n-divider>或</n-divider>
      
      <n-button block tertiary @click="goToGallery">
        跳过登录，直接浏览
      </n-button>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'
import type { FormInst, FormRules } from 'naive-ui'
import { ImagesOutline } from '@vicons/ionicons5'
import { useAuthStore } from '../stores/auth'
import request from '../api/index'

const router = useRouter()
const route = useRoute()
const message = useMessage()
const authStore = useAuthStore()

const loginFormRef = ref<FormInst | null>(null)
const registerFormRef = ref<FormInst | null>(null)
const loading = ref(false)
const registering = ref(false)
const errorMessage = ref('')
const activeTab = ref('login')

const loginForm = ref({
  email: '',
  password: '',
})

const registerForm = ref({
  email: '',
  full_name: '',
  password: '',
  confirmPassword: '',
})

const loginRules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: ['input', 'blur'] },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: ['blur'] },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: ['input', 'blur'] },
    { min: 6, message: '密码至少6位', trigger: ['blur'] },
  ],
}

const registerRules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: ['input', 'blur'] },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: ['blur'] },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: ['input', 'blur'] },
    { min: 6, message: '密码至少6位', trigger: ['blur'] },
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: ['input', 'blur'] },
    {
      validator: (_rule: any, value: string) => {
        if (value !== registerForm.value.password) {
          return new Error('两次密码输入不一致')
        }
        return true
      },
      trigger: ['blur'],
    },
  ],
}

async function handleLogin() {
  if (!loginFormRef.value) return
  
  errorMessage.value = ''

  try {
    await loginFormRef.value.validate()
    loading.value = true

    await authStore.login(loginForm.value.email, loginForm.value.password)
    
    message.success('登录成功')
    
    // 跳转到原目标页面或首页
    const redirect = route.query.redirect as string || '/'
    setTimeout(() => {
      router.push(redirect)
    }, 300)
  } catch (error: any) {
    if (error instanceof Error && error.message) {
      return
    }
    console.error('登录失败:', error)
    const errMsg = error?.response?.data?.detail || '登录失败，请检查邮箱和密码'
    errorMessage.value = errMsg
    message.error(errMsg)
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  if (!registerFormRef.value) return
  
  errorMessage.value = ''

  try {
    await registerFormRef.value.validate()
    registering.value = true

    await request.post('/api/v1/auth/register', {
      email: registerForm.value.email,
      full_name: registerForm.value.full_name || undefined,
      password: registerForm.value.password,
    })
    
    message.success('注册成功，请登录')
    
    // 切换到登录tab
    activeTab.value = 'login'
    loginForm.value.email = registerForm.value.email
    registerForm.value = { email: '', full_name: '', password: '', confirmPassword: '' }
  } catch (error: any) {
    console.error('注册失败:', error)
    const errMsg = error?.response?.data?.detail || '注册失败'
    errorMessage.value = errMsg
    message.error(errMsg)
  } finally {
    registering.value = false
  }
}

function goToGallery() {
  router.push('/')
}
</script>

<style scoped>
.login-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 450px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.card-header h2 {
  margin: 0;
  font-size: 24px;
  color: #18a058;
}
</style>
