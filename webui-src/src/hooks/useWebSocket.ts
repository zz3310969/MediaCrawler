// WebSocket Hook
import { useEffect, useRef, useState } from 'react'
import { WEBSOCKET_CONFIG } from '@/lib/constants'

interface UseWebSocketOptions {
  url: string
  onMessage?: (data: any) => void
  onOpen?: () => void
  onClose?: () => void
  onError?: (error: Event) => void
  autoReconnect?: boolean
  reconnectInterval?: number
}

export function useWebSocket({
  url,
  onMessage,
  onOpen,
  onClose,
  onError,
  autoReconnect = true,
  reconnectInterval = WEBSOCKET_CONFIG.RECONNECT_INTERVAL,
}: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimerRef = useRef<NodeJS.Timeout>()
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<any>(null)
  
  // 使用 ref 存储回调函数，避免依赖变化导致重连
  const onMessageRef = useRef(onMessage)
  const onOpenRef = useRef(onOpen)
  const onCloseRef = useRef(onClose)
  const onErrorRef = useRef(onError)
  
  useEffect(() => {
    onMessageRef.current = onMessage
    onOpenRef.current = onOpen
    onCloseRef.current = onClose
    onErrorRef.current = onError
  }, [onMessage, onOpen, onClose, onError])

  useEffect(() => {
    let connectTimer: NodeJS.Timeout | undefined;

    const connect = () => {
      // 避免重复连接
      if (wsRef.current?.readyState === WebSocket.OPEN || 
          wsRef.current?.readyState === WebSocket.CONNECTING) {
        return
      }

      try {
        const wsUrl = import.meta.env.DEV 
          ? `ws://127.0.0.1:8080${url}` 
          : `ws://${window.location.host}${url}`
        
        console.log('正在连接 WebSocket:', wsUrl)
        const ws = new WebSocket(wsUrl)
        
        ws.onopen = () => {
          console.log('WebSocket 已连接:', url)
          setIsConnected(true)
          onOpenRef.current?.()
        }
        
        ws.onmessage = (event) => {
          // 处理心跳消息
          if (event.data === 'ping' || event.data === 'pong') {
            if (event.data === 'ping') {
              ws.send('pong')
            }
            return
          }
          
          try {
            const data = JSON.parse(event.data)
            // console.log('收到日志:', data) // 减少日志噪音
            setLastMessage(data)
            onMessageRef.current?.(data)
          } catch (error) {
            console.error('解析 WebSocket 消息失败:', error, 'Raw data:', event.data)
          }
        }
        
        ws.onclose = () => {
          console.log('WebSocket 已断开:', url)
          setIsConnected(false)
          onCloseRef.current?.()
          
          // 自动重连
          if (autoReconnect && reconnectTimerRef.current === undefined) {
            console.log(`将在 ${reconnectInterval}ms 后重连...`)
            reconnectTimerRef.current = setTimeout(() => {
              reconnectTimerRef.current = undefined
              connect()
            }, reconnectInterval)
          }
        }
        
        ws.onerror = (error) => {
          // 忽略连接关闭时的错误
          if (ws.readyState !== WebSocket.CLOSED && ws.readyState !== WebSocket.CLOSING) {
            console.error('WebSocket 错误:', error)
            onErrorRef.current?.(error)
          }
        }
        
        wsRef.current = ws
      } catch (error) {
        console.error('创建 WebSocket 失败:', error)
      }
    }

    // 使用短暂延迟来处理 React Strict Mode 的 double-invoke 问题
    // 如果组件被快速卸载（Strict Mode Check），定时器会被清除，不会发起连接
    connectTimer = setTimeout(() => {
      connect()
    }, 100)

    // 清理函数
    return () => {
      // 清除挂起的连接请求
      if (connectTimer) {
        clearTimeout(connectTimer)
      }
      
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current)
        reconnectTimerRef.current = undefined
      }

      if (wsRef.current) {
        console.log('清理 WebSocket 连接')
        // 移除所有事件监听器，防止关闭时触发回调
        wsRef.current.onopen = null
        wsRef.current.onclose = null
        wsRef.current.onerror = null
        wsRef.current.onmessage = null
        
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [url, autoReconnect, reconnectInterval]) // 只依赖这些稳定的值

  const sendMessage = (data: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof data === 'string' ? data : JSON.stringify(data))
    } else {
      console.warn('WebSocket 未连接，无法发送消息')
    }
  }

  return {
    isConnected,
    lastMessage,
    sendMessage,
  }
}

