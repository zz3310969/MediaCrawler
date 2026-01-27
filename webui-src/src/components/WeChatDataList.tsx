import React, { useState, useCallback, useRef, useEffect } from 'react'
import { Search, RefreshCw, Eye, ThumbsUp, MessageCircle, Calendar, ExternalLink, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, ChevronDown, X, Check, User, FileSpreadsheet, CheckSquare, Square, MinusSquare, FileText, FileCode, FileJson, RotateCw } from 'lucide-react'
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
  // 文章勾选状态
  const [selectedArticles, setSelectedArticles] = useState<Set<number>>(new Set())
  const [isExporting, setIsExporting] = useState(false)
  // 导出格式下拉
  const [exportDropdownOpen, setExportDropdownOpen] = useState(false)
  const exportDropdownRef = useRef<HTMLDivElement>(null)
  // 重新采集状态
  const [isRefetching, setIsRefetching] = useState(false)

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
      if (exportDropdownRef.current && !exportDropdownRef.current.contains(event.target as Node)) {
        setExportDropdownOpen(false)
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

  // 文章勾选相关
  const toggleArticleSelection = (articleId: number) => {
    setSelectedArticles(prev => {
      const newSet = new Set(prev)
      if (newSet.has(articleId)) {
        newSet.delete(articleId)
      } else {
        newSet.add(articleId)
      }
      return newSet
    })
  }

  // 全选当前页
  const selectAllCurrentPage = () => {
    const currentPageIds = articles.map((a: WeChatArticleItem) => a.id)
    setSelectedArticles(prev => {
      const newSet = new Set(prev)
      currentPageIds.forEach(id => newSet.add(id))
      return newSet
    })
  }

  // 取消全选当前页
  const deselectAllCurrentPage = () => {
    const currentPageIds = articles.map((a: WeChatArticleItem) => a.id)
    setSelectedArticles(prev => {
      const newSet = new Set(prev)
      currentPageIds.forEach(id => newSet.delete(id))
      return newSet
    })
  }

  // 清除所有选择
  const clearAllSelection = () => {
    setSelectedArticles(new Set())
  }

  // 检查当前页是否全选
  const isAllCurrentPageSelected = articles.length > 0 && articles.every((a: WeChatArticleItem) => selectedArticles.has(a.id))
  const isSomeCurrentPageSelected = articles.some((a: WeChatArticleItem) => selectedArticles.has(a.id))

  // 导出选中的文章 - CSV 格式（仅元数据）
  const handleExportCSV = async () => {
    if (selectedArticles.size === 0) {
      toast.error('请先选择要导出的文章')
      return
    }

    setIsExporting(true)
    setExportDropdownOpen(false)
    try {
      // 获取选中文章的完整数据
      const selectedData = articles.filter((a: WeChatArticleItem) => selectedArticles.has(a.id))
      
      // 生成 CSV 内容
      const headers = ['标题', '公众号', '阅读数', '在看数', '评论数', '发布时间', '链接']
      const rows = selectedData.map((article: WeChatArticleItem) => [
        `"${(article.title || '').replace(/"/g, '""')}"`,
        `"${(article.account_name || '').replace(/"/g, '""')}"`,
        article.read_num,
        article.like_num,
        article.comment_count,
        article.create_time ? new Date(article.create_time * 1000).toLocaleString('zh-CN') : '',
        article.link || ''
      ])
      
      const csvContent = '\uFEFF' + [headers.join(','), ...rows.map(row => row.join(','))].join('\n')
      
      // 下载文件
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `微信文章导出_${new Date().toLocaleDateString('zh-CN').replace(/\//g, '-')}_${selectedArticles.size}篇.csv`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      
      toast.success(`成功导出 ${selectedArticles.size} 篇文章元数据`)
    } catch (err) {
      toast.error('导出失败: ' + (err as Error).message)
    } finally {
      setIsExporting(false)
    }
  }

  // 导出文章内容（HTML/Markdown/JSON）
  const handleExportContent = async (format: 'html' | 'markdown' | 'json') => {
    if (selectedArticles.size === 0) {
      toast.error('请先选择要导出的文章')
      return
    }

    setIsExporting(true)
    setExportDropdownOpen(false)
    
    const formatNames = { html: 'HTML', markdown: 'Markdown', json: 'JSON' }
    toast.info(`正在导出 ${selectedArticles.size} 篇文章为 ${formatNames[format]} 格式...`)
    
    try {
      const blob = await crawlerApi.exportWeChatArticles(Array.from(selectedArticles), format)
      
      // 下载文件
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `微信文章导出_${format}_${new Date().toLocaleDateString('zh-CN').replace(/\//g, '-')}_${selectedArticles.size}篇.zip`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      
      toast.success(`成功导出 ${selectedArticles.size} 篇文章（${formatNames[format]} 格式）`)
    } catch (err) {
      toast.error('导出失败: ' + (err as Error).message)
    } finally {
      setIsExporting(false)
    }
  }

  // 重新采集选中文章的内容
  const handleRefetchContent = async () => {
    if (selectedArticles.size === 0) {
      toast.error('请先选择要重新采集的文章')
      return
    }
    
    if (selectedArticles.size > 20) {
      toast.error('单次最多重新采集 20 篇文章')
      return
    }

    setIsRefetching(true)
    toast.info(`正在重新采集 ${selectedArticles.size} 篇文章内容...`)
    
    try {
      const result = await crawlerApi.refetchWeChatContent(Array.from(selectedArticles))
      const data = result.data
      
      if (data.success > 0) {
        toast.success(`采集完成：${data.success} 篇成功，${data.failed} 篇失败`)
        // 刷新列表
        refetch()
      } else {
        toast.error(`采集失败：${data.results.map(r => r.message).join(', ')}`)
      }
    } catch (err) {
      toast.error('重新采集失败: ' + (err as Error).message)
    } finally {
      setIsRefetching(false)
    }
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
          {/* 选中状态提示 */}
          {selectedArticles.size > 0 && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-green-50 dark:bg-green-900/20 rounded-md border border-green-200 dark:border-green-800">
              <span className="text-sm text-green-700 dark:text-green-300">
                已选 <span className="font-semibold">{selectedArticles.size}</span> 篇
              </span>
              <button
                onClick={clearAllSelection}
                className="text-xs text-green-600 hover:text-green-800 dark:text-green-400 dark:hover:text-green-200 underline"
              >
                清除
              </button>
            </div>
          )}
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
          {/* 重新采集按钮 */}
          <Button 
            variant="outline" 
            size="sm" 
            onClick={handleRefetchContent}
            disabled={isRefetching || selectedArticles.size === 0 || selectedArticles.size > 20}
            className={`h-9 px-3 ${
              selectedArticles.size > 0 && selectedArticles.size <= 20
                ? 'border-blue-500 text-blue-600 hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-900/20' 
                : 'border-slate-200 dark:border-slate-700'
            }`}
            title={selectedArticles.size > 20 ? '单次最多采集20篇' : '重新采集选中文章的内容'}
          >
            {isRefetching ? (
              <RotateCw className="h-4 w-4 animate-spin" />
            ) : (
              <RotateCw className="h-4 w-4" />
            )}
            <span className="ml-2 hidden sm:inline">
              {isRefetching ? '采集中...' : '采集内容'}
            </span>
          </Button>
          {/* 导出下拉菜单 */}
          <div className="relative" ref={exportDropdownRef}>
            <Button 
              variant={selectedArticles.size > 0 ? 'default' : 'outline'}
              size="sm"
              onClick={() => setExportDropdownOpen(!exportDropdownOpen)}
              disabled={isExporting || selectedArticles.size === 0}
              className={`h-9 px-3 ${
                selectedArticles.size > 0 
                  ? 'bg-green-600 hover:bg-green-700 text-white border-green-600' 
                  : 'border-slate-200 dark:border-slate-700'
              }`}
            >
              {isExporting ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <FileSpreadsheet className="h-4 w-4" />
              )}
              <span className="ml-2 hidden sm:inline">
                {selectedArticles.size > 0 ? `导出 (${selectedArticles.size})` : '导出'}
              </span>
              <ChevronDown className={`ml-1 h-3 w-3 transition-transform ${exportDropdownOpen ? 'rotate-180' : ''}`} />
            </Button>
            
            {/* 导出格式下拉菜单 */}
            {exportDropdownOpen && selectedArticles.size > 0 && (
              <div className="absolute top-full right-0 mt-1 w-56 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg z-50 overflow-hidden">
                <div className="px-3 py-2 border-b border-slate-100 dark:border-slate-700">
                  <span className="text-xs text-slate-500">选择导出格式</span>
                </div>
                <div className="py-1">
                  {/* CSV - 仅元数据 */}
                  <button
                    onClick={handleExportCSV}
                    className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors text-left"
                  >
                    <FileSpreadsheet className="h-4 w-4 text-green-500" />
                    <div>
                      <div className="text-sm font-medium text-slate-700 dark:text-slate-200">CSV 表格</div>
                      <div className="text-xs text-slate-500">仅导出元数据（标题、阅读量等）</div>
                    </div>
                  </button>
                  
                  {/* HTML - 完整内容 */}
                  <button
                    onClick={() => handleExportContent('html')}
                    className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors text-left"
                  >
                    <FileCode className="h-4 w-4 text-orange-500" />
                    <div>
                      <div className="text-sm font-medium text-slate-700 dark:text-slate-200">HTML 文件</div>
                      <div className="text-xs text-slate-500">导出完整文章内容（网页格式）</div>
                    </div>
                  </button>
                  
                  {/* Markdown - 完整内容 */}
                  <button
                    onClick={() => handleExportContent('markdown')}
                    className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors text-left"
                  >
                    <FileText className="h-4 w-4 text-blue-500" />
                    <div>
                      <div className="text-sm font-medium text-slate-700 dark:text-slate-200">Markdown 文件</div>
                      <div className="text-xs text-slate-500">导出完整文章内容（MD格式）</div>
                    </div>
                  </button>
                  
                  {/* JSON - 完整数据 */}
                  <button
                    onClick={() => handleExportContent('json')}
                    className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors text-left"
                  >
                    <FileJson className="h-4 w-4 text-purple-500" />
                    <div>
                      <div className="text-sm font-medium text-slate-700 dark:text-slate-200">JSON 数据</div>
                      <div className="text-xs text-slate-500">导出完整数据（含内容和元数据）</div>
                    </div>
                  </button>
                </div>
                <div className="px-3 py-2 border-t border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-900/50">
                  <p className="text-xs text-slate-500">
                    💡 HTML/MD/JSON 需要先启用"下载文章内容"选项采集
                  </p>
                </div>
              </div>
            )}
          </div>
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
            {/* 全选栏 */}
            <div className="flex items-center gap-3 px-4 py-2 bg-slate-50/80 dark:bg-slate-800/30 border-b border-slate-100 dark:border-slate-800">
              <button
                onClick={() => {
                  if (isAllCurrentPageSelected) {
                    deselectAllCurrentPage()
                  } else {
                    selectAllCurrentPage()
                  }
                }}
                className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400 hover:text-green-600 dark:hover:text-green-400 transition-colors"
              >
                {isAllCurrentPageSelected ? (
                  <CheckSquare className="h-4 w-4 text-green-500" />
                ) : isSomeCurrentPageSelected ? (
                  <MinusSquare className="h-4 w-4 text-green-500" />
                ) : (
                  <Square className="h-4 w-4" />
                )}
                <span>{isAllCurrentPageSelected ? '取消全选' : '全选当前页'}</span>
              </button>
              {selectedArticles.size > 0 && (
                <span className="text-xs text-slate-500">
                  (跨页已选 {selectedArticles.size} 篇)
                </span>
              )}
            </div>
            {articles.map((article: WeChatArticleItem) => (
              <article 
                key={article.id} 
                className={`group px-4 py-4 hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors duration-150 ${
                  selectedArticles.has(article.id) ? 'bg-green-50/50 dark:bg-green-900/10' : ''
                }`}
              >
                <div className="flex items-start gap-4">
                  {/* 复选框 */}
                  <button
                    onClick={() => toggleArticleSelection(article.id)}
                    className="flex-shrink-0 mt-1"
                  >
                    {selectedArticles.has(article.id) ? (
                      <CheckSquare className="h-5 w-5 text-green-500" />
                    ) : (
                      <Square className="h-5 w-5 text-slate-300 dark:text-slate-600 hover:text-green-500 transition-colors" />
                    )}
                  </button>
                  
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
