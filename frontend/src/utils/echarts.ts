import type * as echartsNS from 'echarts'

/** 运行时 echarts 实例（来自 CDN 全局对象）。 */
export const echarts = (
  typeof window !== 'undefined' ? (window as unknown as { echarts: typeof echartsNS }).echarts : undefined
) as typeof echartsNS

export type EChartsOption = echartsNS.EChartsOption
