/** 全局业务类型定义（与后端 schema 对齐）。 */

export interface UserInfo {
  id: number
  username: string
  nickname: string | null
  role: string
  permissions: string[]
}

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface Region {
  id: number
  name: string
  type: string
  parent_id: number | null
  adcode: string | null
  longitude: number | null
  latitude: number | null
  children?: Region[]
}

export interface ProductionArea {
  id: number
  name: string
  region_id: number
  region_name?: string | null
  longitude: number | null
  latitude: number | null
  planting_area: number | null
  main_variety: string | null
  production_technology_score: number | null
  transport_score: number | null
  supply_score: number | null
  benefit_score: number | null
  description: string | null
}

export interface Product {
  id: number
  name: string
  variety: string | null
  grade: string | null
  specification: string | null
  listing_time: string | null
  production_area_id: number | null
  production_area_name?: string | null
  description: string | null
}

export interface ProductionData {
  id: number
  production_area_id: number
  production_area_name?: string | null
  product_id: number | null
  product_name?: string | null
  date: string
  planting_area: number | null
  production: number | null
  yield_per_area: number | null
}

export interface SalesData {
  id: number
  region_id: number
  region_name?: string | null
  product_id: number | null
  product_name?: string | null
  date: string
  sales_volume: number | null
  sales_amount: number | null
  sales_channel: string | null
}

export interface PriceData {
  id: number
  production_area_id: number
  production_area_name?: string | null
  product_id: number | null
  product_name?: string | null
  date: string
  average_price: number | null
  highest_price: number | null
  lowest_price: number | null
  wholesale_price: number | null
}

export interface MarketData {
  id: number
  region_id: number
  region_name?: string | null
  date: string
  sales_volume: number | null
  sales_amount: number | null
  market_share: number | null
  market_level: string | null
  growth_rate: number | null
}

export interface PestType {
  id: number
  name: string
  type: string
  description: string | null
  prevention_method: string | null
}

export interface PestRecord {
  id: number
  production_area_id: number
  production_area_name?: string | null
  pest_disease_type_id: number
  pest_disease_type_name?: string | null
  date: string
  affected_area: number | null
  severity: string | null
  production_impact: number | null
  prevention_cost: number | null
}

export interface ModelInfo {
  id: number
  model_name: string
  model_type: string
  version: string
  target: string | null
  algorithm: string | null
  training_dataset: string | null
  evaluation_metric: string | null
  accuracy: number | null
  status: string
  updated_at?: string | null
}

export interface PredictionResult {
  id: number
  prediction_type: string
  prediction_date: string
  target_date: string
  predicted_value: number | null
  risk_level: string | null
  region_name: string | null
  production_area_name: string | null
  model_name: string
}

export interface DecisionAdvice {
  id: number
  advice_type: string
  risk_level: string | null
  title: string
  content: string
  region_name: string | null
  created_at: string | null
}

export interface OperationLog {
  id: number
  user_id: number | null
  username?: string | null
  operation: string
  module: string | null
  request_method: string | null
  request_path: string | null
  ip: string | null
  result: string | null
  created_at: string
}

export interface Role {
  id: number
  name: string
  code: string
  description: string | null
  permissions?: { id: number; name: string; code: string }[]
}

export interface SysUser {
  id: number
  username: string
  nickname: string | null
  role_id: number
  role_name?: string | null
  status: boolean
  created_at: string
}

// ---------- 大屏 ----------
export interface ScreenKpi {
  year: number
  total_production: number
  total_sales_volume: number
  total_sales_amount: number
  avg_wholesale_price: number
  production_sales_rate: number
  yoy_growth_rate: number | null
  province_count: number
  total_sales_volume_yoy: number | null
  total_sales_amount_yoy: number | null
  avg_wholesale_price_yoy: number | null
  production_sales_rate_yoy: number | null
  stock: number
  stock_yoy: number | null
  supply_demand_status: string
}

/** 外部真实参考数据说明（来源与统计时点）。 */
export interface ScreenReference {
  collected_at: string
  national_market_price: {
    value: number
    period: string
    source: string
    note: string
  }
  province_price_source: string
}

export interface GanzhouReference {
  collected_at: string
  city_pest_control: {
    name: string
    control_area: number
    period: string
    source: string
    note: string
  }
  price_source: string
  pest_source: string
  planting_reference: {
    period: string
    source: string
    city: { planting_area: number; production: number }
    note: string
  }
}

export interface ScreenOverview {
  kpi: ScreenKpi
  top10: MarketProvince[]
  price_trend: { history: MonthValue[]; forecast: ForecastValue[] }
  pest_top: { name: string; kind: string; count: number; affected_area: number; production_impact: number }[]
  predictions: PredictionResult[]
  decisions: DecisionAdvice[]
  reference: ScreenReference
}

export interface MarketProvince {
  name: string
  sales_volume: number
  sales_amount: number
  market_share?: number
  market_level: string | null
  growth_rate: number | null
  market_price?: number | null
  market_price_period?: string | null
  market_price_market?: string | null
}

export interface MonthValue {
  month: string
  value: number
}

export interface ForecastValue {
  month: string
  value: number
  lower: number
  upper: number
}

export interface ChinaMapData {
  year: number
  provinces: {
    name: string
    adcode: string
    sales_volume: number
    sales_amount: number
    market_level: string | null
    growth_rate: number
    longitude: number | null
    latitude: number | null
  }[]
  flows: { from_name: string; to_name: string; value: number }[]
}

export interface CountyItem {
  region_id: number
  name: string
  adcode: string
  production: number
  sales_volume: number
  sales_amount: number
  avg_price: number
  production_sales_rate: number
  risk_level: string
  planting_area: number
  area_count: number
  score: number | null
  radar: {
    price: number
    technology: number
    transport: number
    supply: number
    benefit: number
  } | null
  pest_count: number
  pest_affected_area: number
  pest_impact: number
  real_price_per_kg: number | null
  real_price_period: string | null
  pest_control: {
    control_area: number | null
    period: string
    source: string
    note: string
  } | null
}

export interface GanzhouData {
  year: number
  counties: CountyItem[]
  reference: GanzhouReference
}

export interface CountyDetail {
  region_id: number
  name: string
  adcode: string
  production_trend: MonthValue[]
  price_trend: MonthValue[]
  recent_pests: { date: string; severity: string; affected_area: number }[]
  current_risk: string
  risk_predictions: { target_date: string; risk_level: string; predicted_value: number | null }[]
  areas: {
    id: number
    name: string
    longitude: number | null
    latitude: number | null
    planting_area: number
    main_variety: string | null
    score: number | null
  }[]
}

export interface AreaDetail {
  id: number
  name: string
  region_id: number
  region_name: string | null
  longitude: number | null
  latitude: number | null
  planting_area: number
  main_variety: string | null
  description: string | null
  scores: { technology: number; transport: number; supply: number; benefit: number }
  evaluation: {
    price: number
    technology: number
    transport: number
    supply: number
    benefit: number
    total: number
  } | null
  production_trend: MonthValue[]
  price_trend: MonthValue[]
  price_predictions: { target_date: string; value: number; lower: number; upper: number }[]
}

// ---------- 智能预测与产销排产 ----------

/** 价格展望：7 天 / 30 天 / 异常概率 / 置信区间。 */
export interface PriceOutlook {
  current: number
  current_month: string
  d7: number
  d30: number
  target_month: string
  chg7: number | null
  chg30: number | null
  ci_low: number
  ci_high: number
  confidence: number
  anomaly_risk: string
  anomaly_label: string
  max_swing: number
  gap_to_national: number
  national_price: number
  national_period: string
}

export interface MarketDemandItem {
  name: string
  adcode: string | null
  /** 当前产季累计销量（吨） */
  current: number
  /** 新产季首月预测销量（吨） */
  forecast: number
  lower: number
  upper: number
  /** 上一产季同月实际（吨） */
  prev_actual: number
  growth: number | null
  level: string
  action: string
}

export interface DemandForecast {
  season: number
  target_season: number
  target_month: string
  total_forecast: number
  total_prev_actual: number
  markets: MarketDemandItem[]
  all: MarketDemandItem[]
}

export interface ProductionForecast {
  year: number
  value: number
  lower: number
  upper: number
  yoy: number | null
  history: { year: number; value: number }[]
}

export interface StockOutlook {
  opening_stock: number
  stock_yoy: number | null
  first_month_share: number
  first_month_production: number
  supply: number
  demand: number
  coverage: number | null
  gap: number
  risk: string
  label: string
  advice: string
  daily_demand: number
  safety_stock: number
  days_left: number | null
}

export interface PestOutlookItem {
  region_id: number
  name: string
  current: string
  forecast: string
  prob: number | null
  target_date: string | null
  trend: 'up' | 'down' | 'flat'
  recent_count: number
  recent_window: string
}

export interface PestOutlook {
  window: string
  target_month: string | null
  high_count: number
  items: PestOutlookItem[]
  all: PestOutlookItem[]
}

export interface PlanRegion {
  region_id: number
  name: string
  plan: number
  base_plan: number
  delta: number
  risk: string
}

export interface PlanMarket {
  name: string
  delta: number
  delta_wan: number
  growth: number | null
  forecast: number
  action: string
  level: string
}

export interface ProductionPlan {
  plan_7d: number
  baseline_7d: number
  change: number | null
  coverage: number | null
  supply_state: string
  regions: PlanRegion[]
  markets: PlanMarket[]
  basis: string[]
}

export interface ScreenIntelligence {
  season: number
  target_season: number
  price: PriceOutlook | null
  demand: DemandForecast
  production: ProductionForecast | null
  stock: StockOutlook
  pest: PestOutlook
  plan: ProductionPlan
}

export interface MapLayerItem {
  name: string
  value: number
  label?: string
  level?: string
  delta?: number
}

/** 地图图层（flow/demand/price/supply/risk/plan）。 */
export interface MapLayer {
  layer: string
  title: string
  unit: string
  scope: 'china' | 'ganzhou'
  min: number
  max: number
  items: MapLayerItem[]
}

export type MapLayers = Record<string, MapLayer>
