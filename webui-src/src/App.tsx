import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MainLayout } from './components/layout';
import {
  Dashboard,
  Tasks,
  TaskCreate,
  DataManagement,
  AccountManagement,
  ProxyManagement,
  Login,
} from './pages';

// 创建 QueryClient
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

// 系统设置页面占位
function Settings() {
  return (
    <div className="h-full flex flex-col bg-white overflow-hidden">
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="text-6xl">⚙️</div>
          <h2 className="text-2xl font-semibold font-display text-text-primary">系统设置</h2>
          <p className="text-text-secondary">功能开发中...</p>
        </div>
      </div>
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* 登录页面 - 独立布局 */}
          <Route path="/login" element={<Login />} />
          
          {/* 新建任务页面使用独立布局 */}
          <Route path="/tasks/create" element={<TaskCreate />} />
          
          {/* 其他页面使用主布局 */}
          <Route
            path="/*"
            element={
              <MainLayout>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/tasks" element={<Tasks />} />
                  <Route path="/data" element={<DataManagement />} />
                  <Route path="/proxy" element={<ProxyManagement />} />
                  <Route path="/accounts" element={<AccountManagement />} />
                  <Route path="/settings" element={<Settings />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </MainLayout>
            }
          />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
