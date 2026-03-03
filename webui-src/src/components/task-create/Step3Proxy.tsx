import { Input, Switch } from '../common';

interface ProxyConfig {
  use_proxy: boolean;
  retry_count: number;
  timeout: number;
}

interface Step3ProxyProps {
  config: ProxyConfig;
  onChange: (config: Partial<ProxyConfig>) => void;
}

export function Step3Proxy({ config, onChange }: Step3ProxyProps) {
  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold font-display text-text-primary">
          代理设置
        </h2>
        <p className="text-sm text-text-secondary">
          配置代理池和轮询策略以避免被封禁
        </p>
      </div>

      {/* 启用代理开关 */}
      <div className="p-5 bg-slate-50 rounded-lg border border-slate-200">
        <Switch
          checked={config.use_proxy || false}
          onChange={(checked) => onChange({ use_proxy: checked })}
          label="启用代理"
          description="开启后将使用系统代理池进行数据采集"
        />
      </div>

      {/* 代理配置 */}
      {config.use_proxy && (
        <div className="grid grid-cols-2 gap-6">
          <div className="space-y-4">
            <Input
              label="重试次数"
              type="number"
              placeholder="3"
              value={config.retry_count || ''}
              onChange={(e) => onChange({ retry_count: parseInt(e.target.value) || 3 })}
            />
          </div>
          <div className="space-y-4">
            <Input
              label="超时时间(秒)"
              type="number"
              placeholder="30"
              value={config.timeout || ''}
              onChange={(e) => onChange({ timeout: parseInt(e.target.value) || 30 })}
            />
          </div>
        </div>
      )}

      <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
        <p className="text-sm text-blue-700">
          提示：代理池设置请前往「代理池管理」页面配置。此处仅控制当前任务是否使用代理。
        </p>
      </div>
    </div>
  );
}
