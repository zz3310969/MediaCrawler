// 数据管理弹窗
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { FileText, RefreshCw, Download } from 'lucide-react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { crawlerApi, type DataFile } from '@/api/crawler'

interface DataManagerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

// 格式化文件大小
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

// 格式化时间
function formatDate(timestamp: number): string {
  const date = new Date(timestamp * 1000)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).replace(/\//g, '/')
}

// 提取文件类别（从路径中）
function extractCategory(filePath: string): string {
  const match = filePath.match(/^([^/]+)\//)
  if (match) {
    const platform = match[1]
    return platform
  }
  
  // 从文件名推断
  if (filePath.includes('vip_contents')) return 'Vip'
  if (filePath.includes('_contents_')) return 'Contents'
  if (filePath.includes('comments')) return 'Comments'
  if (filePath.includes('creator_content')) return 'Creator Contents'
  if (filePath.includes('creator_creator')) return 'Creator Creators'
  
  return 'Other'
}

export function DataManager({ open, onOpenChange }: DataManagerProps) {
  const [selectedCategory, setSelectedCategory] = useState<string>('all')

  // 获取数据文件列表
  const { data: filesData, isLoading, refetch } = useQuery({
    queryKey: ['data-files'],
    queryFn: () => crawlerApi.getDataFiles(),
    enabled: open,
  })

  const files = filesData?.files || []

  // 统计各类别的文件数量
  const categoryCounts: Record<string, number> = {}
  files.forEach(file => {
    const category = extractCategory(file.path)
    categoryCounts[category] = (categoryCounts[category] || 0) + 1
  })

  // 分类列表
  const categories = [
    { key: 'all', label: '全部', count: files.length },
    ...Object.entries(categoryCounts).map(([key, count]) => ({
      key,
      label: key,
      count,
    }))
  ]

  // 筛选文件
  const filteredFiles = selectedCategory === 'all' 
    ? files 
    : files.filter(file => extractCategory(file.path) === selectedCategory)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent onClose={() => onOpenChange(false)} className="max-w-7xl">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <div>
              <DialogTitle className="text-xl text-cyan-400">数据浏览器</DialogTitle>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-sm text-muted-foreground">数据文件管理</span>
                <Badge variant="secondary" className="text-xs">
                  {files.length} 条
                </Badge>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              disabled={isLoading}
            >
              <RefreshCw className={`h-4 w-4 mr-1 ${isLoading ? 'animate-spin' : ''}`} />
              重新扫描
            </Button>
          </div>
        </DialogHeader>

        <div className="px-6 pb-6">
          {/* 分类标签 */}
          <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
            {categories.map((category) => (
              <button
                key={category.key}
                onClick={() => setSelectedCategory(category.key)}
                className={`px-4 py-2 rounded-md text-sm whitespace-nowrap transition-colors ${
                  selectedCategory === category.key
                    ? 'bg-cyan-500 text-white'
                    : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                }`}
              >
                {category.label} ({category.count})
              </button>
            ))}
          </div>

          {/* 文件列表 */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 max-h-[60vh] overflow-y-auto">
            {isLoading ? (
              <div className="col-span-full text-center py-12 text-muted-foreground">
                加载中...
              </div>
            ) : filteredFiles.length === 0 ? (
              <div className="col-span-full text-center py-12 text-muted-foreground">
                暂无数据文件
              </div>
            ) : (
              filteredFiles.map((file) => (
                <div
                  key={file.path}
                  className="bg-card border border-border rounded-lg p-4 hover:shadow-lg transition-shadow cursor-pointer group"
                >
                  {/* 文件图标和名称 */}
                  <div className="flex items-start gap-3 mb-3">
                    <div className="flex-shrink-0 w-10 h-10 bg-yellow-500/20 rounded flex items-center justify-center">
                      <FileText className="h-6 w-6 text-yellow-500" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm font-medium text-foreground truncate">
                        {file.name}
                      </h4>
                      <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                        <span>{formatFileSize(file.size)}</span>
                        <span>|</span>
                        <span className="text-green-500">
                          {file.record_count !== null ? `${file.record_count} 条` : '-'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* 时间 */}
                  <div className="text-xs text-muted-foreground mb-3">
                    {formatDate(file.modified_at)}
                  </div>

                  {/* 文件类型标签和下载按钮 */}
                  <div className="flex items-center justify-between">
                    <Badge variant="secondary" className="text-xs uppercase bg-yellow-500/10 text-yellow-600 border-yellow-500/20">
                      .{file.type}
                    </Badge>
                    <a
                      href={crawlerApi.downloadFile(file.path)}
                      download
                      className="opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                        <Download className="h-3 w-3" />
                      </Button>
                    </a>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

