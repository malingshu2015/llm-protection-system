import React from 'react';
import { List, Button, Typography, Space, Dropdown, Tag } from 'antd';
import {
  MessageOutlined,
  PlusOutlined,
  DeleteOutlined,
  MoreOutlined,
} from '@ant-design/icons';
import { Session } from '@/types/chat';
import './SessionList.css';

const { Text } = Typography;

interface SessionListProps {
  sessions: Session[];
  currentSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onCreateSession: () => void;
  onDeleteSession: (sessionId: string) => void;
}

export const SessionList: React.FC<SessionListProps> = ({
  sessions,
  currentSessionId,
  onSelectSession,
  onCreateSession,
  onDeleteSession,
}) => {
  return (
    <div className="session-list">
      <div className="session-list-header">
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={onCreateSession}
          block
        >
          新建对话
        </Button>
      </div>

      <List
        dataSource={sessions}
        renderItem={(session) => (
          <List.Item
            className={`session-item ${currentSessionId === session.id ? 'active' : ''}`}
            onClick={() => onSelectSession(session.id)}
          >
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <div className="session-header">
                <Space size={8}>
                  <MessageOutlined />
                  <Text ellipsis style={{ flex: 1 }}>
                    {session.title}
                  </Text>
                </Space>

                <Dropdown
                  menu={{
                    items: [
                      {
                        key: 'delete',
                        label: '删除',
                        icon: <DeleteOutlined />,
                        danger: true,
                        onClick: (e) => {
                          e.domEvent.stopPropagation();
                          onDeleteSession(session.id);
                        },
                      },
                    ],
                  }}
                  trigger={['click']}
                >
                  <Button
                    type="text"
                    size="small"
                    icon={<MoreOutlined />}
                    onClick={(e) => e.stopPropagation()}
                  />
                </Dropdown>
              </div>

              <div className="session-meta">
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {session.messages.length} 条消息
                </Text>
                {session.metadata.tokens > 0 && (
                  <Tag style={{ fontSize: 11 }}>{session.metadata.tokens} tokens</Tag>
                )}
              </div>

              <Text type="secondary" style={{ fontSize: 11 }}>
                {new Date(session.updatedAt).toLocaleDateString()}
              </Text>
            </Space>
          </List.Item>
        )}
      />
    </div>
  );
};
