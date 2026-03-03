/**
 * API 数据获取 Hooks
 */
import { useState, useEffect, useCallback } from 'react'

interface UseApiState<T> {
  data: T | null
  loading: boolean
  error: Error | null
}

interface UseApiResult<T> extends UseApiState<T> {
  refetch: () => Promise<void>
}

/**
 * 通用 API 请求 Hook
 */
export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = []
): UseApiResult<T> {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: true,
    error: null,
  })

  const fetchData = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }))
    try {
      const data = await fetcher()
      setState({ data, loading: false, error: null })
    } catch (err) {
      setState({ data: null, loading: false, error: err as Error })
    }
  }, [fetcher])

  useEffect(() => {
    fetchData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return {
    ...state,
    refetch: fetchData,
  }
}

/**
 * 带轮询的 API 请求 Hook
 */
export function usePollingApi<T>(
  fetcher: () => Promise<T>,
  intervalMs: number,
  enabled: boolean = true
): UseApiResult<T> {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: true,
    error: null,
  })

  const fetchData = useCallback(async () => {
    try {
      const data = await fetcher()
      setState({ data, loading: false, error: null })
    } catch (err) {
      setState((prev) => ({ ...prev, loading: false, error: err as Error }))
    }
  }, [fetcher])

  useEffect(() => {
    if (!enabled) return

    fetchData()
    const timer = setInterval(fetchData, intervalMs)

    return () => clearInterval(timer)
  }, [enabled, intervalMs, fetchData])

  return {
    ...state,
    refetch: fetchData,
  }
}

/**
 * 突变（创建/更新/删除）Hook
 */
export function useMutation<T, P>(
  mutator: (params: P) => Promise<T>
): {
  mutate: (params: P) => Promise<T>
  loading: boolean
  error: Error | null
  data: T | null
  reset: () => void
} {
  const [state, setState] = useState<{
    loading: boolean
    error: Error | null
    data: T | null
  }>({
    loading: false,
    error: null,
    data: null,
  })

  const mutate = useCallback(
    async (params: P): Promise<T> => {
      setState({ loading: true, error: null, data: null })
      try {
        const data = await mutator(params)
        setState({ loading: false, error: null, data })
        return data
      } catch (err) {
        setState({ loading: false, error: err as Error, data: null })
        throw err
      }
    },
    [mutator]
  )

  const reset = useCallback(() => {
    setState({ loading: false, error: null, data: null })
  }, [])

  return {
    ...state,
    mutate,
    reset,
  }
}
