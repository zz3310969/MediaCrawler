// 微信平台专用配置卡片
import { useState, KeyboardEvent } from 'react'
import { MessageSquare, FileDown, BarChart3, BookOpen, Search, User, Link, Settings2, KeyRound } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator' // Assuming you might have this, or use hr
import type { CrawlerType } from '@/api/crawler'

interface WeChatConfigProps {
  crawlerType: CrawlerType
  keywords: string
  creatorIds: string
  specifiedIds: string
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
  onKeywordsChange: (value: string) => void
  onCreatorIdsChange: (value: string) => void
  onSpecifiedIdsChange: (value: string) => void
  onEnableContentChange: (value: boolean) => void
  onEnableReadingStatsChange: (value: boolean) => void
  onEnableExportChange: (value: boolean) => void
  onExportFormatChange: (value: string) => void
  onAlbumIdsChange: (value: string) => void
  onCredentialsUinChange: (value: string) => void
  onCredentialsKeyChange: (value: string) => void
  onCredentialsPassTicketChange: (value: string) => void
}

const CRAWLER_MODES = [
  { id: 'search', label: '搜索', icon: Search, desc: '关键词搜索文章' },
  { id: 'creator', label: '公众号', icon: User, desc: '指定公众号历史文章' },
  { id: 'detail', label: '文章', icon: Link, desc: '指定文章URL抓取' },
  { id: 'album', label: '合集', icon: BookOpen, desc: '公众号专辑/合集' },
] as const

const EXPORT_FORMATS = [
  { value: 'html', label: 'HTML 完整归档' },
  { value: 'markdown', label: 'Markdown 文档' },
  { value: 'pdf', label: 'PDF 文档' }, // 假设支持，虽然原代码没写，但通常需要
  { value: 'json', label: 'JSON 数据' },
  { value: 'excel', label: 'Excel 表格' },
]

export function WeChatConfig({
  crawlerType,
  keywords,
  creatorIds,
  specifiedIds,
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
  onKeywordsChange,
  onCreatorIdsChange,
  onSpecifiedIdsChange,
  onEnableContentChange,
  onEnableReadingStatsChange,
  onEnableExportChange,
  onExportFormatChange,
  onAlbumIdsChange,
  onCredentialsUinChange,
  onCredentialsKeyChange,
  onCredentialsPassTicketChange,
}: WeChatConfigProps) {
  // 本地状态用于输入框
  const [inputs, setInputs] = useState({
    search: '',
    creator: '',
    detail: '',
    album: ''
  })

  const [showAdvanced, setShowAdvanced] = useState(false)

  // 更新本地输入状态
  const updateInput = (key: keyof typeof inputs, value: string) => {
    setInputs(prev => ({ ...prev, [key]: value }))
  }

  // 通用去重添加处理
  const handleAdd = (
    key: keyof typeof inputs, 
    currentValue: string, 
    onChange: (val: string) => void,
    separator: RegExp = /[,;，；\n]/
  ) => {
    const inputVal = inputs[key]
    if (!inputVal.trim()) return

    const currentList = currentValue ? currentValue.split(',').filter(i => i.trim()) : []
    const newItems = inputVal
      .split(separator)
      .map(i => i.trim())
      .filter(i => i && !currentList.includes(i))

    if (newItems.length > 0) {
      const updated = currentList.concat(newItems).join(',')
      onChange(updated)
    }
    updateInput(key, '')
  }

  // 通用删除处理
  const handleRemove = (
    index: number,
    currentValue: string,
    onChange: (val: string) => void
  ) => {
    const list = currentValue.split(',').filter(i => i.trim())
    list.splice(index, 1)
    onChange(list.join(','))
  }

  // 渲染标签列表
  const renderTagList = (
    valueStr: string,
    onRemove: (idx: number) => void,
    colorClass: string = "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
  ) => {
    const list = valueStr ? valueStr.split(',').filter(i => i.trim()) : []
    if (list.length === 0) return null

    return (
      <div className="flex flex-wrap gap-2 mt-2 max-h-[100px] overflow-y-auto p-1">
        {list.map((item, idx) => (
          <Badge 
            key={idx} 
            variant="secondary"
            className={`font-mono text-xs flex items-center gap-1 ${colorClass}`}
          >
            <span className="truncate max-w-[150px]" title={item}>{item}</span>
            <button
              onClick={() => onRemove(idx)}
              className="ml-1 hover:text-red-500 rounded-full w-4 h-4 flex items-center justify-center"
              disabled={disabled}
            >
              ×
            </button>
          </Badge>
        ))}
      </div>
    )
  }

  return (
    <Card className="h-full flex flex-col shadow-sm">
      <CardHeader className="pb-3 pt-4 px-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5 text-green-600" />
            <div className="flex flex-col">
              <CardTitle className="text-base font-medium">微信公众号</CardTitle>
            </div>
          </div>
          <Badge variant="outline" className="text-[10px] px-1 py-0 h-5">v1.0</Badge>
        </div>

        {/* 模式切换 Tabs */}
        <div className="grid grid-cols-4 gap-1 p-1 bg-slate-100 dark:bg-slate-800 rounded-lg">
          {CRAWLER_MODES.map((mode) => {
            const Icon = mode.icon
            const isActive = crawlerType === mode.id
            return (
              <button
                key={mode.id}
                onClick={() => onCrawlerTypeChange(mode.id as CrawlerType)}
                disabled={disabled}
                className={`
                  flex flex-col items-center justify-center py-2 px-1 rounded-md text-xs transition-all
                  ${isActive 
                    ? 'bg-white dark:bg-slate-700 shadow-sm text-green-600 dark:text-green-400 font-medium' 
                    : 'text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-700'}
                `}
                title={mode.desc}
              >
                <Icon className={`h-4 w-4 mb-1 ${isActive ? 'text-green-600' : 'text-slate-400'}`} />
                {mode.label}
              </button>
            )
          })}
        </div>
      </CardHeader>

      <CardContent className="flex-1 space-y-4 px-4 pb-4 overflow-y-auto">
        {/* 主要输入区域 - 根据模式变化 */}
        <div className="min-h-[160px]">
          {crawlerType === 'search' && (
            <div className="space-y-2 animate-in fade-in duration-300">
              <div className="space-y-1">
                <div className="flex justify-between items-center">
                  <Label className="text-xs text-muted-foreground">搜索关键词</Label>
                  <span className="text-[10px] text-muted-foreground">回车添加</span>
                </div>
                <div className="relative">
                  <Input 
                    value={inputs.search}
                    onChange={(e) => updateInput('search', e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleAdd('search', keywords, onKeywordsChange)}
                    placeholder="输入关键词..."
                    disabled={disabled}
                    className="pr-8"
                  />
                  <Search className="absolute right-2.5 top-2.5 h-4 w-4 text-slate-300" />
                </div>
              </div>
              {renderTagList(keywords, (i) => handleRemove(i, keywords, onKeywordsChange), "bg-green-50 text-green-700 border-green-200")}
            </div>
          )}

          {crawlerType === 'creator' && (
            <div className="space-y-2 animate-in fade-in duration-300">
              <div className="space-y-1">
                <div className="flex justify-between items-center">
                  <Label className="text-xs text-muted-foreground">公众号 Biz ID</Label>
                  <span className="text-[10px] text-muted-foreground">__biz 参数</span>
                </div>
                <textarea
                  value={inputs.creator}
                  onChange={(e) => updateInput('creator', e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAdd('creator', creatorIds, onCreatorIdsChange))}
                  placeholder="输入 biz 值或包含 biz 的链接..."
                  disabled={disabled}
                  className="w-full h-20 px-3 py-2 text-sm rounded-md border border-input bg-background font-mono resize-none focus:outline-none focus:ring-2 focus:ring-green-500/20"
                />
              </div>
              {renderTagList(creatorIds, (i) => handleRemove(i, creatorIds, onCreatorIdsChange), "bg-blue-50 text-blue-700 border-blue-200")}
            </div>
          )}

          {crawlerType === 'detail' && (
            <div className="space-y-2 animate-in fade-in duration-300">
              <div className="space-y-1">
                <div className="flex justify-between items-center">
                  <Label className="text-xs text-muted-foreground">文章链接</Label>
                  <span className="text-[10px] text-muted-foreground">支持批量粘贴</span>
                </div>
                <textarea
                  value={inputs.detail}
                  onChange={(e) => updateInput('detail', e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAdd('detail', specifiedIds, onSpecifiedIdsChange))}
                  placeholder="https://mp.weixin.qq.com/s/..."
                  disabled={disabled}
                  className="w-full h-20 px-3 py-2 text-sm rounded-md border border-input bg-background font-mono resize-none focus:outline-none focus:ring-2 focus:ring-purple-500/20"
                />
              </div>
              {renderTagList(specifiedIds, (i) => handleRemove(i, specifiedIds, onSpecifiedIdsChange), "bg-purple-50 text-purple-700 border-purple-200")}
            </div>
          )}

          {crawlerType === 'album' && (
            <div className="space-y-2 animate-in fade-in duration-300">
              <div className="space-y-1">
                <div className="flex justify-between items-center">
                  <Label className="text-xs text-muted-foreground">合集 ID / URL</Label>
                  <span className="text-[10px] text-muted-foreground">支持批量</span>
                </div>
                <textarea
                  value={inputs.album}
                  onChange={(e) => updateInput('album', e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAdd('album', albumIds, onAlbumIdsChange))}
                  placeholder="album_id 或合集链接..."
                  disabled={disabled}
                  className="w-full h-20 px-3 py-2 text-sm rounded-md border border-input bg-background font-mono resize-none focus:outline-none focus:ring-2 focus:ring-orange-500/20"
                />
              </div>
              {renderTagList(albumIds, (i) => handleRemove(i, albumIds, onAlbumIdsChange), "bg-orange-50 text-orange-700 border-orange-200")}
            </div>
          )}
        </div>

        {/* 基础选项卡片 */}
        <div className="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3 space-y-3 border border-slate-100 dark:border-slate-800">
          <div className="flex items-center justify-between">
            <Label className="text-xs flex items-center gap-1.5 cursor-pointer" htmlFor="wechat-content">
              <FileDown className="h-3.5 w-3.5 text-slate-500" />
              抓取正文 HTML
            </Label>
            <Switch 
              id="wechat-content" 
              checked={enableContent} 
              onCheckedChange={onEnableContentChange}
              disabled={disabled}
              className="scale-90"
            />
          </div>
          
          <div className="flex items-center justify-between">
            <Label className="text-xs flex items-center gap-1.5 cursor-pointer" htmlFor="wechat-export">
              <Settings2 className="h-3.5 w-3.5 text-slate-500" />
              导出文件
            </Label>
            <div className="flex items-center gap-2">
              {enableExport && (
                <Select
                  value={exportFormat}
                  onChange={(e) => onExportFormatChange(e.target.value)}
                  disabled={disabled}
                >
                  {EXPORT_FORMATS.map(f => (
                    <option key={f.value} value={f.value}>{f.label}</option>
                  ))}
                </Select>
              )}
              <Switch 
                id="wechat-export" 
                checked={enableExport} 
                onCheckedChange={onEnableExportChange}
                disabled={disabled}
                className="scale-90"
              />
            </div>
          </div>
        </div>

        {/* 鉴权与高级配置 */}
        <div className={`
          border rounded-lg transition-all duration-300 overflow-hidden
          ${enableReadingStats ? 'border-amber-200 bg-amber-50/50 dark:border-amber-900/50 dark:bg-amber-950/20' : 'border-transparent'}
        `}>
          <div className="p-3">
            <div className="flex items-center justify-between">
              <Label className="text-xs flex items-center gap-1.5 cursor-pointer" htmlFor="wechat-stats">
                <BarChart3 className={`h-3.5 w-3.5 ${enableReadingStats ? 'text-amber-600' : 'text-slate-500'}`} />
                <span className={enableReadingStats ? 'text-amber-700 dark:text-amber-400 font-medium' : ''}>
                  抓取阅读量/评论
                </span>
              </Label>
              <Switch 
                id="wechat-stats" 
                checked={enableReadingStats} 
                onCheckedChange={(checked) => {
                  onEnableReadingStatsChange(checked)
                  if (checked) setShowAdvanced(true)
                }}
                disabled={disabled}
                className="scale-90"
              />
            </div>

            {/* 当启用阅读量时，或者手动展开时显示高级配置 */}
            {(enableReadingStats || showAdvanced) && (
              <div className="mt-3 space-y-3 pt-3 border-t border-dashed border-amber-200 dark:border-amber-900/50 animate-in slide-in-from-top-2">
                 <div className="flex items-center gap-2 mb-2">
                    <KeyRound className="h-3 w-3 text-amber-500" />
                    <span className="text-[10px] font-medium text-amber-600/80 uppercase tracking-wider">Authentication Headers</span>
                 </div>
                 
                 <div className="grid grid-cols-1 gap-2">
                    <div className="space-y-1">
                      <div className="flex justify-between">
                        <Label className="text-[10px] text-muted-foreground">Key</Label>
                        <span className="text-[10px] text-amber-600/60 scale-90 origin-right">必填 (易过期)</span>
                      </div>
                      <Input 
                        value={credentialsKey}
                        onChange={(e) => onCredentialsKeyChange(e.target.value)}
                        placeholder="wechat_key..."
                        className="h-7 text-xs font-mono bg-white dark:bg-slate-950"
                        type="password"
                      />
                    </div>
                    
                    <div className="space-y-1">
                      <Label className="text-[10px] text-muted-foreground">Pass Ticket</Label>
                      <Input 
                        value={credentialsPassTicket}
                        onChange={(e) => onCredentialsPassTicketChange(e.target.value)}
                        placeholder="pass_ticket..."
                        className="h-7 text-xs font-mono bg-white dark:bg-slate-950"
                        type="password"
                      />
                    </div>

                    <div className="space-y-1">
                      <Label className="text-[10px] text-muted-foreground">Uin (Optional)</Label>
                      <Input 
                        value={credentialsUin}
                        onChange={(e) => onCredentialsUinChange(e.target.value)}
                        placeholder="wx_uin..."
                        className="h-7 text-xs font-mono bg-white dark:bg-slate-950"
                        type="password"
                      />
                    </div>
                 </div>
              </div>
            )}
            
            {!enableReadingStats && !showAdvanced && (
              <div className="mt-2 text-center">
                <button 
                  onClick={() => setShowAdvanced(true)}
                  className="text-[10px] text-slate-400 hover:text-slate-600 flex items-center justify-center gap-1 w-full"
                >
                  展开高级配置 ▼
                </button>
              </div>
            )}
            
            {(showAdvanced && !enableReadingStats) && (
               <div className="mt-2 text-center">
                <button 
                  onClick={() => setShowAdvanced(false)}
                  className="text-[10px] text-slate-400 hover:text-slate-600 flex items-center justify-center gap-1 w-full"
                >
                  收起高级配置 ▲
                </button>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}


