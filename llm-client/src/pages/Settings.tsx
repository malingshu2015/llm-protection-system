import React from 'react';
import { Card, Typography, Tabs, Form, Input, Switch, Button, Select, Slider, Divider, message } from 'antd';
import { SaveOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

const SettingsPage: React.FC = () => {
  const [form] = Form.useForm();

  const handleSave = () => {
    message.success('配置已保存');
  };

  return (
    <div style={{ height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>系统设置</Title>
        <Button type="primary" icon={<SaveOutlined />} onClick={handleSave}>
          保存更改
        </Button>
      </div>

      <Card bordered={false}>
        <Tabs defaultActiveKey="1">
          {/* 安全规则配置 */}
          <TabPane tab="安全防护规则" key="1">
            <Form layout="vertical" form={form} initialValues={{ 
                enablePromptInjection: true,
                enableSensitiveInfo: true,
                enableHarmfulContent: true,
                sensitivityLevel: 80
            }}>
              <Title level={5}>检测模块开关</Title>
              <Form.Item name="enablePromptInjection" label="Prompt 注入检测" valuePropName="checked">
                <Switch checkedChildren="开启" unCheckedChildren="关闭" />
              </Form.Item>
              <Text type="secondary">防止用户通过对抗性指令绕过模型限制。</Text>
              
              <Divider />
              
              <Form.Item name="enableSensitiveInfo" label="敏感信息过滤 (PII)" valuePropName="checked">
                <Switch checkedChildren="开启" unCheckedChildren="关闭" />
              </Form.Item>
              <Text type="secondary">自动识别并替换手机号、邮箱、身份证等敏感数据。</Text>

              <Divider />

              <Form.Item name="enableHarmfulContent" label="有害内容拦截" valuePropName="checked">
                <Switch checkedChildren="开启" unCheckedChildren="关闭" />
              </Form.Item>
              <Text type="secondary">拦截暴力、色情、仇恨言论等内容。</Text>

              <Divider />

              <Title level={5}>检测灵敏度阈值</Title>
              <Form.Item name="sensitivityLevel" label="全局灵敏度 (0-100)">
                <Slider marks={{ 0: '宽松', 50: '平衡', 100: '严格' }} />
              </Form.Item>
            </Form>
          </TabPane>

          {/* 模型配置 */}
          <TabPane tab="模型与后端" key="2">
            <Form layout="vertical" initialValues={{ 
                backendUrl: 'http://localhost:11434',
                defaultModel: 'llama3'
            }}>
              <Form.Item label="Ollama 后端地址" name="backendUrl">
                <Input placeholder="例如: http://localhost:11434" />
              </Form.Item>
              <Form.Item label="默认模型" name="defaultModel">
                <Select>
                    <Select.Option value="llama3">Llama 3</Select.Option>
                    <Select.Option value="mistral">Mistral</Select.Option>
                    <Select.Option value="qwen">Qwen</Select.Option>
                </Select>
              </Form.Item>
            </Form>
          </TabPane>

          {/* 系统常规 */}
          <TabPane tab="常规设置" key="3">
             <Form layout="vertical">
                <Form.Item label="界面语言">
                    <Select defaultValue="zh_CN">
                        <Select.Option value="zh_CN">简体中文</Select.Option>
                        <Select.Option value="en_US">English</Select.Option>
                    </Select>
                </Form.Item>
                <Form.Item label="主题模式">
                    <Select defaultValue="light">
                        <Select.Option value="light">亮色模式</Select.Option>
                        <Select.Option value="dark">暗色模式</Select.Option>
                        <Select.Option value="auto">跟随系统</Select.Option>
                    </Select>
                </Form.Item>
             </Form>
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default SettingsPage;