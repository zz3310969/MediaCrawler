import { Shield, Info } from 'lucide-react';
import { Switch } from '../common';
import { AntiDetectConfig } from '../../api/antiDetect';

interface Step3AntiDetectProps {
  enabled: boolean;
  config: Partial<AntiDetectConfig>;
  onEnabledChange: (enabled: boolean) => void;
  onConfigChange: (config: Partial<AntiDetectConfig>) => void;
}

export function Step3AntiDetect({
  enabled,
  config,
  onEnabledChange,
  onConfigChange,
}: Step3AntiDetectProps) {
  const handleConfigChange = (key: keyof AntiDetectConfig, value: any) => {
    onConfigChange({ ...config, [key]: value });
  };

  return (
    <div className="space-y-6">
      {/* 标题 */}
      <div>
        <h2 className="text-2xl font-semibold text-foreground mb-2">反爬增强配置</h2>
        <p className="text-muted-foreground">
          启用反爬增强功能，降低被封禁风险
        </p>
      </div>

      {/* 启用开关 */}
      <div className="bg-card border border-border rounded-lg p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
              <Shield className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h3 className="font-medium text-foreground">启用反爬增强</h3>
              <p className="text-sm text-muted-foreground">
                账号-代理-指纹三重绑定，智能限速，人类行为模拟
              </p>
            </div>
          </div>
          <Switch checked={enabled} onChange={onEnabledChange} />
        </div>
      </div>

      {/* 详细配置 */}
      {enabled && (
        <div className="space-y-6">
          {/* 功能模块 */}
          <div className="bg-card border border-border rounded-lg p-6 space-y-4">
            <h3 className="font-medium text-foreground mb-4">功能模块</h3>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">浏览器指纹</p>
                  <p className="text-xs text-muted-foreground">随机化浏览器特征</p>
                </div>
                <Switch
                  checked={config.enable_fingerprint ?? true}
                  onChange={(checked: boolean) => handleConfigChange('enable_fingerprint', checked)}
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">智能限速</p>
                  <p className="text-xs text-muted-foreground">模拟人类浏览节奏</p>
                </div>
                <Switch
                  checked={config.enable_rate_limit ?? true}
                  onChange={(checked: boolean) => handleConfigChange('enable_rate_limit', checked)}
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">人类行为模拟</p>
                  <p className="text-xs text-muted-foreground">自然的滚动、点击、打字</p>
                </div>
                <Switch
                  checked={config.enable_human_behavior ?? true}
                  onChange={(checked: boolean) => handleConfigChange('enable_human_behavior', checked)}
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">账号健康管理</p>
                  <p className="text-xs text-muted-foreground">自动冷却高风险账号</p>
                </div>
                <Switch
                  checked={config.enable_account_health ?? true}
                  onChange={(checked: boolean) => handleConfigChange('enable_account_health', checked)}
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">账号-代理-指纹绑定</p>
                  <p className="text-xs text-muted-foreground">固定绑定，避免频繁切换</p>
                </div>
                <Switch
                  checked={config.enable_binding ?? true}
                  onChange={(checked: boolean) => handleConfigChange('enable_binding', checked)}
                />
              </div>
            </div>
          </div>

          {/* 限速配置 */}
          {config.enable_rate_limit && (
            <div className="bg-card border border-border rounded-lg p-6 space-y-4">
              <h3 className="font-medium text-foreground mb-4">限速配置</h3>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    最小间隔（秒）
                  </label>
                  <input
                    type="number"
                    min="0.5"
                    max="60"
                    step="0.5"
                    value={config.rate_limit_min_interval ?? 3.0}
                    onChange={(e) =>
                      handleConfigChange('rate_limit_min_interval', parseFloat(e.target.value))
                    }
                    className="w-full px-3 py-2 bg-background border border-input rounded-md text-foreground"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    最大间隔（秒）
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="120"
                    step="1"
                    value={config.rate_limit_max_interval ?? 10.0}
                    onChange={(e) =>
                      handleConfigChange('rate_limit_max_interval', parseFloat(e.target.value))
                    }
                    className="w-full px-3 py-2 bg-background border border-input rounded-md text-foreground"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    每小时限制
                  </label>
                  <input
                    type="number"
                    min="10"
                    max="1000"
                    step="10"
                    value={config.rate_limit_hourly_limit ?? 150}
                    onChange={(e) =>
                      handleConfigChange('rate_limit_hourly_limit', parseInt(e.target.value))
                    }
                    className="w-full px-3 py-2 bg-background border border-input rounded-md text-foreground"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    每天限制
                  </label>
                  <input
                    type="number"
                    min="100"
                    max="10000"
                    step="100"
                    value={config.rate_limit_daily_limit ?? 1500}
                    onChange={(e) =>
                      handleConfigChange('rate_limit_daily_limit', parseInt(e.target.value))
                    }
                    className="w-full px-3 py-2 bg-background border border-input rounded-md text-foreground"
                  />
                </div>
              </div>
            </div>
          )}

          {/* 提示信息 */}
          <div className="bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <div className="flex gap-3">
              <Info className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-blue-900 dark:text-blue-100">
                <p className="font-medium mb-1">核心功能：三重绑定</p>
                <p className="text-blue-700 dark:text-blue-300">
                  确保同一账号始终使用相同的代理IP和浏览器指纹，避免频繁切换导致风控。
                  绑定关系会自动持久化保存，重启后保持一致。
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
