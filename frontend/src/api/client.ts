import axios, {
  AxiosError,
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from 'axios'
import { ElMessage } from 'element-plus'

export interface ApiEnvelope<T = unknown> {
  code: number
  message: string
  data: T
}

export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

const TOKEN_KEY = 'orange_access_token'
const REFRESH_KEY = 'orange_refresh_token'

export const tokenStore = {
  get access() {
    return localStorage.getItem(TOKEN_KEY) || ''
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY) || ''
  },
  set(access: string, refresh: string) {
    localStorage.setItem(TOKEN_KEY, access)
    localStorage.setItem(REFRESH_KEY, refresh)
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

const http: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api/v1',
  timeout: 30000,
})

http.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStore.access
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let refreshing: Promise<string> | null = null

async function doRefresh(): Promise<string> {
  const refresh = tokenStore.refresh
  if (!refresh) throw new Error('no refresh token')
  const { data } = await axios.post(
    `${import.meta.env.VITE_API_BASE || '/api/v1'}/auth/refresh`,
    { refresh_token: refresh },
  )
  const payload = data?.data ?? data
  tokenStore.set(payload.access_token, payload.refresh_token)
  return payload.access_token as string
}

http.interceptors.response.use(
  (resp) => resp,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    const status = error.response?.status
    if (status === 401 && original && !original._retry && tokenStore.refresh) {
      original._retry = true
      try {
        refreshing = refreshing || doRefresh()
        const newToken = await refreshing
        refreshing = null
        original.headers.Authorization = `Bearer ${newToken}`
        return http(original)
      } catch (e) {
        refreshing = null
        tokenStore.clear()
        if (location.hash.indexOf('/login') === -1) {
          location.hash = '#/login'
        }
        ElMessage.error('登录已过期，请重新登录')
        return Promise.reject(e)
      }
    }
    return Promise.reject(error)
  },
)

/** 统一解包：成功返回 data，失败抛出 Error 并提示。 */
export async function request<T>(
  config: Parameters<AxiosInstance['request']>[0],
): Promise<T> {
  try {
    const resp = await http.request<ApiEnvelope<T>>(config)
    const body = resp.data
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code !== 0) throw new Error(body.message || '请求失败')
      return body.data as T
    }
    return body as unknown as T
  } catch (err) {
    const e = err as AxiosError<{ message?: string }>
    const msg =
      e.response?.data?.message || e.message || '网络请求失败，请稍后再试'
    ElMessage.error(msg)
    throw new Error(msg)
  }
}

export const get = <T>(
  url: string,
  params?: Record<string, unknown>,
  timeout?: number,
) => request<T>({ method: 'get', url, params, ...(timeout ? { timeout } : {}) })

export const post = <T>(url: string, data?: unknown, params?: Record<string, unknown>) =>
  request<T>({ method: 'post', url, data, params })

export const put = <T>(url: string, data?: unknown) =>
  request<T>({ method: 'put', url, data })

export const del = <T>(url: string) => request<T>({ method: 'delete', url })

export const upload = <T>(url: string, form: FormData, params?: Record<string, unknown>) =>
  request<T>({ method: 'post', url, data: form, params, headers: { 'Content-Type': 'multipart/form-data' } })

export default http
