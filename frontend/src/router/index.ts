import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'
import { tokenStore } from '@/api/client'
import { useUserStore } from '@/stores/user'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { title: '登录', public: true },
  },
  {
    path: '/screen',
    name: 'Screen',
    component: () => import('@/views/screen/index.vue'),
    meta: { title: '数字大屏', public: true },
  },
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/screen/index.vue'),
    meta: { title: '数字大屏', public: true },
  },
  {
    path: '/dashboard',
    component: () => import('@/layouts/AdminLayout.vue'),
    redirect: '',
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: '数据概览', icon: 'DataLine', menu: true },
      },
      {
        path: 'base-data/regions',
        name: 'BaseRegion',
        component: () => import('@/views/base-data/region/index.vue'),
        meta: { title: '区域管理', icon: 'MapLocation', menu: true, group: '基础数据' },
      },
      {
        path: 'base-data/areas',
        name: 'BaseArea',
        component: () => import('@/views/base-data/area/index.vue'),
        meta: { title: '产地管理', icon: 'LocationInformation', menu: true, group: '基础数据' },
      },
      {
        path: 'base-data/products',
        name: 'BaseProduct',
        component: () => import('@/views/base-data/product/index.vue'),
        meta: { title: '品种管理', icon: 'GoodsFilled', menu: true, group: '基础数据' },
      },
      {
        path: 'trade/production',
        name: 'TradeProduction',
        component: () => import('@/views/trade/production/index.vue'),
        meta: { title: '产量数据', icon: 'Grape', menu: true, group: '产销数据' },
      },
      {
        path: 'trade/sales',
        name: 'TradeSales',
        component: () => import('@/views/trade/sales/index.vue'),
        meta: { title: '销量数据', icon: 'ShoppingCartFull', menu: true, group: '产销数据' },
      },
      {
        path: 'trade/price',
        name: 'TradePrice',
        component: () => import('@/views/trade/price/index.vue'),
        meta: { title: '价格数据', icon: 'Money', menu: true, group: '产销数据' },
      },
      {
        path: 'trade/import',
        name: 'TradeImport',
        component: () => import('@/views/trade/import/index.vue'),
        meta: { title: '数据导入', icon: 'UploadFilled', menu: true, group: '产销数据' },
      },
      {
        path: 'market',
        name: 'Market',
        component: () => import('@/views/market/index.vue'),
        meta: { title: '市场管理', icon: 'TrendCharts', menu: true, group: '市场与病虫害' },
      },
      {
        path: 'pest',
        name: 'Pest',
        component: () => import('@/views/pest/index.vue'),
        meta: { title: '病虫害管理', icon: 'Aim', menu: true, group: '市场与病虫害' },
      },
      {
        path: 'analysis',
        name: 'Analysis',
        component: () => import('@/views/analysis/index.vue'),
        meta: { title: '数据分析', icon: 'PieChart', menu: true, group: '智能分析' },
      },
      {
        path: 'prediction',
        name: 'Prediction',
        component: () => import('@/views/prediction/index.vue'),
        meta: { title: '智能预测与决策', icon: 'MagicStick', menu: true, group: '智能分析' },
      },
      {
        path: 'system/users',
        name: 'SystemUser',
        component: () => import('@/views/system/user/index.vue'),
        meta: { title: '用户管理', icon: 'UserFilled', menu: true, group: '系统管理' },
      },
      {
        path: 'system/logs',
        name: 'SystemLog',
        component: () => import('@/views/system/log/index.vue'),
        meta: { title: '操作日志', icon: 'Document', menu: true, group: '系统管理' },
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach(async (to) => {
  document.title = `${to.meta.title ? to.meta.title + ' - ' : ''}${
    import.meta.env.VITE_APP_TITLE || '脐橙产销数据平台'
  }`
  if (to.meta.public) return true
  if (!tokenStore.access) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  const store = useUserStore()
  if (!store.loaded) {
    const info = await store.ensureInfo()
    if (!info) {
      tokenStore.clear()
      return { path: '/login', query: { redirect: to.fullPath } }
    }
  }
  return true
})

export default router
