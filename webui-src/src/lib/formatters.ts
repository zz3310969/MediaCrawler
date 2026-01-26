// 格式化工具函数

/**
 * 格式化文件大小
 */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

/**
 * 格式化时间戳
 */
export function formatDate(timestamp: number): string {
  const date = new Date(timestamp * 1000)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).replace(/\//g, '/')
}

/**
 * 提取文件类别（从路径中）
 */
export function extractCategory(filePath: string): string {
  const match = filePath.match(/^([^/]+)\//)
  if (match) {
    return match[1]
  }
  
  // 从文件名推断
  if (filePath.includes('vip_contents')) return 'Vip'
  if (filePath.includes('_contents_')) return 'Contents'
  if (filePath.includes('comments')) return 'Comments'
  if (filePath.includes('creator_content')) return 'Creator Contents'
  if (filePath.includes('creator_creator')) return 'Creator Creators'
  
  return 'Other'
}

/**
 * 截断长文本
 */
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return `${text.slice(0, maxLength)}...`
}

