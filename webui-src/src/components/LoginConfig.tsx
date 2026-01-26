// 登录配置卡片
import { Key } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { crawlerApi, type LoginType } from '@/api/crawler'

interface LoginConfigProps {
  loginType: LoginType
  cookies?: string
  disabled?: boolean
  onLoginTypeChange: (value: LoginType) => void
  onCookiesChange?: (value: string) => void
}

export function LoginConfig({
  loginType,
  cookies,
  disabled,
  onLoginTypeChange,
  onCookiesChange,
}: LoginConfigProps) {
  // 获取配置选项
  const { data: configOptions } = useQuery({
    queryKey: ['config-options'],
    queryFn: crawlerApi.getConfigOptions,
  })

  const loginTypes = configOptions?.data?.login_types || []

  return (
    <Card className="h-full">
      <CardHeader className="pb-1.5 pt-3 px-4">
        <div className="flex items-center gap-2">
          <Key className="h-5 w-5 text-green-400" />
          <div className="flex items-baseline gap-2">
            <CardTitle className="text-base font-medium">登录配置</CardTitle>
            <CardDescription className="text-xs text-muted-foreground/60">
              登录方式配置
            </CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-2 px-4 pb-3">
        {/* 登录方式 */}
        <div className="space-y-1">
          <Label className="text-xs">登录方式</Label>
          <Select
            value={loginType}
            onChange={(e) => onLoginTypeChange(e.target.value as LoginType)}
            disabled={disabled || loginTypes.length === 0}
          >
            {loginTypes.map((t: { value: string; label: string }) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </Select>
        </div>

        {/* Cookie 输入框（仅在 Cookie 登录时显示） */}
        {loginType === 'cookie' && (
          <div className="space-y-1">
            <Label className="text-xs">Cookies</Label>
            <p className="text-xs text-muted-foreground">粘贴 Cookie 字符串</p>
            <textarea
              placeholder="在此粘贴 Cookies..."
              value={cookies}
              onChange={(e) => onCookiesChange?.(e.target.value)}
              disabled={disabled}
              className="w-full h-20 px-3 py-2 text-sm rounded-md border border-input bg-background resize-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring placeholder:text-xs placeholder:text-muted-foreground"
            />
          </div>
        )}

        {/* 提示信息 */}
        {loginType !== 'cookie' && (
          <div className="mt-6 p-3 bg-blue-500/10 border border-blue-500/20 rounded-md">
            <p className="text-xs text-blue-400">
              {loginType === 'qrcode' && '扫码登录：启动后会弹出二维码窗口'}
              {loginType === 'phone' && '手机号登录：需要手动输入验证码'}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

