import { useState, useEffect } from 'react';
import { X, Server, Plus, Zap, Eye, EyeOff, ChevronDown } from 'lucide-react';
import { Proxy, ProxyProtocol } from '../../types';

interface AddProxyModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (proxy: Omit<Proxy, 'id' | 'status' | 'createdAt'>) => void;
  editProxy?: Proxy | null;
}

const regions = [
  '北京', '上海', '广州', '深圳', '杭州', '成都', '南京', '武汉', '西安', '重庆',
  '天津', '苏州', '郑州', '长沙', '青岛', '大连', '厦门', '福州', '济南', '合肥',
];

export function AddProxyModal({ open, onClose, onSubmit, editProxy }: AddProxyModalProps) {
  const [formData, setFormData] = useState({
    ip: '',
    port: '',
    protocol: 'HTTP' as ProxyProtocol,
    username: '',
    password: '',
    region: '',
    remark: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<'success' | 'failed' | null>(null);

  // 编辑模式时填充数据
  useEffect(() => {
    if (editProxy) {
      setFormData({
        ip: editProxy.ip,
        port: String(editProxy.port),
        protocol: editProxy.protocol,
        username: editProxy.username || '',
        password: editProxy.password || '',
        region: editProxy.region || '',
        remark: editProxy.remark || '',
      });
    } else {
      setFormData({
        ip: '',
        port: '',
        protocol: 'HTTP',
        username: '',
        password: '',
        region: '',
        remark: '',
      });
    }
    setTestResult(null);
  }, [editProxy, open]);

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    // 模拟测试连接
    await new Promise((resolve) => setTimeout(resolve, 1500));
    setTestResult(Math.random() > 0.3 ? 'success' : 'failed');
    setTesting(false);
  };

  const handleSubmit = () => {
    if (!formData.ip || !formData.port || !formData.protocol) return;
    
    onSubmit({
      ip: formData.ip,
      port: parseInt(formData.port),
      protocol: formData.protocol,
      username: formData.username || undefined,
      password: formData.password || undefined,
      region: formData.region || undefined,
      remark: formData.remark || undefined,
    });
    onClose();
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* 遮罩层 */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />

      {/* 弹窗内容 */}
      <div className="relative bg-white rounded-2xl shadow-2xl w-[520px] overflow-hidden">
        {/* 头部 */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center">
              <Server className="w-5 h-5 text-primary" />
            </div>
            <span className="text-lg font-semibold text-text-primary">
              {editProxy ? '编辑代理' : '添加代理'}
            </span>
          </div>
          <button
            onClick={onClose}
            className="w-9 h-9 flex items-center justify-center rounded-lg border border-border hover:bg-slate-50 transition-colors"
          >
            <X className="w-[18px] h-[18px] text-text-secondary" />
          </button>
        </div>

        {/* 表单内容 */}
        <div className="p-6 space-y-5">
          {/* 代理地址 */}
          <div className="space-y-2">
            <label className="flex items-center gap-1 text-sm font-medium text-slate-700">
              代理地址
              <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={formData.ip}
              onChange={(e) => setFormData({ ...formData, ip: e.target.value })}
              placeholder="请输入代理IP地址，如 192.168.1.100"
              className="w-full h-11 px-3.5 rounded-lg border border-border text-sm text-text-primary placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
            />
          </div>

          {/* 端口 + 协议 */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="flex items-center gap-1 text-sm font-medium text-slate-700">
                端口
                <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                value={formData.port}
                onChange={(e) => setFormData({ ...formData, port: e.target.value })}
                placeholder="如 8080"
                className="w-full h-11 px-3.5 rounded-lg border border-border text-sm text-text-primary placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
              />
            </div>
            <div className="space-y-2">
              <label className="flex items-center gap-1 text-sm font-medium text-slate-700">
                协议
                <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <select
                  value={formData.protocol}
                  onChange={(e) => setFormData({ ...formData, protocol: e.target.value as ProxyProtocol })}
                  className="w-full h-11 px-3.5 pr-10 rounded-lg border border-border text-sm text-text-primary bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors appearance-none"
                >
                  <option value="HTTP">HTTP</option>
                  <option value="HTTPS">HTTPS</option>
                  <option value="SOCKS5">SOCKS5</option>
                </select>
                <ChevronDown className="absolute right-3.5 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-text-secondary pointer-events-none" />
              </div>
            </div>
          </div>

          {/* 用户名 + 密码 */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="flex items-center gap-1 text-sm font-medium text-slate-700">
                用户名
                <span className="text-xs text-slate-400">(可选)</span>
              </label>
              <input
                type="text"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                placeholder="请输入用户名"
                className="w-full h-11 px-3.5 rounded-lg border border-border text-sm text-text-primary placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
              />
            </div>
            <div className="space-y-2">
              <label className="flex items-center gap-1 text-sm font-medium text-slate-700">
                密码
                <span className="text-xs text-slate-400">(可选)</span>
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  placeholder="请输入密码"
                  className="w-full h-11 px-3.5 pr-10 rounded-lg border border-border text-sm text-text-primary placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary transition-colors"
                >
                  {showPassword ? <EyeOff className="w-[18px] h-[18px]" /> : <Eye className="w-[18px] h-[18px]" />}
                </button>
              </div>
            </div>
          </div>

          {/* 地区 */}
          <div className="space-y-2">
            <label className="flex items-center gap-1 text-sm font-medium text-slate-700">
              地区
              <span className="text-xs text-slate-400">(可选)</span>
            </label>
            <div className="relative">
              <select
                value={formData.region}
                onChange={(e) => setFormData({ ...formData, region: e.target.value })}
                className="w-full h-11 px-3.5 pr-10 rounded-lg border border-border text-sm text-text-primary bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors appearance-none"
              >
                <option value="">请选择地区</option>
                {regions.map((region) => (
                  <option key={region} value={region}>{region}</option>
                ))}
              </select>
              <ChevronDown className="absolute right-3.5 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-text-secondary pointer-events-none" />
            </div>
          </div>

          {/* 备注 */}
          <div className="space-y-2">
            <label className="flex items-center gap-1 text-sm font-medium text-slate-700">
              备注
              <span className="text-xs text-slate-400">(可选)</span>
            </label>
            <textarea
              value={formData.remark}
              onChange={(e) => setFormData({ ...formData, remark: e.target.value })}
              placeholder="请输入备注信息，如代理用途等"
              rows={3}
              className="w-full px-3.5 py-3 rounded-lg border border-border text-sm text-text-primary placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors resize-none"
            />
          </div>

          {/* 测试结果 */}
          {testResult && (
            <div
              className={`flex items-center gap-2 px-3.5 py-2.5 rounded-lg text-sm ${
                testResult === 'success'
                  ? 'bg-emerald-50 text-emerald-600'
                  : 'bg-red-50 text-red-600'
              }`}
            >
              {testResult === 'success' ? '✓ 连接测试成功' : '✗ 连接测试失败，请检查代理配置'}
            </div>
          )}
        </div>

        {/* 底部按钮 */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-border">
          <button
            onClick={onClose}
            className="h-11 px-6 rounded-lg border border-border text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleTest}
            disabled={!formData.ip || !formData.port || testing}
            className="h-11 px-6 rounded-lg bg-slate-50 border border-border text-sm font-medium text-slate-700 hover:bg-slate-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <Zap className={`w-4 h-4 ${testing ? 'animate-pulse' : ''}`} />
            {testing ? '测试中...' : '测试连接'}
          </button>
          <button
            onClick={handleSubmit}
            disabled={!formData.ip || !formData.port}
            className="h-11 px-6 rounded-lg bg-primary text-sm font-medium text-white hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            {editProxy ? '保存修改' : '添加代理'}
          </button>
        </div>
      </div>
    </div>
  );
}
