import React, { useEffect, useState } from 'react';
import {
  Card,
  Typography,
  Tabs,
  Button,
  Table,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Row,
  Col,
  Alert,
  Divider,
  Tooltip,
  Popconfirm,
  Statistic,
} from 'antd';
import {
  ApiOutlined,
  CopyOutlined,
  DeleteOutlined,
  PlusOutlined,
  KeyOutlined,
  LinkOutlined,
  QuestionCircleOutlined,
  CheckCircleOutlined,
  ThunderboltOutlined,
  SafetyOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { TabPane } = Tabs;
const { TextArea } = Input;

// 系统状态接口
interface SystemStatus {
  api_address: string;
  api_base_path: string;
  total_api_keys: number;
  active_clients: number;
  security_enabled: boolean;
  supported_clients: number;
}

interface APIKey {
  key: string;
  name: string;
  permissions: string[];
  rateLimit: number;
  models: string[];
  createdAt: string;
  lastUsed?: string;
  description?: string;
  clientType?: string;
}

interface ClientConfig {
  name: string;
  icon: string;
  baseUrl: string;
  apiKeyLocation: string;
  setupSteps: string[];
  note?: string;
}

const CLIENT_CONFIGS: ClientConfig[] = [
  {
    name: 'Cherry Studio',
    icon: '🍒',
    baseUrl: 'http://localhost:8082/v1',
    apiKeyLocation: '设置 → 自定义端点 → API密钥',
    setupSteps: [
      '打开 Cherry Studio',
      '进入"设置" → "提供者"',
      '添加新提供者，选择"OpenAI兼容"',
      '基础URL填入: http://localhost:8082/v1',
      'API密钥填入: cherry-studio-key',
      '保存配置'
    ],
    note: '支持流式响应和多轮对话'
  },
  {
    name: 'ChatBox',
    icon: '💬',
    baseUrl: 'http://localhost:8082/v1',
    apiKeyLocation: '设置 → API配置 → API密钥',
    setupSteps: [
      '打开 ChatBox',
      '进入"设置" → "API提供者"',
      '选择"OpenAI"或"自定义"',
      'API Base URL: http://localhost:8082/v1',
      'API Key: chatbox-key',
      '点击测试连接'
    ],
    note: '支持多模型切换'
  },
  {
    name: 'ChatWise',
    icon: '💡',
    baseUrl: 'http://localhost:8082/v1',
    apiKeyLocation: '设置 → API设置 → 密钥',
    setupSteps: [
      '打开 ChatWise',
      '进入"Settings" → "API Configuration"',
      'Endpoint: http://localhost:8082/v1',
      'API Key: chatwise-key 或 api_key_123456',
      '选择模型并保存'
    ],
    note: '支持api_key_格式兼容'
  },
  {
    name: 'Open WebUI',
    icon: '🌐',
    baseUrl: 'http://localhost:8082/v1',
    apiKeyLocation: '设置 → 连接 → OpenAI API',
    setupSteps: [
      '打开 Open WebUI',
      '进入"Admin Panel" → "Settings" → "Connections"',
      '选择"OpenAI API"',
      'API URL: http://localhost:8082/v1',
      'API Key: demo-key-12345',
      '保存设置'
    ],
    note: '需要管理员权限'
  },
  {
    name: 'Cursor / Windsurf',
    icon: '⚡',
    baseUrl: 'http://localhost:8082/v1',
    apiKeyLocation: '设置 → 模型 → 自定义提供者',
    setupSteps: [
      '打开设置，进入"Models"',
      '添加自定义提供者',
      'Base URL: http://localhost:8082/v1',
      'API Key: demo-key-12345',
      '模型名称: 选择已安装的Ollama模型'
    ],
    note: '适合代码辅助场景'
  },
  {
    name: 'Continue',
    icon: '▶️',
    baseUrl: 'http://localhost:8082/v1',
    apiKeyLocation: 'config.json配置文件',
    setupSteps: [
      '打开 ~/.continue/config.json',
      '添加Ollama提供者配置',
      '将API Base改为: http://localhost:8082/v1',
      '添加apiKey字段: demo-key-12345',
      '重启VSCode'
    ],
    note: 'VSCode扩展，需编辑配置文件'
  },
];

const ClientConfigPage: React.FC = () => {
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [selectedClient, setSelectedClient] = useState<ClientConfig | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    api_address: 'localhost:8082',
    api_base_path: '/v1',
    total_api_keys: 0,
    active_clients: 0,
    security_enabled: true,
    supported_clients: CLIENT_CONFIGS.length,
  });

  // 加载系统状态和API密钥
  const loadSystemData = async () => {
    setLoading(true);
    try {
      // 加载API密钥列表
      const keysResponse = await fetch('http://localhost:8082/api/v1/auth/api-keys', {
        headers: {
          'Authorization': 'Bearer admin_d16226b0-d788-49ac-92e8-207422bf42ff'
        }
      });

      if (keysResponse.ok) {
        const data = await keysResponse.json();
        const keys = data.api_keys || [];
        setApiKeys(keys);

        // 更新系统状态
        setSystemStatus(prev => ({
          ...prev,
          total_api_keys: data.total_count || keys.length,
        }));
      }

      // 可以添加更多系统状态API调用
      // 例如：获取活跃客户端数、安全检测状态等
    } catch (error) {
      console.error('加载系统数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSystemData();
  }, []);

  // 复制API密钥
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    message.success('已复制到剪贴板');
  };

  // 生成新API密钥
  const handleGenerateKey = async () => {
    try {
      const values = await form.validateFields();
      const response = await fetch('http://localhost:8082/api/v1/auth/api-keys', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer admin_d16226b0-d788-49ac-92e8-207422bf42ff'
        },
        body: JSON.stringify({
          name: values.name,
          permissions: values.permissions,
          rate_limit: values.rateLimit,
          models: ['*'],
          max_clients: 10,
          license_type: 'standard',
          description: values.description
        }),
      });
      if (response.ok) {
        const data = await response.json();
        message.success(`API密钥生成成功: ${data.api_key}`);
        setModalVisible(false);
        form.resetFields();
        loadSystemData();
      } else {
        const error = await response.json();
        message.error(error.detail || '生成失败');
      }
    } catch (error) {
      message.error('生成失败');
    }
  };

  // 删除API密钥
  const handleDeleteKey = async (key: string) => {
    try {
      // 使用完整的密钥而不是截断的显示值
      const fullKey = apiKeys.find(k => k.key.startsWith(key))?.key || key;
      const response = await fetch(`http://localhost:8082/api/v1/auth/api-keys/${fullKey}`, {
        method: 'DELETE',
        headers: {
          'Authorization': 'Bearer admin_d16226b0-d788-49ac-92e8-207422bf42ff'
        }
      });
      if (response.ok) {
        message.success('删除成功');
        loadSystemData();
      } else {
        const error = await response.json();
        message.error(error.detail || '删除失败');
      }
    } catch (error) {
      message.error('删除失败');
    }
  };

  // API密钥表格列
  const columns = [
    {
      title: '密钥名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: APIKey) => (
        <Space>
          <KeyOutlined />
          <span>{name}</span>
          {record.clientType && (
            <Tag color="blue" style={{ fontSize: 11 }}>{record.clientType}</Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'API密钥',
      dataIndex: 'key',
      key: 'key',
      render: (key: string) => (
        <Space>
          <Text code style={{ fontSize: 11 }}>
            {key.length > 20 ? key.slice(0, 15) + '...' : key}
          </Text>
          <Button
            type="text"
            size="small"
            icon={<CopyOutlined />}
            onClick={() => copyToClipboard(key)}
          />
        </Space>
      ),
    },
    {
      title: '权限',
      dataIndex: 'permissions',
      key: 'permissions',
      render: (perms: string[]) => (
        <>
          {perms.includes('*') ? (
            <Tag color="purple">全部权限</Tag>
          ) : (
            perms.map(p => <Tag key={p}>{p}</Tag>)
          )}
        </>
      ),
    },
    {
      title: '速率限制',
      dataIndex: 'rateLimit',
      key: 'rateLimit',
      render: (limit: number) => (
        <Space>
          <ThunderboltOutlined />
          <span>{limit}/分钟</span>
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: APIKey) => (
        <Space>
          <Popconfirm
            title="确认删除此API密钥？"
            onConfirm={() => handleDeleteKey(record.key)}
            okText="删除"
            cancelText="取消"
          >
            <Button type="text" danger icon={<DeleteOutlined />} size="small" />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ height: '100%', overflowY: 'auto' }}>
      <div style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>客户端配置中心</Title>
        <Text type="secondary">
          配置第三方客户端接入本地大模型防护系统
        </Text>
      </div>

      {/* 系统状态概览 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="API代理地址"
              value={systemStatus.api_address}
              prefix={<LinkOutlined />}
              valueStyle={{ fontSize: 18 }}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              OpenAI兼容接口: {systemStatus.api_base_path}
            </Text>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="活跃API密钥"
              value={systemStatus.total_api_keys}
              prefix={<KeyOutlined />}
              valueStyle={{ fontSize: 18, color: '#3f8600' }}
              loading={loading}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              可用于客户端认证
            </Text>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="支持的客户端"
              value={systemStatus.supported_clients}
              prefix={<ApiOutlined />}
              valueStyle={{ fontSize: 18 }}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              Cherry Studio, ChatBox等
            </Text>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="安全检测"
              value={systemStatus.security_enabled ? '启用' : '禁用'}
              prefix={<SafetyOutlined />}
              valueStyle={{ fontSize: 18, color: systemStatus.security_enabled ? '#cf1322' : '#52c41a' }}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              提示注入/越狱/内容过滤
            </Text>
          </Card>
        </Col>
      </Row>

      <Card bordered={false}>
        <Tabs defaultActiveKey="clients">
          {/* 支持的客户端列表 */}
          <TabPane tab={<span><ApiOutlined /> 客户端配置指南</span>} key="clients">
            <Alert
              message="接入说明"
              description="本系统提供OpenAI API兼容接口，支持所有使用OpenAI格式的第三方客户端。配置时将API Base地址指向本系统端口8082，即可享受安全防护功能。"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Row gutter={[16, 16]}>
              {CLIENT_CONFIGS.map((client) => (
                <Col span={12} key={client.name}>
                  <Card
                    size="small"
                    hoverable
                    onClick={() => setSelectedClient(client)}
                    style={{ height: '100%' }}
                    title={
                      <Space>
                        <span style={{ fontSize: 18 }}>{client.icon}</span>
                        <span>{client.name}</span>
                      </Space>
                    }
                    extra={
                      <Tooltip title="点击查看详细配置步骤">
                        <QuestionCircleOutlined />
                      </Tooltip>
                    }
                  >
                    <Space direction="vertical" size="small" style={{ width: '100%' }}>
                      <div>
                        <Text type="secondary" style={{ fontSize: 12 }}>API地址:</Text>
                        <br />
                        <Text code copyable style={{ fontSize: 12 }}>
                          {client.baseUrl}
                        </Text>
                      </div>
                      <div>
                        <Text type="secondary" style={{ fontSize: 12 }}>推荐密钥:</Text>
                        <br />
                        <Text code copyable style={{ fontSize: 12 }}>
                          {client.name.toLowerCase().replace(/\s/g, '-')}-key
                        </Text>
                      </div>
                      {client.note && (
                        <Tag color="blue" style={{ fontSize: 11 }}>{client.note}</Tag>
                      )}
                    </Space>
                  </Card>
                </Col>
              ))}
            </Row>
          </TabPane>

          {/* API密钥管理 */}
          <TabPane tab={<span><KeyOutlined /> API密钥管理</span>} key="keys">
            <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
              <Alert
                message="API密钥用于客户端认证"
                description="每个第三方客户端都需要配置API密钥才能访问防护系统。预设密钥已为常用客户端创建，您也可以创建自定义密钥。"
                type="warning"
                showIcon
                style={{ flex: 1, marginRight: 16 }}
              />
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => setModalVisible(true)}
              >
                生成新密钥
              </Button>
            </div>

            <Table
              columns={columns}
              dataSource={apiKeys}
              loading={loading}
              rowKey="key"
              size="small"
              pagination={false}
            />
          </TabPane>

          {/* 快速测试 */}
          <TabPane tab={<span><CheckCircleOutlined /> 连接测试</span>} key="test">
            <div style={{ maxWidth: 600, margin: '0 auto' }}>
              <Alert
                message="测试API连接"
                description="使用以下命令测试防护系统是否正常工作"
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />

              <Card title="cURL测试命令" size="small">
                <TextArea
                  value={`curl -X POST http://localhost:8082/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer demo-key-12345" \\
  -d '{
    "model": "llama3",
    "messages": [{"role": "user", "content": "你好"}]
  }'`}
                  autoSize={{ minRows: 8, maxRows: 15 }}
                  readOnly
                  style={{ fontFamily: 'monospace', fontSize: 12 }}
                />
                <Button
                  type="primary"
                  icon={<CopyOutlined />}
                  onClick={() => copyToClipboard('curl')}
                  style={{ marginTop: 8 }}
                >
                  复制命令
                </Button>
              </Card>

              <Divider />

              <Card title="Python测试代码" size="small">
                <TextArea
                  value={`import requests

response = requests.post(
    "http://localhost:8082/v1/chat/completions",
    headers={
        "Authorization": "Bearer demo-key-12345",
        "Content-Type": "application/json"
    },
    json={
        "model": "llama3",
        "messages": [{"role": "user", "content": "你好"}]
    }
)

print(response.json())`}
                  autoSize={{ minRows: 10, maxRows: 15 }}
                  readOnly
                  style={{ fontFamily: 'monospace', fontSize: 12 }}
                />
                <Button
                  type="primary"
                  icon={<CopyOutlined />}
                  onClick={() => copyToClipboard('python')}
                  style={{ marginTop: 8 }}
                >
                  复制代码
                </Button>
              </Card>
            </div>
          </TabPane>
        </Tabs>
      </Card>

      {/* 客户端配置详情弹窗 */}
      <Modal
        title={
          <Space>
            <span style={{ fontSize: 18 }}>{selectedClient?.icon}</span>
            <span>{selectedClient?.name} 配置指南</span>
          </Space>
        }
        open={!!selectedClient}
        onCancel={() => setSelectedClient(null)}
        footer={[
          <Button key="close" onClick={() => setSelectedClient(null)}>
            关闭
          </Button>,
          <Button
            key="copy"
            type="primary"
            icon={<CopyOutlined />}
            onClick={() => {
              if (selectedClient) {
                copyToClipboard(selectedClient.baseUrl);
              }
            }}
          >
            复制API地址
          </Button>,
        ]}
        width={600}
      >
        {selectedClient && (
          <div>
            <Alert
              message="配置步骤"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Card size="small" title="基础信息" style={{ marginBottom: 16 }}>
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                <div>
                  <Text strong>API Base URL:</Text>
                  <div style={{ marginTop: 4 }}>
                    <Text
                      code
                      copyable
                      style={{ fontSize: 13 }}
                    >
                      {selectedClient.baseUrl}
                    </Text>
                  </div>
                </div>
                <div>
                  <Text strong>推荐API密钥:</Text>
                  <div style={{ marginTop: 4 }}>
                    <Text
                      code
                      copyable
                      style={{ fontSize: 13 }}
                    >
                      {selectedClient.name.toLowerCase().replace(/\s/g, '-')}-key
                    </Text>
                  </div>
                </div>
                {selectedClient.note && (
                  <div>
                    <Text strong>注意事项:</Text>
                    <div style={{ marginTop: 4 }}>
                      <Text type="secondary">{selectedClient.note}</Text>
                    </div>
                  </div>
                )}
              </Space>
            </Card>

            <Card size="small" title="配置步骤">
              <ol style={{ paddingLeft: 16, margin: 0 }}>
                {selectedClient.setupSteps.map((step, index) => (
                  <li key={index} style={{ marginBottom: 8 }}>
                    <Text>{step}</Text>
                  </li>
                ))}
              </ol>
            </Card>

            <Divider />

            <Alert
              message="提示"
              description="配置完成后，建议先发送测试消息确认连接正常。如果遇到问题，请检查：1) 本系统服务是否运行在8082端口 2) API密钥是否正确 3) 防火墙是否允许连接"
              type="warning"
              showIcon
            />
          </div>
        )}
      </Modal>

      {/* 生成新API密钥弹窗 */}
      <Modal
        title="生成新API密钥"
        open={modalVisible}
        onOk={handleGenerateKey}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        okText="生成"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="密钥名称"
            rules={[{ required: true, message: '请输入密钥名称' }]}
          >
            <Input placeholder="例如: MyCustomClient" />
          </Form.Item>

          <Form.Item
            name="permissions"
            label="权限"
            initialValue={['chat', 'models']}
            rules={[{ required: true, message: '请选择权限' }]}
          >
            <Select mode="tags" placeholder="选择权限">
              <Select.Option value="chat">聊天</Select.Option>
              <Select.Option value="models">模型列表</Select.Option>
              <Select.Option value="rules">规则管理</Select.Option>
              <Select.Option value="admin">管理员权限</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="rateLimit"
            label="速率限制 (每分钟请求数)"
            initialValue={60}
          >
            <Input type="number" min={1} max={1000} />
          </Form.Item>

          <Form.Item
            name="description"
            label="描述"
          >
            <TextArea placeholder="可选：描述此密钥的用途" rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ClientConfigPage;
