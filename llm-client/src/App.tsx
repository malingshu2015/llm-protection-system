import React, { useEffect } from 'react';
import { HashRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Chat from './pages/Chat';
import Settings from './pages/Settings';
import RulesManage from './pages/RulesManage';
import ClientConfig from './pages/ClientConfig';
import MainLayout from './components/Layout/MainLayout';
import { useAuthStore } from './store/useAuthStore';
import './App.css';

const RulesManageWrapper: React.FC = () => {
  return <Outlet />;
};

const App: React.FC = () => {
  const { isAuthenticated, initAuth } = useAuthStore();

  useEffect(() => {
    initAuth();
    if (window.electronAPI) {
      window.electronAPI.getAppVersion().catch(err => console.error(err));
    }
  }, [initAuth]);

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#f97316',
          colorBgContainer: '#ffffff',
          colorBgLayout: '#fdf6e3',
          fontFamily: '"Inter", "Outfit", "PingFang SC", sans-serif',
          borderRadius: 12,
          colorTextBase: '#1f2937',
        },
        components: {
          Layout: {
            headerBg: '#ffffff',
            siderBg: '#ffffff',
          },
          Menu: {
            itemSelectedBg: '#ffedd5',
            itemSelectedColor: '#c2410c',
            itemBorderRadius: 8,
          },
          Card: {
            boxShadowTertiary: '0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03)',
            headerFontSize: 16,
          },
        }
      }}
    >
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
            <Route path="/rules" element={<RulesManageWrapper />}>
              <Route index element={<RulesManage />} />
              <Route path="policy" element={<Settings />} />
            </Route>
            <Route path="/clients" element={<ClientConfig />} />
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