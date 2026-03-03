import { useState, useEffect, useCallback } from 'react'
import { AlertTriangle } from 'lucide-react'

interface ConfirmOptions {
  title?: string
  message: string
  confirmText?: string
  cancelText?: string
  variant?: 'default' | 'danger'
}

type ConfirmResolver = (value: boolean) => void

let showConfirm: ((options: ConfirmOptions, resolve: ConfirmResolver) => void) | null = null

export function confirm(options: ConfirmOptions): Promise<boolean> {
  return new Promise((resolve) => {
    if (showConfirm) {
      showConfirm(options, resolve)
    } else {
      resolve(false)
    }
  })
}

export function ConfirmContainer() {
  const [open, setOpen] = useState(false)
  const [options, setOptions] = useState<ConfirmOptions | null>(null)
  const [resolver, setResolver] = useState<ConfirmResolver | null>(null)

  useEffect(() => {
    showConfirm = (opts, resolve) => {
      setOptions(opts)
      setResolver(() => resolve)
      setOpen(true)
    }
    return () => {
      showConfirm = null
    }
  }, [])

  const handleConfirm = useCallback(() => {
    resolver?.(true)
    setOpen(false)
  }, [resolver])

  const handleCancel = useCallback(() => {
    resolver?.(false)
    setOpen(false)
  }, [resolver])

  if (!open || !options) return null

  const isDanger = options.variant === 'danger'

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      <div className="fixed inset-0 bg-black/50 animate-in fade-in-0" onClick={handleCancel} />
      <div className="relative z-10 w-full max-w-sm mx-4 bg-white rounded-xl shadow-2xl animate-in fade-in-0 zoom-in-95 duration-200">
        <div className="p-6">
          <div className="flex gap-4">
            {isDanger && (
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-red-600" />
              </div>
            )}
            <div className="flex-1 min-w-0">
              <h3 className="text-base font-semibold text-text-primary">
                {options.title || '确认操作'}
              </h3>
              <p className="mt-2 text-sm text-text-secondary leading-relaxed">
                {options.message}
              </p>
            </div>
          </div>
        </div>
        <div className="flex justify-end gap-3 px-6 py-4 bg-slate-50 rounded-b-xl border-t border-slate-100">
          <button
            onClick={handleCancel}
            className="px-4 py-2 text-sm font-medium text-text-secondary bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
          >
            {options.cancelText || '取消'}
          </button>
          <button
            onClick={handleConfirm}
            className={`px-4 py-2 text-sm font-medium text-white rounded-lg transition-colors ${
              isDanger
                ? 'bg-red-600 hover:bg-red-700'
                : 'bg-primary hover:bg-primary/90'
            }`}
          >
            {options.confirmText || '确定'}
          </button>
        </div>
      </div>
    </div>
  )
}
