<template>
  <el-container class="admin-layout">
    <el-aside :width="collapsed ? '64px' : '220px'" class="sidebar">
      <div class="brand">
        <div class="brand-logo">橙</div>
        <div v-show="!collapsed" class="brand-text">
          <div class="brand-title">信丰脐橙</div>
          <div class="brand-sub">产销数据分析与智能决策</div>
        </div>
      </div>
      <el-scrollbar class="menu-scroll">
        <el-menu
          :default-active="activeMenu"
          :collapse="collapsed"
          :collapse-transition="false"
          background-color="#12261a"
          text-color="#c9d6cc"
          active-text-color="#ffffff"
          router
        >
          <template v-for="item in menuTree" :key="item.key">
            <el-menu-item v-if="!item.children" :index="item.index">
              <el-icon><component :is="item.icon" /></el-icon>
              <template #title>{{ item.title }}</template>
            </el-menu-item>
            <el-sub-menu v-else :index="item.key">
              <template #title>
                <el-icon><component :is="item.icon" /></el-icon>
                <span>{{ item.title }}</span>
              </template>
              <el-menu-item v-for="child in item.children" :key="child.index" :index="child.index">
                <el-icon><component :is="child.icon" /></el-icon>
                <template #title>{{ child.title }}</template>
              </el-menu-item>
            </el-sub-menu>
          </template>
        </el-menu>
      </el-scrollbar>
    </el-aside>

    <el-container>
      <el-header class="topbar">
        <div class="topbar-left">
          <el-icon class="collapse-btn" @click="collapsed = !collapsed">
            <Fold v-if="!collapsed" />
            <Expand v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item>{{ currentGroup || '工作台' }}</el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentTitle">{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="topbar-right">
          <el-button link type="primary" @click="openScreen">
            <el-icon><Monitor /></el-icon>
            <span>数字大屏</span>
          </el-button>
          <el-dropdown @command="onCommand">
            <span class="user-chip">
              <el-avatar :size="28" class="avatar">{{ avatarText }}</el-avatar>
              <span class="nick">{{ userStore.info?.nickname || userStore.info?.username || '用户' }}</span>
              <el-tag size="small" type="success" effect="plain">{{ roleLabel }}</el-tag>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main">
        <router-view v-slot="{ Component }">
          <keep-alive :max="6">
            <component :is="Component" />
          </keep-alive>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const collapsed = ref(false)

interface MenuNode {
  key: string
  index?: string
  title: string
  icon: string
  children?: MenuNode[]
}

const GROUP_ICON: Record<string, string> = {
  基础数据: 'Coin',
  产销数据: 'DataAnalysis',
  市场与病虫害: 'Opportunity',
  智能分析: 'TrendCharts',
  系统管理: 'Setting',
}

const menuTree = computed<MenuNode[]>(() => {
  const isAdmin = userStore.hasRole('admin')
  const nodes: MenuNode[] = []
  const groupMap = new Map<string, MenuNode>()

  const children = (router.getRoutes().find((r) => r.path === '/dashboard')?.children ||
    []) as unknown as {
    path: string
    meta?: Record<string, unknown>
  }[]

  const routeChildren = router
    .getRoutes()
    .filter((r) => r.meta?.menu && r.path !== '/dashboard')

  // 保持路由定义顺序
  const ordered = routeChildren
    .slice()
    .sort((a, b) => orderIndex(a.path) - orderIndex(b.path))

  for (const r of ordered) {
    const meta = r.meta as Record<string, unknown>
    const group = meta.group as string | undefined
    if (group === '系统管理' && !isAdmin) continue
    const node: MenuNode = {
      key: r.path,
      index: r.path,
      title: meta.title as string,
      icon: meta.icon as string,
    }
    if (!group) {
      nodes.push(node)
      continue
    }
    let bucket = groupMap.get(group)
    if (!bucket) {
      bucket = { key: `g-${group}`, title: group, icon: GROUP_ICON[group] || 'Menu', children: [] }
      groupMap.set(group, bucket)
      nodes.push(bucket)
    }
    bucket.children!.push(node)
  }
  void children
  return nodes
})

const MENU_ORDER = [
  '/dashboard',
  '/dashboard/base-data/regions',
  '/dashboard/base-data/areas',
  '/dashboard/base-data/products',
  '/dashboard/trade/production',
  '/dashboard/trade/sales',
  '/dashboard/trade/price',
  '/dashboard/trade/import',
  '/dashboard/market',
  '/dashboard/pest',
  '/dashboard/analysis',
  '/dashboard/prediction',
  '/dashboard/system/users',
  '/dashboard/system/logs',
]
function orderIndex(path: string) {
  const i = MENU_ORDER.indexOf(path)
  return i === -1 ? 999 : i
}

const activeMenu = computed(() => route.path)
const currentTitle = computed(() => route.meta.title as string | undefined)
const currentGroup = computed(() => route.meta.group as string | undefined)
const avatarText = computed(() =>
  (userStore.info?.nickname || userStore.info?.username || 'U').slice(0, 1),
)
const roleLabel = computed(() => {
  const r = userStore.info?.role
  return r === 'admin' ? '管理员' : r === 'operator' ? '操作员' : '访客'
})

function openScreen() {
  window.open('#/screen', '_blank')
}

async function onCommand(cmd: string) {
  if (cmd === 'logout') {
    await ElMessageBox.confirm('确认退出登录？', '提示', { type: 'warning' })
    await userStore.logout()
    router.replace('/login')
  }
}

onMounted(() => {
  userStore.ensureInfo()
})
</script>

<style scoped>
.admin-layout {
  height: 100vh;
}

.sidebar {
  background: #12261a;
  transition: width 0.22s ease;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  height: 64px;
}

.brand-logo {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  background: linear-gradient(135deg, #ff9d3d, #f2760f);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  flex-shrink: 0;
}

.brand-text {
  line-height: 1.2;
  white-space: nowrap;
}

.brand-title {
  color: #fff;
  font-weight: 600;
  font-size: 15px;
}

.brand-sub {
  color: #86a08d;
  font-size: 11px;
  margin-top: 2px;
}

.menu-scroll {
  flex: 1;
}

.sidebar :deep(.el-menu) {
  border-right: none;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid var(--border);
  height: 64px;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.collapse-btn {
  cursor: pointer;
  font-size: 19px;
  color: #57606a;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 18px;
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  outline: none;
}

.avatar {
  background: var(--brand);
}

.nick {
  font-size: 14px;
}

.main {
  background: var(--bg-page);
  padding: 0;
  overflow-y: auto;
}
</style>
