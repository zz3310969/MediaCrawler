/**
 * Session Hook
 * 管理用户会话状态
 */
import { useState, useEffect, useCallback } from 'react';
import { 
  getCurrentUser, 
  logout as apiLogout,
} from '../api/tasks';
import {
  getStoredSessionId,
  clearStoredSessionId,
  redirectToLogin,
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

  const initSession = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const sessionId = getStoredSessionId();
      
      if (sessionId) {
        try {
          const data = await getCurrentUser();
          setSession(data);
          return;
        } catch {
          clearStoredSessionId();
        }
      }
      
      // 没有有效 session，跳转到登录页
      setSession(null);
      redirectToLogin();
    } catch (e) {
      setError(e as Error);
      console.error('Session init error:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } catch (e) {
      console.error('Logout error:', e);
    } finally {
      clearStoredSessionId();
      setSession(null);
      redirectToLogin();
    }
  }, []);

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

