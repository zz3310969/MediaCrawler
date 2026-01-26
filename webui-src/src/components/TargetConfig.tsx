// 目标配置卡片
import { useState, KeyboardEvent } from 'react'
import { Globe } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { crawlerApi, type Platform, type CrawlerType } from '@/api/crawler'

interface TargetConfigProps {
  platform: Platform
  crawlerType: CrawlerType
  keywords: string
  specifiedIds: string
  creatorIds: string
  startPage: number
  disabled?: boolean
  onPlatformChange: (value: Platform) => void
  onCrawlerTypeChange: (value: CrawlerType) => void
  onKeywordsChange: (value: string) => void
  onSpecifiedIdsChange: (value: string) => void
  onCreatorIdsChange: (value: string) => void
  onStartPageChange: (value: number) => void
}

export function TargetConfig({
  platform,
  crawlerType,
  keywords,
  specifiedIds,
  creatorIds,
  startPage,
  disabled,
  onPlatformChange,
  onCrawlerTypeChange,
  onKeywordsChange,
  onSpecifiedIdsChange,
  onCreatorIdsChange,
  onStartPageChange,
}: TargetConfigProps) {
  // 获取平台列表
  const { data: platformsData } = useQuery({
    queryKey: ['platforms'],
    queryFn: crawlerApi.getPlatforms,
  })

  // 获取配置选项
  const { data: configOptions } = useQuery({
    queryKey: ['config-options'],
    queryFn: crawlerApi.getConfigOptions,
  })

  // 临时输入框的值
  const [inputValue, setInputValue] = useState('')
  const [detailInputValue, setDetailInputValue] = useState('')
  const [creatorInputValue, setCreatorInputValue] = useState('')

  // 获取关键词数组
  const keywordList = keywords ? keywords.split(',').filter(k => k.trim()) : []
  
  // 获取帖子ID数组
  const detailList = specifiedIds ? specifiedIds.split(',').filter(k => k.trim()) : []
  
  // 获取创作者ID数组
  const creatorList = creatorIds ? creatorIds.split(',').filter(k => k.trim()) : []

  const platforms = platformsData?.platforms || []
  const crawlerTypes = configOptions?.crawler_types || []

  // 处理回车键添加关键词
  const handleKeywordKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && inputValue.trim()) {
      e.preventDefault()
      const newKeyword = inputValue.trim()
      const updatedKeywords = keywords 
        ? `${keywords},${newKeyword}` 
        : newKeyword
      onKeywordsChange(updatedKeywords)
      setInputValue('') // 清空输入框
    }
  }

  // 删除指定关键词
  const handleRemoveKeyword = (index: number) => {
    const newKeywords = keywordList
      .filter((_, i) => i !== index)
      .join(',')
    onKeywordsChange(newKeywords)
  }

  // 处理回车键添加帖子ID
  const handleDetailKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && detailInputValue.trim()) {
      e.preventDefault()
      const newDetail = detailInputValue.trim()
      const updatedDetails = specifiedIds 
        ? `${specifiedIds},${newDetail}` 
        : newDetail
      onSpecifiedIdsChange(updatedDetails)
      setDetailInputValue('') // 清空输入框
    }
  }

  // 删除指定帖子ID
  const handleRemoveDetail = (index: number) => {
    const newDetails = detailList
      .filter((_, i) => i !== index)
      .join(',')
    onSpecifiedIdsChange(newDetails)
  }

  // 处理回车键添加创作者ID
  const handleCreatorKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && creatorInputValue.trim()) {
      e.preventDefault()
      const newCreator = creatorInputValue.trim()
      const updatedCreators = creatorIds 
        ? `${creatorIds},${newCreator}` 
        : newCreator
      onCreatorIdsChange(updatedCreators)
      setCreatorInputValue('') // 清空输入框
    }
  }

  // 删除指定创作者ID
  const handleRemoveCreator = (index: number) => {
    const newCreators = creatorList
      .filter((_, i) => i !== index)
      .join(',')
    onCreatorIdsChange(newCreators)
  }

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Globe className="h-5 w-5 text-blue-400" />
          <div className="flex items-baseline gap-2">
            <CardTitle className="text-base font-medium">目标配置</CardTitle>
            <CardDescription className="text-xs text-muted-foreground/60">
              平台、属性与搜索类型
            </CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* 平台选择 */}
        <div className="space-y-1.5">
          <Label className="text-xs">平台</Label>
          <Select
            value={platform}
            onChange={(e) => onPlatformChange(e.target.value as Platform)}
            disabled={disabled || platforms.length === 0}
          >
            {platforms.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </Select>
        </div>

        {/* 爬取类型和起始页（同一行） */}
        <div className="grid grid-cols-2 gap-3">
          {/* 爬取类型 */}
          <div className="space-y-1.5">
            <Label className="text-xs">爬取类型</Label>
            <Select
              value={crawlerType}
              onChange={(e) => onCrawlerTypeChange(e.target.value as CrawlerType)}
              disabled={disabled || crawlerTypes.length === 0}
            >
              {crawlerTypes.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </Select>
          </div>

          {/* 起始页 */}
          <div className="space-y-1.5">
            <Label className="text-xs">起始页</Label>
            <Input
              type="number"
              value={startPage}
              onChange={(e) => onStartPageChange(Number(e.target.value))}
              disabled={disabled}
              min={1}
              className="h-9"
            />
          </div>
        </div>

        {/* 根据爬取类型显示不同输入 */}
        {crawlerType === 'search' && (
          <div className="space-y-1.5">
            <Label className="text-xs">关键词</Label>
            <p className="text-xs text-muted-foreground mb-1">
              输入关键词按回车添加，多个用逗号分隔
            </p>
            <Input
              placeholder="输入关键词，按回车添加..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeywordKeyDown}
              disabled={disabled}
              className="h-9"
            />
            {/* 显示已添加的关键词标签 */}
            {keywordList.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {keywordList.map((keyword, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center gap-1.5 px-3 py-1 text-sm bg-cyan-400/20 text-cyan-600 dark:text-cyan-400 rounded border border-cyan-400/40 hover:bg-cyan-400/30 transition-colors"
                  >
                    {keyword}
                    <button
                      onClick={() => handleRemoveKeyword(index)}
                      className="text-cyan-600 dark:text-cyan-400 hover:text-cyan-700 dark:hover:text-cyan-300 font-bold"
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

        {crawlerType === 'detail' && (
          <div className="space-y-1.5">
            <Label className="text-xs">帖子ID</Label>
            <p className="text-xs text-muted-foreground mb-1">
              输入帖子ID，按回车添加
            </p>
            <textarea
              placeholder={"示例:\n123456789\n987654321"}
              value={detailInputValue}
              onChange={(e) => setDetailInputValue(e.target.value)}
              onKeyDown={handleDetailKeyDown}
              disabled={disabled}
              className="w-full h-[72px] px-3 py-2 text-sm rounded-md border border-input bg-background font-mono resize-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
            {/* 显示已添加的帖子ID标签 */}
            {detailList.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {detailList.map((detailId, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center gap-1.5 px-3 py-1 text-sm bg-orange-400/20 text-orange-600 dark:text-orange-400 rounded border border-orange-400/40 hover:bg-orange-400/30 transition-colors font-mono"
                  >
                    {detailId}
                    <button
                      onClick={() => handleRemoveDetail(index)}
                      className="text-orange-600 dark:text-orange-400 hover:text-orange-700 dark:hover:text-orange-300 font-bold"
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

        {crawlerType === 'creator' && (
          <div className="space-y-1.5">
            <Label className="text-xs">创作者 ID</Label>
            <p className="text-xs text-muted-foreground mb-1">
              输入创作者的ID/URL，按回车添加
            </p>
            <textarea
              placeholder={"示例:\n5533390220\nhttps://weibo.com/u/5533390220"}
              value={creatorInputValue}
              onChange={(e) => setCreatorInputValue(e.target.value)}
              onKeyDown={handleCreatorKeyDown}
              disabled={disabled}
              className="w-full h-[72px] px-3 py-2 text-sm rounded-md border border-input bg-background font-mono resize-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
            {/* 显示已添加的创作者ID标签 */}
            {creatorList.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {creatorList.map((creatorId, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center gap-1.5 px-3 py-1 text-sm bg-purple-400/20 text-purple-600 dark:text-purple-400 rounded border border-purple-400/40 hover:bg-purple-400/30 transition-colors font-mono"
                  >
                    {creatorId.length > 30 ? `${creatorId.slice(0, 30)}...` : creatorId}
                    <button
                      onClick={() => handleRemoveCreator(index)}
                      className="text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300 font-bold"
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
      </CardContent>
    </Card>
  )
}

