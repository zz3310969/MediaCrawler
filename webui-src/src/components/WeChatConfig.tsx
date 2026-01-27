// 微信平台专用配置卡片
import { useState, KeyboardEvent } from 'react'
import { MessageSquare, FileDown, BarChart3, BookOpen } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import type { CrawlerType } from '@/api/crawler'

interface WeChatConfigProps {
  crawlerType: CrawlerType
  enableContent: boolean
  enableReadingStats: boolean
  enableExport: boolean
  exportFormat: string
  albumIds: string
  credentialsUin: string
  credentialsKey: string
  credentialsPassTicket: string
  disabled?: boolean
  onCrawlerTypeChange: (value: CrawlerType) => void
  onEnableContentChange: (value: boolean) => void
  onEnableReadingStatsChange: (value: boolean) => void
  onEnableExportChange: (value: boolean) => void
  onExportFormatChange: (value: string) => void
  onAlbumIdsChange: (value: string) => void
  onCredentialsUinChange: (value: string) => void
  onCredentialsKeyChange: (value: string) => void
  onCredentialsPassTicketChange: (value: string) => void
}

const WECHAT_CRAWLER_TYPES = [
  { value: 'search', label: '搜索公众号' },
  { value: 'creator', label: '指定公众号文章列表' },
  { value: 'album', label: '合集文章批量下载' },
  { value: 'detail', label: '指定文章详情' },
]

const EXPORT_FORMATS = [
  { value: 'html', label: 'HTML (完整样式)' },
  { value: 'markdown', label: 'Markdown' },
  { value: 'txt', label: '纯文本 TXT' },
  { value: 'docx', label: 'Word 文档' },
  { value: 'json', label: 'JSON 数据' },
  { value: 'excel', label: 'Excel 表格' },
]

export function WeChatConfig({
  crawlerType,
  enableContent,
  enableReadingStats,
  enableExport,
  exportFormat,
  albumIds,
  credentialsUin,
  credentialsKey,
  credentialsPassTicket,
  disabled,
  onCrawlerTypeChange,
  onEnableContentChange,
  onEnableReadingStatsChange,
  onEnableExportChange,
  onExportFormatChange,
  onAlbumIdsChange,
  onCredentialsUinChange,
  onCredentialsKeyChange,
  onCredentialsPassTicketChange,
}: WeChatConfigProps) {
  const [albumInputValue, setAlbumInputValue] = useState('')

  // 去重辅助函数
  const deduplicateList = (list: string[]): string[] => {
    return Array.from(new Set(list.filter(item => item.trim())))
  }

  // 获取合集ID数组（自动去重）
  const albumList = deduplicateList(albumIds ? albumIds.split(',') : [])

  // 处理回车键添加合集ID
  const handleAlbumKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && albumInputValue.trim()) {
      e.preventDefault()
      
      const newAlbums = albumInputValue
        .split(/[,;，；\n]/)
        .map(a => a.trim())
        .filter(a => a && !albumList.includes(a))
      
      if (newAlbums.length === 0) {
        setAlbumInputValue('')
        return
      }
      
      const updatedAlbums = albumIds 
        ? `${albumIds},${newAlbums.join(',')}` 
        : newAlbums.join(',')
      onAlbumIdsChange(updatedAlbums)
      setAlbumInputValue('')
    }
  }

  // 删除指定合集ID
  const handleRemoveAlbum = (index: number) => {
    const newAlbums = albumList
      .filter((_, i) => i !== index)
      .join(',')
    onAlbumIdsChange(newAlbums)
  }

  const [showCredentials, setShowCredentials] = useState(false)

  return (
    <Card className="h-full">
      <CardHeader className="pb-1.5 pt-3 px-4">
        <div className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5 text-green-500" />
          <div className="flex items-baseline gap-2">
            <CardTitle className="text-base font-medium">微信公众号配置</CardTitle>
            <CardDescription className="text-xs text-muted-foreground/60">
              爬取与导出选项
            </CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3 px-4 pb-3">
        {/* 爬取类型 */}
        <div className="space-y-1">
          <Label className="text-xs">爬取类型</Label>
          <Select
            value={crawlerType}
            onChange={(e) => onCrawlerTypeChange(e.target.value as CrawlerType)}
            disabled={disabled}
          >
            {WECHAT_CRAWLER_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </Select>
        </div>

        {/* 合集模式专用：合集ID输入 */}
        {crawlerType === 'album' && (
          <div className="space-y-1">
            <Label className="text-xs flex items-center gap-1">
              <BookOpen className="h-3 w-3" />
              合集ID/URL
            </Label>
            <p className="text-xs text-muted-foreground mb-1">
              输入合集ID或URL按回车添加，支持批量粘贴
            </p>
            <textarea
              placeholder={"示例:\nalbum_id=123456789\nhttps://mp.weixin.qq.com/mp/appmsgalbum?..."}
              value={albumInputValue}
              onChange={(e) => setAlbumInputValue(e.target.value)}
              onKeyDown={handleAlbumKeyDown}
              disabled={disabled}
              className="w-full h-16 px-3 py-2 text-sm rounded-md border border-input bg-background font-mono resize-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring placeholder:text-xs placeholder:text-muted-foreground"
            />
            {/* 显示已添加的合集ID标签 */}
            {albumList.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {albumList.map((albumId, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center gap-1.5 px-3 py-1 text-sm bg-green-400/20 text-green-600 dark:text-green-400 rounded border border-green-400/40 hover:bg-green-400/30 transition-colors font-mono"
                  >
                    {albumId.length > 30 ? `${albumId.slice(0, 30)}...` : albumId}
                    <button
                      onClick={() => handleRemoveAlbum(index)}
                      className="text-green-600 dark:text-green-400 hover:text-green-700 dark:hover:text-green-300 font-bold"
                      disabled={disabled}
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 功能开关 */}
        <div className="space-y-2 pt-2 border-t border-slate-200 dark:border-slate-700">
          <div className="flex items-center justify-between">
            <Label htmlFor="enable-content" className="text-xs flex items-center gap-1">
              <FileDown className="h-3 w-3" />
              下载文章HTML内容
            </Label>
            <Switch
              id="enable-content"
              checked={enableContent}
              onCheckedChange={onEnableContentChange}
              disabled={disabled}
            />
          </div>

          <div className="flex items-center justify-between">
            <Label htmlFor="enable-stats" className="text-xs flex items-center gap-1">
              <BarChart3 className="h-3 w-3" />
              获取阅读量/点赞数
            </Label>
            <Switch
              id="enable-stats"
              checked={enableReadingStats}
              onCheckedChange={onEnableReadingStatsChange}
              disabled={disabled}
            />
          </div>

          <div className="flex items-center justify-between">
            <Label htmlFor="enable-export" className="text-xs flex items-center gap-1">
              <FileDown className="h-3 w-3" />
              启用文章导出
            </Label>
            <Switch
              id="enable-export"
              checked={enableExport}
              onCheckedChange={onEnableExportChange}
              disabled={disabled}
            />
          </div>
        </div>

        {/* 导出格式（仅在启用导出时显示） */}
        {enableExport && (
          <div className="space-y-1">
            <Label className="text-xs">导出格式</Label>
            <Select
              value={exportFormat}
              onChange={(e) => onExportFormatChange(e.target.value)}
              disabled={disabled}
            >
              {EXPORT_FORMATS.map((f) => (
                <option key={f.value} value={f.value}>
                  {f.label}
                </option>
              ))}
            </Select>
          </div>
        )}

        {/* 凭证配置（获取阅读量需要） */}
        {enableReadingStats && (
          <div className="space-y-2 pt-2 border-t border-slate-200 dark:border-slate-700">
            <button
              type="button"
              onClick={() => setShowCredentials(!showCredentials)}
              className="text-xs text-blue-500 hover:text-blue-600 flex items-center gap-1"
            >
              {showCredentials ? '▼' : '▶'} 高级凭证配置
            </button>
            
            {showCredentials && (
              <div className="space-y-2 pl-2 border-l-2 border-blue-400/30">
                <p className="text-xs text-muted-foreground">
                  获取阅读量等数据需要微信凭证，请从浏览器开发者工具中获取
                </p>
                <div className="space-y-1">
                  <Label className="text-xs">uin</Label>
                  <Input
                    type="password"
                    placeholder="从Cookie中获取"
                    value={credentialsUin}
                    onChange={(e) => onCredentialsUinChange(e.target.value)}
                    disabled={disabled}
                    className="h-7 text-xs font-mono"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">key</Label>
                  <Input
                    type="password"
                    placeholder="从URL参数中获取"
                    value={credentialsKey}
                    onChange={(e) => onCredentialsKeyChange(e.target.value)}
                    disabled={disabled}
                    className="h-7 text-xs font-mono"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">pass_ticket</Label>
                  <Input
                    type="password"
                    placeholder="从URL参数中获取"
                    value={credentialsPassTicket}
                    onChange={(e) => onCredentialsPassTicketChange(e.target.value)}
                    disabled={disabled}
                    className="h-7 text-xs font-mono"
                  />
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

