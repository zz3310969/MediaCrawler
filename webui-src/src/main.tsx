import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

// 初始化主题
const initTheme = () => {
  const savedTheme = localStorage.getItem('theme') || 'dark'
  if (savedTheme === 'auto') {
    const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    document.documentElement.classList.toggle('dark', isDark)
  } else {
    document.documentElement.classList.toggle('dark', savedTheme === 'dark')
  }
}

initTheme()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)

