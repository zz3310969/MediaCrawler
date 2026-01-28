import React, { useState, useRef, useEffect } from 'react'
import { 
  Search, RefreshCw, User, Plus, Trash2, 
  MoreHorizontal, Play, CheckCircle, AlertCircle
} from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { crawlerApi, WeChatAccountItem } from '@/api/crawler'
import { useCrawlerConfig } from '@/hooks/useCrawlerConfig'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog"
import { toast } from '@/components/ui/toast'

export function WeChatAccountManager() {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedAccounts, setSelectedAccounts] = useState<Set<string>>(new Set())
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false)
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
  const [accountToDelete, setAccountToDelete] = useState<WeChatAccountItem | null>(null)
  const [deleteData, setDeleteData] = useState(false)
  const [searchAccountKeyword, setSearchAccountKeyword] = useState('')
  const [searchAccountResults, setSearchAccountResults] = useState<any[]>([])
  const [isSearchingAccount, setIsSearchingAccount] = useState(false)
  
  const queryClient = useQueryClient()
  const { config, updateConfig } = useCrawlerConfig()

  // 获取公众号列表
  const { data: accountsData, isLoading, refetch } = useQuery({
    queryKey: ['wechat-accounts'],
    queryFn: () => crawlerApi.getWeChatAccounts(),
  })
  const accounts = accountsData?.data || []

  // 过滤账号
  const filteredAccounts = accounts.filter((account: WeChatAccountItem) => 
    account.account_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (account.alias && account.alias.toLowerCase().includes(searchTerm.toLowerCase()))
  )

  // 添加公众号 Mutation
  const addAccountMutation = useMutation({
    mutationFn: crawlerApi.addWeChatAccount,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wechat-accounts'] })
      toast.success('添加成功')
      // 不关闭对话框，方便继续添加
    },
    onError: (error: Error) => {
      toast.error(`添加失败: ${error.message}`)
    },
  })

  // 删除公众号 Mutation
  const deleteAccountMutation = useMutation({
    mutationFn: (data: { fakeid: string, deleteData: boolean }) => 
      crawlerApi.deleteWeChatAccount(data.fakeid, data.deleteData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wechat-accounts'] })
      toast.success('删除成功')
      setIsDeleteDialogOpen(false)
      setAccountToDelete(null)
      setSelectedAccounts(new Set())
    },
    onError: (error: Error) => {
      toast.error(`删除失败: ${error.message}`)
    },
  })

  // 启动采集 Mutation
  const startCrawlMutation = useMutation({
    mutationFn: crawlerApi.start,
    onSuccess: () => {
      toast.success('采集任务已启动')
    },
    onError: (error: Error) => {
      toast.error(`启动失败: ${error.message}`)
    },
  })

  // 搜索公众号 (API)
  const handleSearchAccount = async () => {
    if (!searchAccountKeyword.trim()) return
    if (!config.cookies || !config.wechat_token) {
      toast.error('请先登录微信公众号平台')
      return
    }

    setIsSearchingAccount(true)
    try {
      const res = await crawlerApi.searchWeChatAccount(
        searchAccountKeyword, 
        config.cookies, 
        config.wechat_token
      )
      
      if (res?.data?.list) {
         setSearchAccountResults(res.data.list)
      } else {
         toast.info('未搜索到相关公众号')
         setSearchAccountResults([])
      }
    } catch (error: any) {
      console.error(error)
      toast.error(error.message || '搜索失败')
    } finally {
      setIsSearchingAccount(false)
    }
  }

  // 处理添加账号
  const handleAddAccount = (item: any) => {
    addAccountMutation.mutate({
      fakeid: item.fakeid,
      nickname: item.nickname,
      alias: item.alias,
      round_head_img: item.round_head_img,
      service_type: item.service_type,
      // 传递认证信息以获取文章总数
      cookies: config.cookies,
      token: config.wechat_token
    })
  }

  // 处理单个账号采集
  const handleSyncAccount = (account: WeChatAccountItem) => {
    if (!config.cookies || !config.wechat_token) {
      toast.error('请先登录')
      return
    }

    const crawlConfig = {
      ...config,
      platform: 'wechat' as const,
      login_type: 'cookie' as const,
      crawler_type: 'creator' as const, // 使用 creator 模式采集指定账号
      creator_ids: account.fakeid, // 只采集当前账号
      headless: true,
      login_only: false,
    }
    
    startCrawlMutation.mutate(crawlConfig)
  }

  // 处理批量采集
  const handleBatchSync = () => {
    if (selectedAccounts.size === 0) return
    if (!config.cookies || !config.wechat_token) {
      toast.error('请先登录')
      return
    }

    const crawlConfig = {
      ...config,
      platform: 'wechat' as const,
      login_type: 'cookie' as const,
      crawler_type: 'creator' as const,
      creator_ids: Array.from(selectedAccounts).join(','),
      headless: true,
      login_only: false,
    }
    
    startCrawlMutation.mutate(crawlConfig)
  }

  // 格式化时间
  const formatTime = (timestamp?: number) => {
    if (!timestamp) return '-'
    return new Date(timestamp * 1000).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="h-full flex flex-col bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
      
      {/* 工具栏 */}
      <div className="flex-shrink-0 flex items-center justify-between gap-4 px-4 py-3 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
        <div className="flex items-center gap-3 flex-1">
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input 
              placeholder="搜索公众号..." 
              className="pl-9 h-9 bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <Button 
            className="h-9 gap-2 bg-green-600 hover:bg-green-700 text-white"
            onClick={() => setIsAddDialogOpen(true)}
          >
            <Plus className="h-4 w-4" /> 添加公众号
          </Button>
        </div>
        
        <div className="flex items-center gap-2">
          {/* 增量爬取开关 */}
          <label
            className="flex items-center gap-2 px-3 py-1.5 bg-cyan-500/10 border border-cyan-500/20 rounded-md cursor-pointer hover:bg-cyan-500/15 transition-colors"
            title="增量爬取：只同步新文章，跳过已存在的文章"
          >
            <input
              type="checkbox"
              checked={config.enable_incremental || false}
              onChange={(e) => updateConfig({ enable_incremental: e.target.checked })}
              className="w-4 h-4 rounded border-cyan-600 bg-cyan-700 cursor-pointer"
            />
            <span className="text-sm flex items-center gap-1">
              <span>⚡</span>
              <span className="text-cyan-700 dark:text-cyan-400">增量同步</span>
            </span>
          </label>
          
          {/* 采集正文内容开关 */}
          <label
            className="flex items-center gap-2 px-3 py-1.5 bg-orange-500/10 border border-orange-500/20 rounded-md cursor-pointer hover:bg-orange-500/15 transition-colors"
            title="采集正文内容：下载文章HTML正文（会增加采集时间）"
          >
            <input
              type="checkbox"
              checked={config.wechat_enable_content || false}
              onChange={(e) => updateConfig({ wechat_enable_content: e.target.checked })}
              className="w-4 h-4 rounded border-orange-600 bg-orange-700 cursor-pointer"
            />
            <span className="text-sm flex items-center gap-1">
              <span>📄</span>
              <span className="text-orange-700 dark:text-orange-400">采集正文</span>
            </span>
          </label>
          
          {selectedAccounts.size > 0 && (
            <>
              <span className="text-sm text-slate-500 mr-2">
                已选 {selectedAccounts.size} 个
              </span>
              <Button 
                variant="outline" 
                size="sm" 
                className="h-9 gap-2 border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800"
                onClick={handleBatchSync}
              >
                <Play className="h-4 w-4 text-green-600" /> 批量同步
              </Button>
            </>
          )}
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => refetch()} 
            className="h-9 px-3 border-slate-200 dark:border-slate-700"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* 列表内容 */}
      <div className="flex-1 overflow-y-auto min-h-0">
        <table className="w-full text-sm text-left">
          <thead className="text-xs text-slate-500 bg-slate-50/50 dark:bg-slate-900/50 sticky top-0 z-10 backdrop-blur-sm">
            <tr>
              <th className="px-4 py-3 w-12">
                <input 
                  type="checkbox"
                  className="h-4 w-4 rounded border-slate-300 text-green-600 focus:ring-green-500"
                  checked={filteredAccounts.length > 0 && selectedAccounts.size === filteredAccounts.length}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedAccounts(new Set(filteredAccounts.map(a => a.fakeid)))
                    } else {
                      setSelectedAccounts(new Set())
                    }
                  }}
                />
              </th>
              <th className="px-4 py-3">公众号</th>
              <th className="px-4 py-3">最后同步时间</th>
              <th className="px-4 py-3 text-center">消息总数</th>
              <th className="px-4 py-3 text-center">已同步</th>
              <th className="px-4 py-3">同步进度</th>
              <th className="px-4 py-3 text-right">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {filteredAccounts.map((account: WeChatAccountItem) => {
              // 计算进度
              const total = account.total_article_count || 0
              const synced = account.article_count || 0
              const progress = total > 0 ? Math.min(100, Math.round((synced / total) * 100)) : 0
              
              return (
              <tr key={account.fakeid} className="group hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors">
                <td className="px-4 py-3">
                  <input 
                    type="checkbox"
                    className="h-4 w-4 rounded border-slate-300 text-green-600 focus:ring-green-500"
                    checked={selectedAccounts.has(account.fakeid)}
                    onChange={(e) => {
                      const newSet = new Set(selectedAccounts)
                      if (e.target.checked) newSet.add(account.fakeid)
                      else newSet.delete(account.fakeid)
                      setSelectedAccounts(newSet)
                    }}
                  />
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    <Avatar className="h-10 w-10 border border-slate-200 dark:border-slate-700">
                      <AvatarImage src={account.round_head_img} />
                      <AvatarFallback className="bg-green-50 text-green-600 dark:bg-green-900/20 dark:text-green-400">
                        {account.account_name?.[0]}
                      </AvatarFallback>
                    </Avatar>
                    <div>
                      <div className="font-medium text-slate-900 dark:text-slate-100 flex items-center gap-2">
                        {account.account_name}
                        {account.service_type === 1 && <Badge variant="outline" className="text-[10px] px-1 py-0 h-4 border-blue-200 text-blue-600">订阅号</Badge>}
                        {account.service_type === 2 && <Badge variant="outline" className="text-[10px] px-1 py-0 h-4 border-orange-200 text-orange-600">服务号</Badge>}
                      </div>
                      <div className="text-xs text-slate-500 font-mono mt-0.5">
                        {account.alias || account.fakeid}
                      </div>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3 text-slate-500 font-mono text-xs">
                  {formatTime(account.last_sync_time)}
                </td>
                <td className="px-4 py-3 text-center font-mono text-sm">
                  {total > 0 ? total : '-'}
                </td>
                <td className="px-4 py-3 text-center">
                  <Badge variant="secondary" className="bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                    {synced}
                  </Badge>
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-col gap-1 w-32">
                    <div className="flex items-center justify-between text-[10px] text-slate-500">
                      <span>{progress}%</span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-green-500 rounded-full transition-all duration-500" 
                        style={{ width: `${progress}%` }}
                      ></div>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button 
                      size="sm" 
                      variant="outline"
                      className="h-8 px-2 text-green-600 border-green-200 hover:bg-green-50 dark:hover:bg-green-900/20"
                      onClick={() => handleSyncAccount(account)}
                      title="同步文章"
                    >
                      <RefreshCw className="h-4 w-4" />
                    </Button>
                    <Button 
                      size="sm" 
                      variant="ghost" 
                      className="h-8 w-8 p-0 text-red-500 hover:text-red-700 hover:bg-red-50"
                      onClick={() => {
                        setAccountToDelete(account)
                        setIsDeleteDialogOpen(true)
                      }}
                      title="删除账号"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </td>
              </tr>
            )
            })}
            {filteredAccounts.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-12 text-center text-slate-500">
                  <div className="flex flex-col items-center justify-center">
                    <User className="h-12 w-12 text-slate-300 mb-3" />
                    <p>暂无公众号</p>
                    <Button 
                      variant="link" 
                      className="text-green-600 mt-2"
                      onClick={() => setIsAddDialogOpen(true)}
                    >
                      添加一个?
                    </Button>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* 添加公众号对话框 */}
      <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
        <DialogContent className="max-w-[600px] max-h-[80vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>添加公众号</DialogTitle>
            <DialogDescription>
              搜索并添加要采集的公众号。
            </DialogDescription>
          </DialogHeader>
          
          <div className="flex gap-2 my-4">
            <Input 
              value={searchAccountKeyword}
              onChange={(e) => setSearchAccountKeyword(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearchAccount()}
              placeholder="输入公众号名称..."
              className="flex-1"
            />
            <Button 
              onClick={handleSearchAccount}
              disabled={isSearchingAccount}
            >
              {isSearchingAccount ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              <span className="ml-2">搜索</span>
            </Button>
          </div>

          <div className="flex-1 overflow-y-auto border rounded-md min-h-[300px]">
            {searchAccountResults.length === 0 ? (
              <div className="flex items-center justify-center h-full text-slate-400 text-sm">
                {isSearchingAccount ? '搜索中...' : '请输入名称搜索'}
              </div>
            ) : (
              <div className="divide-y divide-slate-100 dark:divide-slate-800">
                {searchAccountResults.map((item, idx) => {
                  const isAdded = accounts.some(a => a.fakeid === item.fakeid)
                  return (
                    <div key={idx} className="flex items-center justify-between p-3 hover:bg-slate-50 dark:hover:bg-slate-800/50">
                      <div className="flex items-center gap-3 overflow-hidden">
                        <Avatar className="h-10 w-10 border">
                          <AvatarImage src={item.round_head_img} />
                          <AvatarFallback>{item.nickname?.[0]}</AvatarFallback>
                        </Avatar>
                        <div className="min-w-0">
                          <div className="font-medium text-sm flex items-center gap-2">
                            <span dangerouslySetInnerHTML={{ __html: item.nickname }}></span>
                            {item.service_type === 1 && <Badge variant="outline" className="text-[10px] px-1 py-0 h-4 text-blue-600 border-blue-200">订阅号</Badge>}
                            {item.service_type === 2 && <Badge variant="outline" className="text-[10px] px-1 py-0 h-4 text-orange-600 border-orange-200">服务号</Badge>}
                          </div>
                          <div className="text-xs text-slate-500 truncate mt-0.5">
                            {item.alias} · {item.signature}
                          </div>
                        </div>
                      </div>
                      <Button 
                        size="sm" 
                        variant={isAdded ? "secondary" : "default"}
                        className={isAdded ? "bg-slate-100 text-slate-500" : "bg-green-600 hover:bg-green-700"}
                        disabled={isAdded || addAccountMutation.isPending}
                        onClick={() => handleAddAccount(item)}
                      >
                        {isAdded ? (
                          <>
                            <CheckCircle className="mr-1 h-3 w-3" /> 已添加
                          </>
                        ) : (
                          <>
                            <Plus className="mr-1 h-3 w-3" /> 添加
                          </>
                        )}
                      </Button>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* 删除确认对话框 */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
            <DialogDescription>
              确定要删除公众号 "{accountToDelete?.account_name}" 吗？
            </DialogDescription>
          </DialogHeader>
          
          <div className="flex items-center space-x-2 py-4">
            <input
              type="checkbox" 
              id="delete-data" 
              className="h-4 w-4 rounded border-slate-300 text-red-600 focus:ring-red-500"
              checked={deleteData}
              onChange={(e) => setDeleteData(e.target.checked)}
            />
            <label
              htmlFor="delete-data"
              className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 text-red-600"
            >
              同时删除该公众号的所有已采集文章数据
            </label>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDeleteDialogOpen(false)}>取消</Button>
            <Button 
              variant="destructive" 
              onClick={() => accountToDelete && deleteAccountMutation.mutate({ 
                fakeid: accountToDelete.fakeid, 
                deleteData 
              })}
              disabled={deleteAccountMutation.isPending}
            >
              {deleteAccountMutation.isPending ? '删除中...' : '确认删除'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

    </div>
  )
}
