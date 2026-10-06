<template>
  <div class="page">
    <h2 class="page-title">智能预测与决策</h2>
    <p class="page-desc">机器学习模型训练与预测：价格预测（回归）与病虫害风险预测（三分类），并据此生成决策建议</p>

    <el-row :gutter="14">
      <el-col :span="24">
        <div class="page-card">
          <div class="section-title">模型列表</div>
          <el-table :data="models" border stripe v-loading="loading">
            <el-table-column prop="model_name" label="模型名称" min-width="170" />
            <el-table-column prop="model_type" label="类型" width="120">
              <template #default="{ row }">
                <el-tag size="small" effect="plain">{{ row.model_type === 'price' ? '价格预测' : '病虫害风险预测' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="version" label="版本" width="90" align="center" />
            <el-table-column prop="algorithm" label="算法" width="200" />
            <el-table-column prop="evaluation_metric" label="评估指标" width="190" />
            <el-table-column label="指标值" width="120" align="right">
              <template #default="{ row }">{{ row.accuracy ?? '-' }}</template>
            </el-table-column>
            <el-table-column prop="training_dataset" label="训练数据" min-width="160" show-overflow-tooltip />
            <el-table-column label="状态" width="90" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="row.status === 'active' ? 'success' : 'info'" effect="plain">
                  {{ row.status === 'active' ? '可用' : '已停用' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>

          <div class="toolbar" style="margin-top: 16px">
            <el-button type="primary" :loading="training" @click="train('price')">训练价格模型</el-button>
            <el-button type="primary" :loading="training" @click="train('pest_disease')">训练病虫害模型</el-button>
            <el-button :loading="running" @click="run('price')">执行价格预测（未来6月）</el-button>
            <el-button :loading="running" @click="run('pest_disease')">执行病虫害预测（未来3月）</el-button>
            <span class="spacer"></span>
            <el-button type="warning" :loading="refreshing" @click="refreshDecision">重新生成决策建议</el-button>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="14" style="margin-top: 14px">
      <el-col :span="14">
        <div class="page-card">
          <div class="section-title">价格历史与预测</div>
          <EChart :option="priceOption" height="360px" :loading="loading" />
        </div>
      </el-col>
      <el-col :span="10">
        <div class="page-card">
          <div class="section-title">预测结果明细</div>
          <el-tabs v-model="predTab">
            <el-tab-pane label="价格预测" name="price" />
            <el-tab-pane label="病虫害风险" name="pest_disease" />
          </el-tabs>
          <el-table :data="filteredPredictions" border stripe max-height="290" size="small">
            <el-table-column prop="target_date" label="预测目标" width="115" />
            <el-table-column label="对象" min-width="130">
              <template #default="{ row }">{{ row.region_name || row.production_area_name || '全区' }}</template>
            </el-table-column>
            <el-table-column label="预测值" width="100" align="right">
              <template #default="{ row }">
                {{ row.predicted_value === null ? '-' : num(row.predicted_value, 2) }}
              </template>
            </el-table-column>
            <el-table-column label="风险等级" width="100" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.risk_level" size="small" :type="riskTag(row.risk_level)" effect="plain">
                  {{ riskLevelLabel[row.risk_level] || row.risk_level }}
                </el-tag>
                <span v-else>-</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="14" style="margin-top: 14px">
      <el-col :span="24">
        <div class="page-card">
          <div class="section-title">智能决策建议</div>
          <el-empty v-if="!decisions.length" description="暂无决策建议" />
          <div v-else class="decision-list">
            <div v-for="d in decisions" :key="d.id" class="decision-item" :class="`lv-${d.risk_level}`">
              <div class="decision-head">
                <el-tag size="small" :type="riskTag(d.risk_level)" effect="dark">
                  {{ riskLevelLabel[d.risk_level || ''] || d.risk_level }}
                </el-tag>
                <el-tag size="small" effect="plain">{{ adviceTypeLabel[d.advice_type] || d.advice_type }}</el-tag>
                <span class="decision-title">{{ d.title }}</span>
                <span class="decision-time">{{ d.created_at }}</span>
              </div>
              <div class="decision-content">{{ d.content }}</div>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { EChartsOption } from 'echarts'
import { ElMessage } from 'element-plus'
import EChart from '@/components/EChart.vue'
import { predictionApi, screenApi } from '@/api'
import type { DecisionAdvice, ModelInfo, PredictionResult } from '@/types'
import { adviceTypeLabel, num, riskLevelLabel } from '@/utils/format'

const loading = ref(false)
const training = ref(false)
const running = ref(false)
const refreshing = ref(false)
const models = ref<ModelInfo[]>([])
const predictions = ref<PredictionResult[]>([])
const decisions = ref<DecisionAdvice[]>([])
const history = ref<{ month: string; value: number }[]>([])
const forecast = ref<{ month: string; value: number; lower: number; upper: number }[]>([])
const predTab = ref('price')

const filteredPredictions = computed(() =>
  predictions.value.filter((p) => p.prediction_type === predTab.value).slice(0, 40),
)

function riskTag(level: string | null) {
  if (level === 'high') return 'danger'
  if (level === 'medium') return 'warning'
  if (level === 'opportunity') return 'success'
  return 'info'
}

const priceOption = computed<EChartsOption>(() => {
  const hm = history.value.map((h) => h.month)
  const fm = forecast.value.map((f) => f.month)
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['历史批发价', '预测均价', '预测下限', '预测上限'], top: 0, textStyle: { fontSize: 11 } },
    grid: { left: 50, right: 24, top: 44, bottom: 60 },
    xAxis: { type: 'category', data: [...hm, ...fm], axisLabel: { rotate: 42, fontSize: 10 } },
    yAxis: { type: 'value', name: '元/kg' },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 16, bottom: 8 }],
    series: [
      { name: '历史批发价', type: 'line', smooth: true, showSymbol: false, itemStyle: { color: '#2c8b4c' }, data: [...history.value.map((h) => h.value), ...fm.map(() => null)] },
      { name: '预测均价', type: 'line', smooth: true, symbolSize: 6, lineStyle: { type: 'dashed', color: '#ff8c32' }, itemStyle: { color: '#ff8c32' }, data: [...hm.map(() => null), ...forecast.value.map((f) => f.value)] },
      { name: '预测下限', type: 'line', smooth: true, showSymbol: false, lineStyle: { type: 'dotted', color: '#c9a227' }, itemStyle: { color: '#c9a227' }, data: [...hm.map(() => null), ...forecast.value.map((f) => f.lower)] },
      { name: '预测上限', type: 'line', smooth: true, showSymbol: false, lineStyle: { type: 'dotted', color: '#c9a227' }, itemStyle: { color: '#c9a227' }, data: [...hm.map(() => null), ...forecast.value.map((f) => f.upper)] },
    ],
  }
})

async function load() {
  loading.value = true
  try {
    const [m, p, d, pt] = await Promise.all([
      predictionApi.models(),
      predictionApi.predictions({ limit: 200 }),
      predictionApi.decisions(30),
      screenApi.priceTrend(36),
    ])
    models.value = m
    predictions.value = p
    decisions.value = d
    history.value = pt.history
    forecast.value = pt.forecast
  } finally {
    loading.value = false
  }
}

async function train(type: string) {
  training.value = true
  try {
    const res = await predictionApi.train(type)
    ElMessage.success(`${res.model} 训练完成，${res.metric} = ${res.score}`)
    await load()
  } finally {
    training.value = false
  }
}

async function run(type: string) {
  running.value = true
  try {
    const months = type === 'price' ? 6 : 3
    const res = await predictionApi.run(type, months)
    ElMessage.success(`已生成 ${res.created} 条预测结果`)
    await load()
  } finally {
    running.value = false
  }
}

async function refreshDecision() {
  refreshing.value = true
  try {
    const res = await predictionApi.refreshDecisions()
    ElMessage.success(`已生成 ${res.created} 条决策建议`)
    await load()
  } finally {
    refreshing.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.decision-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.decision-item {
  border: 1px solid var(--border);
  border-left: 4px solid #c9d2dc;
  border-radius: 8px;
  padding: 12px 16px;
  background: #fafbfc;
}
.decision-item.lv-high {
  border-left-color: #d93025;
  background: #fdf4f3;
}
.decision-item.lv-medium {
  border-left-color: #e6a23c;
  background: #fdf9f0;
}
.decision-item.lv-low {
  border-left-color: #2c8b4c;
  background: #f3faf5;
}
.decision-item.lv-opportunity {
  border-left-color: #2c8b4c;
  background: #f3faf5;
}
.decision-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.decision-title {
  font-weight: 600;
  font-size: 14px;
}
.decision-time {
  margin-left: auto;
  color: #9aa5b1;
  font-size: 12px;
}
.decision-content {
  font-size: 13px;
  color: #4a5560;
  line-height: 1.8;
}
</style>
