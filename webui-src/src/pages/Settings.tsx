import { useState, useEffect, useCallback, useMemo } from 'react'
import { Save, Loader2, RotateCcw, Plug } from 'lucide-react'
import { PageHeader } from '../components/layout'
import { Button } from '../components/common'
import { configApi, ConfigDict, ConfigType } from '../api/config'
import { toast } from '../components/ui/toast'
import { confirm } from '../components/ui/confirm'
import { cn } from '../lib/utils'

// ==================== Tab 定义 ====================

interface TabDef {
  key: ConfigType
  label: string
}

const TABS: TabDef[] = [
  { key: 'crawler', label: '爬虫默认设置' },
  { key: 'browser', label: '浏览器与反检测' },
  { key: 'proxy', label: '代理池设置' },
  { key: 'account', label: '多账号策略' },
  { key: 'system', label: '系统运维' },
  { key: 'webhook', label: 'Webhook 通知' },
  { key: 'external', label: '外部服务' },
]

// ==================== 字段定义 ====================

type FieldType = 'text' | 'number' | 'switch' | 'select' | 'password'

interface FieldOption {
  value: string
  label: string
}

interface FieldDef {
  key: string
  label: string
  description?: string
  type: FieldType
  options?: FieldOption[]
  placeholder?: string
  suffix?: string
}

interface SectionDef {
  title: string
  description?: string
  fields: FieldDef[]
}

const SECTIONS: Record<ConfigType, SectionDef[]> = {
  crawler: [
    {
      title: '性能与限制',
      description: '控制爬取速度和资源消耗',
      fields: [
        { key: 'crawler.concurrency', label: '并发数', description: '同时采集的最大任务数', type: 'number' },
        { key: 'crawler.request_interval', label: '请求间隔', description: '两次请求之间的最小等待时间', type: 'number', suffix: '秒' },
        { key: 'crawler.max_retries', label: '最大重试次数', description: '请求失败后的重试上限', type: 'number' },
        { key: 'crawler.timeout', label: '请求超时', description: '单次请求的最大等待时间', type: 'number', suffix: '秒' },
        { key: 'crawler.max_note_count', label: '最大笔记数', description: '单次任务爬取的笔记上限', type: 'number' },
        { key: 'crawler.enable_comments', label: '启用评论采集', description: '开启后会同时采集笔记下的评论', type: 'switch' },
      ],
    },
    {
      title: '数据保存默认',
      fields: [
        {
          key: 'crawler.save_data_option',
          label: '默认保存方式',
          description: '任务创建时的默认数据存储方式',
          type: 'select',
          options: [
            { value: 'db', label: '数据库 (SQLite)' },
            { value: 'csv', label: 'CSV 文件' },
            { value: 'json', label: 'JSON 文件' },
            { value: 'excel', label: 'Excel 文件' },
          ],
        },
      ],
    },
  ],

  browser: [
    {
      title: '浏览器行为',
      fields: [
        { key: 'browser.headless', label: '无头模式', description: '开启后浏览器在后台运行，不显示窗口', type: 'switch' },
        { key: 'browser.cdp_mode', label: 'CDP 模式', description: '使用 Chrome DevTools Protocol 连接用户已有浏览器，降低被检测风险', type: 'switch' },
        { key: 'browser.save_login_state', label: '保存登录态', description: '下次启动时自动复用上次的 Cookie 和会话', type: 'switch' },
        { key: 'browser.stealth_js', label: '注入反检测脚本', description: '自动注入 stealth.js 绕过指纹检测', type: 'switch' },
      ],
    },
    {
      title: '自定义选项',
      fields: [
        { key: 'browser.user_agent', label: 'User-Agent', description: '留空则使用浏览器默认值', type: 'text', placeholder: '自定义 User-Agent...' },
        { key: 'browser.custom_path', label: '浏览器路径', description: '自定义 Chromium / Chrome 可执行文件路径', type: 'text', placeholder: '/Applications/Google Chrome.app/...' },
      ],
    },
  ],

  proxy: [
    {
      title: '代理池基础',
      fields: [
        { key: 'proxy.enable', label: '启用代理池', description: '开启后爬虫请求将通过代理 IP 发送', type: 'switch' },
        { key: 'proxy.pool_size', label: '池大小', description: '代理池同时维护的最大可用 IP 数', type: 'number' },
        { key: 'proxy.validate_timeout', label: '验证超时', description: '代理 IP 可用性测试的超时时间', type: 'number', suffix: '秒' },
      ],
    },
    {
      title: '绑定策略',
      fields: [
        { key: 'proxy.binding_sticky', label: '粘性绑定', description: '同一账号在会话期间使用固定 IP', type: 'switch' },
        { key: 'proxy.auto_rebind', label: '自动重绑', description: '绑定的代理失效时自动分配新代理', type: 'switch' },
      ],
    },
    {
      title: '代理提供商',
      fields: [
        {
          key: 'proxy.provider',
          label: '提供商',
          type: 'select',
          options: [
            { value: '', label: '无 (手动添加)' },
            { value: 'kuaidaili', label: '快代理' },
            { value: 'wandou', label: '豌豆 HTTP' },
          ],
        },
        { key: 'proxy.provider_api_url', label: '提取 API 地址', description: '从代理提供商获取的 API URL', type: 'text', placeholder: 'https://...' },
      ],
    },
  ],

  account: [
    {
      title: '多账号池',
      fields: [
        { key: 'account.pool_enable', label: '启用多账号', description: '开启后自动在多个账号间轮换', type: 'switch' },
        {
          key: 'account.rotation_strategy',
          label: '轮换策略',
          type: 'select',
          options: [
            { value: 'round_robin', label: '轮询 (Round Robin)' },
            { value: 'random', label: '随机' },
            { value: 'least_used', label: '最少使用' },
          ],
        },
        { key: 'account.cooldown_seconds', label: '冷却时间', description: '账号使用后的最小间隔', type: 'number', suffix: '秒' },
      ],
    },
    {
      title: '异常处理',
      fields: [
        { key: 'account.max_failures', label: '最大失败次数', description: '账号连续失败此次数后标记异常', type: 'number' },
        { key: 'account.auto_disable', label: '自动禁用', description: '失败次数超限后自动禁用该账号', type: 'switch' },
      ],
    },
  ],

  system: [
    {
      title: '日志与数据',
      fields: [
        {
          key: 'system.log_level',
          label: '日志级别',
          type: 'select',
          options: [
            { value: 'DEBUG', label: 'DEBUG' },
            { value: 'INFO', label: 'INFO' },
            { value: 'WARNING', label: 'WARNING' },
            { value: 'ERROR', label: 'ERROR' },
          ],
        },
        { key: 'system.data_retention_days', label: '数据保留天数', description: '超过此天数的数据将被自动清理', type: 'number', suffix: '天' },
      ],
    },
    {
      title: '运维选项',
      fields: [
        { key: 'system.maintenance_mode', label: '维护模式', description: '开启后将暂停所有爬虫任务', type: 'switch' },
        { key: 'system.auto_backup', label: '自动备份', description: '定期备份数据库和配置', type: 'switch' },
        { key: 'system.backup_interval_hours', label: '备份间隔', description: '自动备份的执行周期', type: 'number', suffix: '小时' },
      ],
    },
  ],

  webhook: [
    {
      title: 'Webhook 配置',
      fields: [
        { key: 'webhook.enable', label: '启用 Webhook', description: '开启后在关键事件发生时发送 HTTP 通知', type: 'switch' },
        { key: 'webhook.url', label: '回调地址', description: 'Webhook POST 请求的目标 URL', type: 'text', placeholder: 'https://your-server.com/webhook' },
        { key: 'webhook.secret', label: '签名密钥', description: '用于验证请求合法性的 HMAC 密钥', type: 'password', placeholder: '留空则不签名' },
        { key: 'webhook.retry_count', label: '重试次数', description: '推送失败后的最大重试次数', type: 'number' },
      ],
    },
    {
      title: '触发事件',
      description: '选择哪些事件触发 Webhook 推送',
      fields: [
        { key: 'webhook.on_task_complete', label: '任务完成', description: '爬虫任务成功结束时推送', type: 'switch' },
        { key: 'webhook.on_task_fail', label: '任务失败', description: '爬虫任务异常终止时推送', type: 'switch' },
        { key: 'webhook.on_account_banned', label: '账号封禁', description: '账号被平台封禁时推送', type: 'switch' },
      ],
    },
  ],

  external: [
    {
      title: '腾讯云 COS 存储',
      description: '用于上传爬取的媒体文件到云端对象存储',
      fields: [
        { key: 'external.cos_secret_id', label: 'SecretId', description: '腾讯云 API 密钥 ID', type: 'password', placeholder: 'AKIDxxxxxxxx' },
        { key: 'external.cos_secret_key', label: 'SecretKey', description: '腾讯云 API 密钥', type: 'password', placeholder: '密钥值' },
        {
          key: 'external.cos_region',
          label: 'Region',
          description: '存储桶所在地域',
          type: 'select',
          options: [
            { value: 'ap-beijing', label: '北京 (ap-beijing)' },
            { value: 'ap-shanghai', label: '上海 (ap-shanghai)' },
            { value: 'ap-guangzhou', label: '广州 (ap-guangzhou)' },
            { value: 'ap-chengdu', label: '成都 (ap-chengdu)' },
            { value: 'ap-nanjing', label: '南京 (ap-nanjing)' },
            { value: 'ap-hongkong', label: '香港 (ap-hongkong)' },
          ],
        },
        { key: 'external.cos_bucket_name', label: 'Bucket 名称', description: '存储桶名称 (含 appid 后缀)', type: 'text', placeholder: 'my-bucket-1250000000' },
        { key: 'external.cos_path_prefix', label: '存储路径前缀', description: '上传文件在 Bucket 中的目录前缀', type: 'text', placeholder: 'vip_posters/' },
        {
          key: 'external.cos_save_mode',
          label: '保存模式',
          type: 'select',
          options: [
            { value: 'local', label: '仅本地' },
            { value: 'oss', label: '仅云端 (COS)' },
            { value: 'both', label: '同时保存' },
          ],
        },
      ],
    },
    {
      title: '签名服务',
      description: '远程 JS 签名服务，用于生成平台请求签名',
      fields: [
        { key: 'external.sign_server_enable', label: '启用签名服务', description: '关闭则使用本地 Playwright 生成签名', type: 'switch' },
        { key: 'external.sign_server_url', label: '服务地址', description: '签名服务的 HTTP 地址', type: 'text', placeholder: 'http://localhost:8989' },
        { key: 'external.sign_server_timeout', label: '请求超时', description: '签名请求的最大等待时间', type: 'number', suffix: '秒' },
        { key: 'external.sign_server_retry', label: '重试次数', description: '签名请求失败后的最大重试次数', type: 'number' },
      ],
    },
  ],
}

// ==================== 字段渲染器 ====================

interface FieldRowProps {
  field: FieldDef
  value: unknown
  onChange: (key: string, value: unknown) => void
}

function FieldRow({ field, value, onChange }: FieldRowProps) {
  const renderControl = () => {
    switch (field.type) {
      case 'switch':
        return (
          <button
            type="button"
            role="switch"
            aria-checked={Boolean(value)}
            onClick={() => onChange(field.key, !value)}
            className={cn(
              'relative inline-flex h-7 w-[52px] items-center rounded-full transition-colors shrink-0',
              value ? 'bg-primary' : 'bg-slate-200'
            )}
          >
            <span
              className={cn(
                'inline-block h-[22px] w-[22px] transform rounded-full bg-white shadow-sm transition-transform',
                value ? 'translate-x-[27px]' : 'translate-x-[3px]'
              )}
            />
          </button>
        )

      case 'select':
        return (
          <div className="relative">
            <select
              value={String(value ?? '')}
              onChange={(e) => onChange(field.key, e.target.value)}
              className="h-10 pl-3 pr-8 rounded-lg border border-slate-200 bg-white text-sm text-text-primary appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
            >
              {field.options?.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        )

      case 'password':
        return (
          <input
            type="password"
            value={String(value ?? '')}
            onChange={(e) => onChange(field.key, e.target.value)}
            placeholder={field.placeholder}
            className="h-10 w-[320px] px-3 rounded-lg border border-slate-200 bg-white text-sm text-text-primary placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          />
        )

      case 'number':
        return (
          <div className="flex items-center gap-2">
            <input
              type="number"
              value={value === undefined || value === null ? '' : String(value)}
              onChange={(e) => {
                const v = e.target.value
                onChange(field.key, v === '' ? '' : Number(v))
              }}
              className="h-10 w-[120px] px-3 rounded-lg border border-slate-200 bg-white text-sm text-text-primary text-right focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
            />
            {field.suffix && (
              <span className="text-sm text-text-secondary">{field.suffix}</span>
            )}
          </div>
        )

      default:
        return (
          <input
            type="text"
            value={String(value ?? '')}
            onChange={(e) => onChange(field.key, e.target.value)}
            placeholder={field.placeholder}
            className="h-10 w-[320px] px-3 rounded-lg border border-slate-200 bg-white text-sm text-text-primary placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          />
        )
    }
  }

  return (
    <div className="flex items-center justify-between py-4 px-6 border-b border-slate-50 last:border-b-0">
      <div className="space-y-0.5">
        <div className="text-sm font-medium text-text-primary">{field.label}</div>
        {field.description && (
          <div className="text-xs text-text-secondary">{field.description}</div>
        )}
      </div>
      {renderControl()}
    </div>
  )
}

// ==================== Section 卡片 ====================

interface SectionCardProps {
  section: SectionDef
  values: ConfigDict
  onChange: (key: string, value: unknown) => void
  footer?: React.ReactNode
}

function SectionCard({ section, values, onChange, footer }: SectionCardProps) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-100">
        <h3 className="text-base font-semibold text-text-primary">{section.title}</h3>
        {section.description && (
          <p className="text-xs text-text-secondary mt-1">{section.description}</p>
        )}
      </div>
      <div>
        {section.fields.map((field) => (
          <FieldRow
            key={field.key}
            field={field}
            value={values[field.key]}
            onChange={onChange}
          />
        ))}
      </div>
      {footer && (
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-100">
          {footer}
        </div>
      )}
    </div>
  )
}

// ==================== 主组件 ====================

export function Settings() {
  const [activeTab, setActiveTab] = useState<ConfigType>('crawler')
  const [configs, setConfigs] = useState<ConfigDict>({})
  const [originalConfigs, setOriginalConfigs] = useState<ConfigDict>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [cosTesting, setCosTesting] = useState(false)

  const loadConfigs = useCallback(async (tab: ConfigType) => {
    setLoading(true)
    try {
      const data = await configApi.getGroup(tab)
      setConfigs(data)
      setOriginalConfigs(data)
    } catch {
      toast.error('加载配置失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadConfigs(activeTab)
  }, [activeTab, loadConfigs])

  const handleFieldChange = useCallback((key: string, value: unknown) => {
    setConfigs((prev) => ({ ...prev, [key]: value }))
  }, [])

  const hasChanges = useMemo(() => {
    return JSON.stringify(configs) !== JSON.stringify(originalConfigs)
  }, [configs, originalConfigs])

  const handleSave = async () => {
    setSaving(true)
    try {
      await configApi.updateGroup(activeTab, configs)
      setOriginalConfigs({ ...configs })
      toast.success('配置已保存')
    } catch {
      toast.error('保存失败，请重试')
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    setConfigs({ ...originalConfigs })
  }

  const handleTestCos = async () => {
    const secretId = String(configs['external.cos_secret_id'] ?? '')
    const secretKey = String(configs['external.cos_secret_key'] ?? '')
    const region = String(configs['external.cos_region'] ?? '')
    const bucketName = String(configs['external.cos_bucket_name'] ?? '')

    if (!secretId || !secretKey || !region || !bucketName) {
      toast.error('请先填写完整的 COS 配置（SecretId、SecretKey、Region、Bucket）')
      return
    }

    setCosTesting(true)
    try {
      const result = await configApi.testCos({
        secret_id: secretId,
        secret_key: secretKey,
        region,
        bucket_name: bucketName,
      })
      toast.success(result.message)
    } catch (err: any) {
      toast.error(err?.message || '测试失败')
    } finally {
      setCosTesting(false)
    }
  }

  const handleTabChange = async (tab: ConfigType) => {
    if (hasChanges) {
      const ok = await confirm({
        title: '未保存的更改',
        message: '当前页面有未保存的更改，切换后将丢失这些修改。确定要切换吗？',
        confirmText: '确定切换',
      })
      if (!ok) return
    }
    setActiveTab(tab)
  }

  const sections = SECTIONS[activeTab] ?? []

  return (
    <div className="h-full flex flex-col bg-slate-50 overflow-hidden">
      <div className="flex-1 overflow-y-auto p-8 space-y-6">
        {/* 头部 */}
        <PageHeader
          title="系统设置"
          subtitle="管理爬虫系统的全局配置参数"
          actions={
            <div className="flex items-center gap-3">
              <Button variant="secondary" onClick={handleReset} disabled={!hasChanges || saving}>
                <RotateCcw className="w-4 h-4" />
                恢复更改
              </Button>
              <Button onClick={handleSave} disabled={!hasChanges || saving}>
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                保存配置
              </Button>
            </div>
          }
        />

        {/* Tab 栏 */}
        <div className="border-b border-slate-200">
          <div className="flex gap-0">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => handleTabChange(tab.key)}
                className={cn(
                  'px-5 py-3 text-sm font-medium transition-colors border-b-2 -mb-px',
                  activeTab === tab.key
                    ? 'text-primary border-primary'
                    : 'text-text-secondary border-transparent hover:text-text-primary hover:border-slate-300'
                )}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* 内容区 */}
        {loading ? (
          <div className="flex items-center justify-center py-24">
            <Loader2 className="w-6 h-6 text-primary animate-spin" />
            <span className="ml-3 text-sm text-text-secondary">加载配置...</span>
          </div>
        ) : (
          <div className="space-y-6 pb-6">
            {sections.map((section) => (
              <SectionCard
                key={section.title}
                section={section}
                values={configs}
                onChange={handleFieldChange}
                footer={
                  section.title === '腾讯云 COS 存储' ? (
                    <div className="flex items-center gap-3">
                      <Button
                        variant="secondary"
                        onClick={handleTestCos}
                        disabled={cosTesting}
                        className="gap-1.5"
                      >
                        {cosTesting ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Plug className="w-4 h-4" />
                        )}
                        {cosTesting ? '测试中...' : '测试连接'}
                      </Button>
                      <span className="text-xs text-text-secondary">
                        使用当前填写的配置测试 COS 连通性（无需先保存）
                      </span>
                    </div>
                  ) : undefined
                }
              />
            ))}
          </div>
        )}
      </div>

    </div>
  )
}
