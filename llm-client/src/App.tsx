import React, { useEffect } from 'react';
import { ConfigProvider, theme, Layout } from 'antd';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './pages/Login';
import ChatPage from './pages/Chat';
import SettingsPage from './pages/Settings';
import { useAuthStore } from './store/useAuthStore';
import './App.css';

const { Content } = Layout;

const App: React.FC = () => {
  const { isAuthenticated, initAuth } = useAuthStore();

  useEffect(() => {
    // 初始化认证状态
    initAuth();

    // 获取应用版本
    if (window.electronAPI) {
      window.electronAPI.getAppVersion().then(version => {
        console.log('应用版本:', version);
      });
    }
  }, [initAuth]);

  return (
    <ConfigProvider
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: '#1890ff',
          borderRadius: 6,
        },
      }}
    >
      <BrowserRouter>
        <Layout style={{ minHeight: '100vh' }}>
          <Content>
            <Routes>
              <Route
                path="/login"
                element={isAuthenticated ? <Navigate to="/chat" /> : <LoginPage />}
              />
              <Route
                path="/chat"
                element={isAuthenticated ? <ChatPage /> : <Navigate to="/login" />}
              />
              <Route
                path="/settings"
                element={isAuthenticated ? <SettingsPage /> : <Navigate to="/login" />}
              />
              <Route
                path="/"
                element={<Navigate to={isAuthenticated ? "/chat" : "/login"} />}
              />
            </Routes>
          </Content>
        </Layout>
      </BrowserRouter>
    </ConfigProvider>
  );
};

export default App;
