<template>
  <div class="user-management-container">
    <n-card title="用户管理">
      <!-- 工具栏 -->
      <template #header-extra>
        <n-space>
          <n-input
            v-model:value="searchQuery"
            placeholder="搜索用户..."
            clearable
            style="width: 200px"
            @keyup.enter="fetchUsers"
          >
            <template #prefix>
              <n-icon><SearchIcon /></n-icon>
            </template>
          </n-input>
          <n-select
            v-model:value="roleFilter"
            placeholder="角色筛选"
            :options="roleOptions"
            clearable
            style="width: 120px"
            @update:value="fetchUsers"
          />
          <n-button type="primary" @click="showCreateModal = true">
            <template #icon><n-icon><AddIcon /></n-icon></template>
            新建用户
          </n-button>
        </n-space>
      </template>

      <!-- 用户列表 -->
      <n-spin :show="loading">
        <n-data-table
          :columns="columns"
          :data="users"
          :bordered="false"
          :pagination="pagination"
          :row-key="(row: User) => row.id"
          remote
          @update:page="handlePageChange"
        />
      </n-spin>
    </n-card>

    <!-- 创建用户弹窗 -->
    <n-modal
      v-model:show="showCreateModal"
      preset="card"
      title="新建用户"
      style="width: 500px"
      :mask-closable="false"
    >
      <n-form
        ref="createFormRef"
        :model="createForm"
        :rules="createRules"
        label-placement="left"
        label-width="80px"
      >
        <n-form-item label="邮箱" path="email">
          <n-input v-model:value="createForm.email" placeholder="请输入邮箱" />
        </n-form-item>
        <n-form-item label="姓名" path="full_name">
          <n-input v-model:value="createForm.full_name" placeholder="请输入姓名（可选）" />
        </n-form-item>
        <n-form-item label="密码" path="password">
          <n-input
            v-model:value="createForm.password"
            type="password"
            placeholder="请输入密码"
            show-password-on="click"
          />
        </n-form-item>
        <n-form-item label="角色" path="role">
          <n-select v-model:value="createForm.role" :options="roleOptions" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showCreateModal = false">取消</n-button>
          <n-button type="primary" :loading="submitting" @click="handleCreate">创建</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 编辑用户弹窗 -->
    <n-modal
      v-model:show="showEditModal"
      preset="card"
      title="编辑用户"
      style="width: 500px"
      :mask-closable="false"
    >
      <n-form
        ref="editFormRef"
        :model="editForm"
        label-placement="left"
        label-width="80px"
      >
        <n-form-item label="邮箱">
          <n-input v-model:value="editForm.email" placeholder="请输入邮箱" />
        </n-form-item>
        <n-form-item label="姓名">
          <n-input v-model:value="editForm.full_name" placeholder="请输入姓名" />
        </n-form-item>
        <n-form-item label="新密码">
          <n-input
            v-model:value="editForm.password"
            type="password"
            placeholder="留空则不修改"
            show-password-on="click"
          />
        </n-form-item>
        <n-form-item label="角色">
          <n-select v-model:value="editForm.role" :options="roleOptions" />
        </n-form-item>
        <n-form-item label="状态">
          <n-switch v-model:value="editForm.is_active">
            <template #checked>启用</template>
            <template #unchecked>禁用</template>
          </n-switch>
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showEditModal = false">取消</n-button>
          <n-button type="primary" :loading="submitting" @click="handleUpdate">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, h, onMounted } from 'vue'
import { useMessage, useDialog, NButton, NTag, NSpace, type FormInst } from 'naive-ui'
import { Search as SearchIcon, Add as AddIcon } from '@vicons/ionicons5'
import type { DataTableColumns } from 'naive-ui'
import type { User, UserRole, UserCreateRequest, UserUpdateRequest } from '../../types/user'
import * as usersApi from '../../api/users'
import { useAuthStore } from '../../stores/auth'

const message = useMessage()
const dialog = useDialog()
const authStore = useAuthStore()

// 状态
const loading = ref(false)
const submitting = ref(false)
const users = ref<User[]>([])
const total = ref(0)
const searchQuery = ref('')
const roleFilter = ref<UserRole | null>(null)

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 20,
  pageCount: 1,
  showSizePicker: true,
  pageSizes: [10, 20, 50],
})

// 弹窗状态
const showCreateModal = ref(false)
const showEditModal = ref(false)
const createFormRef = ref<FormInst | null>(null)
const editFormRef = ref<FormInst | null>(null)
const editingUserId = ref<string | null>(null)

// 表单数据
const createForm = reactive<UserCreateRequest>({
  email: '',
  full_name: '',
  password: '',
  role: 'user',
})

const editForm = reactive<UserUpdateRequest & { is_active: boolean }>({
  email: '',
  full_name: '',
  password: '',
  role: 'user',
  is_active: true,
})

// 角色选项
const roleOptions = [
  { label: '超级管理员', value: 'admin' },
  { label: '审核员', value: 'auditor' },
  { label: '部门用户', value: 'dept_user' },
  { label: '普通用户', value: 'user' },
]

// 表单验证规则
const createRules = {
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

// 角色标签映射
const roleTagMap: Record<UserRole, { label: string; type: 'success' | 'warning' | 'info' | 'default' }> = {
  admin: { label: '超级管理员', type: 'success' },
  auditor: { label: '审核员', type: 'warning' },
  dept_user: { label: '部门用户', type: 'info' },
  user: { label: '普通用户', type: 'default' },
}

// 表格列定义
const columns: DataTableColumns<User> = [
  { title: '邮箱', key: 'email', ellipsis: { tooltip: true } },
  { title: '姓名', key: 'full_name', width: 120 },
  {
    title: '角色',
    key: 'role',
    width: 120,
    render: (row) => {
      const tag = roleTagMap[row.role] || { label: row.role, type: 'default' as const }
      return h(NTag, { type: tag.type, size: 'small' }, { default: () => tag.label })
    },
  },
  {
    title: '状态',
    key: 'is_active',
    width: 80,
    render: (row) => h(NTag, { type: row.is_active ? 'success' : 'error', size: 'small' }, { default: () => row.is_active ? '启用' : '禁用' }),
  },
  {
    title: '创建时间',
    key: 'created_at',
    width: 180,
    render: (row) => new Date(row.created_at).toLocaleString('zh-CN'),
  },
  {
    title: '操作',
    key: 'actions',
    width: 150,
    render: (row) => {
      const isSelf = row.id === authStore.user?.id
      return h(NSpace, {}, {
        default: () => [
          h(NButton, { size: 'small', onClick: () => openEditModal(row) }, { default: () => '编辑' }),
          h(NButton, { size: 'small', type: 'error', disabled: isSelf, onClick: () => handleDelete(row) }, { default: () => '删除' }),
        ],
      })
    },
  },
]

// 生命周期
onMounted(() => {
  fetchUsers()
})

// 方法
async function fetchUsers() {
  loading.value = true
  try {
    const skip = (pagination.page - 1) * pagination.pageSize
    const response = await usersApi.getUsers({
      skip,
      limit: pagination.pageSize,
      search: searchQuery.value || undefined,
      role: roleFilter.value || undefined,
    })
    users.value = response.users
    total.value = response.total
    pagination.pageCount = Math.ceil(response.total / pagination.pageSize)
  } catch (error) {
    message.error('加载用户列表失败')
  } finally {
    loading.value = false
  }
}

function handlePageChange(page: number) {
  pagination.page = page
  fetchUsers()
}

async function handleCreate() {
  try {
    await createFormRef.value?.validate()
  } catch {
    return
  }

  submitting.value = true
  try {
    await usersApi.createUser(createForm)
    message.success('用户创建成功')
    showCreateModal.value = false
    resetCreateForm()
    fetchUsers()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '创建用户失败')
  } finally {
    submitting.value = false
  }
}

function openEditModal(user: User) {
  editingUserId.value = user.id
  editForm.email = user.email
  editForm.full_name = user.full_name || ''
  editForm.password = ''
  editForm.role = user.role
  editForm.is_active = user.is_active
  showEditModal.value = true
}

async function handleUpdate() {
  if (!editingUserId.value) return

  submitting.value = true
  try {
    const updateData: UserUpdateRequest = {
      email: editForm.email,
      full_name: editForm.full_name,
      role: editForm.role,
      is_active: editForm.is_active,
    }
    if (editForm.password) {
      updateData.password = editForm.password
    }
    await usersApi.updateUser(editingUserId.value, updateData)
    message.success('用户更新成功')
    showEditModal.value = false
    fetchUsers()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '更新用户失败')
  } finally {
    submitting.value = false
  }
}

function handleDelete(user: User) {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除用户 ${user.email} 吗？此操作不可恢复。`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await usersApi.deleteUser(user.id)
        message.success('用户已删除')
        fetchUsers()
      } catch (error: any) {
        message.error(error?.response?.data?.detail || '删除用户失败')
      }
    },
  })
}

function resetCreateForm() {
  createForm.email = ''
  createForm.full_name = ''
  createForm.password = ''
  createForm.role = 'user'
}
</script>

<style scoped>
.user-management-container {
  padding: 24px;
}
</style>
