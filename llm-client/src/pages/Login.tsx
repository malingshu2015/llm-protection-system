import React, { useState } from 'react';
import { Form, Input, Button, Card, Typography, Space, message } from 'antd';
import { UserOutlined, LockOutlined, ApiOutlined } from '@ant-design/icons';
import { useAuthStore } from '../store/useAuthStore';
import { useNavigate } from 'react-router-dom';
import './Login.css';

const { Title, Text } = Typography;

const LoginPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const { login } = useAuthStore();
  const navigate = useNavigate();

  const onFinish = async (values: any) => {
    setLoading(true);
    try {
      // TODO: 实际的登录 API 调用
      // const response = await loginAPI(values);

      // 模拟登录成功
      setTimeout(() => {
        login(
          'mock-token',
          {
            id: '1',
            username: values.username,
            email: 'user@example.com',
          },
          values.serverUrl
        );
        message.success('登录成功');
        navigate('/chat');
        setLoading(false);
      }, 1000);
    } catch (error) {
      message.error('登录失败，请检查您的凭据');
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <Card className="login-card" bordered={false}>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div className="login-header">
            <Title level={2}>LLM防护客户端</Title>
            <Text type="secondary">安全、可靠的大模型访问工具</Text>
          </div>

          <Form
            name="login"
            onFinish={onFinish}
            autoComplete="off"
            size="large"
          >
            <Form.Item
              name="serverUrl"
              rules={[{ required: true, message: '请输入服务器地址' }]}
              initialValue="http://localhost:8000"
            >
              <Input
                prefix={<ApiOutlined />}
                placeholder="服务器地址"
              />
            </Form.Item>

            <Form.Item
              name="username"
              rules={[{ required: true, message: '请输入用户名' }]}
            >
              <Input
                prefix={<UserOutlined />}
                placeholder="用户名"
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="密码"
              />
            </Form.Item>

            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                block
              >
                登录
              </Button>
            </Form.Item>
          </Form>

          <div className="login-footer">
            <Text type="secondary">
              没有账号？请联系管理员
            </Text>
          </div>
        </Space>
      </Card>
    </div>
  );
};

export default LoginPage;
