import React, { useState } from 'react';
import { Layout, Menu, Button, theme, Avatar, Dropdown } from 'antd';
import {
  MonitorOutlined,
  MessageOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined,
  LogoutOutlined,
  SafetyCertificateOutlined,
  SafetyOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import { useAuthStore } from '../../store/useAuthStore';

const { Header, Sider, Content } = Layout;

const MainLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuthStore();

  const {
    token: { colorBgLayout },
  } = theme.useToken();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const userMenu = {
    items: [
      {
        key: 'logout',
        icon: <LogoutOutlined />,
        label: '退出登录',
        onClick: handleLogout,
      },
    ],
  };

  return (
    <Layout style={{ minHeight: '100vh', background: colorBgLayout }}>
      <Sider trigger={null} collapsible collapsed={collapsed} theme="light" style={{ borderRight: '1px solid #f1e4d9', background: '#fff' }}>
        <div style={{
          height: 64,
          margin: 16,
          display: 'flex',
          alignItems: 'center',
          justifyContent: collapsed ? 'center' : 'flex-start',
          gap: 10,
          overflow: 'hidden',
          whiteSpace: 'nowrap'
        }}>
          <SafetyCertificateOutlined style={{ fontSize: 24, color: '#f97316' }} />
          {!collapsed && (
            <span style={{ fontSize: 20, fontWeight: '800', color: '#1e293b' }}>
              CyberShield
            </span>
          )}
        </div>
        <Menu
          theme="light"
          mode="inline"
          selectedKeys={[location.pathname]}
          onClick={({ key }) => {
            // 如果是父菜单key（不以/开头的或不在路由中的），只展开不导航
            if (key === '/rules-sub') {
              return; // 让Ant Design Menu自动处理展开/收起
            }
            navigate(key);
          }}
          items={[
            {
              key: '/dashboard',
              icon: <MonitorOutlined />,
              label: '安防指挥中心',
            },
            {
              key: '/chat',
              icon: <MessageOutlined />,
              label: '安全 AI 对话',
            },
            {
              key: '/rules-sub',
              icon: <SafetyOutlined />,
              label: '规则管理中心',
              children: [
                {
                  key: '/rules',
                  label: '模型套餐配置',
                },
                {
                  key: '/rules/policy',
                  label: '策略引擎配置',
                },
              ],
            },
            {
              key: '/clients',
              icon: <ApiOutlined />,
              label: '客户端配置',
            },
          ]}
        />
      </Sider>
      <Layout style={{ background: colorBgLayout }}>
        <Header style={{ padding: 0, background: '#fff', display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingRight: 24, borderBottom: '1px solid #f1e4d9' }}>
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{
              fontSize: '16px',
              width: 64,
              height: 64,
            }}
          />
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <span style={{ color: '#52c41a', fontSize: 13, display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#52c41a', boxShadow: '0 0 4px #52c41a' }} />
              系统在线 (8082)
            </span>
            <Dropdown menu={userMenu}>
              <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
                <Avatar icon={<UserOutlined />} style={{ backgroundColor: '#f97316' }} />
                <span style={{ fontWeight: 600 }}>{user?.username || '管理员'}</span>
              </div>
            </Dropdown>
          </div>
        </Header>
        <Content
          style={{
            margin: '24px 24px',
            padding: 0,
            background: 'transparent',
            overflowY: 'auto'
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;
