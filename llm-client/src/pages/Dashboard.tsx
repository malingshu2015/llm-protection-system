import React from 'react';
import { Row, Col, Card, Statistic, Progress, Table, Tag, Typography } from 'antd';
import { 
  SafetyCertificateOutlined, 
  ThunderboltOutlined, 
  ClockCircleOutlined, 
  SafetyOutlined,
  ArrowUpOutlined
} from '@ant-design/icons';

const { Title } = Typography;

const Dashboard: React.FC = () => {
  // 模拟数据 - 后续对接真实 API
  const recentThreats = [
    { key: '1', time: '10:23:45', type: 'Prompt Injection', source: 'User-A', status: '已拦截' },
    { key: '2', time: '10:15:12', type: 'Sensitive Info', source: 'User-B', status: '已脱敏' },
    { key: '3', time: '09:58:33', type: 'Harmful Content', source: 'User-C', status: '已拦截' },
    { key: '4', time: '09:42:10', type: 'Jailbreak Attempt', source: 'User-A', status: '已拦截' },
  ];

  const columns = [
    { title: '时间', dataIndex: 'time', key: 'time' },
    { title: '威胁类型', dataIndex: 'type', key: 'type', render: (text: string) => <Tag color="red">{text}</Tag> },
    { title: '来源用户', dataIndex: 'source', key: 'source' },
    { title: '处理状态', dataIndex: 'status', key: 'status', render: (text: string) => <Tag color="success">{text}</Tag> },
  ];

  return (
    <div style={{ height: '100%' }}>
      <Title level={4} style={{ marginBottom: 24 }}>系统概览</Title>
      
      {/* 顶部统计卡片 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false}>
            <Statistic 
              title="今日拦截总数" 
              value={128} 
              prefix={<SafetyCertificateOutlined style={{ color: '#ff4d4f' }} />} 
              suffix={<small style={{ fontSize: 12, color: '#cf1322' }}><ArrowUpOutlined /> 12%</small>}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false}>
            <Statistic 
              title="安全请求处理" 
              value={3452} 
              prefix={<SafetyOutlined style={{ color: '#52c41a' }} />} 
              suffix={<small style={{ fontSize: 12, color: '#3f8600' }}><ArrowUpOutlined /> 5%</small>}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false}>
            <Statistic 
              title="平均响应延迟" 
              value={45} 
              suffix="ms" 
              prefix={<ThunderboltOutlined style={{ color: '#faad14' }} />} 
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false}>
            <Statistic 
              title="系统运行时间" 
              value="24h 15m" 
              prefix={<ClockCircleOutlined style={{ color: '#1890ff' }} />} 
            />
          </Card>
        </Col>
      </Row>

      {/* 中部图表和状态 */}
      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} lg={16}>
          <Card title="最近威胁拦截记录" bordered={false} style={{ height: '100%' }}>
            <Table 
              dataSource={recentThreats} 
              columns={columns} 
              pagination={false} 
              size="small"
            />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="防护模块状态" bordered={false} style={{ height: '100%' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span>Prompt 注入防护</span>
                  <span style={{ color: '#52c41a' }}>运行中</span>
                </div>
                <Progress percent={100} strokeColor="#52c41a" showInfo={false} size="small" />
              </div>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span>敏感信息过滤</span>
                  <span style={{ color: '#52c41a' }}>运行中</span>
                </div>
                <Progress percent={100} strokeColor="#52c41a" showInfo={false} size="small" />
              </div>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span>内容合规检测</span>
                  <span style={{ color: '#faad14' }}>加载中...</span>
                </div>
                <Progress percent={70} strokeColor="#faad14" showInfo={false} size="small" status="active" />
              </div>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span>越狱检测</span>
                  <span style={{ color: '#52c41a' }}>运行中</span>
                </div>
                <Progress percent={100} strokeColor="#52c41a" showInfo={false} size="small" />
              </div>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
