<template>
  <div class="settings-container">
    <n-card title="系统设置">
      <n-spin :show="loading">
        <n-form
          ref="formRef"
          :model="settings"
          label-placement="left"
          label-width="160px"
          style="max-width: 600px"
        >
          <!-- 人像照片可见性设置 -->
          <n-form-item label="人像照片可见性">
            <n-radio-group v-model:value="settings.portrait_visibility">
              <n-space vertical>
                <n-radio value="public">
                  <n-space align="center">
                    <span>公开</span>
                    <n-tag size="small" type="success">所有人可见</n-tag>
                  </n-space>
                  <n-text depth="3" style="display: block; margin-left: 24px; font-size: 12px;">
                    游客和登录用户均可查看人像类照片
                  </n-text>
                </n-radio>
                <n-radio value="login_required">
                  <n-space align="center">
                    <span>需要登录</span>
                    <n-tag size="small" type="warning">登录后可见</n-tag>
                  </n-space>
                  <n-text depth="3" style="display: block; margin-left: 24px; font-size: 12px;">
                    仅登录用户可查看人像类照片，游客无法访问
                  </n-text>
                </n-radio>
                <n-radio value="authorized_only">
                  <n-space align="center">
                    <span>仅授权用户</span>
                    <n-tag size="small" type="error">受限访问</n-tag>
                  </n-space>
                  <n-text depth="3" style="display: block; margin-left: 24px; font-size: 12px;">
                    仅特定授权用户可查看人像类照片（暂同"需要登录"）
                  </n-text>
                </n-radio>
              </n-space>
            </n-radio-group>
          </n-form-item>

          <n-divider />

          <!-- 保存按钮 -->
          <n-form-item label="">
            <n-space>
              <n-button type="primary" :loading="saving" @click="handleSave">
                保存设置
              </n-button>
              <n-button @click="fetchSettings">重置</n-button>
            </n-space>
          </n-form-item>
        </n-form>
      </n-spin>
    </n-card>

    <!-- 设置说明 -->
    <n-card title="设置说明" style="margin-top: 16px;">
      <n-collapse>
        <n-collapse-item title="人像照片可见性" name="portrait">
          <n-text>
            此设置控制"人像"（Portrait）类别照片的访问权限。
          </n-text>
          <n-ul>
            <n-li><strong>公开</strong>：无需登录即可查看所有人像照片。</n-li>
            <n-li><strong>需要登录</strong>：必须登录后才能看到人像类照片，游客在图库中不会看到此类别。</n-li>
            <n-li><strong>仅授权用户</strong>：仅特定用户可查看（当前实现同"需要登录"，后续可扩展为指定角色）。</n-li>
          </n-ul>
        </n-collapse-item>
      </n-collapse>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import * as settingsApi from '../../api/settings'
import type { PortraitVisibility, SystemSettings } from '../../api/settings'

const message = useMessage()

// 状态
const loading = ref(false)
const saving = ref(false)

// 设置数据
const settings = reactive<SystemSettings>({
  portrait_visibility: 'login_required',
})

// 生命周期
onMounted(() => {
  fetchSettings()
})

// 方法
async function fetchSettings() {
  loading.value = true
  try {
    const data = await settingsApi.getSettings()
    settings.portrait_visibility = data.portrait_visibility
  } catch (error) {
    message.error('加载系统设置失败')
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    await settingsApi.updatePortraitVisibility(settings.portrait_visibility as PortraitVisibility)
    message.success('设置已保存')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '保存设置失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.settings-container {
  padding: 24px;
}
</style>
