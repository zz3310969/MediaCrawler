import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MainLayout } from './components/layout';
import { ToastContainer } from './components/ui/toast';
import { ConfirmContainer } from './components/ui/confirm';
import { getStoredSessionId } from './api/session';
import {
  Dashboard,
  Tasks,
  TaskCreate,
  TaskDetail,
  DataManagement,
  AccountManagement,
  ProxyManagement,
  ScheduleManagement,
  Settings,
  Login,
} from './pages';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const sessionId = getStoredSessionId();
  if (!sessionId) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastContainer />
      <ConfirmContainer />
      <BrowserRouter>
        <Routes>
          {/* 登录页面 - 公开访问 */}
          <Route path="/login" element={<Login />} />
          
          {/* 新建任务页面 - 需要登录 */}
          <Route
            path="/tasks/create"
            element={
              <PrivateRoute>
                <TaskCreate />
              </PrivateRoute>
            }
          />
          
          {/* 其他页面使用主布局 - 需要登录 */}
          <Route
            path="/*"
            element={
              <PrivateRoute>
                <MainLayout>
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/tasks" element={<Tasks />} />
                    <Route path="/tasks/:taskId" element={<TaskDetail />} />
                    <Route path="/data" element={<DataManagement />} />
                    <Route path="/proxy" element={<ProxyManagement />} />
                    <Route path="/schedules" element={<ScheduleManagement />} />
                    <Route path="/accounts" element={<AccountManagement />} />
                    <Route path="/settings" element={<Settings />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                </MainLayout>
              </PrivateRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
