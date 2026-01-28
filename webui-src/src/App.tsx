import { QueryClient, QueryClientProvider, useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { AlertTriangle, LayoutGrid, List, Activity } from 'lucide-react'
import { TargetConfig } from './components/TargetConfig'
import { LoginConfig } from './components/LoginConfig'
import { OutputConfig } from './components/OutputConfig'
import { WeChatConfig } from './components/WeChatConfig'
import { WeChatDashboard } from './components/WeChatDashboard'
import { ProgressPanel } from './components/ProgressPanel'
import { TerminalLog } from './components/TerminalLog'
import { ThemeToggle } from './components/ThemeToggle'
import { ToastContainer, toast } from './components/ui/toast'
import { Button } from './components/ui/button'
import { useCrawlerConfig } from './hooks/useCrawlerConfig'
import { crawlerApi } from './api/crawler'
import { QUERY_CONFIG } from './lib/constants'

// Multi-task imports
import { TaskDashboard } from './components/TaskDashboard'
import { TaskList } from './components/TaskList'
import { TaskDetail } from './components/TaskDetail'
import { TaskCreate } from './components/TaskCreate'
import { useSession } from './hooks/useSession'
import { Task } from './types/task'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: QUERY_CONFIG.RETRY_COUNT,
    },
  },
})

function MultiTaskView() {
  const { session, loading: sessionLoading } = useSession()
  const [view, setView] = useState<'dashboard' | 'list' | 'detail'>('dashboard')
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [createOpen, setCreateOpen] = useState(false)

  if (sessionLoading) {
    return <div className="flex items-center justify-center h-full">Loading session...</div>
  }

  const handleTaskSelect = (task: Task) => {
    setSelectedTask(task)
    setView('detail')
  }

  const handleCreateSuccess = (taskId: string) => {
    // Optionally auto-select the new task or just refresh
    toast.success('任务创建成功')
  }

  return (
    <div className="h-full flex flex-col space-y-4">
      {/* Sub-navigation for Multi-task */}
      {view !== 'detail' && (
        <div className="flex gap-2 border-b pb-2">
          <Button 
            variant={view === 'dashboard' ? 'default' : 'ghost'} 
            size="sm" 
            onClick={() => setView('dashboard')}
          >
            <LayoutGrid className="w-4 h-4 mr-2" />
            仪表盘
          </Button>
          <Button 
            variant={view === 'list' ? 'default' : 'ghost'} 
            size="sm" 
            onClick={() => setView('list')}
          >
            <List className="w-4 h-4 mr-2" />
            任务列表
          </Button>
        </div>
      )}

      <div className="flex-1 overflow-y-auto min-h-0">
        {view === 'dashboard' && (
          <TaskDashboard 
            onTaskSelect={handleTaskSelect}
            onCreateTask={() => setCreateOpen(true)}
          />
        )}
        
        {view === 'list' && (
          <TaskList 
            onTaskSelect={handleTaskSelect}
            onCreateTask={() => setCreateOpen(true)}
          />
        )}
        
        {view === 'detail' && selectedTask && session && (
          <TaskDetail 
            taskId={selectedTask.task_id}
            sessionId={session.session_id}
            onBack={() => {
              setView('dashboard')
              setSelectedTask(null)
            }}
          />
        )}
      </div>

      <TaskCreate 
        open={createOpen} 
        onClose={() => setCreateOpen(false)}
        onCreated={handleCreateSuccess}
      />
    </div>
  )
}

function MainApp() {
  const queryClient = useQueryClient()
  const [mode, setMode] = useState<'classic' | 'multitask'>('classic')
  
  // Classic mode hooks
  const { config, updateConfig, handleCrawlerTypeChange, handleLoginTypeChange } = useCrawlerConfig()
  const { data: statusResponse } = useQuery({
    queryKey: ['crawler-status'],
    queryFn: crawlerApi.getStatus,
    refetchInterval: QUERY_CONFIG.STATUS_REFETCH_INTERVAL,
    enabled: mode === 'classic', // Only fetch in classic mode
  })
  
  const status = statusResponse?.data

  useEffect(() => {
    if (status?.new_cookies && status.new_cookies !== config.cookies) {
      toast.success('已自动捕获并保存登录凭证(Cookie)！')
      updateConfig({ cookies: status.new_cookies })
    }
    if (status?.new_token) {
        console.log('New Token captured:', status.new_token)
        updateConfig({ wechat_token: status.new_token } as any)
    }
  }, [status?.new_cookies, status?.new_token, config.cookies, updateConfig])

  const startMutation = useMutation({
    mutationFn: crawlerApi.start,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crawler-status'] })
      toast.success('爬虫启动成功！')
    },
    onError: (error: Error) => {
      toast.error(`启动失败: ${error.message}`)
    },
  })

  const stopMutation = useMutation({
    mutationFn: crawlerApi.stop,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crawler-status'] })
      toast.info('爬虫已停止')
    },
    onError: (error: Error) => {
      toast.error(`停止失败: ${error.message}`)
    },
  })

  const isRunning = status?.status === 'running'

  const handleStartStop = () => {
    if (isRunning) {
      stopMutation.mutate()
    } else {
      const requestData = { ...config }
      if (config.crawler_type === 'creator_vip') {
        requestData.vip_creator_ids = config.creator_ids
        requestData.creator_ids = ''
      } else if (config.crawler_type === 'creator') {
        requestData.vip_creator_ids = ''
      }
      startMutation.mutate(requestData)
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
            
            {/* 模式切换 */}
            <div className="flex bg-slate-100 dark:bg-slate-800 p-1 rounded-lg ml-4">
              <button 
                onClick={() => setMode('classic')} 
                className={`px-3 py-1 text-xs rounded-md transition-all ${
                  mode === 'classic' 
                    ? 'bg-white dark:bg-slate-700 shadow-sm font-medium text-slate-900 dark:text-white' 
                    : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                }`}
              >
                经典模式
              </button>
              <button 
                onClick={() => setMode('multitask')} 
                className={`px-3 py-1 text-xs rounded-md transition-all ${
                  mode === 'multitask' 
                    ? 'bg-white dark:bg-slate-700 shadow-sm font-medium text-slate-900 dark:text-white' 
                    : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                }`}
              >
                多任务 Pro
              </button>
            </div>
          </div>
          
          {mode === 'classic' && (
            <div className="flex items-center gap-2 px-4 py-2 bg-orange-500/10 border border-orange-500/20 rounded-lg hidden md:flex">
              <AlertTriangle className="h-4 w-4 text-orange-400" />
              <span className="text-xs text-orange-400">
                仅供个人学习研究使用，严禁商用
              </span>
            </div>
          )}

          <div className="flex items-center gap-3 text-sm text-gray-400">
            <ThemeToggle />
            <span className="hidden sm:inline">🌐 中文</span>
            <span className="text-green-400 hidden sm:inline">API: v2.0.0</span>
          </div>
        </div>
      </header>

      {/* 主内容区 */}
      <main className="flex-1 container mx-auto px-6 py-3 overflow-hidden flex flex-col">
        {mode === 'multitask' ? (
          <MultiTaskView />
        ) : (
          /* 经典模式内容 */
          <div className="flex-1 overflow-y-auto">
            {/* 平台选择横条 */}
            <div className="flex items-center gap-2 mb-3 p-2 bg-white/50 dark:bg-slate-900/50 rounded-lg border border-slate-200 dark:border-slate-700 overflow-x-auto">
              <span className="text-sm font-medium text-slate-600 dark:text-slate-400 mr-2 flex-shrink-0">平台:</span>
              {[
                { value: 'xhs', label: '小红书', icon: '🔴' },
                { value: 'dy', label: '抖音', icon: '🎵' },
                { value: 'ks', label: '快手', icon: '⚡' },
                { value: 'bili', label: 'B站', icon: '📺' },
                { value: 'wb', label: '微博', icon: '🔷' },
                { value: 'wechat', label: '微信公众号', icon: '💬' },
                { value: 'tieba', label: '贴吧', icon: '🗣️' },
                { value: 'zhihu', label: '知乎', icon: '💡' },
              ].map((p) => (
                <button
                  key={p.value}
                  onClick={() => updateConfig({ platform: p.value as any })}
                  disabled={isRunning}
                  className={`px-3 py-1.5 text-xs rounded-md transition-all flex-shrink-0 ${
                    config.platform === p.value
                      ? 'bg-gradient-to-r from-cyan-500 to-blue-500 text-white shadow-md'
                      : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
                  } ${isRunning ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  {p.icon} {p.label}
                </button>
              ))}
            </div>

            {/* 进度面板 */}
            <ProgressPanel 
              progress={status?.progress}
              isRunning={isRunning}
              platform={config.platform}
            />

            {/* 微信平台使用全新的仪表盘布局 */}
            {config.platform === 'wechat' ? (
              <WeChatDashboard />
            ) : (
              /* 其他平台使用经典三列布局 */
              <>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
                  {/* 目标配置 */}
                  <TargetConfig
                    crawlerType={config.crawler_type}
                    keywords={config.keywords || ''}
                    specifiedIds={config.specified_ids || ''}
                    creatorIds={config.creator_ids || ''}
                    startPage={config.start_page || 1}
                    disabled={isRunning}
                    onCrawlerTypeChange={handleCrawlerTypeChange}
                    onKeywordsChange={(value) => updateConfig({ keywords: value })}
                    onSpecifiedIdsChange={(value) => updateConfig({ specified_ids: value })}
                    onCreatorIdsChange={(value) => updateConfig({ creator_ids: value })}
                    onStartPageChange={(value) => updateConfig({ start_page: value })}
                  />

                  {/* 登录配置 */}
                  <LoginConfig
                    platform={config.platform}
                    loginType={config.login_type}
                    cookies={config.cookies}
                    disabled={isRunning}
                    onLoginTypeChange={handleLoginTypeChange}
                    onCookiesChange={(value) => updateConfig({ cookies: value })}
                  />

                  {/* 输出配置 */}
                  <OutputConfig
                    platform={config.platform}
                    saveOption={config.save_option || 'json'}
                    enableComments={config.enable_comments || false}
                    enableSubComments={config.enable_sub_comments || false}
                    headless={config.headless || false}
                    enableIncremental={config.enable_incremental || false}
                    incrementalThreshold={config.incremental_early_stop || 3}
                    crawlerType={config.crawler_type}
                    disabled={isRunning}
                    onSaveOptionChange={(value) => updateConfig({ save_option: value })}
                    onEnableCommentsChange={(value) => updateConfig({ enable_comments: value })}
                    onEnableSubCommentsChange={(value) => updateConfig({ enable_sub_comments: value })}
                    onHeadlessChange={(value) => updateConfig({ headless: value })}
                    onEnableIncrementalChange={(value) => updateConfig({ enable_incremental: value })}
                    onIncrementalThresholdChange={(value) => updateConfig({ incremental_early_stop: value })}
                  />
                </div>

                {/* 启动按钮 */}
                <div className="mb-3">
                  <Button
                    onClick={handleStartStop}
                    disabled={startMutation.isPending || stopMutation.isPending}
                    className="w-full h-10 text-base font-medium bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 text-white shadow-lg shadow-cyan-500/20"
                  >
                    {isRunning ? (
                      <>⏸ 停止爬虫</>
                    ) : (
                      <>▶ 开始爬虫</>
                    )}
                  </Button>
                </div>

                {/* 终端日志 */}
                <div className="pb-3">
                  <TerminalLog />
                </div>
              </>
            )}
          </div>
        )}
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
      <ToastContainer />
    </QueryClientProvider>
  )
}

export default App
