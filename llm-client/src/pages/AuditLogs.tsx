import React, { useState } from 'react';
import { Table, Tag, Card, Input, DatePicker, Space, Button, Typography } from 'antd';
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;
const { RangePicker } = DatePicker;

interface AuditLog {
  key: string;
  timestamp: string;
  user: string;
  action: string;
  details: string;
  status: 'success' | 'blocked' | 'warning';
  ip: string;
}

const initialData: AuditLog[] = [
  { key: '1', timestamp: '2023-12-21 10:23:45', user: 'admin', action: 'Prompt Check', details: 'Detected potential prompt injection', status: 'blocked', ip: '192.168.1.5' },
  { key: '2', timestamp: '2023-12-21 10:20:11', user: 'user_01', action: 'Response Filter', details: 'Clean content', status: 'success', ip: '192.168.1.8' },
  { key: '3', timestamp: '2023-12-21 10:15:33', user: 'user_02', action: 'Sensitive Data', details: 'Masked credit card number', status: 'warning', ip: '192.168.1.12' },
  { key: '4', timestamp: '2023-12-21 09:55:00', user: 'admin', action: 'Login', details: 'Successful login', status: 'success', ip: '192.168.1.5' },
  { key: '5', timestamp: '2023-12-21 09:40:22', user: 'unknown', action: 'Login', details: 'Failed login attempt', status: 'blocked', ip: '10.0.0.3' },
];

const AuditLogs: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [data] = useState<AuditLog[]>(initialData);

  const columns: ColumnsType<AuditLog> = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      sorter: (a, b) => a.timestamp.localeCompare(b.timestamp),
    },
    {
      title: '用户',
      dataIndex: 'user',
      key: 'user',
    },
    {
      title: '操作类型',
      dataIndex: 'action',
      key: 'action',
      render: (text) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: '详情',
      dataIndex: 'details',
      key: 'details',
    },
    {
      title: 'IP地址',
      dataIndex: 'ip',
      key: 'ip',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        let color = 'green';
        let text = '通过';
        if (status === 'blocked') { color = 'red'; text = '已拦截'; }
        if (status === 'warning') { color = 'orange'; text = '警告/脱敏'; }
        return <Tag color={color}>{text}</Tag>;
      },
    },
  ];

  const handleRefresh = () => {
    setLoading(true);
    // 模拟API调用
    setTimeout(() => {
        setLoading(false);
        // 这里可以重新fetch数据
    }, 1000);
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={4} style={{ margin: 0 }}>安全审计日志</Title>
        <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={loading}>刷新</Button>
      </div>

      <Card bordered={false} style={{ marginBottom: 16 }}>
        <Space wrap>
            <Input placeholder="搜索用户/详情..." prefix={<SearchOutlined />} style={{ width: 200 }} />
            <RangePicker />
            <Button type="primary">查询</Button>
        </Space>
      </Card>

      <Card bordered={false} style={{ flex: 1 }}>
        <Table 
            columns={columns} 
            dataSource={data} 
            loading={loading}
            pagination={{ pageSize: 10 }}
        />
      </Card>
    </div>
  );
};

export default AuditLogs;
