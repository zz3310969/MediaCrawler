import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Eye, EyeOff, Check, Github, Loader2 } from 'lucide-react';
import { createSession, loginWithPassword } from '../api/tasks';
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

  // 检查是否已有有效 session
  useEffect(() => {
    // 重置跳转状态
    resetRedirectState();
    
    const checkExistingSession = async () => {
      const sessionId = getStoredSessionId();
      if (sessionId) {
        // 已有 session，跳转到目标页面
        const redirectPath = getRedirectPath();
        navigate(redirectPath, { replace: true });
      } else {
        setCheckingSession(false);
      }
    };
    checkExistingSession();
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
      setError(err instanceof Error ? err.message : '登录失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  // 快速登录（创建匿名 session）
  const handleQuickLogin = async () => {
    setLoading(true);
    setError(null);
    
    try {
      await createSession();
      const redirectPath = getRedirectPath();
      navigate(redirectPath, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handleWechatLogin = () => {
    console.log('WeChat login');
  };

  const handleGithubLogin = () => {
    console.log('GitHub login');
  };

  // 检查 session 中显示加载状态
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
      {/* 左侧面板 - 蓝色渐变背景 */}
      <div
        className="w-[640px] min-h-screen p-[60px] flex flex-col justify-between"
        style={{
          background: 'linear-gradient(135deg, #1E40AF 0%, #3B82F6 50%, #60A5FA 100%)',
        }}
      >
        {/* Logo 区域 */}
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-white/20 flex items-center justify-center">
            <span className="text-xl font-bold text-white font-display">MC</span>
          </div>
          <span className="text-2xl font-semibold text-white font-display">MediaCrawler</span>
        </div>

        {/* 中间内容 */}
        <div className="space-y-8">
          {/* 主标题 */}
          <div className="space-y-4">
            <h1 className="text-5xl font-bold text-white font-display leading-tight">
              强大的多平台
            </h1>
            <h1 className="text-5xl font-bold text-white font-display leading-tight">
              数据爬取工具
            </h1>
          </div>

          {/* 副标题 */}
          <p className="text-lg text-white/80 leading-relaxed max-w-[480px]">
            支持小红书、抖音、快手、B站、微博等主流平台
            <br />
            一站式数据采集与分析解决方案
          </p>

          {/* 功能特点 */}
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-white/20 flex items-center justify-center">
                <Check className="w-4 h-4 text-white" />
              </div>
              <span className="text-[15px] font-medium text-white">高效稳定的数据爬取引擎</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-white/20 flex items-center justify-center">
                <Check className="w-4 h-4 text-white" />
              </div>
              <span className="text-[15px] font-medium text-white">智能代理池与反爬策略</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-white/20 flex items-center justify-center">
                <Check className="w-4 h-4 text-white" />
              </div>
              <span className="text-[15px] font-medium text-white">可视化数据分析与导出</span>
            </div>
          </div>
        </div>

        {/* 底部信息 */}
        <div className="space-y-2">
          <p className="text-sm text-white/60">© 2024 MediaCrawler. All rights reserved.</p>
          <p className="text-xs text-white/40">Version 2.0.0</p>
        </div>
      </div>

      {/* 右侧面板 - 登录表单 */}
      <div className="flex-1 min-h-screen flex items-center justify-center bg-white">
        <div className="w-[400px] space-y-8">
          {/* 表单头部 */}
          <div className="space-y-2">
            <h2 className="text-[32px] font-bold text-text-primary font-display">欢迎使用</h2>
            <p className="text-[15px] text-text-secondary">登录以开始使用爬虫管理系统</p>
          </div>

          {/* 错误提示 */}
          {error && (
            <div className="p-4 rounded-xl bg-red-50 border border-red-200">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {/* 快速登录按钮 */}
          <button
            type="button"
            onClick={handleQuickLogin}
            disabled={loading}
            className="w-full h-[52px] rounded-xl bg-primary text-base font-semibold text-white hover:bg-primary/90 transition-colors disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2.5"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>登录中...</span>
              </>
            ) : (
              <>
                <span>快速开始</span>
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>

          {/* 分隔线 */}
          <div className="flex items-center gap-4">
            <div className="flex-1 h-px bg-border" />
            <span className="text-[13px] text-slate-400">或使用账号登录</span>
            <div className="flex-1 h-px bg-border" />
          </div>

          {/* 登录表单 */}
          <form onSubmit={handleLogin} className="space-y-5">
            {/* 用户名 */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">用户名 / 邮箱</label>
              <input
                type="text"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                placeholder="请输入用户名或邮箱"
                className="w-full h-12 px-4 rounded-xl border border-border text-sm text-text-primary placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
              />
            </div>

            {/* 密码 */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-slate-700">密码</label>
                <button type="button" className="text-sm text-primary hover:text-primary/80 transition-colors">
                  忘记密码?
                </button>
              </div>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  placeholder="请输入密码"
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

            {/* 记住我 */}
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

            {/* 登录按钮 */}
            <button
              type="submit"
              disabled={loading}
              className="w-full h-12 rounded-xl border border-border text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? (
                <span>登录中...</span>
              ) : (
                <span>账号登录</span>
              )}
            </button>
          </form>

          {/* 分隔线 */}
          <div className="flex items-center gap-4">
            <div className="flex-1 h-px bg-border" />
            <span className="text-[13px] text-slate-400">第三方登录</span>
            <div className="flex-1 h-px bg-border" />
          </div>

          {/* 第三方登录 */}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleWechatLogin}
              className="flex-1 h-12 rounded-xl border border-border text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors flex items-center justify-center gap-2.5"
            >
              <div className="w-6 h-6 rounded bg-[#07C160] flex items-center justify-center">
                <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M8.691 2.188C3.891 2.188 0 5.476 0 9.53c0 2.212 1.17 4.203 3.002 5.55a.59.59 0 01.213.665l-.39 1.48c-.019.07-.048.141-.048.213 0 .163.13.295.29.295a.326.326 0 00.167-.054l1.903-1.114a.864.864 0 01.717-.098 10.16 10.16 0 002.837.403c.276 0 .543-.027.811-.05a5.79 5.79 0 01-.271-1.763c0-3.56 3.348-6.462 7.47-6.462.254 0 .503.022.754.04C16.501 4.816 12.953 2.188 8.691 2.188zm-2.03 5.03c.588 0 1.063.476 1.063 1.063a1.063 1.063 0 01-2.126 0c0-.587.476-1.063 1.063-1.063zm4.06 0c.588 0 1.063.476 1.063 1.063a1.063 1.063 0 01-2.126 0c0-.587.475-1.063 1.063-1.063zm5.979 3.31c-3.54 0-6.402 2.407-6.402 5.385 0 2.979 2.862 5.386 6.402 5.386.638 0 1.254-.072 1.846-.213a.71.71 0 01.588.08l1.56.914a.268.268 0 00.138.044c.131 0 .238-.107.238-.241 0-.059-.023-.117-.039-.174l-.32-1.211a.485.485 0 01.175-.545c1.5-1.106 2.459-2.736 2.459-4.54 0-2.978-2.862-5.385-6.645-5.385zm-2.426 3.317c.48 0 .869.389.869.869a.869.869 0 01-1.738 0c0-.48.39-.869.869-.869zm4.852 0c.48 0 .869.389.869.869a.869.869 0 01-1.738 0c0-.48.389-.869.869-.869z" />
                </svg>
              </div>
              微信
            </button>
            <button
              type="button"
              onClick={handleGithubLogin}
              className="flex-1 h-12 rounded-xl border border-border text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors flex items-center justify-center gap-2.5"
            >
              <Github className="w-[22px] h-[22px] text-[#24292F]" />
              GitHub
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
