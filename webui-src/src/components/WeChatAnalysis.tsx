import React from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { FileText, Eye, ThumbsUp, Users, ArrowUp, TrendingUp, Activity, Trophy, Crown } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { crawlerApi } from '@/api/crawler'

export function WeChatAnalysis() {
  // 获取统计数据
  const { data: statsData, isLoading: statsLoading } = useQuery({
    queryKey: ['wechat-stats'],
    queryFn: () => crawlerApi.getWeChatStats(),
    staleTime: 60000,
  })

  // 获取热门文章
  const { data: topArticlesData, isLoading: topLoading } = useQuery({
    queryKey: ['wechat-top-articles'],
    queryFn: () => crawlerApi.getWeChatTopArticles(5),
    staleTime: 60000,
  })

  const stats = statsData?.data
  const topArticles = topArticlesData?.data || []

  // 格式化数字
  const formatNumber = (num: number | undefined) => {
    if (num === undefined || num === null) return '0'
    if (num >= 100000000) return (num / 100000000).toFixed(1) + '亿'
    if (num >= 10000) return (num / 10000).toFixed(1) + '万'
    return num.toLocaleString()
  }

  // 格式化日期
  const formatDate = (timestamp: number) => {
    if (!timestamp) return '-'
    const date = new Date(timestamp * 1000)
    return date.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
  }

  const STATS_CONFIG = [
    { 
      title: '文章总数', 
      value: stats?.total_articles,
      change: stats?.today_articles ? `+${stats.today_articles}` : undefined,
      changeLabel: '今日新增',
      icon: FileText,
      color: 'text-blue-600',
      bg: 'bg-blue-100 dark:bg-blue-950/50',
      gradient: 'from-blue-500 to-blue-600'
    },
    { 
      title: '总阅读量', 
      value: stats?.total_reads,
      change: stats?.today_reads ? `+${formatNumber(stats.today_reads)}` : undefined,
      changeLabel: '今日新增',
      icon: Eye,
      color: 'text-emerald-600',
      bg: 'bg-emerald-100 dark:bg-emerald-950/50',
      gradient: 'from-emerald-500 to-emerald-600'
    },
    { 
      title: '总点赞数', 
      value: stats?.total_likes,
      icon: ThumbsUp,
      color: 'text-amber-600',
      bg: 'bg-amber-100 dark:bg-amber-950/50',
      gradient: 'from-amber-500 to-amber-600'
    },
    { 
      title: '采集公众号', 
      value: stats?.total_accounts,
      icon: Users,
      color: 'text-violet-600',
      bg: 'bg-violet-100 dark:bg-violet-950/50',
      gradient: 'from-violet-500 to-violet-600'
    }
  ]

  // 骨架屏组件
  const StatSkeleton = () => (
    <div className="animate-pulse">
      <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-16 mb-3"></div>
      <div className="h-8 bg-slate-200 dark:bg-slate-700 rounded w-24 mb-2"></div>
      <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-20"></div>
    </div>
  )

  return (
    <div className="space-y-6 pb-4">
      {/* 核心指标卡片 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {STATS_CONFIG.map((stat, index) => (
          <Card key={index} className="relative overflow-hidden border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition-shadow">
            {/* 装饰渐变条 */}
            <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${stat.gradient}`}></div>
            
            <CardContent className="p-5">
              {statsLoading ? (
                <StatSkeleton />
              ) : (
                <>
                  <div className="flex justify-between items-start mb-3">
                    <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      {stat.title}
                    </p>
                    <div className={`p-2 rounded-lg ${stat.bg}`}>
                      <stat.icon className={`h-4 w-4 ${stat.color}`} />
                    </div>
                  </div>
                  
                  <h3 className="text-2xl font-bold text-slate-800 dark:text-slate-100 tracking-tight mb-1">
                    {formatNumber(stat.value)}
                  </h3>
                  
                  {stat.change ? (
                    <div className="flex items-center text-xs">
                      <ArrowUp className="h-3 w-3 text-emerald-500 mr-1" />
                      <span className="text-emerald-600 dark:text-emerald-400 font-medium">{stat.change}</span>
                      <span className="text-slate-400 ml-1">{stat.changeLabel}</span>
                    </div>
                  ) : (
                    <div className="h-4"></div>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* 趋势图表占位区 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card className="border-slate-200 dark:border-slate-800 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-blue-500" />
              阅读量趋势
            </CardTitle>
            <CardDescription className="text-xs">最近7天数据</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[180px] flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-800/50 dark:to-slate-900/50 rounded-lg border border-dashed border-slate-200 dark:border-slate-700">
              <div className="text-center">
                <TrendingUp className="h-8 w-8 text-slate-300 dark:text-slate-600 mx-auto mb-2" />
                <p className="text-sm text-slate-400">图表功能开发中...</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200 dark:border-slate-800 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Activity className="h-4 w-4 text-violet-500" />
              采集活跃度
            </CardTitle>
            <CardDescription className="text-xs">每日采集文章数</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[180px] flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-800/50 dark:to-slate-900/50 rounded-lg border border-dashed border-slate-200 dark:border-slate-700">
              <div className="text-center">
                <Activity className="h-8 w-8 text-slate-300 dark:text-slate-600 mx-auto mb-2" />
                <p className="text-sm text-slate-400">图表功能开发中...</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 热门文章排行 */}
      <Card className="border-slate-200 dark:border-slate-800 shadow-sm">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Trophy className="h-4 w-4 text-amber-500" />
                热门文章排行
              </CardTitle>
              <CardDescription className="text-xs mt-1">按阅读量排序 Top 5</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          {topLoading ? (
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="flex items-center gap-4 animate-pulse">
                  <div className="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-700"></div>
                  <div className="flex-1">
                    <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-3/4 mb-2"></div>
                    <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-1/2"></div>
                  </div>
                  <div className="h-5 bg-slate-200 dark:bg-slate-700 rounded w-16"></div>
                </div>
              ))}
            </div>
          ) : topArticles.length === 0 ? (
            <div className="text-center py-12">
              <Trophy className="h-12 w-12 text-slate-200 dark:text-slate-700 mx-auto mb-3" />
              <p className="text-sm text-slate-500">暂无数据</p>
              <p className="text-xs text-slate-400 mt-1">开始采集后将在此显示热门文章</p>
            </div>
          ) : (
            <div className="space-y-3">
              {topArticles.map((article, i) => (
                <div 
                  key={article.id} 
                  className="flex items-center gap-4 p-3 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors group cursor-pointer"
                >
                  {/* 排名徽章 */}
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0 ${
                    i === 0 
                      ? 'bg-gradient-to-br from-amber-400 to-amber-500 text-white shadow-lg shadow-amber-500/30' 
                      : i === 1 
                        ? 'bg-gradient-to-br from-slate-300 to-slate-400 text-white' 
                        : i === 2 
                          ? 'bg-gradient-to-br from-orange-300 to-orange-400 text-white'
                          : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400'
                  }`}>
                    {i === 0 && <Crown className="h-4 w-4" />}
                    {i > 0 && (i + 1)}
                  </div>
                  
                  {/* 文章信息 */}
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-slate-700 dark:text-slate-200 truncate group-hover:text-green-600 dark:group-hover:text-green-400 transition-colors">
                      {article.title || '(无标题)'}
                    </div>
                    <div className="text-xs text-slate-400 mt-0.5 flex items-center gap-2">
                      <span className="truncate max-w-[100px]">{article.account_name || '未知'}</span>
                      <span>•</span>
                      <span>{formatDate(article.create_time)}</span>
                    </div>
                  </div>
                  
                  {/* 阅读量 */}
                  <div className="flex-shrink-0 text-right">
                    <div className="text-sm font-bold text-slate-700 dark:text-slate-200">
                      {formatNumber(article.read_num)}
                    </div>
                    <div className="text-[10px] text-slate-400">阅读</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
