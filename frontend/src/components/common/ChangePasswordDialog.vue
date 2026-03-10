<template>
  <n-modal v-model:show="visible" preset="dialog" title="修改密码" positive-text="确认修改" negative-text="取消"
    :loading="loading" @positive-click="handleSubmit" @negative-click="visible = false">
    <n-form ref="formRef" :model="formData" :rules="rules" label-placement="left" label-width="80">
      <n-form-item label="原密码" path="old_password">
        <n-input v-model:value="formData.old_password" type="password" show-password-on="click"
          placeholder="请输入原密码" />
      </n-form-item>
      <n-form-item label="新密码" path="new_password">
        <n-input v-model:value="formData.new_password" type="password" show-password-on="click"
          placeholder="请输入新密码（至少6位）" />
      </n-form-item>
      <n-form-item label="确认密码" path="confirm_password">
        <n-input v-model:value="formData.confirm_password" type="password" show-password-on="click"
          placeholder="请再次输入新密码" />
      </n-form-item>
    </n-form>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { useMessage, type FormInst, type FormRules } from 'naive-ui'
import { changePassword } from '../../api/auth'

const props = defineProps<{ show: boolean }>()
const emit = defineEmits<{ (e: 'update:show', value: boolean): void }>()

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const loading = ref(false)

const visible = ref(false)
watch(() => props.show, (val) => { visible.value = val })
watch(visible, (val) => { emit('update:show', val) })

const formData = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

const rules: FormRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (_rule: any, value: string) => {
        if (value !== formData.new_password) {
          return new Error('两次输入的密码不一致')
        }
        return true
      },
      trigger: 'blur',
    },
  ],
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
  } catch {
    return false  // 阻止关闭
  }

  loading.value = true
  try {
    await changePassword(formData.old_password, formData.new_password)
    message.success('密码修改成功')
    visible.value = false
    // 重置表单
    formData.old_password = ''
    formData.new_password = ''
    formData.confirm_password = ''
    return true
  } catch (error: any) {
    const detail = error?.response?.data?.detail || '密码修改失败'
    message.error(detail)
    return false  // 阻止关闭
  } finally {
    loading.value = false
  }
}
</script>
