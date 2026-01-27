// 输出配置卡片
import { FileOutput } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { crawlerApi, type SaveOption, type CrawlerType, type Platform } from '@/api/crawler'

interface OutputConfigProps {
  platform?: Platform
  saveOption: SaveOption
  enableComments: boolean
  enableSubComments: boolean
  headless: boolean
  // 增量爬取配置
  enableIncremental?: boolean
  incrementalThreshold?: number
  crawlerType?: CrawlerType
  disabled?: boolean
  onSaveOptionChange: (value: SaveOption) => void
  onEnableCommentsChange: (value: boolean) => void
  onEnableSubCommentsChange: (value: boolean) => void
  onHeadlessChange: (value: boolean) => void
  // 增量爬取回调
  onEnableIncrementalChange?: (value: boolean) => void
  onIncrementalThresholdChange?: (value: number) => void
}

export function OutputConfig({
  platform,
  saveOption,
  enableComments,
  enableSubComments,
  headless,
  enableIncremental = false,
  incrementalThreshold = 3,
  crawlerType,
  disabled,
  onSaveOptionChange,
  onEnableCommentsChange,
  onEnableSubCommentsChange,
  onHeadlessChange,
  onEnableIncrementalChange,
  onIncrementalThresholdChange,
}: OutputConfigProps) {
  // 获取配置选项
  const { data: configResponse } = useQuery({
    queryKey: ['config-options'],
    queryFn: crawlerApi.getConfigOptions,
  })

  const saveOptions = configResponse?.data?.save_options || []
  const incrementalConfig = configResponse?.data?.incremental_config
  
  // 判断当前是否支持增量爬取
  const supportsIncremental = incrementalConfig && 
    crawlerType && 
    incrementalConfig.supports_crawler_types.includes(crawlerType)
  
  // 微信平台已在 WeChatConfig 中配置了评论和阅读量，这里隐藏通用评论开关
  const showCommentsConfig = platform !== 'wechat'

  return (
    <Card className="h-full">
      <CardHeader className="pb-1.5 pt-3 px-4">
        <div className="flex items-center gap-2">
          <FileOutput className="h-5 w-5 text-purple-400" />
          <div className="flex items-baseline gap-2">
            <CardTitle className="text-base font-medium">输出配置</CardTitle>
            <CardDescription className="text-xs text-muted-foreground/60">
              数据存储与运行模式
            </CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-2 px-4 pb-3">
        {/* 保存格式 */}
        <div className="space-y-1">
          <Label className="text-xs">数据存储</Label>
          <Select
            value={saveOption}
            onChange={(e) => onSaveOptionChange(e.target.value as SaveOption)}
            disabled={disabled || saveOptions.length === 0}
          >
            {saveOptions.map((option: { value: string; label: string }) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
        </div>

        {/* 爬取选项 */}
        <div className="space-y-2 pt-1.5">
          {showCommentsConfig && (
            <>
              <label
                htmlFor="enable-comments"
                className="flex items-center justify-between py-1.5 px-3 bg-secondary/50 rounded-md cursor-pointer hover:bg-secondary/70 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="enable-comments"
                    checked={enableComments}
                    onChange={(e) => onEnableCommentsChange(e.target.checked)}
                    disabled={disabled}
                    className="w-4 h-4 rounded border-gray-600 bg-gray-700 cursor-pointer"
                  />
                  <span className="text-sm">评论抓取</span>
                </div>
              </label>

              <label
                htmlFor="enable-sub-comments"
                className="flex items-center justify-between py-1.5 px-3 bg-secondary/50 rounded-md cursor-pointer hover:bg-secondary/70 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="enable-sub-comments"
                    checked={enableSubComments}
                    onChange={(e) => onEnableSubCommentsChange(e.target.checked)}
                    disabled={disabled}
                    className="w-4 h-4 rounded border-gray-600 bg-gray-700 cursor-pointer"
                  />
                  <span className="text-sm">子评论</span>
                </div>
              </label>
            </>
          )}

          <label
            htmlFor="headless"
            className="flex items-center justify-between py-1.5 px-3 bg-secondary/50 rounded-md cursor-pointer hover:bg-secondary/70 transition-colors"
          >
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="headless"
                checked={headless}
                onChange={(e) => onHeadlessChange(e.target.checked)}
                disabled={disabled}
                className="w-4 h-4 rounded border-gray-600 bg-gray-700 cursor-pointer"
              />
              <span className="text-sm">无头模式</span>
            </div>
          </label>
          
          {/* 增量爬取配置 - 仅在创作者模式下显示 */}
          {supportsIncremental && (
            <>
              <label
                htmlFor="enable-incremental"
                className="flex items-center justify-between py-1.5 px-3 bg-cyan-500/10 border border-cyan-500/20 rounded-md cursor-pointer hover:bg-cyan-500/15 transition-colors"
                title="增量爬取：只爬取新内容，效率提升10-100倍"
              >
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="enable-incremental"
                    checked={enableIncremental}
                    onChange={(e) => onEnableIncrementalChange?.(e.target.checked)}
                    disabled={disabled}
                    className="w-4 h-4 rounded border-cyan-600 bg-cyan-700 cursor-pointer"
                  />
                  <span className="text-sm flex items-center gap-1.5">
                    <span>⚡</span>
                    <span>增量爬取</span>
                  </span>
                </div>
                {enableIncremental && (
                  <span className="text-xs text-cyan-400 font-medium">高效模式</span>
                )}
              </label>
              
              {/* 早停阈值 - 仅在启用增量时显示 */}
              {enableIncremental && (
                <div className="space-y-1 ml-6 pl-2 border-l-2 border-cyan-500/30">
                  <Label className="text-xs text-muted-foreground">早停阈值</Label>
                  <Input
                    type="number"
                    value={incrementalThreshold}
                    onChange={(e) => onIncrementalThresholdChange?.(Number(e.target.value))}
                    disabled={disabled}
                    min={incrementalConfig?.threshold_range.min || 1}
                    max={incrementalConfig?.threshold_range.max || 10}
                    className="h-8 text-sm"
                    placeholder="连续N条已存在就停止"
                  />
                  <p className="text-xs text-muted-foreground/60">
                    连续 {incrementalThreshold} 条已存在内容就停止爬取
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

