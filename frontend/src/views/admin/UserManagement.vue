<template>
  <div class="user-management-container">
    <n-card title="用户管理">
      <!-- 工具栏 -->
      <template #header-extra>
        <n-space>
          <n-input
            v-model:value="searchQuery"
            placeholder="搜索学号/邮箱/姓名..."
            clearable
            style="width: 220px"
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
        <n-form-item label="学号" path="student_id">
          <n-input v-model:value="createForm.student_id" placeholder="请输入学号/工号（必填）" />
        </n-form-item>
        <n-form-item label="邮箱" path="email">
          <n-input v-model:value="createForm.email" placeholder="请输入邮箱（可选）" />
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
        <n-form-item label="学号">
          <n-input v-model:value="editForm.student_id" placeholder="请输入学号/工号" />
        </n-form-item>
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

    <!-- 权限管理弹窗 -->
    <n-modal
      v-model:show="showPermissionModal"
      preset="card"
      title="权限管理"
      style="width: 700px"
    >
      <template #header-extra>
        当前用户: {{ activeUser?.full_name }} ({{ activeUser?.student_id }})
      </template>

      <n-space vertical size="large">
        <!-- 现有权限列表 -->
        <n-card size="small" title="已授予权限">
          <n-data-table
            :columns="permissionColumns"
            :data="userPermissions"
            :loading="permissionLoading"
            size="small"
            :max-height="200"
          />
        </n-card>

        <!-- 新增授权 -->
        <n-card size="small" title="新增授权">
          <n-form inline :model="permissionForm" label-placement="left">
            <n-form-item label="资源类别">
              <n-input value="人像摄影 (Portrait)" disabled style="width: 140px" />
            </n-form-item>
            <n-form-item label="有效期(天)">
              <n-input-number v-model:value="permissionForm.days" :min="1" style="width: 100px" />
            </n-form-item>
            <n-form-item label="备注">
              <n-input v-model:value="permissionForm.note" placeholder="选填" />
            </n-form-item>
            <n-form-item>
              <n-button type="primary" :loading="submitting" @click="handleGrantPermission">授予权限</n-button>
            </n-form-item>
          </n-form>
        </n-card>
      </n-space>
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
import * as permissionApi from '../../api/permissions'
import type { PermissionResponse, PermissionGrantRequest } from '../../api/permissions'
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
  student_id: '',
  email: '',
  full_name: '',
  password: '',
  role: 'user',
})

const editForm = reactive<UserUpdateRequest & { is_active: boolean }>({
  student_id: '',
  email: '',
  full_name: '',
  password: '',
  role: 'user',
  is_active: true,
})

// 权限管理状态
const showPermissionModal = ref(false)
const permissionLoading = ref(false)
const activeUser = ref<User | null>(null)
const userPermissions = ref<PermissionResponse[]>([])
const permissionForm = reactive<PermissionGrantRequest>({
  student_id: '',
  resource_type: 'category',
  resource_key: 'Portrait',
  permission_type: 'view',
  days: 30,
  note: ''
})

// 角色选项
const roleOptions = [
  { label: '超级管理员', value: 'admin' },
  { label: '审核员', value: 'auditor' },
  { label: '部门用户', value: 'dept_user' },
  { label: '普通用户', value: 'user' },
]

// 表单验证规则 - 学号必填，邮箱可选
const createRules = {
  student_id: [{ required: true, message: '请输入学号/工号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

// 角色标签映射
const roleTagMap: Record<UserRole, { label: string; type: 'success' | 'warning' | 'info' | 'default' }> = {
  admin: { label: '超级管理员', type: 'success' },
  auditor: { label: '审核员', type: 'warning' },
  dept_user: { label: '部门用户', type: 'info' },
  user: { label: '普通用户', type: 'default' },
}

// 表格列定义 - 学号作为第一列
const columns: DataTableColumns<User> = [
  { title: '学号', key: 'student_id', width: 120, ellipsis: { tooltip: true } },
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
          h(NButton, { size: 'small', type: 'info', onClick: () => openPermissionModal(row) }, { default: () => '授权' }),
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
  editForm.student_id = user.student_id || ''
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
      student_id: editForm.student_id,
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
  createForm.student_id = ''
  createForm.email = ''
  createForm.full_name = ''
  createForm.password = ''
  createForm.role = 'user'
}

// 权限管理方法
async function openPermissionModal(user: User) {
  if (!user.student_id) {
    message.warning('该用户未绑定学号，无法进行授权管理')
    return
  }
  activeUser.value = user
  showPermissionModal.value = true
  permissionForm.student_id = user.student_id
  permissionForm.days = 30
  permissionForm.note = ''
  await fetchUserPermissions(user.student_id)
}

async function fetchUserPermissions(studentId: string) {
  permissionLoading.value = true
  try {
    const res = await permissionApi.getUserPermissions(studentId)
    userPermissions.value = res.permissions
  } catch (error) {
    message.error('加载权限列表失败')
  } finally {
    permissionLoading.value = false
  }
}

async function handleGrantPermission() {
  if (!activeUser.value?.student_id) return
  
  submitting.value = true
  try {
    await permissionApi.grantPermission(permissionForm)
    message.success('授权成功')
    await fetchUserPermissions(activeUser.value.student_id)
    permissionForm.note = '' // 重置备注
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '授权失败')
  } finally {
    submitting.value = false
  }
}

async function handleRevokePermission(permissionId: string) {
  try {
    await permissionApi.revokePermission(permissionId)
    message.success('已撤销权限')
    if (activeUser.value?.student_id) {
      await fetchUserPermissions(activeUser.value.student_id)
    }
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '撤销失败')
  }
}

const permissionColumns = [
  { title: '资源类型', key: 'resource_type', width: 100 },
  { title: '资源键值', key: 'resource_key', width: 100 },
  { title: '有效期至', key: 'end_time', width: 180, render: (row: any) => row.end_time ? new Date(row.end_time).toLocaleString() : '永久' },
  { title: '状态', key: 'is_active', width: 80, render: (row: any) => h(NTag, { type: row.is_active ? 'success' : 'error', size: 'small' }, { default: () => row.is_active ? '有效' : '过期' }) },
  {
    title: '操作',
    key: 'actions',
    width: 80,
    render: (row: any) => h(NButton, { size: 'small', type: 'error', onClick: () => handleRevokePermission(row.id) }, { default: () => '撤销' })
  }
]
</script>

<style scoped>
.user-management-container {
  padding: 24px;
}
</style>
