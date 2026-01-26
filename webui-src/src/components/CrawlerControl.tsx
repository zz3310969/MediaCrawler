// 爬虫控制面板
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Play, Square, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { crawlerApi, type CrawlerStartRequest, type Platform, type LoginType, type CrawlerType } from '@/api/crawler'

const PLATFORMS = [
  { value: 'xhs', label: '小红书', icon: '🔴' },
  { value: 'dy', label: '抖音', icon: '🎵' },
  { value: 'ks', label: '快手', icon: '⚡' },
  { value: 'bili', label: 'B站', icon: '📺' },
  { value: 'wb', label: '微博', icon: '🔷' },
  { value: 'tieba', label: '贴吧', icon: '🗣️' },
  { value: 'zhihu', label: '知乎', icon: '💡' },
] as const

export function CrawlerControl() {
  const queryClient = useQueryClient()
  
  // 表单状态
  const [config, setConfig] = useState<CrawlerStartRequest>({
    platform: 'xhs',
    login_type: 'qrcode',
    crawler_type: 'search',
    keywords: '',
    start_page: 1,
    enable_comments: true,
    enable_sub_comments: false,
    save_option: 'json',
    headless: false,
  })

  // 查询爬虫状态
  const { data: statusResponse } = useQuery({
    queryKey: ['crawler-status'],
    queryFn: crawlerApi.getStatus,
    refetchInterval: 1000,
  })
  
  const status = statusResponse?.data

  // 启动爬虫
  const startMutation = useMutation({
    mutationFn: crawlerApi.start,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crawler-status'] })
    },
    onError: (error: Error) => {
      alert('启动失败: ' + error.message)
    },
  })

  // 停止爬虫
  const stopMutation = useMutation({
    mutationFn: crawlerApi.stop,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crawler-status'] })
    },
    onError: (error: Error) => {
      alert('停止失败: ' + error.message)
    },
  })

  const handleStart = () => {
    startMutation.mutate(config)
  }

  const handleStop = () => {
    stopMutation.mutate()
  }

  const isRunning = status?.status === 'running'
  const isIdle = status?.status === 'idle'

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span>爬虫控制台</span>
          {isRunning && <Loader2 className="h-4 w-4 animate-spin text-green-500" />}
          <Badge variant={isRunning ? 'default' : 'secondary'}>
            {status?.status === 'running' ? '运行中' : 
             status?.status === 'stopping' ? '停止中' : 
             status?.status === 'error' ? '错误' : '空闲'}
          </Badge>
        </CardTitle>
        <CardDescription>
          配置并启动爬虫任务
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* 平台选择 */}
        <div className="space-y-2">
          <Label>选择平台</Label>
          <Select
            value={config.platform}
            onChange={(e) => setConfig({ ...config, platform: e.target.value as Platform })}
            disabled={isRunning}
          >
            {PLATFORMS.map((platform) => (
              <option key={platform.value} value={platform.value}>
                {platform.icon} {platform.label}
              </option>
            ))}
          </Select>
        </div>

        {/* 登录方式 */}
        <div className="space-y-2">
          <Label>登录方式</Label>
          <Select
            value={config.login_type}
            onChange={(e) => setConfig({ ...config, login_type: e.target.value as LoginType })}
            disabled={isRunning}
          >
            <option value="qrcode">扫码登录</option>
            <option value="phone">手机号登录</option>
            <option value="cookie">Cookie登录</option>
          </Select>
        </div>

        {/* 爬取类型 */}
        <div className="space-y-2">
          <Label>爬取类型</Label>
          <Select
            value={config.crawler_type}
            onChange={(e) => setConfig({ ...config, crawler_type: e.target.value as CrawlerType })}
            disabled={isRunning}
          >
            <option value="search">关键词搜索</option>
            <option value="detail">指定帖子详情</option>
            <option value="creator">创作者主页</option>
          </Select>
        </div>

        {/* 关键词输入 */}
        {config.crawler_type === 'search' && (
          <div className="space-y-2">
            <Label>搜索关键词</Label>
            <Input
              placeholder="输入搜索关键词，多个关键词用逗号分隔"
              value={config.keywords}
              onChange={(e) => setConfig({ ...config, keywords: e.target.value })}
              disabled={isRunning}
            />
          </div>
        )}

        {/* 指定ID */}
        {config.crawler_type === 'detail' && (
          <div className="space-y-2">
            <Label>帖子ID列表</Label>
            <Input
              placeholder="输入帖子ID，多个ID用逗号分隔"
              value={config.specified_ids}
              onChange={(e) => setConfig({ ...config, specified_ids: e.target.value })}
              disabled={isRunning}
            />
          </div>
        )}

        {/* 创作者ID */}
        {config.crawler_type === 'creator' && (
          <div className="space-y-2">
            <Label>创作者ID列表</Label>
            <Input
              placeholder="输入创作者ID，多个ID用逗号分隔"
              value={config.creator_ids}
              onChange={(e) => setConfig({ ...config, creator_ids: e.target.value })}
              disabled={isRunning}
            />
          </div>
        )}

        {/* 高级选项 */}
        <div className="space-y-3 pt-4 border-t">
          <div className="flex items-center justify-between">
            <Label htmlFor="enable-comments">爬取评论</Label>
            <Switch
              id="enable-comments"
              checked={config.enable_comments}
              onCheckedChange={(checked) => setConfig({ ...config, enable_comments: checked })}
              disabled={isRunning}
            />
          </div>

          <div className="flex items-center justify-between">
            <Label htmlFor="enable-sub-comments">爬取二级评论</Label>
            <Switch
              id="enable-sub-comments"
              checked={config.enable_sub_comments}
              onCheckedChange={(checked) => setConfig({ ...config, enable_sub_comments: checked })}
              disabled={isRunning}
            />
          </div>

          <div className="flex items-center justify-between">
            <Label htmlFor="headless">无头模式</Label>
            <Switch
              id="headless"
              checked={config.headless}
              onCheckedChange={(checked) => setConfig({ ...config, headless: checked })}
              disabled={isRunning}
            />
          </div>
        </div>

        {/* 操作按钮 */}
        <div className="flex gap-2 pt-4">
          <Button
            className="flex-1"
            onClick={handleStart}
            disabled={!isIdle || startMutation.isPending}
          >
            {startMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                启动中...
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                启动爬虫
              </>
            )}
          </Button>

          <Button
            variant="destructive"
            onClick={handleStop}
            disabled={!isRunning || stopMutation.isPending}
          >
            {stopMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                停止中...
              </>
            ) : (
              <>
                <Square className="mr-2 h-4 w-4" />
                停止
              </>
            )}
          </Button>
        </div>

        {/* 错误信息 */}
        {status?.error_message && (
          <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-md text-red-400 text-sm">
            {status.error_message}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

