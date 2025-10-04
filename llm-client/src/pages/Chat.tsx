import React, { useState, useEffect } from 'react';
import { Layout, Typography, message, Space, Button } from 'antd';
import { SettingOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useChatStore } from '@/store/useChatStore';
import { useAuthStore } from '@/store/useAuthStore';
import { SessionList } from '@/components/Chat/SessionList';
import { MessageList } from '@/components/Chat/MessageList';
import { InputBox } from '@/components/Chat/InputBox';
import { gatewayClient } from '@/services/api/gateway';
import { inputFilter } from '@/services/filter/input-filter';
import { policyManager } from '@/services/policy/policy-manager';
import { v4 as uuidv4 } from 'uuid';
import './Chat.css';

const { Header, Content, Sider } = Layout;
const { Title } = Typography;

const ChatPage: React.FC = () => {
  const navigate = useNavigate();
  const { token, serverUrl, logout } = useAuthStore();
  const {
    sessions,
    currentSessionId,
    createSession,
    deleteSession,
    setCurrentSession,
    addMessage,
    getAllSessions,
  } = useChatStore();

  const [loading, setLoading] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [connected, setConnected] = useState(false);

  // 初始化连接
  useEffect(() => {
    const initConnection = async () => {
      try {
        if (!serverUrl || !token) {
          message.error('未配置服务器或令牌');
          return;
        }

        // 连接到网关
        await gatewayClient.connect(serverUrl, token);
        setConnected(true);

        // 初始化策略管理器
        await policyManager.initialize();

        // 监听策略更新
        const unsubscribe = policyManager.onPolicyUpdate((policy) => {
          inputFilter.loadPolicy(policy);
          message.info('安全策略已更新');
        });

        // 监听强制下线
        window.addEventListener('force_logout', ((event: CustomEvent) => {
          message.error(`已被强制下线: ${event.detail}`);
          logout();
          navigate('/login');
        }) as EventListener);

        return () => {
          unsubscribe();
          gatewayClient.disconnect();
        };
      } catch (error) {
        message.error('连接服务器失败: ' + (error as Error).message);
      }
    };

    initConnection();
  }, [serverUrl, token, logout, navigate]);

  const handleCreateSession = () => {
    createSession('default', `对话 ${getAllSessions().length + 1}`);
  };

  const handleDeleteSession = (sessionId: string) => {
    deleteSession(sessionId);
    message.success('会话已删除');
  };

  const handleSendMessage = async (text: string) => {
    if (!currentSessionId) {
      message.warning('请先创建或选择一个会话');
      return;
    }

    setLoading(true);

    try {
      // 1. 本地过滤
      const filterResult = await inputFilter.filter(text);
      if (filterResult.blocked) {
        message.error({
          content: filterResult.reason,
          duration: 3,
        });
        setLoading(false);
        return;
      }

      // 2. 添加用户消息
      const userMessage = {
        id: uuidv4(),
        role: 'user' as const,
        content: text,
        timestamp: new Date(),
      };
      addMessage(currentSessionId, userMessage);

      // 3. 发送到服务器（流式响应）
      setStreamingText('');
      await gatewayClient.streamMessage(currentSessionId, text, (chunk) => {
        setStreamingText((prev) => prev + chunk);
      });

      // 4. 添加助手回复
      const assistantMessage = {
        id: uuidv4(),
        role: 'assistant' as const,
        content: streamingText,
        timestamp: new Date(),
      };
      addMessage(currentSessionId, assistantMessage);
    } catch (error) {
      message.error('发送失败: ' + (error as Error).message);
    } finally {
      setLoading(false);
      setStreamingText('');
    }
  };

  const currentSession = currentSessionId
    ? sessions.get(currentSessionId)
    : null;

  return (
    <Layout className="chat-layout">
      <Sider width={280} className="chat-sider">
        <SessionList
          sessions={getAllSessions()}
          currentSessionId={currentSessionId}
          onSelectSession={setCurrentSession}
          onCreateSession={handleCreateSession}
          onDeleteSession={handleDeleteSession}
        />
      </Sider>

      <Layout>
        <Header className="chat-header">
          <Space>
            <Title level={4} style={{ margin: 0 }}>
              {currentSession?.title || '对话窗口'}
            </Title>
            {connected && (
              <span style={{ color: '#52c41a', fontSize: 12 }}>● 已连接</span>
            )}
          </Space>

          <Space>
            <Button
              type="text"
              icon={<SettingOutlined />}
              onClick={() => navigate('/settings')}
            >
              设置
            </Button>
          </Space>
        </Header>

        <Content className="chat-content">
          {currentSession ? (
            <>
              <MessageList
                messages={currentSession.messages}
                streamingText={streamingText}
              />
              <InputBox
                onSend={handleSendMessage}
                disabled={!connected}
                loading={loading}
              />
            </>
          ) : (
            <div className="chat-placeholder">
              <Title level={3} type="secondary">
                选择一个会话或创建新对话
              </Title>
              <Button type="primary" size="large" onClick={handleCreateSession}>
                开始新对话
              </Button>
            </div>
          )}
        </Content>
      </Layout>
    </Layout>
  );
};

export default ChatPage;
