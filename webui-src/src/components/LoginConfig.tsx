import React, { useEffect } from 'react'
import { Key, QrCode, Smartphone } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { LoginType } from '@/api/crawler'

interface LoginConfigProps {
  platform: string
  loginType: LoginType
  cookies?: string
  disabled?: boolean
  onLoginTypeChange: (type: LoginType) => void
  onCookiesChange: (cookies: string) => void
}

// 不同平台支持的登录类型
const PLATFORM_LOGIN_OPTIONS: Record<string, { value: LoginType; label: string }[]> = {
  // 微信公众号支持 mp_qrcode, qrcode, cookie
  wechat: [
    { value: 'mp_qrcode', label: '公众号后台扫码 (推荐)' },
    { value: 'qrcode', label: '微信APP扫码' },
    { value: 'cookie', label: 'Cookie 登录' },
  ],
  // 其他平台支持 qrcode, phone, cookie
  default: [
    { value: 'qrcode', label: '扫码登录 (推荐)' },
    { value: 'phone', label: '手机验证码登录' },
    { value: 'cookie', label: 'Cookie 登录' },
  ],
}

// 获取当前登录类型的显示名称
function getLoginTypeLabel(loginType: LoginType, platform: string): string {
  const options = platform === 'wechat' ? PLATFORM_LOGIN_OPTIONS.wechat : PLATFORM_LOGIN_OPTIONS.default
  const option = options.find(o => o.value === loginType)
  return option?.label || loginType
}

// 检查登录类型是否为扫码类型
function isQrCodeType(loginType: LoginType): boolean {
  return loginType === 'qrcode' || loginType === 'mp_qrcode'
}

export function LoginConfig({ 
  platform, 
  loginType, 
  cookies, 
  disabled, 
  onLoginTypeChange, 
  onCookiesChange 
}: LoginConfigProps) {
  // 获取当前平台支持的登录选项
  const loginOptions = platform === 'wechat' ? PLATFORM_LOGIN_OPTIONS.wechat : PLATFORM_LOGIN_OPTIONS.default
  
  // 当平台变化时，自动切换到该平台支持的默认登录类型
  useEffect(() => {
    const supportedTypes = loginOptions.map(o => o.value)
    if (!supportedTypes.includes(loginType)) {
      // 当前登录类型不被新平台支持，切换到默认类型
      onLoginTypeChange(loginOptions[0].value)
    }
  }, [platform, loginType, loginOptions, onLoginTypeChange])
  
  return (
    <Card className="border-0 shadow-none">
      <CardHeader className="px-0 pt-0">
        <CardTitle className="text-base">登录配置</CardTitle>
        <CardDescription>
          选择登录方式，扫码登录更稳定，Cookie 登录适合调试
        </CardDescription>
      </CardHeader>
      <CardContent className="px-0 space-y-4">
        <div className="space-y-3">
          <Label>登录方式</Label>
          <Select
            value={loginType}
            onChange={(e) => onLoginTypeChange(e.target.value as LoginType)}
            disabled={disabled}
          >
            {loginOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
          
          <div className="flex items-center text-xs text-muted-foreground mt-1 gap-2">
             {isQrCodeType(loginType) ? (
               <QrCode className="h-3 w-3" />
             ) : loginType === 'phone' ? (
               <Smartphone className="h-3 w-3" />
             ) : (
               <Key className="h-3 w-3" />
             )}
             <span>当前: {getLoginTypeLabel(loginType, platform)}</span>
          </div>
        </div>

        {loginType === 'cookie' && (
          <div className="space-y-2">
            <Label htmlFor="cookies">Cookies</Label>
            <textarea
              id="cookies"
              placeholder="请粘贴 Cookies 字符串..."
              value={cookies || ''}
              onChange={(e) => onCookiesChange(e.target.value)}
              disabled={disabled}
              className="flex min-h-[100px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 font-mono text-xs"
            />
            <p className="text-[10px] text-muted-foreground">
              请确保 Cookies 包含必要的认证信息。
            </p>
          </div>
        )}

        {isQrCodeType(loginType) && (
          <div className="rounded-md bg-slate-50 dark:bg-slate-900 p-4 text-sm text-muted-foreground">
            <p>点击下方"启动登录"按钮，将会获取登录二维码。</p>
            <p className="mt-2 text-xs">如果是首次登录，获取二维码可能需要几秒钟。</p>
          </div>
        )}
        
        {loginType === 'phone' && (
          <div className="rounded-md bg-slate-50 dark:bg-slate-900 p-4 text-sm text-muted-foreground">
            <p>手机验证码登录需要配置短信接收服务。</p>
            <p className="mt-2 text-xs">详情请参考项目文档中的短信配置说明。</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
