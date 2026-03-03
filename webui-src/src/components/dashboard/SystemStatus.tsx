import { Progress } from '../common';
import { SystemStatus as SystemStatusType } from '../../types';

interface SystemStatusProps {
  status: SystemStatusType;
}

export function SystemStatus({ status }: SystemStatusProps) {
  return (
    <div className="bg-white rounded-lg border border-border p-5 space-y-4">
      {/* 头部 */}
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold font-display text-text-primary">系统状态</h3>
        <span className="text-xs text-success">● 运行中</span>
      </div>

      {/* 状态列表 */}
      <div className="space-y-4">
        {/* CPU */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-text-secondary">CPU 使用率</span>
            <span className="text-text-primary font-medium">{status.cpu}%</span>
          </div>
          <Progress
            value={status.cpu}
            size="sm"
            color={status.cpu > 80 ? 'error' : status.cpu > 60 ? 'warning' : 'primary'}
          />
        </div>

        {/* 内存 */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-text-secondary">内存使用</span>
            <span className="text-text-primary font-medium">{status.memory}%</span>
          </div>
          <Progress
            value={status.memory}
            size="sm"
            color={status.memory > 80 ? 'error' : status.memory > 60 ? 'warning' : 'primary'}
          />
        </div>

        {/* 网络 */}
        <div className="flex justify-between text-sm">
          <span className="text-text-secondary">网络状态</span>
          <span className="text-text-primary font-medium">{status.network}</span>
        </div>

        {/* 运行时间 */}
        <div className="flex justify-between text-sm">
          <span className="text-text-secondary">运行时间</span>
          <span className="text-text-primary font-medium">{status.uptime}</span>
        </div>
      </div>
    </div>
  );
}
