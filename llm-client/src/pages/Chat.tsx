import React, { useState, useEffect, useRef } from 'react';
import { Layout, List, Input, Button, Avatar, Typography, Badge, message as antMessage, Empty } from 'antd';
import {
  SendOutlined,
  PlusOutlined,
  DeleteOutlined,
  UserOutlined,
  RobotOutlined,
  LoadingOutlined
} from '@ant-design/icons';
import { useAuthStore } from '../store/useAuthStore';
import { useChatStore } from '../store/useChatStore';
import { websocketService } from '../services/websocket';
import { v4 as uuidv4 } from 'uuid';

const { Sider, Content } = Layout;
const { TextArea } = Input;
const { Text } = Typography;

const Chat: React.FC = () => {
  const { token, serverUrl } = useAuthStore();
  const {
    sessions,
    currentSessionId,
    createSession,
    setCurrentSession,
    addMessage,
    deleteSession,
    getAllSessions,
  } = useChatStore();

  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const currentSession = currentSessionId ? sessions.get(currentSessionId) : null;
  const sessionList = getAllSessions();

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentSession?.messages]);

  // WebSocket 连接
  useEffect(() => {
    if (!token || !serverUrl) return;

    const clientId = uuidv4();

    // 简单的去抖动或防止重复连接逻辑可以在这里优化，暂时保持简单
    if (!websocketService.isConnected()) {
      websocketService.connect(serverUrl, token, clientId)
        .then(() => setWsConnected(true))
        .catch(() => antMessage.error('无法连接到聊天服务器'));
    } else {
      setWsConnected(true);
    }

    const handleChatResponse = (data: any) => {
      if (data.sessionId && data.reply) {
        const message = {
          id: data.messageId || uuidv4(),
          role: 'assistant' as const,
          content: data.reply,
          timestamp: new Date(data.timestamp || new Date()),
        };
        addMessage(data.sessionId, message);
        setLoading(false);
      }
    };

    const handleError = (data: any) => {
      setLoading(false);
      antMessage.error(data.error?.message || '发送失败');
    };

    websocketService.on('chat:response', handleChatResponse);
    websocketService.on('error', handleError);

    return () => {
      websocketService.off('chat:response', handleChatResponse);
      websocketService.off('error', handleError);
      // 注意：这里是否断开取决于是否希望切换页面时保持连接。
      // 为了体验流畅，通常保持连接，但在组件卸载时断开是安全的做法。
    };
  }, [token, serverUrl, addMessage]);

  const handleCreateSession = () => {
    const newSession = createSession('default', `新对话 ${sessionList.length + 1}`);
    setCurrentSession(newSession.id);
  };

  const handleSendMessage = async () => {
    if (!inputText.trim() || !currentSessionId) return;

    setLoading(true);
    const userMessage = {
      id: uuidv4(),
      role: 'user' as const,
      content: inputText,
      timestamp: new Date(),
    };

    addMessage(currentSessionId, userMessage);
    const textToSend = inputText;
    setInputText('');

    try {
      if (!websocketService.isConnected()) {
        // 尝试重连
        await websocketService.connect(serverUrl!, token!, uuidv4());
        setWsConnected(true);
      }
      await websocketService.sendChatMessage(currentSessionId, textToSend);
    } catch (error) {
      antMessage.error('消息发送失败');
      setLoading(false);
    }
  };

  return (
    <Layout style={{ height: 'calc(100vh - 112px)', background: '#fff', border: '1px solid #f0f0f0', borderRadius: 8 }}>
      <Sider width={250} theme="light" style={{ borderRight: '1px solid #f0f0f0' }}>
        <div style={{ padding: '16px', borderBottom: '1px solid #f0f0f0' }}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            block
            onClick={handleCreateSession}
          >
            新建对话
          </Button>
        </div>
        <div style={{ overflowY: 'auto', height: 'calc(100% - 64px)' }}>
          <List
            dataSource={sessionList}
            renderItem={(item) => (
              <List.Item
                style={{
                  padding: '12px 16px',
                  cursor: 'pointer',
                  backgroundColor: item.id === currentSessionId ? '#e6f7ff' : 'transparent',
                  borderRight: item.id === currentSessionId ? '2px solid #1890ff' : 'none'
                }}
                onClick={() => setCurrentSession(item.id)}
                actions={[
                  <Button
                    type="text"
                    size="small"
                    icon={<DeleteOutlined />}
                    onClick={(e) => { e.stopPropagation(); deleteSession(item.id); }}
                    danger
                  />
                ]}
              >
                <List.Item.Meta
                  title={<Text ellipsis style={{ width: 140 }}>{item.title}</Text>}
                />
              </List.Item>
            )}
          />
        </div>
      </Sider>

      <Content style={{ display: 'flex', flexDirection: 'column' }}>
        {/* 聊天内容区域 */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
          {!currentSession ? (
            <div style={{ height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
              <Empty description="选择或创建一个新的对话开始" />
            </div>
          ) : (
            currentSession.messages.map((msg) => (
              <div
                key={msg.id}
                style={{
                  display: 'flex',
                  justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  marginBottom: 20,
                }}
              >
                <div style={{
                  display: 'flex',
                  flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
                  maxWidth: '80%',
                  gap: 12
                }}>
                  <Avatar
                    icon={msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                    style={{ backgroundColor: msg.role === 'user' ? '#1890ff' : '#52c41a' }}
                  />
                  <div style={{
                    backgroundColor: msg.role === 'user' ? '#e6f7ff' : '#f6f6f6',
                    padding: '12px 16px',
                    borderRadius: 8,
                    borderTopRightRadius: msg.role === 'user' ? 0 : 8,
                    borderTopLeftRadius: msg.role === 'user' ? 8 : 0,
                  }}>
                    <Text style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</Text>
                    <div style={{ fontSize: 10, color: '#999', marginTop: 4, textAlign: 'right' }}>
                      {new Date(msg.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* 输入框区域 */}
        <div style={{ padding: '16px 24px', borderTop: '1px solid #f0f0f0', backgroundColor: '#fff' }}>
          <div style={{ position: 'relative' }}>
            <TextArea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="输入消息..."
              autoSize={{ minRows: 2, maxRows: 6 }}
              disabled={!currentSession || loading}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
            />
            <div style={{
              position: 'absolute',
              right: 8,
              bottom: 8,
              display: 'flex',
              alignItems: 'center',
              gap: 8
            }}>
              {!wsConnected && <Badge status="error" text="未连接" />}
              <Button
                type="primary"
                icon={loading ? <LoadingOutlined /> : <SendOutlined />}
                onClick={handleSendMessage}
                disabled={!currentSession || loading || !inputText.trim()}
              >
                发送
              </Button>
            </div>
          </div>
        </div>
      </Content>
    </Layout>
  );
};

export default Chat;