import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff, Check, Loader2 } from 'lucide-react';
import { loginWithPassword } from '../api/tasks';
import { getStoredSessionId, getRedirectPath, resetRedirectState } from '../api/session';

export function Login() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    rememberMe: true,
  });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [checkingSession, setCheckingSession] = useState(true);

  useEffect(() => {
    resetRedirectState();
    const sessionId = getStoredSessionId();
    if (sessionId) {
      const redirectPath = getRedirectPath();
      navigate(redirectPath, { replace: true });
    } else {
      setCheckingSession(false);
    }
  }, [navigate]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.username.trim()) {
      setError('请输入用户名');
      return;
    }
    if (!formData.password) {
      setError('请输入密码');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      await loginWithPassword({
        username: formData.username.trim(),
        password: formData.password,
      });
      
      const redirectPath = getRedirectPath();
      navigate(redirectPath, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败，请检查用户名和密码');
    } finally {
      setLoading(false);
    }
  };

  if (checkingSession) {
    return (
      <div className="min-h-screen w-full flex items-center justify-center bg-white">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 text-primary animate-spin" />
          <p className="text-text-secondary">检查登录状态...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen w-full flex">
      {/* 左侧面板 */}
      <div
        className="w-[640px] min-h-screen p-[60px] flex flex-col justify-between"
        style={{
          background: 'linear-gradient(135deg, #1E40AF 0%, #3B82F6 50%, #60A5FA 100%)',
        }}
      >
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-white/20 flex items-center justify-center">
            <span className="text-xl font-bold text-white font-display">MC</span>
          </div>
          <span className="text-2xl font-semibold text-white font-display">MediaCrawler</span>
        </div>

        <div className="space-y-8">
          <div className="space-y-4">
            <h1 className="text-5xl font-bold text-white font-display leading-tight">
              强大的多平台
            </h1>
            <h1 className="text-5xl font-bold text-white font-display leading-tight">
              数据爬取工具
            </h1>
          </div>

          <p className="text-lg text-white/80 leading-relaxed max-w-[480px]">
            支持小红书、抖音、快手、B站、微博等主流平台
            <br />
            一站式数据采集与分析解决方案
          </p>

          <div className="space-y-4">
            {[
              '高效稳定的数据爬取引擎',
              '智能代理池与反爬策略',
              '可视化数据分析与导出',
            ].map((feature) => (
              <div key={feature} className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-white/20 flex items-center justify-center">
                  <Check className="w-4 h-4 text-white" />
                </div>
                <span className="text-[15px] font-medium text-white">{feature}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-sm text-white/60">© 2024 MediaCrawler. All rights reserved.</p>
          <p className="text-xs text-white/40">Version 2.0.0</p>
        </div>
      </div>

      {/* 右侧登录表单 */}
      <div className="flex-1 min-h-screen flex items-center justify-center bg-white">
        <div className="w-[400px] space-y-8">
          <div className="space-y-2">
            <h2 className="text-[32px] font-bold text-text-primary font-display">欢迎登录</h2>
            <p className="text-[15px] text-text-secondary">请使用账号密码登录以开始使用</p>
          </div>

          {error && (
            <div className="p-4 rounded-xl bg-red-50 border border-red-200">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-5">
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">用户名</label>
              <input
                type="text"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                placeholder="请输入用户名"
                autoComplete="username"
                className="w-full h-12 px-4 rounded-xl border border-border text-sm text-text-primary placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">密码</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  placeholder="请输入密码"
                  autoComplete="current-password"
                  className="w-full h-12 px-4 pr-12 rounded-xl border border-border text-sm text-text-primary placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary transition-colors"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <div className="flex items-center gap-2.5">
              <button
                type="button"
                onClick={() => setFormData({ ...formData, rememberMe: !formData.rememberMe })}
                className={`w-5 h-5 rounded flex items-center justify-center transition-colors ${
                  formData.rememberMe ? 'bg-primary' : 'border border-border'
                }`}
              >
                {formData.rememberMe && <Check className="w-3.5 h-3.5 text-white" />}
              </button>
              <span className="text-sm text-slate-700">记住我的登录状态</span>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full h-[52px] rounded-xl bg-primary text-base font-semibold text-white hover:bg-primary/90 transition-colors disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2.5"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>登录中...</span>
                </>
              ) : (
                <span>登录</span>
              )}
            </button>
          </form>

          <p className="text-center text-xs text-slate-400">
            默认管理员账号：admin / admin123
          </p>
        </div>
      </div>
    </div>
  );
}
