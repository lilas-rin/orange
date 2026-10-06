<template>
  <div class="page">
    <h2 class="page-title">操作日志</h2>
    <p class="page-desc">系统操作审计日志，记录登录、数据变更、模型运行等关键操作</p>

    <div class="page-card">
      <div class="toolbar">
        <el-select v-model="query.module" placeholder="模块" clearable style="width: 160px">
          <el-option label="认证" value="auth" />
          <el-option label="系统管理" value="system" />
          <el-option label="数据导入" value="import" />
          <el-option label="智能预测" value="prediction" />
          <el-option label="决策建议" value="decision" />
        </el-select>
        <el-select v-model="query.result" placeholder="结果" clearable style="width: 130px">
          <el-option label="成功" value="success" />
          <el-option label="失败" value="failure" />
        </el-select>
        <el-button type="primary" :icon="Search" @click="load(1)">查询</el-button>
        <el-button :icon="Refresh" @click="reset">重置</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" border stripe>
        <el-table-column type="index" label="#" width="56" />
        <el-table-column prop="created_at" label="时间" width="180">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="username" label="操作人" width="120">
          <template #default="{ row }">{{ row.username || '-' }}</template>
        </el-table-column>
        <el-table-column prop="module" label="模块" width="120" />
        <el-table-column prop="operation" label="操作内容" min-width="240" show-overflow-tooltip />
        <el-table-column prop="request_method" label="方法" width="90" align="center" />
        <el-table-column prop="request_path" label="请求路径" min-width="220" show-overflow-tooltip />
        <el-table-column prop="ip" label="IP" width="130" />
        <el-table-column label="结果" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.result === 'failure' ? 'danger' : 'success'" effect="plain">
              {{ row.result === 'failure' ? '失败' : '成功' }}
            </el-tag>
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
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import dayjs from 'dayjs'
import { Refresh, Search } from '@element-plus/icons-vue'
import { systemApi } from '@/api'
import type { OperationLog } from '@/types'

const loading = ref(false)
const rows = ref<OperationLog[]>([])
const total = ref(0)
const query = reactive({ page: 1, page_size: 20, module: '', result: '' })

function formatTime(t: string) {
  return dayjs(t).format('YYYY-MM-DD HH:mm:ss')
}

async function load(page?: number) {
  if (page) query.page = page
  loading.value = true
  try {
    const res = await systemApi.logs({
      page: query.page,
      page_size: query.page_size,
      module: query.module || undefined,
      result: query.result || undefined,
    })
    rows.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function reset() {
  query.module = ''
  query.result = ''
  load(1)
}

onMounted(() => load())
</script>
