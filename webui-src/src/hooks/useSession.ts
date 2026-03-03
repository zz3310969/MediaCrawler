/**
 * Session Hook
 * 管理用户会话状态
 */
import { useState, useEffect, useCallback } from 'react';
import { 
  createSession, 
  getCurrentUser, 
  logout as apiLogout,
} from '../api/tasks';
import {
  getStoredSessionId,
  clearStoredSessionId 
} from '../api/session';
import type { SessionResponse } from '../types/task';

interface UseSessionReturn {
  session: SessionResponse | null;
  loading: boolean;
  error: Error | null;
  isAuthenticated: boolean;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

export function useSession(): UseSessionReturn {
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  // 初始化 session
  const initSession = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // 检查是否已有 session
      const sessionId = getStoredSessionId();
      
      if (sessionId) {
        // 验证现有 session
        try {
          const data = await getCurrentUser();
          setSession(data);
          return;
        } catch {
          // session 无效，清除
          clearStoredSessionId();
        }
      }
      
      // 创建新 session
      const data = await createSession();
      setSession(data);
    } catch (e) {
      setError(e as Error);
      console.error('Session init error:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  // 登出
  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } catch (e) {
      console.error('Logout error:', e);
    } finally {
      setSession(null);
      // 重新创建匿名 session
      await initSession();
    }
  }, [initSession]);

  // 刷新
  const refresh = useCallback(async () => {
    await initSession();
  }, [initSession]);

  useEffect(() => {
    initSession();
  }, [initSession]);

  return {
    session,
    loading,
    error,
    isAuthenticated: !!session,
    logout,
    refresh,
  };
}

export default useSession;

