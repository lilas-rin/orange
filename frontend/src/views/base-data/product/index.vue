<template>
  <div class="page">
    <h2 class="page-title">品种管理</h2>
    <p class="page-desc">维护脐橙品种（产品）档案，包括品种、等级、规格、上市时间与关联产地</p>

    <div class="page-card">
      <div class="toolbar">
        <el-input v-model="query.name" placeholder="品种名称" clearable style="width: 200px" @keyup.enter="load(1)" />
        <el-button type="primary" :icon="Search" @click="load(1)">查询</el-button>
        <span class="spacer"></span>
        <el-button type="primary" :icon="Plus" @click="openCreate">新增品种</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" border stripe>
        <el-table-column type="index" label="#" width="56" />
        <el-table-column prop="name" label="品种名称" min-width="190" />
        <el-table-column prop="variety" label="品种" width="110" />
        <el-table-column prop="grade" label="等级" width="90" />
        <el-table-column prop="specification" label="规格" width="130" />
        <el-table-column prop="listing_time" label="上市时间" width="120" />
        <el-table-column prop="production_area_name" label="关联产地" min-width="160">
          <template #default="{ row }">{{ row.production_area_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="description" label="简介" min-width="220" show-overflow-tooltip />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="query.page"
          v-model:page-size="query.page_size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @current-change="load()"
          @size-change="load(1)"
        />
      </div>
    </div>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑品种' : '新增品种'" width="560px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="品种名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-row :gutter="14">
          <el-col :span="12">
            <el-form-item label="品种">
              <el-input v-model="form.variety" placeholder="如 纽荷尔" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="等级">
              <el-select v-model="form.grade" style="width: 100%">
                <el-option label="特级" value="特级" />
                <el-option label="一级" value="一级" />
                <el-option label="二级" value="二级" />
                <el-option label="统货" value="统货" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="规格">
              <el-input v-model="form.specification" placeholder="如 果径80-85mm" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="上市时间">
              <el-input v-model="form.listing_time" placeholder="如 11月中下旬" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="关联产地">
              <el-select v-model="form.production_area_id" filterable clearable style="width: 100%">
                <el-option v-for="a in areas" :key="a.id" :label="a.name" :value="a.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="简介">
              <el-input v-model="form.description" type="textarea" :rows="2" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import { baseApi } from '@/api'
import type { Product, ProductionArea } from '@/types'

const loading = ref(false)
const saving = ref(false)
const rows = ref<Product[]>([])
const areas = ref<ProductionArea[]>([])
const total = ref(0)
const query = reactive({ page: 1, page_size: 20, name: '' })

const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref<FormInstance>()
const form = reactive<Partial<Product>>({})

const rules: FormRules = {
  name: [{ required: true, message: '请输入品种名称', trigger: 'blur' }],
}

async function load(page?: number) {
  if (page) query.page = page
  loading.value = true
  try {
    const res = await baseApi.products({
      page: query.page,
      page_size: query.page_size,
      name: query.name || undefined,
    })
    rows.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function openCreate() {
  isEdit.value = false
  Object.keys(form).forEach((k) => delete (form as any)[k])
  dialogVisible.value = true
}

function openEdit(row: Product) {
  isEdit.value = true
  Object.assign(form, row)
  dialogVisible.value = true
}

async function onSave() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      if (isEdit.value && form.id) {
        await baseApi.updateProduct(form.id, form)
      } else {
        await baseApi.createProduct(form)
      }
      ElMessage.success('保存成功')
      dialogVisible.value = false
      await load()
    } finally {
      saving.value = false
    }
  })
}

async function onDelete(row: Product) {
  await ElMessageBox.confirm(`确认删除品种「${row.name}」？`, '提示', { type: 'warning' })
  await baseApi.deleteProduct(row.id)
  ElMessage.success('删除成功')
  await load()
}

onMounted(async () => {
  const res = await baseApi.areas({ page: 1, page_size: 100 })
  areas.value = res.items
  await load()
})
</script>
