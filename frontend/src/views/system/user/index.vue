<template>
  <div class="page">
    <h2 class="page-title">用户管理</h2>
    <p class="page-desc">系统用户与角色权限管理，支持管理员 / 操作员 / 访客三类角色</p>

    <div class="page-card">
      <div class="toolbar">
        <el-input v-model="query.username" placeholder="用户名" clearable style="width: 200px" @keyup.enter="load(1)" />
        <el-button type="primary" :icon="Search" @click="load(1)">查询</el-button>
        <span class="spacer"></span>
        <el-button type="primary" :icon="Plus" @click="openCreate">新增用户</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" border stripe>
        <el-table-column type="index" label="#" width="56" />
        <el-table-column prop="username" label="用户名" width="160" />
        <el-table-column prop="nickname" label="昵称" min-width="140" />
        <el-table-column label="角色" width="140">
          <template #default="{ row }">
            <el-tag size="small" :type="roleTag(row.role_id)" effect="plain">{{ row.role_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status ? 'success' : 'danger'" effect="plain">
              {{ row.status ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="warning" @click="openResetPwd(row)">重置密码</el-button>
            <el-button link type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="query.page"
          v-model:page-size="query.page_size"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="load()"
        />
      </div>
    </div>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑用户' : '新增用户'" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :disabled="isEdit" />
        </el-form-item>
        <el-form-item v-if="!isEdit" label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="至少 6 位" />
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="form.nickname" />
        </el-form-item>
        <el-form-item label="角色" prop="role_id">
          <el-select v-model="form.role_id" style="width: 100%">
            <el-option v-for="r in roles" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.status" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="pwdVisible" title="重置密码" width="420px">
      <el-form ref="pwdFormRef" :model="pwdForm" :rules="pwdRules" label-width="90px">
        <el-form-item label="用户">
          <el-input :model-value="pwdForm.username" disabled />
        </el-form-item>
        <el-form-item label="新密码" prop="password">
          <el-input v-model="pwdForm.password" type="password" show-password placeholder="至少 6 位" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onResetPwd">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import { systemApi } from '@/api'
import type { Role, SysUser } from '@/types'

const loading = ref(false)
const saving = ref(false)
const rows = ref<SysUser[]>([])
const roles = ref<Role[]>([])
const total = ref(0)
const query = reactive({ page: 1, page_size: 20, username: '' })

const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref<FormInstance>()
const form = reactive<{ id?: number; username: string; password?: string; nickname?: string; role_id?: number; status: boolean }>({
  username: '',
  status: true,
})

const pwdVisible = ref(false)
const pwdFormRef = ref<FormInstance>()
const pwdForm = reactive<{ id?: number; username: string; password: string }>({ username: '', password: '' })

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, min: 6, message: '密码至少 6 位', trigger: 'blur' }],
  role_id: [{ required: true, message: '请选择角色', trigger: 'change' }],
}
const pwdRules: FormRules = {
  password: [{ required: true, min: 6, message: '密码至少 6 位', trigger: 'blur' }],
}

function roleTag(id: number) {
  const code = roles.value.find((r) => r.id === id)?.code
  return code === 'admin' ? 'danger' : code === 'operator' ? 'warning' : 'info'
}

async function load(page?: number) {
  if (page) query.page = page
  loading.value = true
  try {
    const res = await systemApi.users({
      page: query.page,
      page_size: query.page_size,
      username: query.username || undefined,
    })
    rows.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function openCreate() {
  isEdit.value = false
  Object.assign(form, { id: undefined, username: '', password: '', nickname: '', role_id: roles.value[1]?.id, status: true })
  dialogVisible.value = true
}

function openEdit(row: SysUser) {
  isEdit.value = true
  Object.assign(form, { id: row.id, username: row.username, password: '', nickname: row.nickname, role_id: row.role_id, status: row.status })
  dialogVisible.value = true
}

async function onSave() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      if (isEdit.value && form.id) {
        await systemApi.updateUser(form.id, { nickname: form.nickname, role_id: form.role_id, status: form.status })
      } else {
        await systemApi.createUser({ username: form.username, password: form.password, nickname: form.nickname, role_id: form.role_id, status: form.status })
      }
      ElMessage.success('保存成功')
      dialogVisible.value = false
      await load()
    } finally {
      saving.value = false
    }
  })
}

function openResetPwd(row: SysUser) {
  Object.assign(pwdForm, { id: row.id, username: row.username, password: '' })
  pwdVisible.value = true
}

async function onResetPwd() {
  if (!pwdFormRef.value) return
  await pwdFormRef.value.validate(async (valid) => {
    if (!valid || !pwdForm.id) return
    saving.value = true
    try {
      await systemApi.updateUser(pwdForm.id, { password: pwdForm.password })
      ElMessage.success('密码已重置')
      pwdVisible.value = false
    } finally {
      saving.value = false
    }
  })
}

async function onDelete(row: SysUser) {
  await ElMessageBox.confirm(`确认删除用户「${row.username}」？`, '提示', { type: 'warning' })
  await systemApi.deleteUser(row.id)
  ElMessage.success('删除成功')
  await load()
}

onMounted(async () => {
  roles.value = await systemApi.roles()
  await load()
})
</script>
