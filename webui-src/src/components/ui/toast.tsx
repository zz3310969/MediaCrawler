// Toast 通知组件（简化版）
import { useState, useEffect } from 'react'
import { X, CheckCircle, AlertCircle, Info } from 'lucide-react'

export type ToastType = 'success' | 'error' | 'info'

interface Toast {
  id: number
  type: ToastType
  message: string
}

let toastIdCounter = 0
const toastListeners = new Set<(toast: Toast) => void>()

export const toast = {
  success: (message: string) => {
    const toast: Toast = { id: toastIdCounter++, type: 'success', message }
    toastListeners.forEach(listener => listener(toast))
  },
  error: (message: string) => {
    const toast: Toast = { id: toastIdCounter++, type: 'error', message }
    toastListeners.forEach(listener => listener(toast))
  },
  info: (message: string) => {
    const toast: Toast = { id: toastIdCounter++, type: 'info', message }
    toastListeners.forEach(listener => listener(toast))
  },
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<Toast[]>([])

  useEffect(() => {
    const listener = (toast: Toast) => {
      setToasts(prev => [...prev, toast])
      // 3秒后自动移除
      setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== toast.id))
      }, 3000)
    }

    toastListeners.add(listener)
    return () => {
      toastListeners.delete(listener)
    }
  }, [])

  const removeToast = (id: number) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }

  const getIcon = (type: ToastType) => {
    switch (type) {
      case 'success': return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'error': return <AlertCircle className="h-5 w-5 text-red-500" />
      case 'info': return <Info className="h-5 w-5 text-blue-500" />
    }
  }

  const getBgColor = (type: ToastType) => {
    switch (type) {
      case 'success': return 'bg-green-500/10 border-green-500/20'
      case 'error': return 'bg-red-500/10 border-red-500/20'
      case 'info': return 'bg-blue-500/10 border-blue-500/20'
    }
  }

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`flex items-center gap-3 px-4 py-3 rounded-lg border backdrop-blur-sm shadow-lg animate-in slide-in-from-top ${getBgColor(t.type)}`}
        >
          {getIcon(t.type)}
          <span className="text-sm text-foreground">{t.message}</span>
          <button
            onClick={() => removeToast(t.id)}
            className="ml-2 text-muted-foreground hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
    </div>
  )
}

