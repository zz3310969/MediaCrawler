import React, { useState } from 'react'
import { 
  Search, User, FileText, BookOpen, 
  Play, Square, RefreshCw, Eye,
  LayoutGrid, List, PlusCircle, CheckCircle, BarChart2
} from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { crawlerApi } from '@/api/crawler'
import { useCrawlerConfig } from '@/hooks/useCrawlerConfig'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar'
import { toast } from '@/components/ui/toast'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { LoginConfig } from './LoginConfig'
import { TerminalLog } from './TerminalLog'
import { WeChatDataList } from './WeChatDataList'
import { WeChatAnalysis } from './WeChatAnalysis'
import { useMutation, useQueryClient } from '@tanstack/react-query'

// 模拟数据类型
// interface Article {
//   id: string
//   title: string
//   account: string
//   readCount: number
//   likeCount: number
//   commentCount: number
//   pubDate: string
//   url: string
// }

// 模拟数据
// const MOCK_DATA: Article[] = [
//   { id: '1', title: '2025年人工智能发展趋势报告', account: 'AI前线', readCount: 100000, likeCount: 2345, commentCount: 120, pubDate: '2025-01-27', url: '#' },
//   { id: '2', title: 'Python 3.13 新特性解析', account: 'Python开发者', readCount: 45000, likeCount: 890, commentCount: 45, pubDate: '2025-01-26', url: '#' },
// ]

export function WeChatDashboard() {
  const [activeTab, setActiveTab] = useState('data')
  const [isRunning, setIsRunning] = useState(false)
  const [mode, setMode] = useState('search')
  const { config, updateConfig } = useCrawlerConfig()
  const queryClient = useQueryClient()
  const [loginDialogOpen, setLoginDialogOpen] = useState(false)
  
  // 查询爬虫状态，用于监听登录完成
  const { data: statusResponse } = useQuery({
    queryKey: ['crawler-status'],
    queryFn: crawlerApi.getStatus,
    refetchInterval: isRunning ? 1000 : 5000, // 运行时更频繁轮询
  })
  
  const status = statusResponse?.data
  
  // 监听登录状态变化，自动更新 Cookie 和 Token
  React.useEffect(() => {
    if (status?.new_cookies && status.new_cookies !== config.cookies) {
      toast.success('登录成功！Cookie 已自动保存')
      updateConfig({ cookies: status.new_cookies })
    }
    if (status?.new_token && status.new_token !== config.wechat_token) {
      toast.success('Token 已自动保存')
      updateConfig({ wechat_token: status.new_token })
    }
    // 如果状态变为 idle 且之前是 running，说明登录流程结束
    if (status?.status === 'idle' && isRunning) {
      setIsRunning(false)
      setLoginDialogOpen(false) // 自动关闭登录对话框
    }
  }, [status?.new_cookies, status?.new_token, status?.status, config.cookies, config.wechat_token, isRunning, updateConfig])
  
  // 启动爬虫 Mutation（用于登录）
  const startMutation = useMutation({
    mutationFn: crawlerApi.start,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crawler-status'] })
      setIsRunning(true)
      toast.success('登录浏览器已启动，请在弹出的窗口中扫码')
    },
    onError: (error: Error) => {
      toast.error(`启动失败: ${error.message}`)
    },
  })

  // 启动采集 Mutation
  const startCrawlMutation = useMutation({
    mutationFn: crawlerApi.start,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crawler-status'] })
      setIsRunning(true)
      toast.success('采集任务已启动')
    },
    onError: (error: Error) => {
      toast.error(`启动失败: ${error.message}`)
    },
  })

  // 停止爬虫 Mutation
  const stopMutation = useMutation({
    mutationFn: crawlerApi.stop,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crawler-status'] })
      setIsRunning(false)
      toast.success('采集任务已停止')
    },
    onError: (error: Error) => {
      toast.error(`停止失败: ${error.message}`)
    },
  })

  // 处理开始/停止采集
  const handleStartStopCrawl = () => {
    if (isRunning) {
      // 停止采集
      stopMutation.mutate()
    } else {
      // 检查是否已登录
      if (!config.cookies || !config.wechat_token) {
        toast.error('请先登录微信公众号平台')
        return
      }
      
      // 根据当前模式构建配置
      const crawlerType = mode === 'search' ? 'search' : 
                          mode === 'account' ? 'creator' :
                          mode === 'article' ? 'detail' : 'album'
      
      const crawlConfig = {
        ...config,
        platform: 'wechat' as const,
        login_type: 'cookie' as const, // 使用已保存的 Cookie 登录
        crawler_type: crawlerType as 'search' | 'detail' | 'creator' | 'album',
        headless: true, // 采集时可以使用无头模式
        login_only: false, // 需要进行数据采集
      }
      
      startCrawlMutation.mutate(crawlConfig)
    }
  }

  // 启动登录流程
  const handleStartLogin = () => {
    // 强制使用非无头模式启动，确保浏览器窗口能弹出来
    const loginConfig = {
      ...config,
      platform: 'wechat' as const,
      login_type: 'mp_qrcode' as const,
      crawler_type: 'search' as const, // 登录时默认用 search 模式占位
      headless: false, // 关键：强制有头模式
      login_only: true, // 关键：只登录获取 Cookie/Token，不进行数据爬取
    }
    startMutation.mutate(loginConfig)
  }
  
  // 搜索相关状态
  const [searchKeyword, setSearchKeyword] = useState('')
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [isSearching, setIsSearching] = useState(false)

  // 处理搜索
  const handleSearch = async () => {
    if (!searchKeyword.trim()) return
    if (!config.cookies || !config.wechat_token) {
      toast.error('请先登录微信公众号平台以获取 Token')
      return
    }

    setIsSearching(true)
    try {
      const res = await crawlerApi.searchWeChatAccount(
        searchKeyword, 
        config.cookies, 
        config.wechat_token
      )
      
      // 解析搜索结果
      // 微信返回的结构通常在 list 字段中
      if (res?.data?.list) {
         setSearchResults(res.data.list)
      } else {
         toast.info('未搜索到相关公众号')
         setSearchResults([])
      }
    } catch (error: any) {
      console.error(error)
      toast.error(error.message || '搜索失败，请检查 Cookie/Token 是否过期')
    } finally {
      setIsSearching(false)
    }
  }

  // 添加公众号到配置
  const handleAddAccount = (account: any) => {
    // fakeid 是公众号的唯一标识 (base64编码)
    const fakeid = account.fakeid
    const nickname = account.nickname
    
    if (!fakeid) return

    const currentIds = config.creator_ids ? config.creator_ids.split(',') : []
    if (!currentIds.includes(fakeid)) {
       const newIds = [...currentIds, fakeid].join(',')
       updateConfig({ creator_ids: newIds })
       toast.success(`已添加公众号：${nickname}`)
    } else {
       toast.info(`公众号 ${nickname} 已在列表中`)
    }
  }

  return (
    <div className="flex h-[calc(100vh-60px)] gap-4 p-4 bg-slate-50/50 dark:bg-slate-950/50">
      
      {/* 左侧控制栏 Sidebar */}
      <div className="w-[360px] flex-shrink-0 flex flex-col gap-4">
        
        {/* 状态与控制卡片 */}
        <Card className="flex-1 flex flex-col shadow-md border-slate-200 dark:border-slate-800">
          <CardHeader className="pb-2 bg-slate-50 dark:bg-slate-900/50 rounded-t-lg border-b">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className={`h-2 w-2 rounded-full ${isRunning ? 'bg-green-500 animate-pulse' : 'bg-slate-300'}`}></div>
                <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
                  {isRunning ? '服务运行中' : '服务空闲'}
                </span>
              </div>
              {config.cookies && config.wechat_token ? (
                  <Badge variant="outline" className="text-xs bg-white dark:bg-slate-800 text-green-600 border-green-200">
                     <CheckCircle className="h-3 w-3 mr-1" /> 已登录
                  </Badge>
              ) : (
                  <Dialog open={loginDialogOpen} onOpenChange={setLoginDialogOpen}>
                    <DialogTrigger asChild>
                      <Badge variant="outline" className="text-xs bg-white dark:bg-slate-800 text-slate-500 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-900">
                         未登录 (点击登录)
                      </Badge>
                    </DialogTrigger>
                    <DialogContent className="max-w-[400px]">
                      <DialogHeader>
                        <DialogTitle>登录微信公众平台</DialogTitle>
                      </DialogHeader>
                      <div className="space-y-4">
                        <div className="h-[300px]">
                          <LoginConfig
                            platform="wechat"
                            loginType={config.login_type}
                            cookies={config.cookies}
                            disabled={isRunning}
                            onLoginTypeChange={(value) => updateConfig({ login_type: value })}
                            onCookiesChange={(value) => updateConfig({ cookies: value })}
                          />
                        </div>
                        
                        {/* 只有在扫码模式下才显示启动按钮 */}
                        {config.login_type === 'mp_qrcode' && (
                          <Button 
                            className="w-full bg-green-600 hover:bg-green-700 text-white"
                            onClick={handleStartLogin}
                            disabled={isRunning || startMutation.isPending}
                          >
                            {isRunning ? '正在运行...' : (
                              <>
                                <Play className="mr-2 h-4 w-4" /> 启动登录浏览器
                              </>
                            )}
                          </Button>
                        )}
                      </div>
                    </DialogContent>
                  </Dialog>
              )}
            </div>
          </CardHeader>
          
          <CardContent className="flex-1 overflow-y-auto p-4 space-y-6">
            
            {/* 模式选择 */}
            <div className="space-y-3">
              <Label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">采集模式</Label>
              <div className="grid grid-cols-4 gap-1 p-1 bg-slate-100 dark:bg-slate-800 rounded-lg">
                {[
                  { id: 'search', icon: Search, label: '搜索' },
                  { id: 'account', icon: User, label: '账号' },
                  { id: 'article', icon: FileText, label: '文章' },
                  { id: 'album', icon: BookOpen, label: '合集' }
                ].map(m => (
                  <button
                    key={m.id}
                    onClick={() => setMode(m.id)}
                    className={`flex flex-col items-center justify-center py-2 rounded-md text-xs transition-all ${
                      mode === m.id 
                        ? 'bg-white dark:bg-slate-700 shadow-sm text-green-600 font-medium' 
                        : 'text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-700'
                    }`}
                  >
                    <m.icon className="h-4 w-4 mb-1" />
                    {m.label}
                  </button>
                ))}
              </div>
            </div>

            {/* 搜索模式专属：交互式搜索 */}
            {mode === 'account' && (
              <div className="space-y-3 animate-in fade-in slide-in-from-top-2">
                 <Label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    搜索公众号 (API)
                 </Label>
                 <div className="flex gap-2">
                    <Input 
                       value={searchKeyword}
                       onChange={(e) => setSearchKeyword(e.target.value)}
                       onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                       placeholder="输入公众号名称..."
                       className="bg-slate-50 dark:bg-slate-900 h-9 text-sm"
                    />
                    <Button 
                       size="sm" 
                       onClick={handleSearch}
                       disabled={isSearching}
                       className="bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900"
                    >
                       {isSearching ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                    </Button>
                 </div>
                 
                 {/* 搜索结果列表 */}
                 {searchResults.length > 0 && (
                    <div className="border rounded-md max-h-[200px] overflow-y-auto bg-white dark:bg-slate-900">
                       {searchResults.map((item: any, idx) => (
                          <div 
                            key={idx} 
                            className="flex items-center justify-between p-2 hover:bg-slate-50 dark:hover:bg-slate-800 border-b last:border-0"
                          >
                             <div className="flex items-center gap-2 overflow-hidden">
                                <Avatar className="h-8 w-8 rounded-full border">
                                   <AvatarImage src={item.round_head_img} />
                                   <AvatarFallback>{item.nickname?.[0]}</AvatarFallback>
                                </Avatar>
                                <div className="min-w-0">
                                   <div className="text-xs font-medium truncate" title={item.nickname}>
                                      <span dangerouslySetInnerHTML={{ __html: item.nickname }}></span>
                                   </div>
                                   <div className="text-[10px] text-muted-foreground truncate" title={item.alias}>
                                      {item.alias}
                                   </div>
                                </div>
                             </div>
                             <Button 
                                size="sm" 
                                variant="ghost" 
                                className="h-7 w-7 p-0 text-green-600 hover:text-green-700 hover:bg-green-50"
                                onClick={() => handleAddAccount(item)}
                                title="添加到采集列表"
                             >
                                <PlusCircle className="h-4 w-4" />
                             </Button>
                          </div>
                       ))}
                    </div>
                 )}
              </div>
            )}

            {/* 动态输入区 */}
            <div className="space-y-3">
              <Label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                {mode === 'search' && '关键词配置'}
                {mode === 'account' && '目标账号列表 (fakeid)'}
                {mode === 'article' && '文章链接'}
                {mode === 'album' && '合集配置'}
              </Label>
              <div className="space-y-2">
                <Input 
                  value={
                      mode === 'search' ? config.keywords :
                      mode === 'account' ? config.creator_ids :
                      mode === 'article' ? config.specified_ids : config.wechat_album_ids
                  }
                  onChange={(e) => {
                      const val = e.target.value
                      if (mode === 'search') updateConfig({ keywords: val })
                      else if (mode === 'account') updateConfig({ creator_ids: val })
                      else if (mode === 'article') updateConfig({ specified_ids: val })
                      else if (mode === 'album') updateConfig({ wechat_album_ids: val })
                  }}
                  placeholder={
                    mode === 'search' ? "输入关键词，回车添加..." :
                    mode === 'account' ? "输入公众号 Biz ID..." :
                    mode === 'article' ? "粘贴文章 URL..." : "输入合集 ID..."
                  }
                  className="bg-slate-50 dark:bg-slate-900 border-slate-200"
                />
                
                {/* 已添加的标签展示 (简单版) */}
                <div className="text-[10px] text-muted-foreground">
                   {mode === 'account' && "可直接输入 ID，或使用上方搜索功能添加"}
                </div>
              </div>
            </div>

            <Separator />

            {/* 采集选项 */}
            <div className="space-y-3">
              <Label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">数据选项</Label>
              <div className="space-y-2">
                <div className="flex items-center justify-between p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-slate-400" />
                    <span className="text-sm">正文内容 (HTML)</span>
                  </div>
                  <Switch 
                    id="content" 
                    checked={config.wechat_enable_content}
                    onCheckedChange={(c) => updateConfig({ wechat_enable_content: c })}
                  />
                </div>
                <div className="flex items-center justify-between p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors">
                  <div className="flex items-center gap-2">
                    <Eye className="h-4 w-4 text-slate-400" />
                    <span className="text-sm">阅读量/点赞</span>
                  </div>
                  <Switch 
                    id="stats" 
                    checked={config.wechat_enable_reading_stats}
                    onCheckedChange={(c) => updateConfig({ wechat_enable_reading_stats: c })}
                  />
                </div>
              </div>
            </div>

          </CardContent>

          <div className="p-4 border-t bg-slate-50 dark:bg-slate-900/50 rounded-b-lg">
            <Button 
              className={`w-full h-11 text-base font-medium shadow-lg transition-all ${
                isRunning 
                  ? 'bg-red-500 hover:bg-red-600 shadow-red-500/20' 
                  : 'bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 shadow-green-500/20'
              }`}
              onClick={handleStartStopCrawl}
              disabled={startCrawlMutation.isPending || stopMutation.isPending}
            >
              {isRunning ? (
                <>
                  <Square className="mr-2 h-4 w-4 fill-current" /> 停止采集
                </>
              ) : (
                <>
                  <Play className="mr-2 h-4 w-4 fill-current" /> 开始采集
                </>
              )}
            </Button>
          </div>
        </Card>
      </div>

      {/* 右侧工作区 Workspace */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col overflow-hidden">
          {/* Tab 头部 - 固定 */}
          <div className="flex-shrink-0 flex items-center justify-between mb-3">
            <TabsList className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 shadow-sm p-1 h-10">
              <TabsTrigger 
                value="data" 
                className="gap-2 px-4 data-[state=active]:bg-green-50 data-[state=active]:text-green-700 dark:data-[state=active]:bg-green-950/30 dark:data-[state=active]:text-green-400"
              >
                <LayoutGrid className="h-4 w-4" /> 数据管理
              </TabsTrigger>
              <TabsTrigger 
                value="analysis" 
                className="gap-2 px-4 data-[state=active]:bg-green-50 data-[state=active]:text-green-700 dark:data-[state=active]:bg-green-950/30 dark:data-[state=active]:text-green-400"
              >
                <BarChart2 className="h-4 w-4" /> 统计分析
              </TabsTrigger>
              <TabsTrigger 
                value="log" 
                className="gap-2 px-4 data-[state=active]:bg-green-50 data-[state=active]:text-green-700 dark:data-[state=active]:bg-green-950/30 dark:data-[state=active]:text-green-400"
              >
                <List className="h-4 w-4" /> 运行日志
              </TabsTrigger>
            </TabsList>
          </div>

          {/* Tab 内容区 - 可滚动 */}
          <TabsContent value="data" className="flex-1 min-h-0 mt-0 overflow-hidden">
            <WeChatDataList />
          </TabsContent>

          <TabsContent value="analysis" className="flex-1 min-h-0 mt-0 overflow-hidden">
            <div className="h-full overflow-y-auto scrollbar-thin scrollbar-thumb-slate-300 dark:scrollbar-thumb-slate-600 scrollbar-track-transparent pr-2">
              <WeChatAnalysis />
            </div>
          </TabsContent>

          <TabsContent value="log" className="flex-1 min-h-0 mt-0 overflow-hidden">
            <Card className="h-full border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden flex flex-col">
              <TerminalLog />
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

