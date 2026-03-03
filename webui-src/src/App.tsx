import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MainLayout } from './components/layout';
import { ToastContainer } from './components/ui/toast';
import { ConfirmContainer } from './components/ui/confirm';
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

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastContainer />
      <ConfirmContainer />
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
                  <Route path="/tasks/:taskId" element={<TaskDetail />} />
                  <Route path="/data" element={<DataManagement />} />
                  <Route path="/proxy" element={<ProxyManagement />} />
                  <Route path="/schedules" element={<ScheduleManagement />} />
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
