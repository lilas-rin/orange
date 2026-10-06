<template>
  <div class="page">
    <h2 class="page-title">区域管理</h2>
    <p class="page-desc">维护「全国 → 省/直辖市 → 地级市 → 县/区」行政区划树，销售流向与地图钻取均以此为基础</p>

    <div class="page-card">
      <div class="toolbar">
        <el-input v-model="keyword" placeholder="按名称筛选" clearable style="width: 220px" />
        <span class="spacer"></span>
        <el-button type="primary" :icon="Plus" @click="openCreate()">新增区域</el-button>
      </div>

      <el-table
        v-loading="loading"
        :data="filteredTree"
        row-key="id"
        border
        default-expand-all
        :tree-props="{ children: 'children' }"
      >
        <el-table-column prop="name" label="区域名称" min-width="220" />
        <el-table-column label="层级" width="120">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ regionTypeLabel[row.type] || row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="adcode" label="行政区划代码" width="140" />
        <el-table-column label="经度" width="110">
          <template #default="{ row }">{{ row.longitude ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="纬度" width="110">
          <template #default="{ row }">{{ row.latitude ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openCreate(row)">新增下级</el-button>
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="96px">
        <el-form-item label="区域名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="层级" prop="type">
          <el-select v-model="form.type" style="width: 100%">
            <el-option label="国家" value="country" />
            <el-option label="省/直辖市" value="province" />
            <el-option label="地级市" value="city" />
            <el-option label="县/区" value="county" />
          </el-select>
        </el-form-item>
        <el-form-item label="上级区域">
          <el-input :model-value="parentName" disabled />
        </el-form-item>
        <el-form-item label="区划代码">
          <el-input v-model="form.adcode" placeholder="如 360722" />
        </el-form-item>
        <el-form-item label="经度">
          <el-input-number v-model="form.longitude as number" :precision="4" :controls="false" style="width: 100%" />
        </el-form-item>
        <el-form-item label="纬度">
          <el-input-number v-model="form.latitude as number" :precision="4" :controls="false" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { baseApi } from '@/api'
import type { Region } from '@/types'
import { regionTypeLabel } from '@/utils/format'

const loading = ref(false)
const saving = ref(false)
const tree = ref<Region[]>([])
const keyword = ref('')

const dialogVisible = ref(false)
const isEdit = ref(false)
const parentName = ref('无（顶级）')
const formRef = ref<FormInstance>()
const form = reactive<Partial<Region>>({
  id: undefined,
  name: '',
  type: 'county',
  parent_id: null,
  adcode: '',
  longitude: undefined,
  latitude: undefined,
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入区域名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择层级', trigger: 'change' }],
}

const dialogTitle = computed(() => (isEdit.value ? '编辑区域' : '新增区域'))

const filteredTree = computed(() => {
  if (!keyword.value.trim()) return tree.value
  const kw = keyword.value.trim()
  const walk = (nodes: Region[]): Region[] =>
    nodes
      .map((n) => {
        const children = n.children ? walk(n.children) : []
        if (n.name.includes(kw) || children.length) return { ...n, children }
        return null
      })
      .filter(Boolean) as Region[]
  return walk(tree.value)
})

async function load() {
  loading.value = true
  try {
    tree.value = await baseApi.regionTree()
  } finally {
    loading.value = false
  }
}

function findName(nodes: Region[], id: number): string | null {
  for (const n of nodes) {
    if (n.id === id) return n.name
    if (n.children) {
      const r = findName(n.children, id)
      if (r) return r
    }
  }
  return null
}

function openCreate(parent?: Region) {
  isEdit.value = false
  Object.assign(form, {
    id: undefined,
    name: '',
    type: parent ? (parent.type === 'country' ? 'province' : parent.type === 'province' ? 'city' : 'county') : 'province',
    parent_id: parent?.id ?? null,
    adcode: '',
    longitude: undefined,
    latitude: undefined,
  })
  parentName.value = parent ? parent.name : '无（顶级）'
  dialogVisible.value = true
}

function openEdit(row: Region) {
  isEdit.value = true
  Object.assign(form, {
    id: row.id,
    name: row.name,
    type: row.type,
    parent_id: row.parent_id,
    adcode: row.adcode,
    longitude: row.longitude,
    latitude: row.latitude,
  })
  parentName.value = row.parent_id ? findName(tree.value, row.parent_id) || '-' : '无（顶级）'
  dialogVisible.value = true
}

async function onSave() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      const payload = { ...form }
      if (isEdit.value && form.id) {
        await baseApi.updateRegion(form.id, payload)
      } else {
        delete payload.id
        await baseApi.createRegion(payload)
      }
      ElMessage.success('保存成功')
      dialogVisible.value = false
      await load()
    } finally {
      saving.value = false
    }
  })
}

async function onDelete(row: Region) {
  await ElMessageBox.confirm(`确认删除区域「${row.name}」？`, '提示', { type: 'warning' })
  await baseApi.deleteRegion(row.id)
  ElMessage.success('删除成功')
  await load()
}

onMounted(load)
</script>
