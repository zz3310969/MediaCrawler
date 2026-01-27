// 爬虫进度面板
import { Activity, FileText, MessageSquare, Image, FileDown, User, BookOpen } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { CrawlerProgress } from '@/api/crawler'

interface ProgressPanelProps {
  progress?: CrawlerProgress
  isRunning: boolean
  platform?: string
}

export function ProgressPanel({ progress, isRunning, platform }: ProgressPanelProps) {
  if (!isRunning && !progress) {
    return null
  }

  const stats = [
    {
      icon: FileText,
      label: '已爬取文章',
      value: progress?.articles_crawled ?? 0,
      total: progress?.articles_total,
      color: 'text-blue-500',
      bgColor: 'bg-blue-500/10',
    },
    {
      icon: MessageSquare,
      label: '已爬取评论',
      value: progress?.comments_crawled ?? 0,
      color: 'text-green-500',
      bgColor: 'bg-green-500/10',
    },
    {
      icon: Image,
      label: '已下载资源',
      value: progress?.resources_downloaded ?? 0,
      color: 'text-purple-500',
      bgColor: 'bg-purple-500/10',
    },
    {
      icon: FileDown,
      label: '已导出文件',
      value: progress?.exports_completed ?? 0,
      color: 'text-orange-500',
      bgColor: 'bg-orange-500/10',
    },
  ]

  const percentage = progress?.percentage ?? 0

  return (
    <Card className="mb-3">
      <CardHeader className="pb-2 pt-3 px-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className={`h-5 w-5 ${isRunning ? 'text-green-500 animate-pulse' : 'text-slate-400'}`} />
            <CardTitle className="text-base font-medium">爬取进度</CardTitle>
          </div>
          
          {/* 当前账号/合集信息 */}
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            {progress?.current_account && (
              <span className="flex items-center gap-1">
                <User className="h-3 w-3" />
                {progress.current_account}
              </span>
            )}
            {progress?.current_album && (
              <span className="flex items-center gap-1">
                <BookOpen className="h-3 w-3" />
                {progress.current_album}
              </span>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="px-4 pb-3">
        {/* 进度条 */}
        {progress?.articles_total && progress.articles_total > 0 && (
          <div className="mb-3">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-muted-foreground">总进度</span>
              <span className="text-xs font-medium">{percentage.toFixed(1)}%</span>
            </div>
            <div className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-300 ease-out"
                style={{ width: `${Math.min(percentage, 100)}%` }}
              />
            </div>
          </div>
        )}

        {/* 统计卡片 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {stats.map((stat) => (
            <div 
              key={stat.label}
              className={`flex items-center gap-2 p-2 rounded-lg ${stat.bgColor}`}
            >
              <stat.icon className={`h-4 w-4 ${stat.color}`} />
              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground">{stat.label}</span>
                <span className="text-sm font-semibold">
                  {stat.value}
                  {stat.total !== undefined && stat.total > 0 && (
                    <span className="text-xs text-muted-foreground font-normal"> / {stat.total}</span>
                  )}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* 微信平台特有提示 */}
        {platform === 'wechat' && isRunning && (
          <div className="mt-3 p-2 bg-yellow-500/10 border border-yellow-500/20 rounded-md">
            <p className="text-xs text-yellow-600 dark:text-yellow-400">
              💡 提示：获取阅读量和评论需要有效的微信凭证，凭证可能在短时间内过期
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

