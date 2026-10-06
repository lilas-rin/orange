<template>
  <div class="page">
    <h2 class="page-title">数据导入</h2>
    <p class="page-desc">支持 Excel / CSV 批量导入产量、销量、价格数据。导入前会先校验并预览，确认无误后再写入数据库</p>

    <el-row :gutter="14">
      <el-col :span="10">
        <div class="page-card">
          <div class="section-title">1. 选择导入类型</div>
          <el-radio-group v-model="target" class="target-group">
            <el-radio-button value="production">产量数据</el-radio-button>
            <el-radio-button value="sales">销量数据</el-radio-button>
            <el-radio-button value="price">价格数据</el-radio-button>
          </el-radio-group>

          <div class="section-title" style="margin-top: 22px">2. 上传文件</div>
          <el-upload
            drag
            :auto-upload="false"
            :show-file-list="false"
            accept=".xlsx,.xls,.csv"
            :on-change="onFileChange"
          >
            <el-icon class="up-icon"><UploadFilled /></el-icon>
            <div class="up-text">将 Excel / CSV 文件拖到此处，或<em>点击选择</em></div>
            <div class="up-hint">支持 .xlsx / .xls / .csv</div>
          </el-upload>

          <div v-if="fileName" class="file-chip">
            <el-icon><Document /></el-icon>
            <span>{{ fileName }}</span>
            <el-button link type="primary" :loading="previewing" @click="onPreview">重新预览</el-button>
          </div>

          <div class="section-title" style="margin-top: 22px">字段模板</div>
          <el-table :data="templateRows" size="small" border>
            <el-table-column prop="col" label="列名" min-width="150" />
            <el-table-column prop="req" label="必填" width="70" align="center">
              <template #default="{ row }">
                <el-tag :type="row.req === '是' ? 'danger' : 'info'" size="small" effect="plain">{{ row.req }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="desc" label="说明" min-width="150" />
          </el-table>
          <el-button link type="primary" style="margin-top: 8px" @click="downloadTemplate">
            下载 CSV 模板
          </el-button>
        </div>
      </el-col>

      <el-col :span="14">
        <div class="page-card">
          <div class="section-title">3. 数据预览与校验</div>
          <el-empty v-if="!preview" description="请先选择文件并预览" />
          <template v-else>
            <div class="preview-summary">
              <el-tag type="info">总行数：{{ preview.total }}</el-tag>
              <el-tag type="success">可导入：{{ preview.valid_count }}</el-tag>
              <el-tag :type="preview.error_count ? 'danger' : 'info'">错误行：{{ preview.error_count }}</el-tag>
              <span class="spacer"></span>
              <el-button
                type="primary"
                :disabled="preview.error_count > 0 || preview.valid_count === 0"
                :loading="committing"
                @click="onCommit"
              >
                确认导入 {{ preview.valid_count }} 条
              </el-button>
            </div>

            <el-alert
              v-if="preview.error_count > 0"
              type="error"
              :closable="false"
              show-icon
              title="存在错误数据，请修正后重新上传"
              style="margin-bottom: 10px"
            />

            <el-tabs v-if="preview.error_count > 0" v-model="tab">
              <el-tab-pane label="合法数据" name="valid">
                <el-table :data="preview.valid_rows" size="small" border max-height="420">
                  <el-table-column type="index" label="#" width="52" />
                  <el-table-column
                    v-for="c in previewCols"
                    :key="c"
                    :prop="c"
                    :label="c"
                    min-width="130"
                  />
                </el-table>
              </el-tab-pane>
              <el-tab-pane :label="`错误数据 (${preview.error_count})`" name="error">
                <el-table :data="preview.error_rows" size="small" border max-height="420">
                  <el-table-column prop="row" label="行号" width="70" />
                  <el-table-column label="错误原因" min-width="240">
                    <template #default="{ row }">
                      <el-tag type="danger" size="small" effect="plain">{{ row.errors.join('；') }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="原始数据" min-width="260">
                    <template #default="{ row }">{{ JSON.stringify(row.data) }}</template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>
            </el-tabs>
            <el-table v-else :data="preview.valid_rows" size="small" border max-height="460">
              <el-table-column type="index" label="#" width="52" />
              <el-table-column v-for="c in previewCols" :key="c" :prop="c" :label="c" min-width="130" />
            </el-table>
          </template>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage, type UploadFile } from 'element-plus'
import { Document, UploadFilled } from '@element-plus/icons-vue'
import { tradeApi, type ImportPreviewResult } from '@/api'

const target = ref<'production' | 'sales' | 'price'>('production')
const file = ref<File | null>(null)
const fileName = ref('')
const previewing = ref(false)
const committing = ref(false)
const preview = ref<ImportPreviewResult | null>(null)
const tab = ref('valid')

const TEMPLATES = {
  production: [
    { col: '产地', req: '是', desc: '产地名称，需与系统一致' },
    { col: '日期', req: '是', desc: 'YYYY-MM-DD' },
    { col: '产量(吨)', req: '是', desc: '正数' },
    { col: '品种', req: '否', desc: '品种名称' },
    { col: '种植面积(亩)', req: '否', desc: '数值' },
    { col: '单产(吨/亩)', req: '否', desc: '数值' },
  ],
  sales: [
    { col: '销售地区', req: '是', desc: '省份名称，需与系统一致' },
    { col: '日期', req: '是', desc: 'YYYY-MM-DD' },
    { col: '销量(吨)', req: '是', desc: '正数' },
    { col: '销售额(万元)', req: '是', desc: '正数' },
    { col: '渠道', req: '否', desc: '批发 / 电商 等' },
  ],
  price: [
    { col: '产地', req: '是', desc: '产地名称，需与系统一致' },
    { col: '日期', req: '是', desc: 'YYYY-MM-DD' },
    { col: '平均价(元/kg)', req: '是', desc: '正数' },
    { col: '最高价(元/kg)', req: '否', desc: '数值' },
    { col: '最低价(元/kg)', req: '否', desc: '数值' },
    { col: '批发价(元/kg)', req: '否', desc: '数值' },
  ],
}

const templateRows = computed(() => TEMPLATES[target.value])

const previewCols = computed(() => {
  if (!preview.value || !preview.value.valid_rows.length) return []
  return Object.keys(preview.value.valid_rows[0])
})

watch(target, () => {
  preview.value = null
  file.value = null
  fileName.value = ''
})

function onFileChange(uploadFile: UploadFile) {
  const raw = uploadFile.raw
  if (!raw) return
  file.value = raw
  fileName.value = raw.name
  onPreview()
}

async function onPreview() {
  if (!file.value) return
  previewing.value = true
  try {
    preview.value = await tradeApi.importPreview(target.value, file.value)
    tab.value = preview.value.error_count > 0 ? 'error' : 'valid'
  } finally {
    previewing.value = false
  }
}

async function onCommit() {
  if (!file.value) return
  committing.value = true
  try {
    const res = await tradeApi.importCommit(target.value, file.value)
    ElMessage.success(`成功导入 ${res.imported} 条数据`)
    preview.value = null
    file.value = null
    fileName.value = ''
  } finally {
    committing.value = false
  }
}

function downloadTemplate() {
  const cols = TEMPLATES[target.value].map((c) => c.col)
  const sample =
    target.value === 'production'
      ? ['安西镇脐橙基地', '2025-11-15', '1200', '纽荷尔', '6000', '0.2']
      : target.value === 'sales'
        ? ['广东省', '2025-11-15', '800', '560', '批发']
        : ['安西镇脐橙基地', '2025-11-15', '3.2', '3.8', '2.6', '3.3']
  const csv = '\ufeff' + cols.join(',') + '\n' + sample.join(',') + '\n'
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `导入模板_${target.value}.csv`
  a.click()
  URL.revokeObjectURL(a.href)
}
</script>

<style scoped>
.target-group {
  margin-bottom: 6px;
}
.up-icon {
  font-size: 44px;
  color: #b7c2cc;
  margin-top: 16px;
}
.up-text {
  color: #5b6673;
  font-size: 13px;
}
.up-text em {
  color: var(--brand);
  font-style: normal;
}
.up-hint {
  color: #a3adb8;
  font-size: 12px;
  margin-top: 4px;
}
.file-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  background: #f2f7f3;
  border: 1px solid #d8e8dc;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 13px;
}
.preview-summary {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.preview-summary .spacer {
  flex: 1;
}
</style>
