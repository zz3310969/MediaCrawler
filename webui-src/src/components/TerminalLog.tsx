// 终端风格日志查看器
import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { FileText, Trash2, Maximize2, Database } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useWebSocket } from '@/hooks/useWebSocket'
import { DataManager } from './DataManager'
import { crawlerApi, type LogEntry } from '@/api/crawler'

const LOG_LEVEL_COLORS = {
  info: 'text-blue-400',
  success: 'text-green-400',
  warning: 'text-yellow-400',
  error: 'text-red-400',
  debug: 'text-gray-400',
} as const

const ASCII_LOGO = `
███╗   ███╗███████╗██████╗ ██╗ █████╗  ██████╗██████╗  █████╗ ██╗    ██╗██╗     ███████╗██████╗ 
████╗ ████║██╔════╝██╔══██╗██║██╔══██╗██╔════╝██╔══██╗██╔══██╗██║    ██║██║     ██╔════╝██╔══██╗
██╔████╔██║█████╗  ██║  ██║██║███████║██║     ██████╔╝███████║██║ █╗ ██║██║     █████╗  ██████╔╝
██║╚██╔╝██║██╔══╝  ██║  ██║██║██╔══██║██║     ██╔══██╗██╔══██║██║███╗██║██║     ██╔══╝  ██╔══██╗
██║ ╚═╝ ██║███████╗██████╔╝██║██║  ██║╚██████╗██║  ██║██║  ██║╚███╔███╔╝███████╗███████╗██║  ██║
╚═╝     ╚═╝╚══════╝╚═════╝ ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚══╝╚══╝ ╚══════╝╚══════╝╚═╝  ╚═╝
`

export function TerminalLog() {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const [showLogo, setShowLogo] = useState(true)
  const [showDataManager, setShowDataManager] = useState(false)

  // 查询爬虫状态
  const { data: status } = useQuery({
    queryKey: ['crawler-status'],
    queryFn: crawlerApi.getStatus,
    refetchInterval: 1000, // 每秒刷新
  })

  // WebSocket 连接
  const { isConnected } = useWebSocket({
    url: '/api/ws/logs',
    onMessage: (data: LogEntry) => {
      console.log('收到 WebSocket 消息:', data)
      setLogs((prev) => [...prev, data])
      setShowLogo(false)
    },
    onOpen: () => {
      console.log('WebSocket 已连接')
    },
    onClose: () => {
      console.log('WebSocket 已断开')
    },
    onError: (error) => {
      console.error('WebSocket 错误:', error)
    },
  })

  // 获取状态显示文本和样式
  const getStatusDisplay = () => {
    if (!isConnected) {
      return { text: 'OFFLINE', variant: 'secondary' as const }
    }
    
    const statusMap = {
      'idle': { text: 'IDLE', variant: 'secondary' as const },
      'running': { text: 'RUNNING', variant: 'default' as const },
      'stopping': { text: 'STOPPING', variant: 'secondary' as const },
      'error': { text: 'ERROR', variant: 'destructive' as const },
    }
    
    return statusMap[status?.status || 'idle'] || statusMap.idle
  }

  const statusDisplay = getStatusDisplay()

  // 自动滚动到底部
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs])

  // 清空日志
  const handleClear = () => {
    setLogs([])
    setShowLogo(true)
  }

  return (
    <>
      <div className="bg-[#1a1d23] rounded-lg border border-gray-800 shadow-2xl overflow-hidden">
        {/* macOS 风格顶栏 */}
        <div className="bg-[#2d3139] border-b border-gray-800 px-4 py-2 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-[#ff5f56]"></div>
              <div className="w-3 h-3 rounded-full bg-[#ffbd2e]"></div>
              <div className="w-3 h-3 rounded-full bg-[#27c93f]"></div>
            </div>
            <span className="text-sm text-gray-400 font-medium">系统控制台</span>
            <Badge variant={statusDisplay.variant} className="text-xs">
              {statusDisplay.text}
            </Badge>
          </div>
          
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 px-2 py-1 text-xs text-gray-400">
              <FileText className="h-3 w-3" />
              <span>{logs.length} 条记录</span>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowDataManager(true)}
              className="h-7 text-xs text-gray-400 hover:text-gray-200"
            >
              <Database className="h-3 w-3 mr-1" />
              数据管理
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClear}
              disabled={logs.length === 0}
              className="h-7 text-xs text-gray-400 hover:text-gray-200"
            >
              <Trash2 className="h-3 w-3 mr-1" />
              清空
            </Button>
          </div>
        </div>

      {/* 日志内容区域 */}
      <div 
        ref={scrollContainerRef}
        className="h-[calc(100vh-600px)] min-h-[250px] max-h-[400px] overflow-y-auto p-4 font-mono text-xs bg-[#0d1117]"
      >
        {showLogo && (
          <div className="text-cyan-500/60 leading-tight mb-4">
            <pre className="text-[8px] select-none">{ASCII_LOGO}</pre>
            <div className="text-center text-gray-500 text-xs mt-2">
              [ NEURAL EXTRACTION UNIT v1.0 ]
            </div>
          </div>
        )}

        {logs.length === 0 && !showLogo && (
          <div className="text-gray-600 text-center py-8">
            等待日志输出...
          </div>
        )}

        {logs.map((log) => (
          <div key={log.id} className="py-1 hover:bg-gray-900/30">
            <span className="text-gray-600">
              [{log.timestamp}]
            </span>
            <span className={`ml-2 font-semibold ${LOG_LEVEL_COLORS[log.level]}`}>
              [{log.level === 'info' ? '信息' : 
                log.level === 'success' ? '系统' : 
                log.level === 'error' ? '错误' : 
                log.level === 'warning' ? '警告' : '调试'}]
            </span>
            <span className="ml-2 text-gray-300">
              {log.message}
            </span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>

    {/* 数据管理弹窗 */}
    <DataManager open={showDataManager} onOpenChange={setShowDataManager} />
    </>
  )
}

