import React from 'react'
import { Key, QrCode } from 'lucide-react'
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

export function LoginConfig({ 
  platform, 
  loginType, 
  cookies, 
  disabled, 
  onLoginTypeChange, 
  onCookiesChange 
}: LoginConfigProps) {
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
            <option value="mp_qrcode">扫码登录 (推荐)</option>
            <option value="cookie">Cookie 登录</option>
          </Select>
          
          <div className="flex items-center text-xs text-muted-foreground mt-1 gap-2">
             {loginType === 'mp_qrcode' ? <QrCode className="h-3 w-3" /> : <Key className="h-3 w-3" />}
             <span>当前: {loginType === 'mp_qrcode' ? '扫码登录' : 'Cookie 登录'}</span>
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

        {loginType === 'mp_qrcode' && (
          <div className="rounded-md bg-slate-50 dark:bg-slate-900 p-4 text-sm text-muted-foreground">
            <p>点击下方"启动登录"按钮，将会获取登录二维码。</p>
            <p className="mt-2 text-xs">如果是首次登录，获取二维码可能需要几秒钟。</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
