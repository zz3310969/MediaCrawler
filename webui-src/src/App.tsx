import { useState } from 'react'
import { QueryClient, QueryClientProvider, useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Play, AlertTriangle } from 'lucide-react'
import { TargetConfig } from './components/TargetConfig'
import { LoginConfig } from './components/LoginConfig'
import { OutputConfig } from './components/OutputConfig'
import { TerminalLog } from './components/TerminalLog'
import { ThemeToggle } from './components/ThemeToggle'
import { Button } from './components/ui/button'
import { crawlerApi, type CrawlerStartRequest, type Platform, type LoginType, type CrawlerType, type SaveOption } from './api/crawler'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

function MainApp() {
  const queryClient = useQueryClient()
  
  // 爬虫配置状态
  const [config, setConfig] = useState<CrawlerStartRequest>({
    platform: 'bili',
    login_type: 'qrcode',
    crawler_type: 'search',
    keywords: '',
    specified_ids: '',
    creator_ids: '',
    start_page: 1,
    enable_comments: true,
    enable_sub_comments: false,
    save_option: 'json',
    cookies: '',
    headless: false,
  })

  // 处理爬取类型变化，清空相关字段
  const handleCrawlerTypeChange = (value: CrawlerType) => {
    setConfig({
      ...config,
      crawler_type: value,
      keywords: '',
      specified_ids: '',
      creator_ids: '',
    })
  }

  // 处理登录方式变化
  const handleLoginTypeChange = (value: LoginType) => {
    setConfig({
      ...config,
      login_type: value,
      cookies: value === 'cookie' ? config.cookies : '',
    })
  }

  // 查询爬虫状态
  const { data: status } = useQuery({
    queryKey: ['crawler-status'],
    queryFn: crawlerApi.getStatus,
    refetchInterval: 1000,
  })

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
  })

  const isRunning = status?.status === 'running'
  const isIdle = status?.status === 'idle'

  const handleStartStop = () => {
    if (isRunning) {
      stopMutation.mutate()
    } else {
      startMutation.mutate(config)
    }
  }

  return (
    <div className="h-screen flex flex-col bg-gradient-to-br from-slate-50 via-slate-100 to-slate-50 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 overflow-hidden">
      {/* 顶部导航 */}
      <header className="flex-shrink-0 border-b border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-slate-950/50 backdrop-blur">
        <div className="container mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
              <span className="text-2xl">🕷️</span>
              <span>MediaCrawler</span>
            </h1>
            <button className="px-3 py-1 text-xs border border-gray-300 dark:border-gray-700 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400">
              ⭐ Star
            </button>
          </div>
          
          {/* 警告横幅 */}
          <div className="flex items-center gap-2 px-4 py-2 bg-orange-500/10 border border-orange-500/20 rounded-lg">
            <AlertTriangle className="h-4 w-4 text-orange-400" />
            <span className="text-xs text-orange-400">
              1. 本项目仅供个人学习研究使用 &nbsp;&nbsp; 2. 严禁将其用于任何商业用途或违法活动
            </span>
          </div>

          <div className="flex items-center gap-3 text-sm text-gray-400">
            <ThemeToggle />
            <span>🌐 中文</span>
            <span className="text-green-400">API: v1.0.0</span>
            <span className="flex items-center gap-1">
              本地 <span className="w-2 h-2 bg-green-500 rounded-full"></span>
            </span>
          </div>
        </div>
      </header>

      {/* 主内容区 */}
      <main className="flex-1 container mx-auto px-6 py-4 overflow-y-auto">
        {/* 三列配置卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          {/* 目标配置 */}
          <TargetConfig
            platform={config.platform}
            crawlerType={config.crawler_type}
            keywords={config.keywords}
            specifiedIds={config.specified_ids}
            creatorIds={config.creator_ids}
            startPage={config.start_page}
            disabled={isRunning}
            onPlatformChange={(value) => setConfig({ ...config, platform: value })}
            onCrawlerTypeChange={handleCrawlerTypeChange}
            onKeywordsChange={(value) => setConfig({ ...config, keywords: value })}
            onSpecifiedIdsChange={(value) => setConfig({ ...config, specified_ids: value })}
            onCreatorIdsChange={(value) => setConfig({ ...config, creator_ids: value })}
            onStartPageChange={(value) => setConfig({ ...config, start_page: value })}
          />

          {/* 登录配置 */}
          <LoginConfig
            loginType={config.login_type}
            cookies={config.cookies}
            disabled={isRunning}
            onLoginTypeChange={handleLoginTypeChange}
            onCookiesChange={(value) => setConfig({ ...config, cookies: value })}
          />

          {/* 输出配置 */}
          <OutputConfig
            saveOption={config.save_option}
            enableComments={config.enable_comments}
            enableSubComments={config.enable_sub_comments}
            headless={config.headless}
            disabled={isRunning}
            onSaveOptionChange={(value) => setConfig({ ...config, save_option: value })}
            onEnableCommentsChange={(value) => setConfig({ ...config, enable_comments: value })}
            onEnableSubCommentsChange={(value) => setConfig({ ...config, enable_sub_comments: value })}
            onHeadlessChange={(value) => setConfig({ ...config, headless: value })}
          />
        </div>

        {/* 启动按钮 */}
        <div className="mb-4">
          <Button
            onClick={handleStartStop}
            disabled={startMutation.isPending || stopMutation.isPending}
            className="w-full h-12 text-lg font-medium bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 text-white shadow-lg shadow-cyan-500/20"
          >
            {isRunning ? (
              <>⏸ 停止爬虫</>
            ) : (
              <>▶ 开始爬虫</>
            )}
          </Button>
        </div>

        {/* 终端日志 - 自适应剩余高度 */}
        <div className="pb-4">
          <TerminalLog />
        </div>
      </main>

      {/* 底部 */}
      <footer className="flex-shrink-0 border-t border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-slate-950/50 backdrop-blur">
        <div className="container mx-auto px-6 py-2 text-center text-slate-400 dark:text-slate-500 text-xs">
          MediaCrawler © 2025 - 仅供学习研究使用
        </div>
      </footer>
    </div>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <MainApp />
    </QueryClientProvider>
  )
}

export default App
