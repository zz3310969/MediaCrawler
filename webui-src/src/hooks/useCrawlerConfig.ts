// 爬虫配置管理 Hook
import { useState, useCallback, useEffect } from 'react'
import type { CrawlerStartRequest, CrawlerType, LoginType } from '@/api/crawler'

const STORAGE_KEY = 'crawler_config'

// 默认配置
const DEFAULT_CONFIG: CrawlerStartRequest = {
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
}

export function useCrawlerConfig() {
  // 从 localStorage 加载配置
  const [config, setConfig] = useState<CrawlerStartRequest>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) {
        return { ...DEFAULT_CONFIG, ...JSON.parse(saved) }
      }
    } catch (error) {
      console.error('加载配置失败:', error)
    }
    return DEFAULT_CONFIG
  })

  // 保存配置到 localStorage
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(config))
    } catch (error) {
      console.error('保存配置失败:', error)
    }
  }, [config])

  // 更新单个字段
  const updateConfig = useCallback((updates: Partial<CrawlerStartRequest>) => {
    setConfig(prev => ({ ...prev, ...updates }))
  }, [])

  // 处理爬取类型变化（清空相关字段）
  const handleCrawlerTypeChange = useCallback((value: CrawlerType) => {
    setConfig(prev => ({
      ...prev,
      crawler_type: value,
      keywords: '',
      specified_ids: '',
      creator_ids: '',
    }))
  }, [])

  // 处理登录方式变化
  const handleLoginTypeChange = useCallback((value: LoginType) => {
    setConfig(prev => ({
      ...prev,
      login_type: value,
      cookies: value === 'cookie' ? prev.cookies : '',
    }))
  }, [])

  // 重置配置
  const resetConfig = useCallback(() => {
    setConfig(DEFAULT_CONFIG)
  }, [])

  return {
    config,
    updateConfig,
    handleCrawlerTypeChange,
    handleLoginTypeChange,
    resetConfig,
  }
}

