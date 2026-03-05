import React, { useEffect, useState } from 'react';
import { Card, Typography, Tabs, Form, Switch, Button, Select, Slider, Divider, message, Spin, Space, Checkbox, Tag } from 'antd';
import { SaveOutlined, ReloadOutlined, RobotOutlined } from '@ant-design/icons';
import { apiService } from '../services/api';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

const SettingsPage: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [models, setModels] = useState<any[]>([]);
  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [language, setLanguage] = useState<string>('zh_CN');

  // 加载模型列表
  const fetchModels = async () => {
    try {
      const response = await fetch('http://localhost:8082/api/v1/ollama/models');
      const data = await response.json();
      if (data.data) {
        setModels(data.data);
        // 加载已保存的模型选择
        const savedModels = apiService.getSelectedModels();
        if (savedModels.length > 0) {
          setSelectedModels(savedModels);
        } else {
          // 默认选择前3个模型
          setSelectedModels(data.data.slice(0, 3).map((m: any) => m.id));
        }
      }
    } catch (error) {
      console.error('获取模型列表失败:', error);
    }
  };

  // 加载设置
  const fetchSettings = async () => {
    setLoading(true);
    try {
      const data = await apiService.getSecuritySettings();
      console.log('[Settings] 从 API 获取的配置:', data);
      console.log('[Settings] enable_content_masking 值:', data.enable_content_masking);
      form.setFieldsValue({
        enablePromptInjection: data.enable_prompt_injection,
        enableSensitiveInfo: data.enable_sensitive_info,
        enableHarmfulContent: data.enable_harmful_content,
        sensitivityLevel: data.sensitivity_level,
        dryRunMode: data.dry_run_mode,
        enableRateLimiting: data.enable_rate_limiting,
        enableContentMasking: data.enable_content_masking
      });
      console.log('[Settings] 表单值已设置');
    } catch (error: any) {
      message.error('获取设置失败: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
    fetchModels();
  }, []);

  const handleSave = async () => {
    try {
      setSaving(true);
      const values = await form.validateFields();

      const updateData = {
        enable_prompt_injection: values.enablePromptInjection,
        enable_sensitive_info: values.enableSensitiveInfo,
        enable_harmful_content: values.enableHarmfulContent,
        sensitivity_level: values.sensitivityLevel,
        dry_run_mode: values.dryRunMode,
        enable_rate_limiting: values.enableRateLimiting,
        enable_content_masking: values.enableContentMasking,
        selected_models: selectedModels  // 添加选择的模型
      };

      await apiService.updateSecuritySettings(updateData);
      message.success('防御策略配置已同步并保存');
    } catch (error: any) {
      if (error.errorFields) return;
      message.error('保存失败: ' + error.message);
    } finally {
      setSaving(false);
    }
  };

  const handleModelToggle = (modelId: string) => {
    setSelectedModels(prev => {
      if (prev.includes(modelId)) {
        return prev.filter(id => id !== modelId);
      } else {
        return [...prev, modelId];
      }
    });
  };

  // 语言切换处理
  const handleLanguageChange = (lang: string) => {
    setLanguage(lang);
    // 这里可以添加实际的国际化逻辑
    message.info(`语言已切换为: ${lang === 'zh_CN' ? '简体中文' : 'English'}`);
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <Spin size="large" tip="正在加载系统配置..." />
      </div>
    );
  }

  return (
    <div style={{ height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>系统防护策略</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchSettings}>刷新</Button>
          <Button type="primary" icon={<SaveOutlined />} onClick={handleSave} loading={saving}>
            保存并应用
          </Button>
        </Space>
      </div>

      <Card bordered={false}>
        <Tabs defaultActiveKey="1">
          {/* 模型选择 */}
          <TabPane tab={<span><RobotOutlined /> 模型选择</span>} key="0">
            <div>
              <Title level={5}>选择要防护的大模型</Title>
              <Text type="secondary">选择需要应用安全防护策略的本地模型。未选择的模型将直接放行，不进行安全检测。</Text>

              <Divider />

              <div style={{ marginTop: 16 }}>
                {models.length === 0 ? (
                  <Text type="secondary">未检测到本地模型，请确保 Ollama 服务正在运行</Text>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
                    {models.map(model => (
                      <Card
                        key={model.id}
                        size="small"
                        hoverable
                        onClick={() => handleModelToggle(model.id)}
                        style={{
                          borderColor: selectedModels.includes(model.id) ? '#f97316' : '#d9d9d9',
                          backgroundColor: selectedModels.includes(model.id) ? '#ffedd5' : '#ffffff'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <Text strong style={{ fontSize: 13 }}>{model.id}</Text>
                          <Checkbox checked={selectedModels.includes(model.id)} />
                        </div>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {model.parent || 'Ollama'}
                        </Text>
                      </Card>
                    ))}
                  </div>
                )}
              </div>

              <Divider />

              <div>
                <Text strong>已选择 {selectedModels.length} 个模型进行防护</Text>
                {selectedModels.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    {selectedModels.map(id => (
                      <Tag key={id} color="orange" style={{ marginBottom: 4 }}>{id}</Tag>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </TabPane>

          {/* 安全规则配置 */}
          <TabPane tab="核心防御模块" key="1">
            <Form layout="vertical" form={form}>
              <Title level={5}>模块开关控制</Title>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
                <div>
                  <Form.Item name="enablePromptInjection" label="Prompt 注入检测 (AI 反越狱)" valuePropName="checked">
                    <Switch checkedChildren="开启" unCheckedChildren="关闭" />
                  </Form.Item>
                  <Text type="secondary">防御 DAN、角色扮演等尝试绕过模型系统指令的攻击。</Text>
                </div>

                <div>
                  <Form.Item name="enableSensitiveInfo" label="数据脱敏 (PII 治理)" valuePropName="checked">
                    <Switch checkedChildren="开启" unCheckedChildren="关闭" />
                  </Form.Item>
                  <Text type="secondary">自动识别并遮蔽手机号、身份证、邮箱等个人隐私数据。</Text>
                </div>

                <div>
                  <Form.Item name="enableHarmfulContent" label="内容合规拦截 (T&S)" valuePropName="checked">
                    <Switch checkedChildren="开启" unCheckedChildren="关闭" />
                  </Form.Item>
                  <Text type="secondary">过滤暴力、色情、仇恨言论及违法违规活动信息。</Text>
                </div>

                <div>
                  <Form.Item name="dryRunMode" label="观察模式 (Dry-Run)" valuePropName="checked">
                    <Switch checkedChildren="开启" unCheckedChildren="关闭" />
                  </Form.Item>
                  <Text type="secondary">检测并记录风险但不实际拦截请求，用于规则调优。</Text>
                </div>
              </div>

              <Divider />

              <Title level={5}>判定灵敏度控制</Title>
              <Form.Item name="sensitivityLevel" label="全局置信度阈值 (0-100)">
                <Slider
                  marks={{ 0: '宽松', 60: '平衡', 90: '严格' }}
                  step={1}
                  tipFormatter={(value) => `置信度 > ${value}% 时触发拦截`}
                />
              </Form.Item>
              <Text type="secondary">降低阈值会增加拦截率，但也可能导致更多误报。建议初次部署设为 60-70。</Text>
            </Form>
          </TabPane>

          {/* 系统常规 */}
          <TabPane tab="常规与高级设置" key="3">
            <Form layout="vertical" form={form}>
              <Form.Item name="enableRateLimiting" label="频率限制 (Rate Limiting)" valuePropName="checked">
                <Switch checkedChildren="开启" unCheckedChildren="关闭" />
              </Form.Item>

              <Divider />

              <Form.Item label="管理端语言">
                <Select
                  value={language}
                  onChange={handleLanguageChange}
                  style={{ width: 200 }}
                >
                  <Select.Option value="zh_CN">简体中文</Select.Option>
                  <Select.Option value="en_US">English</Select.Option>
                </Select>
              </Form.Item>
              <Text type="secondary">选择管理界面的显示语言（需要刷新页面生效）</Text>
            </Form>
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default SettingsPage;
