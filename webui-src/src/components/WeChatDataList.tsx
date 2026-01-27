import React, { useState, useCallback, useRef, useEffect } from 'react'
import { Search, Download, RefreshCw, Eye, ThumbsUp, MessageCircle, Calendar, ExternalLink, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, ChevronDown, X, Check, User } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Select } from '@/components/ui/select'
import { useQuery } from '@tanstack/react-query'
import { crawlerApi, WeChatArticleItem, WeChatAccountItem } from '@/api/crawler'
import { toast } from '@/components/ui/toast'

export function WeChatDataList() {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [searchTerm, setSearchTerm] = useState('')
  const [timeRange, setTimeRange] = useState<'all' | 'today' | 'week' | 'month'>('all')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [selectedAccounts, setSelectedAccounts] = useState<string[]>([])
  const [accountDropdownOpen, setAccountDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // 防抖搜索
  React.useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchTerm)
      setPage(1) // 搜索时重置页码
    }, 300)
    return () => clearTimeout(timer)
  }, [searchTerm])

  // 点击外部关闭下拉框
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setAccountDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // 获取公众号列表
  const { data: accountsData } = useQuery({
    queryKey: ['wechat-accounts'],
    queryFn: () => crawlerApi.getWeChatAccounts(),
    staleTime: 60000,
  })
  const accounts = accountsData?.data || []

  // 获取文章列表
  const { data, isLoading, refetch, isError, error, isFetching } = useQuery({
    queryKey: ['wechat-articles', page, pageSize, debouncedSearch, timeRange, selectedAccounts],
    queryFn: () => crawlerApi.getWeChatArticles({
      page,
      page_size: pageSize,
      search: debouncedSearch || undefined,
      time_range: timeRange,
      order_by: 'create_time',
      order_dir: 'desc',
      account_ids: selectedAccounts.length > 0 ? selectedAccounts.join(',') : undefined,
    }),
    staleTime: 30000,
    placeholderData: (previousData) => previousData, // 保持上一次数据，避免闪烁
  })

  const articles = data?.data?.articles || []
  const total = data?.data?.total || 0
  const totalPages = Math.ceil(total / pageSize)

  // 格式化数字显示
  const formatNumber = useCallback((num: number) => {
    if (num >= 100000) return '10万+'
    if (num >= 10000) return (num / 10000).toFixed(1) + '万'
    return num.toLocaleString()
  }, [])

  // 格式化日期
  const formatDate = useCallback((timestamp: number) => {
    if (!timestamp) return '-'
    const date = new Date(timestamp * 1000)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))
    
    if (days === 0) return '今天'
    if (days === 1) return '昨天'
    if (days < 7) return `${days}天前`
    
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
  }, [])

  const handleRefresh = () => {
    refetch()
    toast.success('刷新成功')
  }

  const handleTimeRangeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setTimeRange(e.target.value as typeof timeRange)
    setPage(1)
  }

  const handlePageSizeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setPageSize(Number(e.target.value))
    setPage(1)
  }

  // 切换账号选择
  const toggleAccount = (fakeid: string) => {
    setSelectedAccounts(prev => {
      const newSelection = prev.includes(fakeid)
        ? prev.filter(id => id !== fakeid)
        : [...prev, fakeid]
      setPage(1) // 切换账号时重置页码
      return newSelection
    })
  }

  // 清除账号选择
  const clearAccountSelection = () => {
    setSelectedAccounts([])
    setPage(1)
  }

  // 获取已选账号名称
  const getSelectedAccountNames = () => {
    return selectedAccounts
      .map(id => accounts.find((a: WeChatAccountItem) => a.fakeid === id)?.account_name)
      .filter(Boolean)
  }

  // 分页跳转
  const goToPage = (targetPage: number) => {
    const validPage = Math.max(1, Math.min(totalPages, targetPage))
    setPage(validPage)
  }

  return (
    <div className="h-full flex flex-col bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
      
      {/* 工具栏 - 固定在顶部 */}
      <div className="flex-shrink-0 flex items-center justify-between gap-4 px-4 py-3 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
        <div className="flex items-center gap-3 flex-1">
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input 
              placeholder="搜索文章标题..." 
              className="pl-9 h-9 bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-green-500/20"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <Select 
            value={timeRange} 
            onChange={handleTimeRangeChange}
            className="h-9 w-28 text-sm bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700"
          >
            <option value="all">全部时间</option>
            <option value="today">今天</option>
            <option value="week">近7天</option>
            <option value="month">近30天</option>
          </Select>
          
          {/* 公众号多选过滤器 */}
          <div className="relative" ref={dropdownRef}>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setAccountDropdownOpen(!accountDropdownOpen)}
              className={`h-9 min-w-[140px] max-w-[240px] justify-between text-sm bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 ${
                selectedAccounts.length > 0 ? 'border-green-500 text-green-600 dark:text-green-400' : ''
              }`}
            >
              <div className="flex items-center gap-2 truncate">
                <User className="h-3.5 w-3.5 flex-shrink-0" />
                {selectedAccounts.length === 0 ? (
                  <span className="text-slate-500">全部公众号</span>
                ) : selectedAccounts.length === 1 ? (
                  <span className="truncate">{getSelectedAccountNames()[0]}</span>
                ) : (
                  <span>已选 {selectedAccounts.length} 个</span>
                )}
              </div>
              <div className="flex items-center gap-1 flex-shrink-0">
                {selectedAccounts.length > 0 && (
                  <span
                    onClick={(e) => {
                      e.stopPropagation()
                      clearAccountSelection()
                    }}
                    className="p-0.5 hover:bg-slate-200 dark:hover:bg-slate-700 rounded"
                  >
                    <X className="h-3 w-3" />
                  </span>
                )}
                <ChevronDown className={`h-4 w-4 transition-transform ${accountDropdownOpen ? 'rotate-180' : ''}`} />
              </div>
            </Button>
            
            {/* 下拉菜单 */}
            {accountDropdownOpen && (
              <div className="absolute top-full left-0 mt-1 w-64 max-h-80 overflow-auto bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg z-50">
                {accounts.length === 0 ? (
                  <div className="px-3 py-4 text-sm text-slate-500 text-center">
                    暂无公众号数据
                  </div>
                ) : (
                  <>
                    {/* 全选/清除 */}
                    <div className="px-3 py-2 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
                      <span className="text-xs text-slate-500">共 {accounts.length} 个公众号</span>
                      {selectedAccounts.length > 0 && (
                        <button
                          onClick={clearAccountSelection}
                          className="text-xs text-green-600 hover:text-green-700 dark:text-green-400"
                        >
                          清除选择
                        </button>
                      )}
                    </div>
                    {/* 账号列表 */}
                    <div className="py-1">
                      {accounts.map((account: WeChatAccountItem) => (
                        <div
                          key={account.fakeid}
                          onClick={() => toggleAccount(account.fakeid)}
                          className={`flex items-center gap-3 px-3 py-2 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors ${
                            selectedAccounts.includes(account.fakeid) ? 'bg-green-50 dark:bg-green-900/20' : ''
                          }`}
                        >
                          <div className={`w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 ${
                            selectedAccounts.includes(account.fakeid)
                              ? 'bg-green-500 border-green-500 text-white'
                              : 'border-slate-300 dark:border-slate-600'
                          }`}>
                            {selectedAccounts.includes(account.fakeid) && <Check className="h-3 w-3" />}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-medium text-slate-700 dark:text-slate-200 truncate">
                              {account.account_name || '未知公众号'}
                            </div>
                            <div className="text-xs text-slate-500">
                              {account.article_count} 篇文章
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button 
            variant="outline" 
            size="sm" 
            onClick={handleRefresh} 
            disabled={isLoading}
            className="h-9 px-3 border-slate-200 dark:border-slate-700"
          >
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
            <span className="ml-2 hidden sm:inline">刷新</span>
          </Button>
          <Button 
            variant="outline" 
            size="sm"
            className="h-9 px-3 border-slate-200 dark:border-slate-700"
          >
            <Download className="h-4 w-4" />
            <span className="ml-2 hidden sm:inline">导出</span>
          </Button>
        </div>
      </div>

      {/* 文章列表 - 可滚动区域 */}
      <div className="flex-1 overflow-y-auto min-h-0 scrollbar-thin scrollbar-thumb-slate-300 dark:scrollbar-thumb-slate-600 scrollbar-track-transparent hover:scrollbar-thumb-slate-400 dark:hover:scrollbar-thumb-slate-500">
        
        {/* 加载状态 */}
        {isLoading && !articles.length && (
          <div className="flex flex-col items-center justify-center h-full py-16">
            <RefreshCw className="h-8 w-8 animate-spin text-green-500 mb-4" />
            <p className="text-sm text-slate-500">加载中...</p>
          </div>
        )}
        
        {/* 错误状态 */}
        {isError && (
          <div className="flex flex-col items-center justify-center h-full py-16">
            <div className="w-16 h-16 rounded-full bg-red-50 dark:bg-red-950/30 flex items-center justify-center mb-4">
              <span className="text-2xl">😵</span>
            </div>
            <p className="text-sm text-red-500 mb-4">加载失败: {(error as Error)?.message || '未知错误'}</p>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              重试
            </Button>
          </div>
        )}
        
        {/* 空状态 */}
        {!isLoading && !isError && articles.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full py-16">
            <div className="w-20 h-20 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center mb-4">
              <span className="text-4xl">📭</span>
            </div>
            <p className="text-base font-medium text-slate-700 dark:text-slate-300 mb-2">暂无数据</p>
            <p className="text-sm text-slate-500">请先在左侧配置公众号，然后点击"开始采集"</p>
          </div>
        )}
        
        {/* 文章列表 */}
        {articles.length > 0 && (
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {articles.map((article: WeChatArticleItem) => (
              <article 
                key={article.id} 
                className="group px-4 py-4 hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors duration-150"
              >
                <div className="flex items-start gap-4">
                  {/* 封面图 (如果有) */}
                  {article.cover && (
                    <div className="flex-shrink-0 w-24 h-16 rounded-md overflow-hidden bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
                      <img 
                        src={article.cover} 
                        alt="" 
                        className="w-full h-full object-cover"
                        loading="lazy"
                        referrerPolicy="no-referrer"
                        onError={(e) => {
                          const img = e.target as HTMLImageElement
                          img.style.display = 'none'
                          // 显示占位图标
                          const parent = img.parentElement
                          if (parent && !parent.querySelector('.placeholder-icon')) {
                            const placeholder = document.createElement('div')
                            placeholder.className = 'placeholder-icon text-slate-400 dark:text-slate-500'
                            placeholder.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/></svg>'
                            parent.appendChild(placeholder)
                          }
                        }}
                      />
                    </div>
                  )}
                  
                  {/* 文章信息 */}
                  <div className="flex-1 min-w-0">
                    {/* 标题行 */}
                    <div className="flex items-start gap-2 mb-2">
                      <h3 
                        className="text-sm font-medium leading-snug text-slate-800 dark:text-slate-200 line-clamp-2 group-hover:text-green-600 dark:group-hover:text-green-400 transition-colors cursor-pointer"
                        title={article.title}
                      >
                        {article.title || '(无标题)'}
                      </h3>
                      {article.read_num >= 100000 && (
                        <Badge className="flex-shrink-0 bg-gradient-to-r from-orange-500 to-red-500 text-white text-[10px] px-1.5 py-0 h-5 border-0">
                          爆款
                        </Badge>
                      )}
                    </div>
                    
                    {/* 元信息 */}
                    <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400 mb-2">
                      <span className="font-medium text-slate-600 dark:text-slate-300 truncate max-w-[120px]" title={article.account_name}>
                        {article.account_name || '未知公众号'}
                      </span>
                      <span className="flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        {formatDate(article.create_time)}
                      </span>
                      {article.link && (
                        <a 
                          href={article.link} 
                          target="_blank" 
                          rel="noreferrer" 
                          className="flex items-center gap-1 text-slate-400 hover:text-green-500 transition-colors opacity-0 group-hover:opacity-100"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <ExternalLink className="h-3 w-3" />
                          原文
                        </a>
                      )}
                    </div>

                    {/* 数据指标 */}
                    <div className="flex items-center gap-5">
                      <div className="flex items-center gap-1.5 text-xs">
                        <Eye className="h-3.5 w-3.5 text-blue-500" />
                        <span className="font-medium text-slate-700 dark:text-slate-300">{formatNumber(article.read_num)}</span>
                        <span className="text-slate-400">阅读</span>
                      </div>
                      <div className="flex items-center gap-1.5 text-xs">
                        <ThumbsUp className="h-3.5 w-3.5 text-amber-500" />
                        <span className="font-medium text-slate-700 dark:text-slate-300">{formatNumber(article.like_num)}</span>
                        <span className="text-slate-400">在看</span>
                      </div>
                      <div className="flex items-center gap-1.5 text-xs">
                        <MessageCircle className="h-3.5 w-3.5 text-green-500" />
                        <span className="font-medium text-slate-700 dark:text-slate-300">{article.comment_count}</span>
                        <span className="text-slate-400">评论</span>
                      </div>
                    </div>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>

      {/* 分页栏 - 固定在底部 */}
      {articles.length > 0 && (
        <div className="flex-shrink-0 flex items-center justify-between px-4 py-3 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
          {/* 左侧：数据统计 */}
          <div className="flex items-center gap-3 text-sm text-slate-500">
            <span>共 <span className="font-medium text-slate-700 dark:text-slate-300">{total.toLocaleString()}</span> 条</span>
            <span className="text-slate-300 dark:text-slate-600">|</span>
            <div className="flex items-center gap-1">
              <span>每页</span>
              <Select 
                value={String(pageSize)} 
                onChange={handlePageSizeChange}
                className="h-7 w-16 text-xs bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700"
              >
                <option value="10">10</option>
                <option value="20">20</option>
                <option value="50">50</option>
                <option value="100">100</option>
              </Select>
              <span>条</span>
            </div>
          </div>
          
          {/* 右侧：分页控制 */}
          <div className="flex items-center gap-1">
            {/* 首页 */}
            <Button 
              variant="ghost" 
              size="sm"
              className="h-8 w-8 p-0"
              disabled={page <= 1}
              onClick={() => goToPage(1)}
              title="首页"
            >
              <ChevronsLeft className="h-4 w-4" />
            </Button>
            
            {/* 上一页 */}
            <Button 
              variant="ghost" 
              size="sm"
              className="h-8 w-8 p-0"
              disabled={page <= 1}
              onClick={() => goToPage(page - 1)}
              title="上一页"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            
            {/* 页码显示 */}
            <div className="flex items-center gap-1 mx-2">
              {/* 动态生成页码按钮 */}
              {(() => {
                const pages: (number | string)[] = []
                const showPages = 5 // 显示的页码数量
                
                if (totalPages <= showPages) {
                  // 总页数较少，全部显示
                  for (let i = 1; i <= totalPages; i++) {
                    pages.push(i)
                  }
                } else {
                  // 总页数较多，显示部分
                  if (page <= 3) {
                    pages.push(1, 2, 3, 4, '...', totalPages)
                  } else if (page >= totalPages - 2) {
                    pages.push(1, '...', totalPages - 3, totalPages - 2, totalPages - 1, totalPages)
                  } else {
                    pages.push(1, '...', page - 1, page, page + 1, '...', totalPages)
                  }
                }
                
                return pages.map((p, idx) => (
                  p === '...' ? (
                    <span key={`ellipsis-${idx}`} className="px-2 text-slate-400">...</span>
                  ) : (
                    <Button
                      key={p}
                      variant={page === p ? 'default' : 'ghost'}
                      size="sm"
                      className={`h-8 min-w-[32px] px-2 text-sm ${
                        page === p 
                          ? 'bg-green-600 hover:bg-green-700 text-white' 
                          : 'text-slate-600 dark:text-slate-400'
                      }`}
                      onClick={() => goToPage(p as number)}
                    >
                      {p}
                    </Button>
                  )
                ))
              })()}
            </div>
            
            {/* 下一页 */}
            <Button 
              variant="ghost" 
              size="sm"
              className="h-8 w-8 p-0"
              disabled={page >= totalPages}
              onClick={() => goToPage(page + 1)}
              title="下一页"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
            
            {/* 末页 */}
            <Button 
              variant="ghost" 
              size="sm"
              className="h-8 w-8 p-0"
              disabled={page >= totalPages}
              onClick={() => goToPage(totalPages)}
              title="末页"
            >
              <ChevronsRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
