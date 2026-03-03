/**
 * Task Events Hook
 * 通过 WebSocket 订阅任务事件
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import type { TaskEvent } from '../types/task';
import { getStoredSessionId } from '../api/session';

interface UseTaskEventsOptions {
  taskId?: string;
  enabled?: boolean;
  onEvent?: (event: TaskEvent) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

interface UseTaskEventsReturn {
  connected: boolean;
  events: TaskEvent[];
  clearEvents: () => void;
  reconnect: () => void;
}

export function useTaskEvents(options: UseTaskEventsOptions = {}): UseTaskEventsReturn {
  const { taskId, enabled = true, onEvent, onConnect, onDisconnect } = options;
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<TaskEvent[]>([]);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  const connect = useCallback(() => {
    if (!enabled) return;
    
    const sessionId = getStoredSessionId();
    if (!sessionId) {
      console.warn('No session ID, cannot connect to WebSocket');
      return;
    }

    // 构建 WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    
    let url: string;
    if (taskId) {
      url = `${protocol}//${host}/ws/tasks/${taskId}/logs?session_id=${sessionId}`;
    } else {
      url = `${protocol}//${host}/ws/session/events?session_id=${sessionId}`;
    }

    // 关闭现有连接
    if (wsRef.current) {
      wsRef.current.close();
    }

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      console.log('[WS] Connected');
      onConnect?.();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // 处理心跳
        if (data.type === 'ping') {
          ws.send(JSON.stringify({ type: 'pong' }));
          return;
        }
        
        // 处理连接确认
        if (data.type === 'connected' || data.type === 'pong') {
          return;
        }

        // 任务事件
        const taskEvent = data as TaskEvent;
        setEvents((prev) => [...prev.slice(-99), taskEvent]);
        onEvent?.(taskEvent);
      } catch (e) {
        console.error('[WS] Failed to parse message:', e);
      }
    };

    ws.onerror = (error) => {
      console.error('[WS] Error:', error);
    };

    ws.onclose = (event) => {
      setConnected(false);
      console.log('[WS] Disconnected:', event.code, event.reason);
      onDisconnect?.();
      
      // 自动重连（如果不是主动关闭）
      if (enabled && event.code !== 1000) {
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('[WS] Attempting to reconnect...');
          connect();
        }, 3000);
      }
    };
  }, [taskId, enabled, onEvent, onConnect, onDisconnect]);

  const reconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    connect();
  }, [connect]);

  useEffect(() => {
    connect();
    
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounted');
      }
    };
  }, [connect]);

  return {
    connected,
    events,
    clearEvents,
    reconnect,
  };
}

export default useTaskEvents;

