// 实时日志查看器
import { useEffect, useRef, useState } from 'react'
import { Terminal, Trash2, Download } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useWebSocket } from '@/hooks/useWebSocket'
import type { LogEntry } from '@/api/crawler'

const LOG_LEVEL_COLORS = {
  info: 'text-blue-400',
  success: 'text-green-400',
  warning: 'text-yellow-400',
  error: 'text-red-400',
  debug: 'text-gray-400',
} as const

const LOG_LEVEL_BG = {
  info: 'bg-blue-500/10 border-blue-500/20',
  success: 'bg-green-500/10 border-green-500/20',
  warning: 'bg-yellow-500/10 border-yellow-500/20',
  error: 'bg-red-500/10 border-red-500/20',
  debug: 'bg-gray-500/10 border-gray-500/20',
} as const

export function LogViewer() {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)

  // WebSocket 连接
  const { isConnected } = useWebSocket({
    url: '/ws/logs',
    onMessage: (data: LogEntry) => {
      setLogs((prev) => [...prev, data])
    },
  })

  // 自动滚动到底部
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs])

  // 清空日志
  const handleClear = () => {
    setLogs([])
  }

  // 导出日志
  const handleExport = () => {
    const content = logs
      .map((log) => `[${log.timestamp}] [${log.level.toUpperCase()}] ${log.message}`)
      .join('\n')
    
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `crawler-logs-${Date.now()}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <Card className="w-full h-full flex flex-col">
      <CardHeader className="flex-shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Terminal className="h-5 w-5" />
              <span>实时日志</span>
              <Badge variant={isConnected ? 'default' : 'secondary'}>
                {isConnected ? '已连接' : '未连接'}
              </Badge>
            </CardTitle>
            <CardDescription>
              共 {logs.length} 条日志记录
            </CardDescription>
          </div>
          
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleExport}
              disabled={logs.length === 0}
            >
              <Download className="h-4 w-4 mr-1" />
              导出
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleClear}
              disabled={logs.length === 0}
            >
              <Trash2 className="h-4 w-4 mr-1" />
              清空
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex-1 overflow-hidden p-0">
        <div 
          ref={scrollContainerRef}
          className="h-full overflow-y-auto p-4 space-y-1 font-mono text-sm bg-slate-950"
        >
          {logs.length === 0 ? (
            <div className="text-gray-500 text-center py-8">
              暂无日志记录
            </div>
          ) : (
            logs.map((log) => (
              <div
                key={log.id}
                className={`p-2 rounded border ${LOG_LEVEL_BG[log.level]}`}
              >
                <span className="text-gray-500 text-xs">
                  [{log.timestamp}]
                </span>
                <span className={`ml-2 font-semibold ${LOG_LEVEL_COLORS[log.level]}`}>
                  [{log.level.toUpperCase()}]
                </span>
                <span className="ml-2 text-gray-300">
                  {log.message}
                </span>
              </div>
            ))
          )}
          <div ref={bottomRef} />
        </div>
      </CardContent>
    </Card>
  )
}

