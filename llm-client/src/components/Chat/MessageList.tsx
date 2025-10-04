import React, { useEffect, useRef } from 'react';
import { List, Avatar, Typography, Space, Tag } from 'antd';
import { UserOutlined, RobotOutlined } from '@ant-design/icons';
import { Message } from '@/types/chat';
import './MessageList.css';

const { Text, Paragraph } = Typography;

interface MessageListProps {
  messages: Message[];
  streamingText?: string;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  streamingText,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingText]);

  return (
    <div className="message-list">
      <List
        dataSource={messages}
        renderItem={(message) => (
          <List.Item className={`message-item ${message.role}`}>
            <Space align="start" size={12}>
              <Avatar
                icon={message.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                style={{
                  backgroundColor: message.role === 'user' ? '#1890ff' : '#52c41a',
                }}
              />

              <div className="message-content">
                <div className="message-header">
                  <Text strong>
                    {message.role === 'user' ? '你' : 'AI 助手'}
                  </Text>
                  <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </Text>
                </div>

                <Paragraph className="message-text">{message.content}</Paragraph>

                {message.warnings && message.warnings.length > 0 && (
                  <Space size={4} wrap>
                    {message.warnings.map((warning, idx) => (
                      <Tag key={idx} color="warning" style={{ fontSize: 11 }}>
                        {warning}
                      </Tag>
                    ))}
                  </Space>
                )}

                {message.tokens && (
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {message.tokens} tokens
                  </Text>
                )}
              </div>
            </Space>
          </List.Item>
        )}
      />

      {/* 流式响应显示 */}
      {streamingText && (
        <List.Item className="message-item assistant streaming">
          <Space align="start" size={12}>
            <Avatar icon={<RobotOutlined />} style={{ backgroundColor: '#52c41a' }} />
            <div className="message-content">
              <div className="message-header">
                <Text strong>AI 助手</Text>
                <Tag color="processing" style={{ marginLeft: 8 }}>
                  正在输入...
                </Tag>
              </div>
              <Paragraph className="message-text">{streamingText}</Paragraph>
            </div>
          </Space>
        </List.Item>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
};
