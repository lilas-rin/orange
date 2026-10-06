import { del, get, post, put, upload, type PageResult } from './client'
import type {
  AreaDetail,
  ChinaMapData,
  CountyDetail,
  DecisionAdvice,
  GanzhouData,
  MarketData,
  MapLayers,
  ModelInfo,
  OperationLog,
  PestRecord,
  PestType,
  PredictionResult,
  PriceData,
  ProductionArea,
  ProductionData,
  Product,
  Region,
  Role,
  SalesData,
  ScreenIntelligence,
  ScreenOverview,
  SysUser,
  TokenPair,
  UserInfo,
} from '@/types'

// ---------------- 认证 ----------------
export const authApi = {
  login: (username: string, password: string) =>
    post<TokenPair>('/auth/login', { username, password }),
  refresh: (refresh_token: string) =>
    post<TokenPair>('/auth/refresh', { refresh_token }),
  logout: (refresh_token: string) => post<void>('/auth/logout', { refresh_token }),
  me: () => get<UserInfo>('/auth/me'),
}

// ---------------- 基础数据 ----------------
export const baseApi = {
  regions: (params?: { type?: string; parent_id?: number }) =>
    get<Region[]>('/base-data/regions', params),
  regionTree: () => get<Region[]>('/base-data/regions/tree'),
  createRegion: (data: Partial<Region>) => post<Region>('/base-data/regions', data),
  updateRegion: (id: number, data: Partial<Region>) =>
    put<Region>(`/base-data/regions/${id}`, data),
  deleteRegion: (id: number) => del<void>(`/base-data/regions/${id}`),

  areas: (params?: Record<string, unknown>) =>
    get<PageResult<ProductionArea>>('/base-data/areas', params),
  createArea: (data: Partial<ProductionArea>) =>
    post<ProductionArea>('/base-data/areas', data),
  updateArea: (id: number, data: Partial<ProductionArea>) =>
    put<ProductionArea>(`/base-data/areas/${id}`, data),
  deleteArea: (id: number) => del<void>(`/base-data/areas/${id}`),

  products: (params?: Record<string, unknown>) =>
    get<PageResult<Product>>('/base-data/products', params),
  createProduct: (data: Partial<Product>) =>
    post<Product>('/base-data/products', data),
  updateProduct: (id: number, data: Partial<Product>) =>
    put<Product>(`/base-data/products/${id}`, data),
  deleteProduct: (id: number) => del<void>(`/base-data/products/${id}`),
}

// ---------------- 产销数据 ----------------
export const tradeApi = {
  production: (params?: Record<string, unknown>) =>
    get<PageResult<ProductionData>>('/production', params),
  createProduction: (data: Partial<ProductionData>) =>
    post<ProductionData>('/production', data),
  updateProduction: (id: number, data: Partial<ProductionData>) =>
    put<ProductionData>(`/production/${id}`, data),
  deleteProduction: (id: number) => del<void>(`/production/${id}`),

  sales: (params?: Record<string, unknown>) =>
    get<PageResult<SalesData>>('/sales', params),
  createSales: (data: Partial<SalesData>) => post<SalesData>('/sales', data),
  updateSales: (id: number, data: Partial<SalesData>) =>
    put<SalesData>(`/sales/${id}`, data),
  deleteSales: (id: number) => del<void>(`/sales/${id}`),

  prices: (params?: Record<string, unknown>) =>
    get<PageResult<PriceData>>('/prices', params),
  createPrice: (data: Partial<PriceData>) => post<PriceData>('/prices', data),
  updatePrice: (id: number, data: Partial<PriceData>) =>
    put<PriceData>(`/prices/${id}`, data),
  deletePrice: (id: number) => del<void>(`/prices/${id}`),

  markets: (params?: Record<string, unknown>) =>
    get<PageResult<MarketData>>('/markets', params),
  createMarket: (data: Partial<MarketData>) => post<MarketData>('/markets', data),
  updateMarket: (id: number, data: Partial<MarketData>) =>
    put<MarketData>(`/markets/${id}`, data),
  deleteMarket: (id: number) => del<void>(`/markets/${id}`),

  pestTypes: () => get<PestType[]>('/pest-types'),
  createPestType: (data: Partial<PestType>) => post<PestType>('/pest-types', data),

  pestRecords: (params?: Record<string, unknown>) =>
    get<PageResult<PestRecord>>('/pest-records', params),
  createPestRecord: (data: Partial<PestRecord>) =>
    post<PestRecord>('/pest-records', data),
  updatePestRecord: (id: number, data: Partial<PestRecord>) =>
    put<PestRecord>(`/pest-records/${id}`, data),
  deletePestRecord: (id: number) => del<void>(`/pest-records/${id}`),

  importPreview: (target: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return upload<ImportPreviewResult>('/import/preview', form, { target })
  },
  importCommit: (target: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return upload<ImportCommitResult>('/import/commit', form, { target })
  },
}

export interface ImportPreviewResult {
  total: number
  valid_count: number
  error_count: number
  valid_rows: Record<string, unknown>[]
  error_rows: { row: number; data: Record<string, unknown>; errors: string[] }[]
}

export interface ImportCommitResult {
  imported: number
}

// ---------------- 数据分析 ----------------
export const analysisApi = {
  productionSales: (params?: Record<string, unknown>) =>
    get<{
      monthly: { month: string; production: number; sales: number; rate: number | null; gap: number }[]
      by_area: { name: string; production: number }[]
      by_county: { name: string; production: number }[]
      summary: { total_production: number; total_sales: number; rate: number | null }
    }>('/analysis/production-sales', params),
  price: (params?: Record<string, unknown>) =>
    get<{
      monthly: { month: string; avg: number; max: number; min: number }[]
      by_area: { name: string; avg: number; max: number; min: number }[]
      summary: { avg_price: number; highest: number | null; lowest: number | null; volatility: number | null }
    }>('/analysis/price', params),
  market: (params?: Record<string, unknown>) =>
    get<{
      year: number
      provinces: {
        name: string
        sales_volume: number
        sales_amount: number
        market_share: number | null
        market_level: string | null
        growth_rate: number | null
      }[]
      top10: {
        name: string
        sales_volume: number
        sales_amount: number
        market_share: number | null
        market_level: string | null
        growth_rate: number | null
      }[]
      level_distribution: Record<string, number>
    }>('/analysis/market', params),
  pest: (params?: Record<string, unknown>) =>
    get<{
      by_type: { name: string; kind: string; count: number; affected_area: number; production_impact: number }[]
      by_county: { name: string; count: number; affected_area: number; production_impact: number }[]
      by_month: { month: string; count: number; affected_area: number }[]
    }>('/analysis/pest', params),
  evaluation: () =>
    get<{
      ranking: {
        area_id: number
        name: string
        price: number
        technology: number
        transport: number
        supply: number
        benefit: number
        total: number
        rank: number
      }[]
    }>('/analysis/evaluation'),
}

// ---------------- 预测与决策 ----------------
export const predictionApi = {
  train: (modelType: string) =>
    post<{ model: string; version: string; metric: string; score: number }>(
      '/predictions/train',
      undefined,
      { model_type: modelType },
    ),
  run: (modelType: string, months = 6) =>
    post<{ model: string; created: number }>('/predictions/run', undefined, {
      model_type: modelType,
      months,
    }),
  predictions: (params?: { type?: string; limit?: number }) =>
    get<PredictionResult[]>('/predictions', params),
  models: () => get<ModelInfo[]>('/models'),
  decisions: (limit = 20) => get<DecisionAdvice[]>('/decisions', { limit }),
  refreshDecisions: () => post<{ created: number }>('/decisions/refresh'),
}

// ---------------- 数字大屏 ----------------
export const screenApi = {
  overview: () => get<ScreenOverview>('/screen/overview'),
  chinaMap: () => get<ChinaMapData>('/screen/china-map'),
  ganzhou: () => get<GanzhouData>('/screen/ganzhou'),
  countyDetail: (regionId: number) => get<CountyDetail>(`/screen/county/${regionId}`),
  areaDetail: (areaId: number) => get<AreaDetail>(`/screen/area/${areaId}`),
  priceTrend: (months = 24) =>
    get<{ history: { month: string; value: number }[]; forecast: { month: string; value: number; lower: number; upper: number }[] }>(
      '/screen/price-trend',
      { months },
    ),
  predictions: (type?: string, limit = 20) =>
    get<PredictionResult[]>('/screen/predictions', { type, limit }),
  decisions: (limit = 10) => get<DecisionAdvice[]>('/screen/decisions', { limit }),
  /**
   * 智能预测与产销排产（价格/需求/产量/库存/病虫害 + 排产建议）。
   * 该接口要为每个省拟合随机森林，冷启动可达数十秒，故单独放宽超时。
   */
  intelligence: () => get<ScreenIntelligence>('/screen/intelligence', undefined, 90000),
  /** 地图全部图层，一次取回，前端切换无需再请求。同样属重计算接口。 */
  layers: () => get<MapLayers>('/screen/layers', undefined, 90000),
}

// ---------------- 系统管理 ----------------
export const systemApi = {
  users: (params?: Record<string, unknown>) =>
    get<PageResult<SysUser>>('/system/users', params),
  createUser: (data: Record<string, unknown>) => post<SysUser>('/system/users', data),
  updateUser: (id: number, data: Record<string, unknown>) =>
    put<SysUser>(`/system/users/${id}`, data),
  deleteUser: (id: number) => del<void>(`/system/users/${id}`),
  roles: () => get<Role[]>('/system/roles'),
  logs: (params?: Record<string, unknown>) =>
    get<PageResult<OperationLog>>('/system/logs', params),
}
