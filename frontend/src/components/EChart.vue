<template>
  <div ref="el" class="echart" :style="{ height }"></div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch, nextTick } from 'vue'
import { echarts } from '@/utils/echarts'
import type { EChartsOption } from '@/utils/echarts'

const props = defineProps<{
  option: EChartsOption
  height?: string
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'click', params: unknown): void
  (e: 'mouseover', params: unknown): void
  (e: 'mouseout', params: unknown): void
  (e: 'globalout', params: unknown): void
}>()

const el = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null
let ro: ResizeObserver | null = null

function render() {
  if (!el.value) return
  if (!chart) {
    chart = echarts.init(el.value)
    chart.on('click', (params) => emit('click', params))
    chart.on('mouseover', (params) => emit('mouseover', params))
    chart.on('mouseout', (params) => emit('mouseout', params))
    chart.on('globalout', (params) => emit('globalout', params))
  }
  chart.setOption(props.option, true)
}

onMounted(() => {
  render()
  if (el.value && typeof ResizeObserver !== 'undefined') {
    ro = new ResizeObserver(() => chart?.resize())
    ro.observe(el.value)
  }
  window.addEventListener('resize', onResize)
})

function onResize() {
  chart?.resize()
}

watch(
  () => props.option,
  () => nextTick(render),
  { deep: true },
)

watch(
  () => props.loading,
  (v) => {
    if (!chart) return
    if (v) {
      chart.showLoading('default', { text: '加载中', color: '#1f7a3f', textColor: '#6b7684' })
    } else {
      chart.hideLoading()
    }
  },
)

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  ro?.disconnect()
  chart?.dispose()
  chart = null
})

defineExpose({ getChart: () => chart })
</script>

<style scoped>
/* min-width:0 + overflow:hidden：
 * ECharts 会给内部 DOM 写入上一次尺寸的内联 px 宽高，若不在这里兜住，
 * 该宽度会向上传递成父级 flex/grid 项的 min-content，把布局钉死在历史最大尺寸上。 */
.echart {
  width: 100%;
  min-width: 0;
  overflow: hidden;
}
</style>
