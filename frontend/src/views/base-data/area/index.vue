<template>
  <div class="page">
    <h2 class="page-title">产地管理</h2>
    <p class="page-desc">维护镇级脐橙产地信息与四维能力评分（生产技术、交通运输、供应能力、效益水平）</p>

    <div class="page-card">
      <div class="toolbar">
        <el-input v-model="query.name" placeholder="产地名称" clearable style="width: 180px" @keyup.enter="load(1)" />
        <el-select v-model="query.region_id" placeholder="所属县区" clearable filterable style="width: 170px">
          <el-option v-for="c in counties" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <el-button type="primary" :icon="Search" @click="load(1)">查询</el-button>
        <el-button :icon="Refresh" @click="reset">重置</el-button>
        <span class="spacer"></span>
        <el-button type="primary" :icon="Plus" @click="openCreate">新增产地</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" border stripe>
        <el-table-column type="index" label="#" width="56" />
        <el-table-column prop="name" label="产地名称" min-width="190" />
        <el-table-column prop="region_name" label="所属县区" width="110" />
        <el-table-column prop="main_variety" label="主栽品种" width="110" />
        <el-table-column label="种植面积(亩)" width="130" align="right">
          <template #default="{ row }">{{ num(row.planting_area) }}</template>
        </el-table-column>
        <el-table-column label="生产技术" width="100" align="center">
          <template #default="{ row }">{{ row.production_technology_score ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="交通运输" width="100" align="center">
          <template #default="{ row }">{{ row.transport_score ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="供应能力" width="100" align="center">
          <template #default="{ row }">{{ row.supply_score ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="效益水平" width="100" align="center">
          <template #default="{ row }">{{ row.benefit_score ?? '-' }}</template>
        </el-table-column>
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
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @current-change="load()"
          @size-change="load(1)"
        />
      </div>
    </div>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑产地' : '新增产地'" width="620px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-row :gutter="14">
          <el-col :span="12">
            <el-form-item label="产地名称" prop="name">
              <el-input v-model="form.name" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="所属县区" prop="region_id">
              <el-select v-model="form.region_id" filterable style="width: 100%">
                <el-option v-for="c in counties" :key="c.id" :label="c.name" :value="c.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="主栽品种">
              <el-input v-model="form.main_variety" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="种植面积(亩)">
              <el-input-number v-model="form.planting_area as number" :min="0" :controls="false" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="经度">
              <el-input-number v-model="form.longitude as number" :precision="4" :controls="false" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="纬度">
              <el-input-number v-model="form.latitude as number" :precision="4" :controls="false" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="生产技术分">
              <el-input-number v-model="form.production_technology_score as number" :min="0" :max="100" :controls="false" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="交通运输分">
              <el-input-number v-model="form.transport_score as number" :min="0" :max="100" :controls="false" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="供应能力分">
              <el-input-number v-model="form.supply_score as number" :min="0" :max="100" :controls="false" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="效益水平分">
              <el-input-number v-model="form.benefit_score as number" :min="0" :max="100" :controls="false" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="产地简介">
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
import { Plus, Refresh, Search } from '@element-plus/icons-vue'
import { baseApi } from '@/api'
import type { ProductionArea, Region } from '@/types'
import { num } from '@/utils/format'

const loading = ref(false)
const saving = ref(false)
const rows = ref<ProductionArea[]>([])
const counties = ref<Region[]>([])
const total = ref(0)
const query = reactive<{ page: number; page_size: number; name: string; region_id: number | null }>({
  page: 1,
  page_size: 20,
  name: '',
  region_id: null,
})

const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref<FormInstance>()
const form = reactive<Partial<ProductionArea>>({})

const rules: FormRules = {
  name: [{ required: true, message: '请输入产地名称', trigger: 'blur' }],
  region_id: [{ required: true, message: '请选择所属县区', trigger: 'change' }],
}

async function load(page?: number) {
  if (page) query.page = page
  loading.value = true
  try {
    const res = await baseApi.areas({
      page: query.page,
      page_size: query.page_size,
      name: query.name || undefined,
      region_id: query.region_id ?? undefined,
    })
    rows.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function reset() {
  query.name = ''
  query.region_id = null
  load(1)
}

function openCreate() {
  isEdit.value = false
  Object.keys(form).forEach((k) => delete (form as any)[k])
  dialogVisible.value = true
}

function openEdit(row: ProductionArea) {
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
        await baseApi.updateArea(form.id, form)
      } else {
        await baseApi.createArea(form)
      }
      ElMessage.success('保存成功')
      dialogVisible.value = false
      await load()
    } finally {
      saving.value = false
    }
  })
}

async function onDelete(row: ProductionArea) {
  await ElMessageBox.confirm(`确认删除产地「${row.name}」？相关产销数据不会自动删除。`, '提示', {
    type: 'warning',
  })
  await baseApi.deleteArea(row.id)
  ElMessage.success('删除成功')
  await load()
}

onMounted(async () => {
  counties.value = await baseApi.regions({ type: 'county' })
  await load()
})
</script>
