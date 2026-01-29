// API 客户端配置
import axios from 'axios'
import { getStoredSessionId } from './tasks'

export const client = axios.create({
  baseURL: import.meta.env.DEV ? 'http://127.0.0.1:8080' : '',
  timeout: 30000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
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

// 响应拦截器
client.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    console.error('API Error:', message)
    return Promise.reject(new Error(message))
  }
)

