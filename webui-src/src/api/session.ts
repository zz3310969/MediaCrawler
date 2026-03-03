/**
 * Session 管理
 */

// Session ID 存储 key
const SESSION_ID_KEY = 'mc_session_id'

// 登录页面路径
export const LOGIN_PATH = '/login'

// 防止重复跳转的标志
let isRedirecting = false

/**
 * 获取存储的 Session ID
 */
export function getStoredSessionId(): string | null {
  return localStorage.getItem(SESSION_ID_KEY)
}

/**
 * 存储 Session ID
 */
export function setStoredSessionId(sessionId: string): void {
  localStorage.setItem(SESSION_ID_KEY, sessionId)
}

/**
 * 清除 Session ID
 */
export function clearStoredSessionId(): void {
  localStorage.removeItem(SESSION_ID_KEY)
}

/**
 * 检查是否已登录
 */
export function isLoggedIn(): boolean {
  return !!getStoredSessionId()
}

/**
 * 重定向到登录页
 */
export function redirectToLogin(): void {
  // 防止重复跳转
  if (isRedirecting) {
    console.log('[Session] Already redirecting, skip')
    return
  }
  
  const currentPath = window.location.pathname
  console.log('[Session] redirectToLogin called, currentPath:', currentPath)
  
  if (currentPath !== LOGIN_PATH) {
    isRedirecting = true
    // 保存当前路径，登录后跳回
    sessionStorage.setItem('redirectAfterLogin', currentPath)
    console.log('[Session] Saved redirect path, navigating to login...')
    // 使用 replace 跳转到登录页，避免在历史记录中留下当前页面
    window.location.replace(LOGIN_PATH)
  }
}

/**
 * 获取登录后的重定向路径
 */
export function getRedirectPath(): string {
  const path = sessionStorage.getItem('redirectAfterLogin') || '/'
  sessionStorage.removeItem('redirectAfterLogin')
  return path
}

/**
 * 重置跳转状态（登录页面加载后调用）
 */
export function resetRedirectState(): void {
  isRedirecting = false
}
