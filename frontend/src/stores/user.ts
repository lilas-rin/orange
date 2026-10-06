import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '@/api'
import { tokenStore } from '@/api/client'
import type { UserInfo } from '@/types'

export const useUserStore = defineStore('user', () => {
  const info = ref<UserInfo | null>(null)
  const loaded = ref(false)

  async function login(username: string, password: string) {
    const tokens = await authApi.login(username, password)
    tokenStore.set(tokens.access_token, tokens.refresh_token)
    await fetchInfo()
  }

  async function fetchInfo() {
    info.value = await authApi.me()
    loaded.value = true
    return info.value
  }

  async function ensureInfo() {
    if (info.value || !tokenStore.access) return info.value
    try {
      return await fetchInfo()
    } catch {
      return null
    }
  }

  async function logout() {
    try {
      if (tokenStore.refresh) await authApi.logout(tokenStore.refresh)
    } catch {
      /* ignore */
    }
    tokenStore.clear()
    info.value = null
    loaded.value = false
  }

  function hasPermission(code: string) {
    return info.value?.permissions?.includes(code) ?? false
  }

  function hasRole(code: string) {
    return info.value?.role === code
  }

  return { info, loaded, login, fetchInfo, ensureInfo, logout, hasPermission, hasRole }
})
