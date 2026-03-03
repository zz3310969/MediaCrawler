import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Bug, Play } from 'lucide-react';
import { Button } from '../components/common';
import {
  StepsSidebar,
  Step1Platform,
  StepAccount,
  Step2Config,
  Step3AntiDetect,
  Step3Proxy,
  Step4Confirm,
} from '../components/task-create';
import { Platform, TaskConfig } from '../types';
import { AntiDetectConfig } from '../api/antiDetect';
import { toast } from '../components/ui/toast';
import { tasksApi } from '../api/tasks';

const STEPS = [
  { id: 1, title: '选择平台', description: '选择爬取目标' },
  { id: 2, title: '选择账号', description: '选择登录账号' },
  { id: 3, title: '配置参数', description: '设置爬取规则' },
  { id: 4, title: '反爬增强', description: '配置反检测' },
  { id: 5, title: '代理设置', description: '配置代理池' },
  { id: 6, title: '确认执行', description: '检查并开始' },
];

interface ProxyConfig {
  use_proxy: boolean;
  retry_count: number;
  timeout: number;
}

export function TaskCreate() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [selectedPlatform, setSelectedPlatform] = useState<Platform | null>(null);
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);

  // 任务配置
  const [config, setConfig] = useState<Partial<TaskConfig>>({
    crawler_type: 'search',
    max_notes: 100,
    enable_comments: false,
    enable_media: false,
    concurrency: 3,
    crawl_interval: 1.0,
    save_option: 'db',
  });

  // 反爬增强配置
  const [antiDetectEnabled, setAntiDetectEnabled] = useState(false);
  const [antiDetectConfig, setAntiDetectConfig] = useState<Partial<AntiDetectConfig>>({
    enable_fingerprint: true,
    enable_rate_limit: true,
    enable_human_behavior: true,
    enable_account_health: true,
    enable_binding: true,
    rate_limit_min_interval: 3.0,
    rate_limit_max_interval: 10.0,
    rate_limit_hourly_limit: 150,
    rate_limit_daily_limit: 1500,
  });

  // 代理配置（独立管理）
  const [proxyConfig, setProxyConfig] = useState<ProxyConfig>({
    use_proxy: false,
    retry_count: 3,
    timeout: 30,
  });

  const handleConfigChange = (updates: Partial<TaskConfig>) => {
    setConfig((prev) => ({ ...prev, ...updates }));
  };

  const handleProxyConfigChange = (updates: Partial<ProxyConfig>) => {
    setProxyConfig((prev) => ({ ...prev, ...updates }));
  };

  const handleNext = () => {
    if (currentStep < 6) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handlePrev = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSubmit = async () => {
    if (!selectedPlatform) {
      console.error('No platform selected');
      return;
    }

    try {
      // 收集平台特有参数到 extra
      const extra: Record<string, unknown> = {};
      const platformExtraKeys = [
        'sort_type', 'publish_time_type',
        'bili_search_mode', 'bili_qn',
        'weibo_search_type', 'enable_full_text',
        'vip_creator_ids',
        'wechat_album_ids', 'wechat_enable_content', 'wechat_enable_reading_stats',
        'tieba_name_list',
      ];
      for (const key of platformExtraKeys) {
        const val = (config as Record<string, unknown>)[key];
        if (val !== undefined && val !== '' && val !== null) {
          extra[key] = val;
        }
      }

      const taskConfig = {
        platform: selectedPlatform,
        crawler_type: config.crawler_type || 'search',
        keywords: config.keywords || [],
        creator_ids: config.creator_ids || [],
        note_urls: config.note_urls || [],
        max_notes: config.max_notes || 100,
        enable_comments: config.enable_comments || false,
        enable_media: config.enable_media || false,
        concurrency: config.concurrency || 3,
        crawl_interval: config.crawl_interval || 1.0,
        account_id: selectedAccountId || undefined,
        login_type: 'cookie' as const,
        save_option: (config.save_option || 'db') as 'csv' | 'json' | 'excel' | 'db' | 'sqlite' | 'postgres',
        enable_anti_detect: antiDetectEnabled,
        anti_detect_config: antiDetectEnabled ? antiDetectConfig : undefined,
        extra: Object.keys(extra).length > 0 ? extra : undefined,
      };

      const taskRequest = {
        config: taskConfig,
      };

      console.log('Creating task:', taskRequest);

      // 调用 API 创建任务
      const task = await tasksApi.create(taskRequest);
      console.log('Task created successfully:', task);

      // 导航到任务列表页面
      navigate('/tasks');
    } catch (error) {
      console.error('Failed to create task:', error);
      toast.error('创建任务失败: ' + (error instanceof Error ? error.message : String(error)));
    }
  };

  const canProceed = () => {
    switch (currentStep) {
      case 1:
        return selectedPlatform !== null;
      case 2:
        return true;
      case 3: {
        if (!config.crawler_type || !config.max_notes) return false;
        const type = config.crawler_type;
        if (type === 'search') {
          return (config.keywords && config.keywords.length > 0) ||
            (selectedPlatform === 'tieba' && config.tieba_name_list);
        }
        if (type === 'detail') {
          return config.note_urls && config.note_urls.length > 0;
        }
        if (type === 'creator') {
          return config.creator_ids && config.creator_ids.length > 0;
        }
        if (type === 'creator_vip') {
          return config.vip_creator_ids && config.vip_creator_ids.length > 0;
        }
        if (type === 'album') {
          return !!config.wechat_album_ids;
        }
        return true;
      }
      case 4:
        return true;
      case 5:
        return true;
      case 6:
        return true;
      default:
        return false;
    }
  };

  return (
    <div className="h-screen flex bg-white">
      {/* 左侧侧边栏 - 步骤导航 */}
      <aside className="w-[260px] h-full bg-sidebar border-r border-border flex flex-col">
        <div className="p-6 pb-8 space-y-8">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-primary flex items-center justify-center">
              <Bug className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-semibold font-display text-text-primary">
              MediaCrawler
            </span>
          </div>

          {/* 步骤导航 */}
          <StepsSidebar steps={STEPS} currentStep={currentStep} />
        </div>

        {/* 底部用户区域 */}
        <div className="mt-auto p-6 pt-4 border-t border-border">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center">
              <span className="text-sm font-semibold text-white">MC</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-text-primary truncate">Admin User</p>
              <p className="text-xs text-text-secondary">管理员</p>
            </div>
          </div>
        </div>
      </aside>

      {/* 右侧主内容 */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* 顶部栏 */}
        <div className="flex-shrink-0 flex items-center justify-end px-12 pt-6">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 px-4 py-2 text-sm text-text-secondary hover:text-text-primary rounded-lg hover:bg-slate-100 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            返回首页
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-12 pt-4 pb-24">
          {currentStep === 1 && (
            <Step1Platform
              selectedPlatform={selectedPlatform}
              onSelect={setSelectedPlatform}
            />
          )}
          {currentStep === 2 && selectedPlatform && (
            <StepAccount
              platform={selectedPlatform}
              selectedAccountId={selectedAccountId}
              onSelect={setSelectedAccountId}
            />
          )}
          {currentStep === 3 && selectedPlatform && (
            <Step2Config platform={selectedPlatform} config={config} onChange={handleConfigChange} />
          )}
          {currentStep === 4 && (
            <Step3AntiDetect
              enabled={antiDetectEnabled}
              config={antiDetectConfig}
              onEnabledChange={setAntiDetectEnabled}
              onConfigChange={setAntiDetectConfig}
            />
          )}
          {currentStep === 5 && (
            <Step3Proxy config={proxyConfig} onChange={handleProxyConfigChange} />
          )}
          {currentStep === 6 && (
            <Step4Confirm
              platform={selectedPlatform}
              config={config}
              proxyConfig={proxyConfig}
              selectedAccountId={selectedAccountId}
              onEdit={setCurrentStep}
            />
          )}
        </div>

        {/* 底部按钮 */}
        <div className="flex-shrink-0 px-12 py-6 border-t border-border bg-white">
          <div className="flex items-center gap-4">
            {currentStep > 1 && (
              <Button variant="secondary" onClick={handlePrev}>
                上一步
              </Button>
            )}
            {currentStep < 6 ? (
              <Button onClick={handleNext} disabled={!canProceed()}>
                下一步
              </Button>
            ) : (
              <Button
                variant="success"
                onClick={handleSubmit}
                className="gap-2"
              >
                <Play className="w-4 h-4" />
                开始执行任务
              </Button>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
