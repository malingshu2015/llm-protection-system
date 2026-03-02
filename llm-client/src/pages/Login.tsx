import React, { useState } from 'react';
import { Form, Input, Button, Card, Typography, Alert, message } from 'antd';
import { UserOutlined, LockOutlined, CloudServerOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/useAuthStore';
import { apiService } from '../services/api';

const { Title, Text } = Typography;

const Login: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login } = useAuthStore();
  const navigate = useNavigate();

  const onFinish = async (values: any) => {
    setLoading(true);
    setError('');

    try {
      apiService.setBaseURL(values.serverUrl);
      const response = await apiService.login(values.username, values.password);

      login(
        response.access_token,
        {
          id: response.user.id,
          username: response.user.username,
          email: response.user.email,
        },
        values.serverUrl
      );
      
      message.success('登录成功');
      navigate('/dashboard'); // 登录后去 Dashboard 而不是 Chat
    } catch (err: any) {
      console.error('登录失败:', err);
      let errorMessage = '登录失败,请检查用户名和密码';
      if (err.response?.data?.detail) {
        if (typeof err.response.data.detail === 'string') {
          errorMessage = err.response.data.detail;
        } else if (Array.isArray(err.response.data.detail)) {
          errorMessage = err.response.data.detail[0]?.msg || errorMessage;
        }
      }
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      height: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(120deg, #1890ff 0%, #a0d911 100%)',
    }}>
      <Card 
        style={{ width: 400, boxShadow: '0 4px 12px rgba(0,0,0,0.15)' }}
        bordered={false}
      >
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <Title level={3} style={{ color: '#1890ff', margin: 0 }}>LLM Shield</Title>
          <Text type="secondary">企业级大模型安全网关</Text>
        </div>

        {error && <Alert message={error} type="error" showIcon style={{ marginBottom: 16 }} />}

        <Form
          name="login"
          initialValues={{ serverUrl: 'http://localhost:8082' }}
          onFinish={onFinish}
          layout="vertical"
          size="large"
        >
          <Form.Item
            name="serverUrl"
            rules={[{ required: true, message: '请输入服务器地址' }]}
          >
            <Input prefix={<CloudServerOutlined />} placeholder="服务器地址" />
          </Form.Item>

          <Form.Item
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input prefix={<UserOutlined />} placeholder="用户名" />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" block loading={loading}>
              登 录
            </Button>
          </Form.Item>
        </Form>
        <div style={{ textAlign: 'center' }}>
            <Text type="secondary" style={{ fontSize: 12 }}>© 2025 LLM Protection Team</Text>
        </div>
      </Card>
    </div>
  );
};

export default Login;