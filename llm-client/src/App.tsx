import React, { useEffect } from 'react';
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Chat from './pages/Chat';
import AuditLogs from './pages/AuditLogs';
import Settings from './pages/Settings';
import MainLayout from './components/Layout/MainLayout';
import { useAuthStore } from './store/useAuthStore';
import './App.css';

const App: React.FC = () => {
  const { isAuthenticated, initAuth } = useAuthStore();

  useEffect(() => {
    initAuth();
    if (window.electronAPI) {
      window.electronAPI.getAppVersion().catch(err => console.error(err));
    }
  }, [initAuth]);

  return (
    <ConfigProvider locale={zhCN}>
      <HashRouter>
        <Routes>
          {/* Public Routes */}
          <Route 
            path="/login" 
            element={isAuthenticated ? <Navigate to="/dashboard" /> : <Login />} 
          />

          {/* Protected Routes */}
          <Route element={isAuthenticated ? <MainLayout /> : <Navigate to="/login" />}>
             <Route path="/dashboard" element={<Dashboard />} />
             <Route path="/chat" element={<Chat />} />
             <Route path="/logs" element={<AuditLogs />} />
             <Route path="/settings" element={<Settings />} />
          </Route>

          {/* Default Redirect */}
          <Route 
            path="*" 
            element={<Navigate to={isAuthenticated ? "/dashboard" : "/login"} />} 
          />
        </Routes>
      </HashRouter>
    </ConfigProvider>
  );
};

export default App;