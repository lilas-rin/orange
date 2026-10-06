<template>
  <div class="page">
    <h2 class="page-title">价格数据</h2>
    <p class="page-desc">按产地与月份维护脐橙平均价、最高价、最低价与批发价（元/kg）</p>

    <div class="page-card">
      <div class="toolbar">
        <el-select v-model="query.production_area_id" placeholder="选择产地" clearable filterable style="width: 210px">
          <el-option v-for="a in areas" :key="a.id" :label="a.name" :value="a.id" />
        </el-select>
        <el-date-picker
          v-model="range"
          type="daterange"
          value-format="YYYY-MM-DD"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 260px"
        />
        <el-button type="primary" :icon="Search" @click="load(1)">查询</el-button>
        <el-button :icon="Refresh" @click="reset">重置</el-button>
        <span class="spacer"></span>
        <el-button type="primary" :icon="Plus" @click="openCreate">新增记录</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" border stripe>
        <el-table-column type="index" label="#" width="56" />
        <el-table-column prop="production_area_name" label="产地" min-width="180" />
        <el-table-column prop="date" label="日期" width="120" />
        <el-table-column label="平均价" width="110" align="right">
          <template #default="{ row }">{{ num(row.average_price, 2) }}</template>
        </el-table-column>
        <el-table-column label="最高价" width="110" align="right">
          <template #default="{ row }">{{ num(row.highest_price, 2) }}</template>
        </el-table-column>
        <el-table-column label="最低价" width="110" align="right">
          <template #default="{ row }">{{ num(row.lowest_price, 2) }}</template>
        </el-table-column>
        <el-table-column label="批发价" width="110" align="right">
          <template #default="{ row }">{{ num(row.wholesale_price, 2) }}</template>
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

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑价格记录' : '新增价格记录'" width="540px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="130px">
        <el-form-item label="产地" prop="production_area_id">
          <el-select v-model="form.production_area_id" filterable style="width: 100%">
            <el-option v-for="a in areas" :key="a.id" :label="a.name" :value="a.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期" prop="date">
          <el-date-picker v-model="form.date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="平均价(元/kg)" prop="average_price">
          <el-input-number v-model="form.average_price as number" :min="0" :precision="2" :controls="false" style="width: 100%" />
        </el-form-item>
        <el-form-item label="最高价(元/kg)">
          <el-input-number v-model="form.highest_price as number" :min="0" :precision="2" :controls="false" style="width: 100%" />
        </el-form-item>
        <el-form-item label="最低价(元/kg)">
          <el-input-number v-model="form.lowest_price as number" :min="0" :precision="2" :controls="false" style="width: 100%" />
        </el-form-item>
        <el-form-item label="批发价(元/kg)">
          <el-input-number v-model="form.wholesale_price as number" :min="0" :precision="2" :controls="false" style="width: 100%" />
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
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Refresh, Search } from '@element-plus/icons-vue'
import { baseApi, tradeApi } from '@/api'
import type { PriceData, ProductionArea } from '@/types'
import { num } from '@/utils/format'

const loading = ref(false)
const saving = ref(false)
const rows = ref<PriceData[]>([])
const areas = ref<ProductionArea[]>([])
const total = ref(0)
const range = ref<[string, string] | null>(null)
const query = reactive({ page: 1, page_size: 20, production_area_id: null as number | null })

const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref<FormInstance>()
const form = reactive<Partial<PriceData>>({})

const rules: FormRules = {
  production_area_id: [{ required: true, message: '请选择产地', trigger: 'change' }],
  date: [{ required: true, message: '请选择日期', trigger: 'change' }],
  average_price: [{ required: true, message: '请输入平均价', trigger: 'blur' }],
}

async function load(page?: number) {
  if (page) query.page = page
  loading.value = true
  try {
    const res = await tradeApi.prices({
      page: query.page,
      page_size: query.page_size,
      production_area_id: query.production_area_id ?? undefined,
      start: range.value?.[0],
      end: range.value?.[1],
    })
    rows.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function reset() {
  query.production_area_id = null
  range.value = null
  load(1)
}

function openCreate() {
  isEdit.value = false
  Object.keys(form).forEach((k) => delete (form as any)[k])
  dialogVisible.value = true
}

function openEdit(row: PriceData) {
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
        await tradeApi.updatePrice(form.id, form)
      } else {
        await tradeApi.createPrice(form)
      }
      ElMessage.success('保存成功')
      dialogVisible.value = false
      await load()
    } finally {
      saving.value = false
    }
  })
}

async function onDelete(row: PriceData) {
  await ElMessageBox.confirm('确认删除该价格记录？', '提示', { type: 'warning' })
  await tradeApi.deletePrice(row.id)
  ElMessage.success('删除成功')
  await load()
}

onMounted(async () => {
  const res = await baseApi.areas({ page: 1, page_size: 200 })
  areas.value = res.items
  await load()
})
</script>
