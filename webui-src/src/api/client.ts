/**
 * API 客户端配置
 * 统一的 axios 实例，所有 API 调用都使用此客户端
 */
import axios from 'axios'
import {
  getStoredSessionId,
  clearStoredSessionId,
  redirectToLogin,
  LOGIN_PATH,
} from './session'

// 不需要重定向到登录页的 API 路径
const AUTH_WHITELIST = ['/api/auth/session', '/api/auth/login', '/api/health']

// 创建 axios 实例
export const client = axios.create({
  baseURL: import.meta.env.DEV ? 'http://127.0.0.1:8080' : '',
  timeout: 30000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器 - 添加 Session ID
client.interceptors.request.use(
  (config) => {
    const sessionId = getStoredSessionId()
    if (sessionId) {
      config.headers['X-Session-ID'] = sessionId
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器 - 处理 401 跳转登录
client.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const requestUrl = error.config?.url || ''

    console.log('[API Client] Error intercepted:', { status, requestUrl, error })

    // 401 未授权 - 跳转到登录页
    if (status === 401) {
      console.log('[API Client] 401 detected, checking whitelist...')
      // 检查是否在白名单中
      const isWhitelisted = AUTH_WHITELIST.some((path) => requestUrl.includes(path))
      console.log('[API Client] Is whitelisted:', isWhitelisted)

      if (!isWhitelisted) {
        // 清除无效的 session
        clearStoredSessionId()
        console.log('[API Client] Session cleared')

        // 当前不在登录页则跳转
        const currentPath = window.location.pathname
        console.log('[API Client] Current path:', currentPath, 'Login path:', LOGIN_PATH)
        
        if (currentPath !== LOGIN_PATH) {
          console.log('[API Client] Redirecting to login...')
          redirectToLogin()
          // 返回一个永不 resolve 的 promise，防止后续代码执行
          return new Promise(() => {})
        }
      }
    }
    
    // 处理网络错误或 CORS 阻止的情况（status 为 undefined）
    // 如果错误消息包含 "Network Error"，可能是 CORS 问题导致的 401
    if (!status && error.message === 'Network Error') {
      console.log('[API Client] Network error detected, might be CORS blocked 401')
      // 检查是否有 session，如果没有则跳转登录
      if (!getStoredSessionId() && window.location.pathname !== LOGIN_PATH) {
        console.log('[API Client] No session, redirecting to login...')
        redirectToLogin()
        return new Promise(() => {})
      }
    }

    const message = error.response?.data?.detail || error.message || '请求失败'
    console.error('API Error:', message)
    return Promise.reject(new Error(message))
  }
)

// 导出 session 相关函数，方便其他模块使用
export { getStoredSessionId, clearStoredSessionId } from './session'
