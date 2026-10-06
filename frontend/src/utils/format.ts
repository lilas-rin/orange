/** 数字格式化工具。 */

export function num(v: number | null | undefined, digits = 0): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '-'
  return v.toLocaleString('zh-CN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

/** 吨 → 万吨（保留 2 位）。 */
export function wanTon(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '-'
  return num(v / 10000, 2)
}

/** 万元 → 亿元。 */
export function yiYuan(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '-'
  return num(v / 10000, 2)
}

export function pct(v: number | null | undefined, digits = 1): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '-'
  return `${num(v, digits)}%`
}

export const marketLevelLabel: Record<string, string> = {
  core: '核心市场',
  main: '重点市场',
  potential: '潜力市场',
}

export const riskLevelLabel: Record<string, string> = {
  low: '低风险',
  medium: '中风险',
  high: '高风险',
  opportunity: '机会',
}

export const severityLabel: Record<string, string> = {
  mild: '轻度',
  moderate: '中度',
  severe: '重度',
}

export const adviceTypeLabel: Record<string, string> = {
  price: '价格决策',
  pest_disease: '病虫害防控',
  market: '市场策略',
  supply: '供应保障',
  comprehensive: '综合研判',
}

export const predictionTypeLabel: Record<string, string> = {
  price: '价格预测',
  production: '产量预测',
  sales: '销量预测',
  market_demand: '市场需求预测',
  pest_disease: '病虫害风险预测',
}

export const regionTypeLabel: Record<string, string> = {
  country: '国家',
  province: '省/直辖市',
  city: '地级市',
  county: '县/区',
}
