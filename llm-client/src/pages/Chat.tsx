import React, { useState, useEffect, useRef } from 'react';
import { Layout, List, Input, Button, Avatar, Typography, Badge, message as antMessage, Empty, Select, Tag, Upload } from 'antd';
import {
  SendOutlined,
  PlusOutlined,
  DeleteOutlined,
  UserOutlined,
  RobotOutlined,
  LoadingOutlined,
  SafetyOutlined,
  CheckCircleOutlined,
  LockOutlined,
  PaperClipOutlined,
  CloseCircleOutlined
} from '@ant-design/icons';
import type { UploadProps } from 'antd';
import { useAuthStore } from '../store/useAuthStore';
import { useChatStore } from '../store/useChatStore';
import { websocketService } from '../services/websocket';
import { v4 as uuidv4 } from 'uuid';

const { Sider, Content } = Layout;
const { TextArea } = Input;
const { Text, Title } = Typography;

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
  const [models, setModels] = useState<any[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('llama3.2:latest');
  const [attachedImages, setAttachedImages] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<any>(null);

  const currentSession = currentSessionId ? sessions.get(currentSessionId) : null;
  const sessionList = getAllSessions();

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentSession?.messages]);

  // 加载模型列表
  useEffect(() => {
    fetchModels();
    // 从 localStorage 加载之前选择的模型
    const savedModel = localStorage.getItem('selected_model');
    if (savedModel) {
      setSelectedModel(savedModel);
    }
  }, []);

  const fetchModels = async () => {
    try {
      const response = await fetch('http://localhost:8082/api/v1/ollama/models');
      const data = await response.json();
      if (data.data) {
        setModels(data.data);
      }
    } catch (error) {
      console.error('获取模型列表失败:', error);
    }
  };

  const handleModelChange = (modelId: string) => {
    setSelectedModel(modelId);
    localStorage.setItem('selected_model', modelId);
    antMessage.success(`已切换到模型: ${modelId}`);
  };

  // 处理文件上传
  const handleFileUpload: UploadProps['onChange'] = (info) => {
    if (info.file.status === 'done') {
      const file = info.file.originFileObj;
      if (!file) return;
      if (file.type?.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (e) => {
          const base64 = e.target?.result as string;
          setAttachedImages(prev => [...prev, base64]);
        };
        reader.readAsDataURL(file);
      } else {
        // 处理其他文件（显示文件名）
        const fileName = file.name;
        setAttachedImages(prev => [...prev, `FILE:${fileName}`]);
      }
    }
  };

  // 移除附件
  const handleRemoveAttachment = (index: number) => {
    setAttachedImages(prev => prev.filter((_, i) => i !== index));
  };

  // 处理粘贴事件
  const handlePaste = (e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.type.indexOf('image') !== -1) {
        const blob = item.getAsFile();
        if (blob) {
          const reader = new FileReader();
          reader.onload = (e) => {
            const base64 = e.target?.result as string;
            setAttachedImages(prev => [...prev, base64]);
          };
          reader.readAsDataURL(blob);
        }
      }
    }
  };

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
      // 在我们的后端响应中，sessionId 等数据是在顶层的，而不再被包裹在 data 这个子键中了。
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

    const handleChatError = (payload: any) => {
      console.log("[DEBUG Chat.tsx] Received chat:error payload:", payload);
      // payload means the full websocket message if no data property is used by the backend
      // we check both approaches:
      const sessionId = payload.sessionId || payload.data?.sessionId;
      const content = payload.content || payload.data?.content;

      if (sessionId && content) {
        console.log("[DEBUG Chat.tsx] Successfully parsed error msg for session:", sessionId);
        const messageObj = {
          id: payload.messageId || uuidv4(),
          role: 'assistant' as const,
          content: content,
          timestamp: new Date(payload.timestamp || new Date()),
          isError: true // 标记为错误消息，可以在 UI 中进行特殊样式处理
        };
        addMessage(sessionId, messageObj);
        setLoading(false);
      } else {
        console.warn("[DEBUG Chat.tsx] Missing sessionId or content. sessionId:", sessionId, "content:", content);
      }
    };

    websocketService.on('chat:response', handleChatResponse);
    websocketService.on('chat:error', handleChatError);
    websocketService.on('error', handleError);

    return () => {
      websocketService.off('chat:response', handleChatResponse);
      websocketService.off('chat:error', handleChatError);
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
    if (!inputText.trim() && attachedImages.length === 0) return;
    if (!currentSessionId) return;

    setLoading(true);

    // 构建消息内容（包含图片）
    let content = inputText;
    if (attachedImages.length > 0) {
      const imageText = attachedImages.map((img, i) => {
        if (img.startsWith('FILE:')) {
          return `[文件: ${img.replace('FILE:', '')}]`;
        }
        return `[图片 ${i + 1}]`;
      }).join('\n');
      content = imageText + (inputText ? '\n' + inputText : '');
    }

    const userMessage = {
      id: uuidv4(),
      role: 'user' as const,
      content: content,
      timestamp: new Date(),
      images: attachedImages.length > 0 ? attachedImages : undefined,
    };

    addMessage(currentSessionId, userMessage);
    const textToSend = inputText;
    const imagesToSend = [...attachedImages];
    setInputText('');
    setAttachedImages([]);

    try {
      if (!websocketService.isConnected()) {
        // 尝试重连
        await websocketService.connect(serverUrl!, token!, uuidv4());
        setWsConnected(true);
      }
      // 发送消息时带上选择的模型和图片
      await websocketService.sendChatMessage(currentSessionId, textToSend, selectedModel, imagesToSend);
    } catch (error) {
      antMessage.error('消息发送失败');
      setLoading(false);
      // 恢复附件
      setAttachedImages(imagesToSend);
    }
  };

  return (
    <Layout style={{ height: 'calc(100vh - 120px)', background: '#fdf6e3', borderRadius: 20, overflow: 'hidden' }}>
      <Sider width={280} theme="light" style={{ borderRight: '1px solid #f1e4d9', background: '#fff' }}>
        <div style={{ padding: '24px', borderBottom: '1px solid #f8f9fa' }}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            block
            size="large"
            style={{ fontWeight: 700, borderRadius: 12 }}
            onClick={handleCreateSession}
          >
            开启安全新对话
          </Button>
        </div>
        <div style={{ overflowY: 'auto', height: 'calc(100% - 84px)', padding: '12px' }}>
          <List
            dataSource={sessionList}
            renderItem={(item) => (
              <List.Item
                style={{
                  padding: '16px',
                  marginBottom: 8,
                  borderRadius: 12,
                  cursor: 'pointer',
                  backgroundColor: item.id === currentSessionId ? '#fff7ed' : 'transparent',
                  border: item.id === currentSessionId ? '1px solid #ffedd5' : '1px solid transparent',
                  transition: 'all 0.2s'
                }}
                className="chat-session-item"
                onClick={() => setCurrentSession(item.id)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                  <Text strong={item.id === currentSessionId} ellipsis style={{ maxWidth: 160, color: item.id === currentSessionId ? '#c2410c' : '#4b5563' }}>
                    {item.title}
                  </Text>
                  <Button
                    type="text"
                    size="small"
                    icon={<DeleteOutlined style={{ fontSize: 12 }} />}
                    onClick={(e) => { e.stopPropagation(); deleteSession(item.id); }}
                    danger
                  />
                </div>
              </List.Item>
            )}
          />
        </div>
      </Sider>

      <Content style={{ display: 'flex', flexDirection: 'column', background: '#fdf6e3' }}>
        {/* Header with Security Status */}
        <div style={{ padding: '16px 32px', background: '#fff', borderBottom: '1px solid #f1e4d9', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={5} style={{ margin: 0, fontWeight: 800 }}>{currentSession?.title || '安全对话窗口'}</Title>
            <Text type="secondary" style={{ fontSize: 12 }}>对话全程受 CyberShield 实时防御加固</Text>
          </div>
          <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
            {/* 模型选择器 */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <RobotOutlined style={{ color: '#f97316' }} />
              <Select
                value={selectedModel}
                onChange={handleModelChange}
                style={{ width: 200 }}
                placeholder="选择模型"
                showSearch
                optionFilterProp="children"
              >
                {models.map(model => (
                  <Select.Option key={model.id} value={model.id}>
                    {model.id}
                  </Select.Option>
                ))}
              </Select>
            </div>

            <span style={{ padding: '4px 12px', borderRadius: 20, fontWeight: 700, border: '1px solid #86efac', background: '#dcfce7', color: '#166534', fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
              <SafetyOutlined />
              安全加固: 开启
            </span>
            <Badge status={wsConnected ? 'success' : 'error'} text={wsConnected ? '引擎在线' : '引擎离线'} style={{ fontWeight: 600 }} />
          </div>
        </div>

        {/* 聊天内容区域 */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '40px 32px' }}>
          {!currentSession ? (
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', gap: 16 }}>
              <Empty description={<Text type="secondary">选择一个历史记录或发起新的安全会话</Text>} />
              <Button type="primary" onClick={handleCreateSession}>立即开始</Button>
            </div>
          ) : (
            currentSession.messages.map((msg) => (
              <div
                key={msg.id}
                style={{
                  display: 'flex',
                  justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  marginBottom: 32,
                }}
              >
                <div style={{
                  display: 'flex',
                  flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
                  maxWidth: '75%',
                  gap: 16
                }}>
                  <Avatar
                    icon={msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                    style={{
                      backgroundColor: msg.role === 'user' ? '#f97316' : '#fff',
                      color: msg.role === 'user' ? '#fff' : '#f97316',
                      border: msg.role === 'user' ? 'none' : '1px solid #f1e4d9',
                      boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
                    }}
                  />
                  <div>
                    <div style={{
                      backgroundColor: msg.isError ? '#fef2f2' : (msg.role === 'user' ? '#f97316' : '#fff'),
                      color: msg.isError ? '#dc2626' : (msg.role === 'user' ? '#fff' : '#1f2937'),
                      padding: '16px 20px',
                      borderRadius: 16,
                      borderTopRightRadius: msg.role === 'user' ? 4 : 16,
                      borderTopLeftRadius: msg.role === 'user' ? 16 : 4,
                      boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)',
                      fontSize: 14,
                      lineHeight: 1.6,
                      border: msg.isError ? '1px solid #fecaca' : (msg.role === 'user' ? 'none' : '1px solid #f1f5f9')
                    }}>
                      {/* 显示图片附件 */}
                      {(msg as any).images && (msg as any).images.length > 0 && (
                        <div style={{ marginBottom: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                          {(msg as any).images.map((img: string, i: number) => (
                            img.startsWith('FILE:') ? (
                              <Tag key={i} icon={<PaperClipOutlined style={{ fontSize: 12 }} />} style={{ padding: '4px 8px' }}>
                                {img.replace('FILE:', '')}
                              </Tag>
                            ) : (
                              <img
                                key={i}
                                src={img}
                                alt={`attachment-${i}`}
                                style={{ maxWidth: 200, maxHeight: 200, borderRadius: 8, border: '1px solid #e5e7eb' }}
                              />
                            )
                          ))}
                        </div>
                      )}
                      <Text style={{ color: 'inherit', whiteSpace: 'pre-wrap' }}>
                        {msg.isError && <SafetyOutlined style={{ marginRight: 8 }} />}
                        {msg.content}
                      </Text>
                    </div>

                    {/* Security Badge for each message */}
                    <div style={{
                      marginTop: 8,
                      display: 'flex',
                      justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                      alignItems: 'center',
                      gap: 6,
                      padding: '0 4px'
                    }}>
                      {msg.role === 'assistant' ? (
                        <span style={{ fontSize: 11, color: msg.isError ? '#ef4444' : '#10b981', display: 'flex', alignItems: 'center', gap: 4, fontWeight: 600 }}>
                          {msg.isError ? (
                            <>
                              <SafetyOutlined style={{ fontSize: 10 }} />
                              已检测到安全风险并成功拦截
                            </>
                          ) : (
                            <>
                              <CheckCircleOutlined style={{ fontSize: 10 }} />
                              已通过系统安全扫描
                            </>
                          )}
                        </span>
                      ) : (
                        <span style={{ fontSize: 11, color: '#f59e0b', display: 'flex', alignItems: 'center', gap: 4, fontWeight: 600 }}>
                          <LockOutlined style={{ fontSize: 10 }} />
                          隐私盾: 部分敏感字段已按策略自动隐匿
                        </span>
                      )}
                      <span style={{ fontSize: 10, color: '#9ca3af', marginLeft: 8 }}>
                        {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* 输入框区域 */}
        <div style={{ padding: '24px 40px 40px 40px', background: '#fff', borderTop: '1px solid #f1e4d9' }}>
          {/* 附件预览区 */}
          {attachedImages.length > 0 && (
            <div style={{ marginBottom: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {attachedImages.map((img, index) => (
                <div key={index} style={{ position: 'relative', display: 'inline-block' }}>
                  {img.startsWith('FILE:') ? (
                    <Tag closable onClose={() => handleRemoveAttachment(index)} style={{ padding: '4px 8px', fontSize: 13 }}>
                      <PaperClipOutlined style={{ marginRight: 4 }} />
                      {img.replace('FILE:', '')}
                    </Tag>
                  ) : (
                    <>
                      <div style={{ width: 60, height: 60, borderRadius: 8, overflow: 'hidden', border: '1px solid #e5e7eb' }}>
                        <img src={img} alt="attachment" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                      </div>
                      <Button
                        type="text"
                        size="small"
                        icon={<CloseCircleOutlined />}
                        onClick={() => handleRemoveAttachment(index)}
                        style={{ position: 'absolute', top: -4, right: -4, background: '#fff', borderRadius: '50%' }}
                      />
                    </>
                  )}
                </div>
              ))}
            </div>
          )}

          <div style={{
            background: '#f8fafc',
            borderRadius: 16,
            padding: '12px 16px',
            border: '1px solid #e2e8f0',
            boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.02)'
          }}>
            <TextArea
              ref={inputRef}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="输入消息或直接粘贴图片... (支持 Ctrl+V 粘贴图片)"
              autoSize={{ minRows: 2, maxRows: 6 }}
              disabled={!currentSession || loading}
              bordered={false}
              style={{ fontSize: 14, background: 'transparent' }}
              onPaste={handlePaste}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 12 }}>
              <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                <Upload
                  accept="image/*,.pdf,.doc,.docx,.txt"
                  showUploadList={false}
                  beforeUpload={() => false}
                  onChange={handleFileUpload}
                >
                  <Button type="text" icon={<PaperClipOutlined />} style={{ color: '#6b7280' }}>
                    上传文件
                  </Button>
                </Upload>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  支持图片、文档等 • 可直接粘贴截图
                </Text>
              </div>
              <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                {!wsConnected && <Badge status="error" text="未连接" />}
                <Button
                  type="primary"
                  icon={loading ? <LoadingOutlined /> : <SendOutlined />}
                  onClick={handleSendMessage}
                  disabled={!currentSession || loading || (!inputText.trim() && attachedImages.length === 0)}
                  style={{ borderRadius: 8, height: 36, paddingLeft: 24, paddingRight: 24, fontWeight: 700 }}
                >
                  发送
                </Button>
              </div>
            </div>
          </div>
        </div>
      </Content>
    </Layout>
  );
};

export default Chat;