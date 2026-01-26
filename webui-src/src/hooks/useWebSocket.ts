// WebSocket Hook
import { useEffect, useRef, useState } from 'react'

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
  reconnectInterval = 3000,
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
    const connect = () => {
      // 避免重复连接
      if (wsRef.current?.readyState === WebSocket.OPEN || 
          wsRef.current?.readyState === WebSocket.CONNECTING) {
        return
      }

      try {
        const wsUrl = import.meta.env.DEV 
          ? `ws://localhost:8080${url}` 
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
            console.log('收到日志:', data)
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
          console.error('WebSocket 错误:', error)
          onErrorRef.current?.(error)
        }
        
        wsRef.current = ws
      } catch (error) {
        console.error('创建 WebSocket 失败:', error)
      }
    }

    connect()

    // 清理函数
    return () => {
      console.log('清理 WebSocket 连接')
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current)
        reconnectTimerRef.current = undefined
      }
      if (wsRef.current) {
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

