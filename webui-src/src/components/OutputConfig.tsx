// 输出配置卡片
import { FileOutput } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { crawlerApi, type SaveOption } from '@/api/crawler'

interface OutputConfigProps {
  saveOption: SaveOption
  enableComments: boolean
  enableSubComments: boolean
  headless: boolean
  disabled?: boolean
  onSaveOptionChange: (value: SaveOption) => void
  onEnableCommentsChange: (value: boolean) => void
  onEnableSubCommentsChange: (value: boolean) => void
  onHeadlessChange: (value: boolean) => void
}

export function OutputConfig({
  saveOption,
  enableComments,
  enableSubComments,
  headless,
  disabled,
  onSaveOptionChange,
  onEnableCommentsChange,
  onEnableSubCommentsChange,
  onHeadlessChange,
}: OutputConfigProps) {
  // 获取配置选项
  const { data: configOptions } = useQuery({
    queryKey: ['config-options'],
    queryFn: crawlerApi.getConfigOptions,
  })

  const saveOptions = configOptions?.save_options || []

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <FileOutput className="h-5 w-5 text-purple-400" />
          <span>输出配置</span>
        </CardTitle>
        <CardDescription className="text-xs">
          爬取和后处理选项
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* 保存格式 */}
        <div className="space-y-1.5">
          <Label className="text-xs">保存格式</Label>
          <Select
            value={saveOption}
            onChange={(e) => onSaveOptionChange(e.target.value as SaveOption)}
            disabled={disabled || saveOptions.length === 0}
          >
            {saveOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
        </div>

        {/* 爬取选项 */}
        <div className="space-y-3 pt-2">
          <label
            htmlFor="enable-comments"
            className="flex items-center justify-between py-2 px-3 bg-secondary/50 rounded-md cursor-pointer hover:bg-secondary/70 transition-colors"
          >
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="enable-comments"
                checked={enableComments}
                onChange={(e) => onEnableCommentsChange(e.target.checked)}
                disabled={disabled}
                className="w-4 h-4 rounded border-gray-600 bg-gray-700 cursor-pointer"
              />
              <span className="text-sm">评论抓取</span>
            </div>
          </label>

          <label
            htmlFor="enable-sub-comments"
            className="flex items-center justify-between py-2 px-3 bg-secondary/50 rounded-md cursor-pointer hover:bg-secondary/70 transition-colors"
          >
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="enable-sub-comments"
                checked={enableSubComments}
                onChange={(e) => onEnableSubCommentsChange(e.target.checked)}
                disabled={disabled}
                className="w-4 h-4 rounded border-gray-600 bg-gray-700 cursor-pointer"
              />
              <span className="text-sm">子评论</span>
            </div>
          </label>

          <label
            htmlFor="headless"
            className="flex items-center justify-between py-2 px-3 bg-secondary/50 rounded-md cursor-pointer hover:bg-secondary/70 transition-colors"
          >
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="headless"
                checked={headless}
                onChange={(e) => onHeadlessChange(e.target.checked)}
                disabled={disabled}
                className="w-4 h-4 rounded border-gray-600 bg-gray-700 cursor-pointer"
              />
              <span className="text-sm">无头模式</span>
            </div>
          </label>
        </div>
      </CardContent>
    </Card>
  )
}

