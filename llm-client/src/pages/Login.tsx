import React, { useState } from 'react';
import { Form, Input, Button, Card, Typography, Alert, message } from 'antd';
import { UserOutlined, LockOutlined, CloudServerOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
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
      background: 'linear-gradient(135deg, #fdf6e3 0%, #ffedd5 100%)',
    }}>
      <Card
        style={{ width: 420, boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1)', borderRadius: 24 }}
        bordered={false}
      >
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{
            width: 64, height: 64, background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
            borderRadius: 16, margin: '0 auto 16px auto', display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 10px 15px -3px rgba(249,115,22,0.3)'
          }}>
            <SafetyCertificateOutlined style={{ fontSize: 32, color: '#fff' }} />
          </div>
          <Title level={3} style={{ color: '#1f2937', margin: 0, fontWeight: 800 }}>CyberShield</Title>
          <Text type="secondary" style={{ fontSize: 13 }}>企业级 LLM 安全防御指挥中心 (v2.2.1-PRO)</Text>
        </div>

        {error && <Alert message={error} type="error" showIcon style={{ marginBottom: 16 }} />}

        <Form
          name="login"
          initialValues={{ serverUrl: 'http://localhost:8089', username: 'testadmin', password: 'Password123!' }}
          onFinish={onFinish}
          layout="vertical"
          size="large"
        >
          <Form.Item
            name="serverUrl"
            rules={[{ required: true, message: '请输入服务器地址' }]}
          >
            <Input prefix={<CloudServerOutlined style={{ color: '#9ca3af' }} />} placeholder="服务器地址" style={{ borderRadius: 8 }} />
          </Form.Item>

          <Form.Item
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input prefix={<UserOutlined style={{ color: '#9ca3af' }} />} placeholder="管理员账户" style={{ borderRadius: 8 }} />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入防伪验证凭证' }]}
          >
            <Input.Password prefix={<LockOutlined style={{ color: '#9ca3af' }} />} placeholder="防伪验证凭证" style={{ borderRadius: 8 }} />
          </Form.Item>

          <Form.Item style={{ marginTop: 32 }}>
            <Button type="primary" htmlType="submit" block loading={loading} style={{ height: 44, borderRadius: 8, fontWeight: 700, fontSize: 16 }}>
              进入指挥中心
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