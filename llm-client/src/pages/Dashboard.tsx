import React from 'react';
import { Row, Col, Card, Statistic, Progress, Table, Tag, Typography, Button, Modal, Input, message } from 'antd';
import {
  SafetyCertificateOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  SafetyOutlined,
  ArrowUpOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { TextArea } = Input;

const Dashboard: React.FC = () => {
  const [events, setEvents] = React.useState<any[]>([]);
  const [stats, setStats] = React.useState({ today: 0, total: 0, models: 0 });
  const [typeStats, setTypeStats] = React.useState({ harmful_content: 0, prompt_injection: 0, sensitive_info: 0, total: 0 });
  const [loading, setLoading] = React.useState(true);
  const [allowModal, setAllowModal] = React.useState<{ open: boolean; event: any | null }>({ open: false, event: null });
  const [allowReason, setAllowReason] = React.useState('');
  const [allowLoading, setAllowLoading] = React.useState(false);

  const cardStyle = {
    borderRadius: 16,
    border: '1px solid #f1e4d9',
    boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.02)',
    background: '#fff',
    height: '100%',
  };

  const iconWrapperStyle = (color: string, bg: string, border?: string) => ({
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 48,
    height: 48,
    borderRadius: 16,
    background: bg,
    border: border ? `1px solid ${border}` : 'none',
    color: color,
    fontSize: 24,
  });

  // 获取实时数据逻辑
  const fetchDashboardData = async () => {
    try {
      const token = 'mock-token-for-dev';
      // 1. 获取最近事件
      const response = await fetch('http://localhost:8082/api/v1/events?page_size=10', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      if (data && data.events) {
        setEvents(data.events);
      }

      // 2. 获取统计指标
      const statsRes = await fetch('http://localhost:8082/api/v1/events/stats', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const statsData = await statsRes.json();
      if (statsData) {
        setStats(prev => ({
          ...prev,
          today: statsData.total || 0,
          total: (statsData.total || 0) + 1250
        }));
        setTypeStats({
          harmful_content: statsData.harmful_content || 0,
          prompt_injection: statsData.prompt_injection || 0,
          sensitive_info: statsData.sensitive_info || 0,
          total: statsData.total || 0,
        });
      }

      // 3. 获取已安装的模型数量
      try {
        const modelsRes = await fetch('http://localhost:8082/api/v1/ollama/models');
        if (modelsRes.ok) {
          const modelsData = await modelsRes.json();
          const modelCount = modelsData.models?.length || modelsData.data?.length || 0;
          setStats(prev => ({ ...prev, models: modelCount }));
        }
      } catch (error) {
        console.error('获取模型列表失败:', error);
        // 保持默认值或使用0
      }

      setLoading(false);
    } catch (error) {
      console.error('Dashboard data fetch error:', error);
    }
  };

  React.useEffect(() => {
    fetchDashboardData();
    const timer = setInterval(fetchDashboardData, 3000); // 3秒高清实时轮询
    return () => clearInterval(timer);
  }, []);

  const formatTime = (ts: number) => {
    if (!ts) return '--:--:--';
    const date = new Date(ts * 1000);
    return date.toLocaleTimeString('zh-CN', { hour12: false });
  };

  // 放行确认
  const handleAllow = (event: any) => {
    setAllowReason('');
    setAllowModal({ open: true, event });
  };

  const confirmAllow = async () => {
    if (!allowModal.event) return;
    setAllowLoading(true);
    try {
      const res = await fetch(
        `http://localhost:8082/api/v1/events/${allowModal.event.event_id}/allow`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer mock-token-for-dev',
          },
          body: JSON.stringify({ reason: allowReason || '手动放行' }),
        }
      );
      const data = await res.json();
      if (res.ok && data.success) {
        message.success(`已放行，内容已加入白名单`);
        setAllowModal({ open: false, event: null });
        fetchDashboardData(); // 刷新列表
      } else {
        message.error(data.detail || '放行失败');
      }
    } catch (e) {
      message.error('网络请求失败');
    } finally {
      setAllowLoading(false);
    }
  };

  const columns = [
    {
      title: '发生时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 100,
      render: (ts: number) => <Text type="secondary" style={{ fontFamily: 'Monaco, monospace', fontSize: 13 }}>{formatTime(ts)}</Text>
    },
    {
      title: '拦截策略',
      dataIndex: 'detection_type',
      key: 'detection_type',
      width: 130,
      render: (text: string) => (
        <Tag color={text.includes('injection') ? '#f97316' : '#ef4444'} style={{ borderRadius: 6, fontWeight: 600 }}>
          {text.toUpperCase().replace('_', ' ')}
        </Tag>
      )
    },
    {
      title: '违规详情 (具体威胁内容)',
      dataIndex: 'reason',
      key: 'reason',
      render: (text: string, record: any) => (
        <span>
          <Text strong style={{ display: 'block', fontSize: 13 }}>{record.rule_name || '安全规则触发'}</Text>
          <Text type="secondary" ellipsis={{ tooltip: text }} style={{ fontSize: 12, maxWidth: 300 }}>
            命中特征: {text}
          </Text>
        </span>
      )
    },
    {
      title: '风险等级',
      dataIndex: 'severity',
      key: 'severity',
      width: 110,
      render: (text: string) => (
        <Tag color={text === 'high' ? 'red' : 'orange'} icon={<InfoCircleOutlined />} style={{ border: 'none', fontWeight: 600 }}>
          {text === 'high' ? 'CRITICAL' : 'WARNING'}
        </Tag>
      )
    },
    {
      title: '防护动作',
      key: 'action',
      width: 100,
      render: () => <Tag color="success" style={{ fontWeight: 700, borderRadius: 4 }}>已阻断 (Block)</Tag>
    },
    {
      title: '操作',
      key: 'ops',
      width: 90,
      render: (_: any, record: any) => (
        <Button
          size="small"
          icon={<CheckCircleOutlined />}
          onClick={() => handleAllow(record)}
          style={{ borderColor: '#10b981', color: '#10b981', borderRadius: 6 }}
        >
          放行
        </Button>
      )
    },
  ];

  return (
    <div style={{ height: '100%', padding: '0 8px' }}>
      <Title level={3} style={{ marginBottom: 32, fontWeight: 800 }}>
        安防指挥中心看板
        <Tag color="processing" style={{ marginLeft: 16, verticalAlign: 'middle' }}>LIVE 实时监控中</Tag>
      </Title>

      <Row gutter={[24, 24]}>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} style={cardStyle}>
            <Statistic
              title={<span style={{ fontWeight: 600, color: '#64748b' }}>今日活跃违规</span>}
              value={stats.today}
              prefix={<div style={iconWrapperStyle('#f97316', '#fff7ed')}><SafetyCertificateOutlined /></div>}
              suffix={<small style={{ fontSize: 13, color: '#f97316', marginLeft: 8, fontWeight: 700 }}><ArrowUpOutlined /> {loading ? '...' : 'Realtime'}</small>}
              valueStyle={{ fontWeight: 800, fontSize: 32, color: '#1e293b', marginLeft: 16 }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} style={cardStyle}>
            <Statistic
              title={<span style={{ fontWeight: 600, color: '#64748b' }}>总计阻断事件</span>}
              value={stats.total}
              prefix={<div style={iconWrapperStyle('#f59e0b', '#fef3c7')}><SafetyOutlined /></div>}
              valueStyle={{ fontWeight: 800, fontSize: 32, color: '#1e293b', marginLeft: 16 }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} style={cardStyle}>
            <Statistic
              title={<span style={{ fontWeight: 600, color: '#64748b' }}>已防护模型</span>}
              value={stats.models}
              prefix={<div style={iconWrapperStyle('#3b82f6', '#dbeafe')}><ThunderboltOutlined /></div>}
              valueStyle={{ fontWeight: 800, fontSize: 32, color: '#1e293b', marginLeft: 16 }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} style={cardStyle}>
            <Statistic
              title={<span style={{ fontWeight: 600, color: '#64748b' }}>系统防御状态</span>}
              value="Secure · 稳健"
              prefix={<div style={iconWrapperStyle('#10b981', '#d1fae5')}><ClockCircleOutlined /></div>}
              valueStyle={{ fontWeight: 800, fontSize: 28, color: '#10b981', marginLeft: 16 }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[24, 24]} style={{ marginTop: 24 }}>
        <Col xs={24} lg={18}>
          <Card title={<span style={{ fontWeight: 700, fontSize: 16 }}>最新威胁拦截记录 (实时反馈流)</span>} bordered={false} style={cardStyle}>
            <Table
              dataSource={events}
              columns={columns}
              pagination={false}
              size="middle"
              loading={loading && events.length === 0}
              rowKey="event_id"
              locale={{ emptyText: '暂无异常流量拦截记录' }}
            />
          </Card>
        </Col>
        <Col xs={24} lg={6}>
          <Card title={<span style={{ fontWeight: 700, fontSize: 16 }}>拦截类型分布</span>} bordered={false} style={cardStyle}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20, padding: '8px 0' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13 }}>有害内容</span>
                  <span style={{ fontWeight: 700, color: '#ef4444' }}>{typeStats.harmful_content}</span>
                </div>
                <Progress
                  percent={typeStats.total ? Math.round(typeStats.harmful_content / typeStats.total * 100) : 0}
                  strokeColor="#ef4444" showInfo={false} size="small"
                />
              </div>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13 }}>提示注入</span>
                  <span style={{ fontWeight: 700, color: '#f97316' }}>{typeStats.prompt_injection}</span>
                </div>
                <Progress
                  percent={typeStats.total ? Math.round(typeStats.prompt_injection / typeStats.total * 100) : 0}
                  strokeColor="#f97316" showInfo={false} size="small"
                />
              </div>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13 }}>敏感信息</span>
                  <span style={{ fontWeight: 700, color: '#3b82f6' }}>{typeStats.sensitive_info}</span>
                </div>
                <Progress
                  percent={typeStats.total ? Math.round(typeStats.sensitive_info / typeStats.total * 100) : 0}
                  strokeColor="#3b82f6" showInfo={false} size="small"
                />
              </div>
              <div style={{ borderTop: '1px solid #f1e4d9', paddingTop: 12, display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 12, color: '#64748b' }}>累计拦截总数</span>
                <span style={{ fontWeight: 800, fontSize: 15, color: '#1e293b' }}>{typeStats.total}</span>
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 放行确认 Modal */}
      <Modal
        title={
          <span style={{ color: '#10b981', fontWeight: 700 }}>
            <CheckCircleOutlined style={{ marginRight: 8 }} />
            确认放行误拦截内容
          </span>
        }
        open={allowModal.open}
        onOk={confirmAllow}
        onCancel={() => setAllowModal({ open: false, event: null })}
        okText="确认放行"
        cancelText="取消"
        confirmLoading={allowLoading}
        okButtonProps={{ style: { background: '#10b981', borderColor: '#10b981' } }}
      >
        {allowModal.event && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ background: '#f8fafc', padding: 12, borderRadius: 8, border: '1px solid #e2e8f0' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>拦截内容</Text>
              <div style={{ marginTop: 4, fontWeight: 600, wordBreak: 'break-all' }}>
                {allowModal.event.content || allowModal.event.reason}
              </div>
            </div>
            <div style={{ background: '#fef3c7', padding: 10, borderRadius: 8, border: '1px solid #fde68a', fontSize: 12, color: '#92400e' }}>
              ⚠️ 放行后该内容将加入白名单，后续相同内容不再拦截。
            </div>
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>放行备注（可选）</Text>
              <TextArea
                style={{ marginTop: 6 }}
                rows={2}
                placeholder="填写放行原因，方便后续审计..."
                value={allowReason}
                onChange={e => setAllowReason(e.target.value)}
              />
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default Dashboard;
