// 主题切换组件
import { useState, useEffect } from 'react'
import { Sun, Moon, Monitor, ChevronDown, Check } from 'lucide-react'

type Theme = 'light' | 'dark' | 'auto'

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem('theme') as Theme
    return saved || 'dark'
  })
  const [isOpen, setIsOpen] = useState(false)

  useEffect(() => {
    const root = document.documentElement
    
    if (theme === 'auto') {
      // 自动模式：根据系统主题
      const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      root.classList.toggle('dark', isDark)
      root.classList.toggle('light', !isDark)
    } else {
      // 手动模式
      root.classList.toggle('dark', theme === 'dark')
      root.classList.toggle('light', theme === 'light')
    }
    
    localStorage.setItem('theme', theme)
  }, [theme])

  const handleThemeChange = (newTheme: Theme) => {
    setTheme(newTheme)
    setIsOpen(false)
  }

  const themeOptions = [
    { value: 'light' as Theme, label: 'Light', icon: Sun },
    { value: 'dark' as Theme, label: 'Dark', icon: Moon },
    { value: 'auto' as Theme, label: 'Auto', icon: Monitor },
  ]

  const currentTheme = themeOptions.find(t => t.value === theme)
  const CurrentIcon = currentTheme?.icon || Sun

  return (
    <div className="relative">
      {/* 按钮 */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-400 bg-slate-800/50 border border-slate-700 rounded-md hover:bg-slate-800 hover:text-gray-300 transition-colors"
      >
        <CurrentIcon className="h-4 w-4" />
        <span className="capitalize">{theme}</span>
        <ChevronDown className="h-3 w-3" />
      </button>

      {/* 下拉菜单 */}
      {isOpen && (
        <>
          {/* 背景遮罩 */}
          <div 
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          
          {/* 菜单内容 */}
          <div className="absolute right-0 mt-2 w-48 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-20 overflow-hidden">
            {themeOptions.map((option) => {
              const Icon = option.icon
              const isSelected = theme === option.value
              
              return (
                <button
                  key={option.value}
                  onClick={() => handleThemeChange(option.value)}
                  className={`w-full flex items-center justify-between px-4 py-3 text-sm hover:bg-slate-700/50 transition-colors ${
                    isSelected ? 'bg-cyan-500/10 text-cyan-400' : 'text-gray-300'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon className="h-4 w-4" />
                    <span>{option.label}</span>
                  </div>
                  {isSelected && <Check className="h-4 w-4 text-cyan-400" />}
                </button>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}

