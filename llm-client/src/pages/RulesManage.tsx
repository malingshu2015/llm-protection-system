/**
 * 规则管理页面
 * 提供规则的增删改查、批量操作、组合管理等功能
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Table,
  Button,
  Input,
  Select,
  Tag,
  Space,
  Modal,
  Form,
  Switch,
  message,
  Popconfirm,
  Tooltip,
  Badge,
  Row,
  Col,
  Statistic,
  Divider,
  Tabs,
  Alert,
  List,
  Typography,
  Progress
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
  ReloadOutlined,
  SafetyOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  CopyOutlined,
  PlayCircleOutlined,
  FilterOutlined,
  FileTextOutlined,
  TagsOutlined,
  CheckSquareOutlined,
  ExportOutlined,
  ImportOutlined,
  AppstoreOutlined
} from '@ant-design/icons';
import { apiService } from '../services/api';

const { Option } = Select;
const { TextArea } = Input;
const { TabPane } = Tabs;
const { Text } = Typography;

// 检测类型选项
const DETECTION_TYPES = [
  { value: 'prompt_injection', label: '提示注入', color: 'orange' },
  { value: 'jailbreak', label: '越狱攻击', color: 'red' },
  { value: 'harmful_content', label: '有害内容', color: 'magenta' },
  { value: 'sensitive_info', label: '敏感信息', color: 'purple' },
  { value: 'compliance_violation', label: '合规违规', color: 'blue' },
  { value: 'content_monitoring', label: '内容监控', color: 'cyan' },
  { value: 'custom', label: '自定义', color: 'default' },
];

// 严重级别选项
const SEVERITY_LEVELS = [
  { value: 'critical', label: '严重', color: '#ff4d4f' },
  { value: 'high', label: '高', color: '#ff7a45' },
  { value: 'medium', label: '中', color: '#ffa940' },
  { value: 'low', label: '低', color: '#73d13d' },
];

// 规则接口
interface Rule {
  id: string;
  name: string;
  description: string;
  detection_type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  patterns: string[];
  keywords: string[];
  enabled: boolean;
  block: boolean;
  priority: number;
  categories: string[];
  created_at?: string;
  updated_at?: string;
  isSystemRule?: boolean; // 标记是否为系统预设规则
}

// 规则组合接口
interface RuleGroup {
  id: string;
  name: string;
  description: string;
  ruleIds: string[];
  enabled: boolean;
  createdAt: string;
  modelType?: string; // 关联的模型类型
}

// 模型配置
const MODEL_TYPES = [
  { value: 'llama', label: 'Llama 系列', icon: '🦙', description: 'Meta Llama 模型优化配置' },
  { value: 'mistral', label: 'Mistral 系列', icon: '🌊', description: 'Mistral AI 模型优化配置' },
  { value: 'qwen', label: 'Qwen 系列', icon: '💫', description: '阿里通义千问模型优化配置' },
  { value: 'gemma', label: 'Gemma 系列', icon: '💎', description: 'Google Gemma 模型优化配置' },
  { value: 'phi', label: 'Phi 系列', icon: '🧠', description: 'Microsoft Phi 模型优化配置' },
  { value: 'custom', label: '自定义模型', icon: '🎯', description: '自定义模型配置' },
];

// 获取模型显示名称
const getModelDisplayName = (modelType?: string) => {
  const model = MODEL_TYPES.find(m => m.value === modelType);
  return model ? `${model.icon} ${model.label}` : modelType || '未知';
};

const RulesManage: React.FC = () => {
  // ==================== 状态管理 ====================
  const [rules, setRules] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [searchText, setSearchText] = useState('');
  const [filterType, setFilterType] = useState<string>('');
  const [filterSeverity, setFilterSeverity] = useState<string>('');
  const [filterEnabled, setFilterEnabled] = useState<boolean | null>(null);
  const [filterSource, setFilterSource] = useState<string>(''); // 新增：过滤规则来源

  // 模态框状态
  const [isEditModalVisible, setIsEditModalVisible] = useState(false);
  const [isTestModalVisible, setIsTestModalVisible] = useState(false);
  const [isGroupModalVisible, setIsGroupModalVisible] = useState(false);
  const [editingRule, setEditingRule] = useState<Rule | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  // 表单
  const [form] = Form.useForm();
  const [testForm] = Form.useForm();
  const [groupForm] = Form.useForm();

  // 统计数据
  const [stats, setStats] = useState({
    total: 0,
    enabled: 0,
    systemRules: 0,
    customRules: 0,
    byType: {
      prompt_injection: 0,
      jailbreak: 0,
      harmful_content: 0,
      sensitive_info: 0,
      compliance: 0,
    } as Record<string, number>,
    bySeverity: {} as Record<string, number>,
  });

  // 规则组合
  const [ruleGroups, setRuleGroups] = useState<RuleGroup[]>([]);
  const [activeTab, setActiveTab] = useState('rules');
  const [selectedModel] = useState<string>('llama'); // 选中的模型（固定为llama）

  // 待应用的配置变更（分类级别的pending状态）
  const [pendingCategoryChanges, setPendingCategoryChanges] = useState<Record<string, boolean>>({});

  // ==================== 数据加载 ====================
  const loadRules = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (filterType) params.detection_type = filterType;
      if (filterEnabled !== null) params.enabled = filterEnabled;

      const data = await apiService.getRules(params);

      // 处理返回的规则数据，后端直接返回数组，不是 {rules: [...]} 格式
      const rulesArray = Array.isArray(data) ? data : (data.rules || []);

      // 处理返回的规则数据，确保每条规则都有完整的字段
      const processedRules = rulesArray.map((rule: any) => ({
        ...rule,
        // 标记系统预设规则
        isSystemRule: rule.id?.startsWith('pi-') ||
                      rule.id?.startsWith('jb-') ||
                      rule.id?.startsWith('hc-') ||
                      rule.id?.startsWith('si-') ||
                      rule.id?.startsWith('cmp-'),
        // 确保必要字段存在
        patterns: rule.patterns || [],
        keywords: rule.keywords || [],
        categories: rule.categories || [],
        enabled: rule.enabled !== false, // 默认启用
        block: rule.block !== false, // 默认阻止
      }));

      setRules(processedRules);

      // 计算统计
      setStats({
        total: processedRules.length,
        enabled: processedRules.filter((r: Rule) => r.enabled).length,
        systemRules: processedRules.filter((r: any) => r.isSystemRule).length,
        customRules: processedRules.filter((r: any) => !r.isSystemRule).length,
        byType: processedRules.reduce((acc: Record<string, number>, r: Rule) => {
          acc[r.detection_type] = (acc[r.detection_type] || 0) + 1;
          return acc;
        }, {}),
        bySeverity: processedRules.reduce((acc: Record<string, number>, r: Rule) => {
          acc[r.severity] = (acc[r.severity] || 0) + 1;
          return acc;
        }, {}),
      });

      // 首次加载时初始化模型特定的规则组合
      if (!localStorage.getItem('model_rule_groups_initialized')) {
        initializeModelRuleGroups(processedRules);
        localStorage.setItem('model_rule_groups_initialized', 'true');
      }
    } catch (error) {
      message.error('加载规则列表失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [filterType, filterEnabled]);

  // 初始化模型特定的规则组合
  const initializeModelRuleGroups = (allRules: Rule[]) => {
    const modelGroups = [
      {
        id: 'model-llama-3',
        name: 'Llama 3 防护组合',
        description: '针对 Llama 3 模型优化的安全规则组合',
        ruleIds: allRules
          .filter(r => r.severity === 'critical' || r.severity === 'high')
          .slice(0, 20)
          .map(r => r.id),
        enabled: true,
        modelType: 'llama',
        createdAt: new Date().toISOString(),
      },
      {
        id: 'model-mistral',
        name: 'Mistral 防护组合',
        description: '针对 Mistral 模型优化的安全规则组合',
        ruleIds: allRules
          .filter(r => r.detection_type === 'jailbreak' || r.detection_type === 'prompt_injection')
          .slice(0, 15)
          .map(r => r.id),
        enabled: true,
        modelType: 'mistral',
        createdAt: new Date().toISOString(),
      },
      {
        id: 'model-qwen',
        name: 'Qwen 防护组合',
        description: '针对 Qwen 模型优化的安全规则组合（包含中文内容检测）',
        ruleIds: allRules
          .filter(r => r.categories?.includes('chinese') || r.detection_type === 'harmful_content')
          .slice(0, 18)
          .map(r => r.id),
        enabled: true,
        modelType: 'qwen',
        createdAt: new Date().toISOString(),
      },
      {
        id: 'model-gemma',
        name: 'Gemma 防护组合',
        description: '针对 Gemma 模型优化的安全规则组合',
        ruleIds: allRules
          .filter(r => r.severity === 'high' || r.detection_type === 'jailbreak')
          .slice(0, 12)
          .map(r => r.id),
        enabled: true,
        modelType: 'gemma',
        createdAt: new Date().toISOString(),
      },
    ];

    localStorage.setItem('rule_groups', JSON.stringify(modelGroups));
    setRuleGroups(modelGroups);
  };

  // 加载规则组合（从本地存储）
  const loadRuleGroups = useCallback(() => {
    try {
      const saved = localStorage.getItem('rule_groups');
      if (saved) {
        setRuleGroups(JSON.parse(saved));
      }
    } catch (error) {
      console.error('加载规则组合失败:', error);
    }
  }, []);

  useEffect(() => {
    loadRules();
    loadRuleGroups();
  }, [loadRules, loadRuleGroups]);

  // ==================== 表格列定义 ====================
  const columns = [
    {
      title: '规则ID',
      dataIndex: 'id',
      key: 'id',
      width: 150,
      render: (id: string, record: Rule) => (
        <Space>
          <Text code copyable={{ text: id }}>
            {id.length > 15 ? `${id.slice(0, 12)}...` : id}
          </Text>
          {record.isSystemRule && (
            <Tag color="blue" style={{ fontSize: 10 }}>系统</Tag>
          )}
        </Space>
      ),
    },
    {
      title: '规则名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      render: (name: string, record: Rule) => (
        <Space direction="vertical" size={0}>
          <Text strong>{name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.description?.slice(0, 30)}
            {record.description?.length > 30 ? '...' : ''}
          </Text>
        </Space>
      ),
    },
    {
      title: '检测类型',
      dataIndex: 'detection_type',
      key: 'detection_type',
      width: 120,
      render: (type: string) => {
        const typeInfo = DETECTION_TYPES.find(t => t.value === type);
        return (
          <Tag color={typeInfo?.color || 'default'}>
            {typeInfo?.label || type}
          </Tag>
        );
      },
    },
    {
      title: '严重级别',
      dataIndex: 'severity',
      key: 'severity',
      width: 100,
      render: (severity: string) => {
        const level = SEVERITY_LEVELS.find(s => s.value === severity);
        return (
          <Badge
            color={level?.color}
            text={level?.label || severity}
          />
        );
      },
    },
    {
      title: '状态',
      key: 'status',
      width: 150,
      render: (_: any, record: Rule) => (
        <Space>
          <Switch
            checked={record.enabled}
            onChange={(checked) => handleToggleRule(record.id, checked)}
            checkedChildren="启用"
            unCheckedChildren="禁用"
            size="small"
          />
          {record.block ? (
            <Tag color="red">阻止</Tag>
          ) : (
            <Tag color="orange">警告</Tag>
          )}
        </Space>
      ),
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 80,
      sorter: (a: Rule, b: Rule) => a.priority - b.priority,
    },
    {
      title: '模式/关键词',
      key: 'patterns',
      width: 150,
      render: (_: any, record: Rule) => (
        <Space>
          <Tooltip title={`${record.patterns?.length || 0} 个正则模式`}>
            <Tag icon={<FileTextOutlined />}>
              {record.patterns?.length || 0}
            </Tag>
          </Tooltip>
          <Tooltip title={`${record.keywords?.length || 0} 个关键词`}>
            <Tag icon={<TagsOutlined />}>
              {record.keywords?.length || 0}
            </Tag>
          </Tooltip>
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 250,
      fixed: 'right' as const,
      render: (_: any, record: Rule) => (
        <Space>
          {record.isSystemRule && (
            <Tooltip title="基于模板创建">
              <Button
                type="text"
                icon={<AppstoreOutlined />}
                onClick={() => handleCreateFromTemplate(record)}
                style={{ color: '#722ed1' }}
              />
            </Tooltip>
          )}
          <Tooltip title="编辑">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
              disabled={record.isSystemRule}
            />
          </Tooltip>
          <Tooltip title="测试">
            <Button
              type="text"
              icon={<PlayCircleOutlined />}
              onClick={() => handleTest(record)}
            />
          </Tooltip>
          <Tooltip title="复制">
            <Button
              type="text"
              icon={<CopyOutlined />}
              onClick={() => handleCopy(record)}
            />
          </Tooltip>
          {!record.isSystemRule && (
            <Popconfirm
              title="确认删除"
              description="删除后无法恢复，是否继续？"
              onConfirm={() => handleDelete(record.id)}
              okText="删除"
              cancelText="取消"
              okButtonProps={{ danger: true }}
            >
              <Tooltip title="删除">
                <Button
                  type="text"
                  danger
                  icon={<DeleteOutlined />}
                />
              </Tooltip>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  // ==================== 事件处理 ====================
  // 切换规则状态
  const handleToggleRule = async (ruleId: string, enabled: boolean, showNotification = true) => {
    try {
      await apiService.updateRule(ruleId, { enabled });
      if (showNotification) {
        message.success(`已${enabled ? '启用' : '禁用'}规则`);
      }
      // 重新加载规则以更新UI
      await loadRules();
    } catch (error) {
      message.error('操作失败');
      throw error; // 重新抛出错误以便调用方处理
    }
  };

  // 应用配置（批量应用待处理的分类变更）
  const handleApplyConfig = async () => {
    const pendingKeys = Object.keys(pendingCategoryChanges);
    if (pendingKeys.length === 0) {
      message.info('没有待应用的配置变更');
      return;
    }

    try {
      const loadingMessage = message.loading('正在应用配置...', 0);
      let totalUpdated = 0;

      // 处理每个待应用的分类变更
      for (const categoryKey of pendingKeys) {
        const targetEnabled = pendingCategoryChanges[categoryKey];

        // 找到该分类下需要更新的规则
        const typeMapping: Record<string, string> = {
          'prompt_injection': 'prompt_injection',
          'jailbreak': 'jailbreak',
          'harmful_content': 'harmful_content',
          'sensitive_info': 'sensitive_info',
          'compliance': 'compliance_violation',
        };

        const detectionType = typeMapping[categoryKey] || categoryKey;
        const rulesToUpdate = rules.filter(
          (rule) => rule.detection_type === detectionType && rule.enabled !== targetEnabled
        );

        // 逐个更新规则
        for (const rule of rulesToUpdate) {
          await apiService.updateRule(rule.id, { enabled: targetEnabled });
          totalUpdated++;
        }
      }

      loadingMessage();
      message.success(`配置应用成功，共更新 ${totalUpdated} 条规则`);

      // 清空待应用的变更
      setPendingCategoryChanges({});

      // 重新加载规则
      await loadRules();
    } catch (error) {
      message.error('应用配置失败');
      console.error('应用配置错误:', error);
    }
  };

  // 导出配置
  const handleExportConfig = () => {
    // 构建配置数据
    const config = {
      version: '2.2.1',
      exportTime: new Date().toISOString(),
      modelPackage: selectedModel,
      categories: {
        prompt_injection: {
          name: '提示注入检测',
          enabled: stats.byType.prompt_injection > 0,
          rulesCount: stats.byType.prompt_injection,
        },
        jailbreak: {
          name: '越狱攻击检测',
          enabled: stats.byType.jailbreak > 0,
          rulesCount: stats.byType.jailbreak,
        },
        harmful_content: {
          name: '有害内容拦截',
          enabled: stats.byType.harmful_content > 0,
          rulesCount: stats.byType.harmful_content,
        },
        sensitive_info: {
          name: '敏感信息脱敏',
          enabled: stats.byType.sensitive_info > 0,
          rulesCount: stats.byType.sensitive_info,
        },
        compliance: {
          name: '内容合规检查',
          enabled: stats.byType.compliance > 0,
          rulesCount: stats.byType.compliance,
        },
      },
      rules: rules.map(rule => ({
        id: rule.id,
        name: rule.name,
        detection_type: rule.detection_type,
        enabled: rule.enabled,
        severity: rule.severity,
      })),
      summary: {
        total: stats.total,
        enabled: stats.enabled,
        systemRules: stats.systemRules,
        customRules: stats.customRules,
      },
    };

    // 转换为 JSON 并创建下载
    const dataStr = JSON.stringify(config, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `llm-protection-config-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    message.success('配置导出成功');
  };

  // 编辑规则
  const handleEdit = (rule: Rule) => {
    setEditingRule(rule);
    setIsCreating(false);
    form.setFieldsValue({
      ...rule,
      patterns: rule.patterns?.join('\n') || '',
      keywords: rule.keywords?.join('\n') || '',
      categories: rule.categories?.join(', ') || '',
    });
    setIsEditModalVisible(true);
  };

  // 创建新规则
  const handleCreate = () => {
    setEditingRule(null);
    setIsCreating(true);
    form.resetFields();
    form.setFieldsValue({
      detection_type: 'custom',
      severity: 'medium',
      enabled: true,
      block: true,
      priority: 100,
    });
    setIsEditModalVisible(true);
  };

  // 测试规则
  const handleTest = (rule: Rule) => {
    setEditingRule(rule);
    testForm.resetFields();
    setIsTestModalVisible(true);
  };

  // 复制规则
  const handleCopy = (rule: Rule) => {
    const newRule = {
      ...rule,
      id: `${rule.id}_copy_${Date.now()}`,
      name: `${rule.name} (复制)`,
      enabled: false,
    };
    setEditingRule(null);
    setIsCreating(true);
    form.setFieldsValue({
      ...newRule,
      patterns: rule.patterns?.join('\n') || '',
      keywords: rule.keywords?.join('\n') || '',
      categories: rule.categories?.join(', ') || '',
    });
    setIsEditModalVisible(true);
    message.info('已复制规则内容，请修改后保存');
  };

  // 删除规则
  const handleDelete = async (ruleId: string) => {
    try {
      await apiService.deleteRule(ruleId);
      message.success('规则已删除');
      loadRules();
    } catch (error) {
      message.error('删除失败');
    }
  };

  // 批量启用
  const handleBatchEnable = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择规则');
      return;
    }
    try {
      await apiService.batchToggleRules(selectedRowKeys as string[], true);
      message.success(`已启用 ${selectedRowKeys.length} 条规则`);
      setSelectedRowKeys([]);
      loadRules();
    } catch (error) {
      message.error('批量启用失败');
    }
  };

  // 批量禁用
  const handleBatchDisable = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择规则');
      return;
    }
    try {
      await apiService.batchToggleRules(selectedRowKeys as string[], false);
      message.success(`已禁用 ${selectedRowKeys.length} 条规则`);
      setSelectedRowKeys([]);
      loadRules();
    } catch (error) {
      message.error('批量禁用失败');
    }
  };

  // 批量删除
  const handleBatchDelete = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择规则');
      return;
    }
    Modal.confirm({
      title: '确认批量删除',
      content: `确定要删除选中的 ${selectedRowKeys.length} 条规则吗？此操作不可恢复。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await apiService.batchDeleteRules(selectedRowKeys as string[]);
          message.success(`已删除 ${selectedRowKeys.length} 条规则`);
          setSelectedRowKeys([]);
          loadRules();
        } catch (error) {
          message.error('批量删除失败');
        }
      },
    });
  };

  // 保存规则
  const handleSaveRule = async (values: any) => {
    try {
      const ruleData = {
        ...values,
        patterns: values.patterns?.split('\n').filter((p: string) => p.trim()) || [],
        keywords: values.keywords?.split('\n').filter((k: string) => k.trim()) || [],
        categories: values.categories?.split(',').map((c: string) => c.trim()).filter(Boolean) || [],
      };

      if (isCreating) {
        await apiService.createRule(ruleData);
        message.success('规则创建成功');
      } else if (editingRule) {
        await apiService.updateRule(editingRule.id, ruleData);
        message.success('规则更新成功');
      }

      setIsEditModalVisible(false);
      loadRules();
    } catch (error) {
      message.error(isCreating ? '创建失败' : '更新失败');
    }
  };

  // 测试正则表达式
  const handleRunTest = async (values: { testText: string }) => {
    if (!editingRule) return;

    const results = [];
    for (const pattern of editingRule.patterns || []) {
      try {
        const result = await apiService.validatePattern(pattern, values.testText);
        results.push({
          pattern,
          ...result,
        });
      } catch (error) {
        results.push({
          pattern,
          valid: false,
          error: '测试失败',
        });
      }
    }

    Modal.info({
      title: '测试结果',
      width: 600,
      content: (
        <List
          size="small"
          dataSource={results}
          renderItem={(item: any) => (
            <List.Item>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Text code style={{ fontSize: 11 }}>{item.pattern.slice(0, 50)}...</Text>
                {item.valid ? (
                  item.matches ? (
                    <Tag color="success" icon={<CheckCircleOutlined />}>匹配成功</Tag>
                  ) : (
                    <Tag color="default">未匹配</Tag>
                  )
                ) : (
                  <Tag color="error" icon={<CloseCircleOutlined />}>{item.error}</Tag>
                )}
              </Space>
            </List.Item>
          )}
        />
      ),
    });
  };

  // 保存规则组合
  const handleSaveGroup = (values: any) => {
    const newGroup: RuleGroup = {
      id: `group_${Date.now()}`,
      name: values.name,
      description: values.description,
      ruleIds: selectedRowKeys as string[],
      enabled: true,
      createdAt: new Date().toISOString(),
      modelType: values.modelType, // 关联模型类型
    };

    const updatedGroups = [...ruleGroups, newGroup];
    setRuleGroups(updatedGroups);
    localStorage.setItem('rule_groups', JSON.stringify(updatedGroups));

    message.success(`规则组合"${values.name}"已创建${values.modelType ? `，关联模型: ${getModelDisplayName(values.modelType)}` : ''}`);
    setIsGroupModalVisible(false);
    setSelectedRowKeys([]);
  };

  // 导出规则
  const handleExportRules = () => {
    const exportData = {
      version: '1.0',
      exportDate: new Date().toISOString(),
      rules: filteredRules,
      groups: ruleGroups,
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `llm-protection-rules-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    message.success(`已导出 ${filteredRules.length} 条规则和 ${ruleGroups.length} 个组合`);
  };

  // 导入规则
  const handleImportRules = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'application/json';
    input.onchange = async (e: Event) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;

      try {
        const text = await file.text();
        const data = JSON.parse(text);

        if (data.rules && Array.isArray(data.rules)) {
          // 合并导入的规则
          const currentRuleIds = new Set(rules.map(r => r.id));
          let importedCount = 0;

          for (const rule of data.rules) {
            if (!currentRuleIds.has(rule.id)) {
              rules.push(rule);
              importedCount++;
            }
          }

          setRules([...rules]);
          message.success(`成功导入 ${importedCount} 条新规则`);
          loadRules();
        } else {
          message.error('无效的规则文件格式');
        }
      } catch (error) {
        message.error('导入失败：文件解析错误');
        console.error(error);
      }
    };
    input.click();
  };

  // 从系统规则创建模板
  const handleCreateFromTemplate = (templateRule: Rule) => {
    const newRule = {
      ...templateRule,
      id: `custom-${Date.now()}`,
      name: `${templateRule.name} (自定义)`,
      isSystemRule: false,
      enabled: false,
    };

    setEditingRule(null);
    setIsCreating(true);
    form.setFieldsValue({
      ...newRule,
      patterns: templateRule.patterns?.join('\n') || '',
      keywords: templateRule.keywords?.join('\n') || '',
      categories: templateRule.categories?.join(', ') || '',
    });
    setIsEditModalVisible(true);
    message.info('已基于系统规则创建模板，请修改后保存');
  };

  // 过滤规则
  const filteredRules = rules.filter(rule => {
    if (searchText && !rule.name?.toLowerCase().includes(searchText.toLowerCase()) &&
        !rule.id?.toLowerCase().includes(searchText.toLowerCase())) {
      return false;
    }
    if (filterSeverity && rule.severity !== filterSeverity) {
      return false;
    }
    if (filterSource === 'system' && !rule.isSystemRule) {
      return false;
    }
    if (filterSource === 'custom' && rule.isSystemRule) {
      return false;
    }
    if (filterEnabled !== null && rule.enabled !== filterEnabled) {
      return false;
    }
    return true;
  });

  // ==================== 渲染 ====================
  return (
    <div style={{ padding: '24px' }}>
      <Tabs activeKey={activeTab} onChange={setActiveTab} type="card">
        <TabPane tab="📦 模型套餐配置" key="model-packages">
          <ModelPackagesView
            rules={rules}
            onApplyConfig={handleApplyConfig}
            onExportConfig={handleExportConfig}
            pendingCategoryChanges={pendingCategoryChanges}
            setPendingCategoryChanges={setPendingCategoryChanges}
          />
        </TabPane>

        <TabPane tab="📋 全部规则管理" key="rules">
          {/* 统计卡片 */}
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col span={4}>
              <Card>
                <Statistic
                  title="总规则数"
                  value={stats.total}
                  prefix={<SafetyOutlined />}
                />
              </Card>
            </Col>
            <Col span={4}>
              <Card>
                <Statistic
                  title="已启用"
                  value={stats.enabled}
                  valueStyle={{ color: '#52c41a' }}
                  suffix={`/ ${stats.total}`}
                />
              </Card>
            </Col>
            <Col span={4}>
              <Card>
                <Statistic
                  title="系统规则"
                  value={stats.systemRules || 0}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Card>
            </Col>
            <Col span={4}>
              <Card>
                <Statistic
                  title="自定义规则"
                  value={stats.customRules || 0}
                  valueStyle={{ color: '#722ed1' }}
                />
              </Card>
            </Col>
            <Col span={4}>
              <Card>
                <Statistic
                  title="严重级别"
                  value={stats.bySeverity.critical || 0}
                  valueStyle={{ color: '#ff4d4f' }}
                  suffix="严重"
                />
              </Card>
            </Col>
            <Col span={4}>
              <Card>
                <Statistic
                  title="高危规则"
                  value={stats.bySeverity.high || 0}
                  valueStyle={{ color: '#ff7a45' }}
                  suffix="高危"
                />
              </Card>
            </Col>
          </Row>

          {/* 操作栏 */}
          <Card style={{ marginBottom: 24 }}>
            <Space wrap>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleCreate}
              >
                新建规则
              </Button>
              <Button
                icon={<CheckSquareOutlined />}
                onClick={handleBatchEnable}
                disabled={selectedRowKeys.length === 0}
              >
                批量启用
              </Button>
              <Button
                icon={<CloseCircleOutlined />}
                onClick={handleBatchDisable}
                disabled={selectedRowKeys.length === 0}
              >
                批量禁用
              </Button>
              <Button
                danger
                icon={<DeleteOutlined />}
                onClick={handleBatchDelete}
                disabled={selectedRowKeys.length === 0}
              >
                批量删除
              </Button>
              <Button
                icon={<FilterOutlined />}
                onClick={() => setIsGroupModalVisible(true)}
                disabled={selectedRowKeys.length === 0}
              >
                保存为组合
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={loadRules}
                loading={loading}
              >
                刷新
              </Button>
              <Divider type="vertical" />
              <Button
                icon={<ExportOutlined />}
                onClick={handleExportRules}
              >
                导出规则
              </Button>
              <Button
                icon={<ImportOutlined />}
                onClick={handleImportRules}
              >
                导入规则
              </Button>
              <Divider type="vertical" />
              <Input
                placeholder="搜索规则名称/ID"
                prefix={<SearchOutlined />}
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                style={{ width: 200 }}
                allowClear
              />
              <Select
                placeholder="检测类型"
                value={filterType}
                onChange={setFilterType}
                style={{ width: 150 }}
                allowClear
              >
                {DETECTION_TYPES.map(t => (
                  <Option key={t.value} value={t.value}>{t.label}</Option>
                ))}
              </Select>
              <Select
                placeholder="严重级别"
                value={filterSeverity}
                onChange={setFilterSeverity}
                style={{ width: 120 }}
                allowClear
              >
                {SEVERITY_LEVELS.map(s => (
                  <Option key={s.value} value={s.value}>{s.label}</Option>
                ))}
              </Select>
              <Select
                placeholder="规则来源"
                value={filterSource}
                onChange={setFilterSource}
                style={{ width: 120 }}
                allowClear
              >
                <Option value="system">系统规则</Option>
                <Option value="custom">自定义规则</Option>
              </Select>
              <Select
                placeholder="状态"
                value={filterEnabled}
                onChange={setFilterEnabled}
                style={{ width: 120 }}
                allowClear
              >
                <Option value={true}>已启用</Option>
                <Option value={false}>已禁用</Option>
              </Select>
            </Space>
          </Card>

          {/* 规则表格 */}
          <Card>
            <Table
              rowKey="id"
              columns={columns}
              dataSource={filteredRules}
              loading={loading}
              rowSelection={{
                selectedRowKeys,
                onChange: setSelectedRowKeys,
              }}
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 条规则`,
              }}
              scroll={{ x: 1200 }}
            />
          </Card>
        </TabPane>
      </Tabs>

      {/* 编辑/创建规则模态框 */}
      <Modal
        title={isCreating ? '创建新规则' : '编辑规则'}
        open={isEditModalVisible}
        onOk={form.submit}
        onCancel={() => setIsEditModalVisible(false)}
        width={800}
        okText="保存"
        cancelText="取消"
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSaveRule}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="id"
                label="规则ID"
                rules={[{ required: true, message: '请输入规则ID' }]}
              >
                <Input disabled={!isCreating} placeholder="如: custom-001" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="name"
                label="规则名称"
                rules={[{ required: true, message: '请输入规则名称' }]}
              >
                <Input placeholder="规则名称" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="description"
            label="规则描述"
          >
            <TextArea rows={2} placeholder="描述规则的作用..." />
          </Form.Item>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="detection_type"
                label="检测类型"
                rules={[{ required: true }]}
              >
                <Select>
                  {DETECTION_TYPES.map(t => (
                    <Option key={t.value} value={t.value}>{t.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="severity"
                label="严重级别"
                rules={[{ required: true }]}
              >
                <Select>
                  {SEVERITY_LEVELS.map(s => (
                    <Option key={s.value} value={s.value}>{s.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="priority"
                label="优先级"
                rules={[{ required: true }]}
              >
                <Input type="number" min={1} max={1000} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="enabled"
                label="启用状态"
                valuePropName="checked"
              >
                <Switch checkedChildren="启用" unCheckedChildren="禁用" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="block"
                label="处理方式"
                valuePropName="checked"
              >
                <Switch checkedChildren="阻止" unCheckedChildren="警告" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="patterns"
            label="正则模式 (每行一个)"
          >
            <TextArea
              rows={4}
              placeholder="(?i)pattern1&#10;(?i)pattern2"
            />
          </Form.Item>

          <Form.Item
            name="keywords"
            label="关键词 (每行一个)"
          >
            <TextArea
              rows={3}
              placeholder="keyword1&#10;keyword2"
            />
          </Form.Item>

          <Form.Item
            name="categories"
            label="分类标签 (逗号分隔)"
          >
            <Input placeholder="如: violence, harmful_content" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 测试规则模态框 */}
      <Modal
        title="测试规则"
        open={isTestModalVisible}
        onCancel={() => setIsTestModalVisible(false)}
        footer={null}
        width={600}
      >
        {editingRule && (
          <>
            <Alert
              message={`测试规则: ${editingRule.name}`}
              description={`包含 ${editingRule.patterns?.length || 0} 个正则模式`}
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <Form
              form={testForm}
              onFinish={handleRunTest}
            >
              <Form.Item
                name="testText"
                label="测试文本"
                rules={[{ required: true, message: '请输入测试文本' }]}
              >
                <TextArea
                  rows={4}
                  placeholder="输入要测试的文本..."
                />
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" block>
                  运行测试
                </Button>
              </Form.Item>
            </Form>
          </>
        )}
      </Modal>

      {/* 保存组合模态框 */}
      <Modal
        title="创建规则组合"
        open={isGroupModalVisible}
        onOk={groupForm.submit}
        onCancel={() => setIsGroupModalVisible(false)}
        width={600}
      >
        <Alert
          message={`已选择 ${selectedRowKeys.length} 条规则`}
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Form
          form={groupForm}
          layout="vertical"
          onFinish={handleSaveGroup}
        >
          <Form.Item
            name="name"
            label="组合名称"
            rules={[{ required: true, message: '请输入组合名称' }]}
          >
            <Input placeholder="如: 高危规则组合" />
          </Form.Item>
          <Form.Item
            name="description"
            label="组合描述"
            rules={[{ required: true, message: '请输入组合描述' }]}
          >
            <TextArea rows={2} placeholder="描述这个组合的用途..." />
          </Form.Item>
          <Form.Item
            name="modelType"
            label="关联模型（可选）"
            tooltip="选择关联的模型类型，系统将自动应用该模型的优化配置"
          >
            <Select placeholder="选择模型类型" allowClear>
              {MODEL_TYPES.map(model => (
                <Option key={model.value} value={model.value}>
                  <Space>
                    <span>{model.icon}</span>
                    <span>{model.label}</span>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      - {model.description}
                    </Text>
                  </Space>
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

// ==================== 模型套餐视图组件 ====================
interface ModelPackagesViewProps {
  rules: Rule[];
  onApplyConfig: () => Promise<void>;
  onExportConfig: () => void;
  pendingCategoryChanges: Record<string, boolean>;
  setPendingCategoryChanges: React.Dispatch<React.SetStateAction<Record<string, boolean>>>;
}

const ModelPackagesView: React.FC<ModelPackagesViewProps> = ({
  rules,
  onApplyConfig,
  onExportConfig,
  pendingCategoryChanges,
  setPendingCategoryChanges,
}) => {
  const [selectedModel, setSelectedModel] = useState<string>('llama'); // 默认选择Llama

  // 计算每个分类的规则数量
  const getCategoryStats = () => {
    const stats: any = {
      prompt_injection: { total: 0, enabled: 0, rules: [] as Rule[] },
      jailbreak: { total: 0, enabled: 0, rules: [] as Rule[] },
      harmful_content: { total: 0, enabled: 0, rules: [] as Rule[] },
      sensitive_info: { total: 0, enabled: 0, rules: [] as Rule[] },
      compliance: { total: 0, enabled: 0, rules: [] as Rule[] },
    };

    rules.forEach((rule) => {
      let type = rule.detection_type;

      // 处理类型别名：compliance_violation -> compliance
      if (type === 'compliance_violation') {
        type = 'compliance';
      }

      // 确保类型匹配
      if (type && stats[type]) {
        stats[type].total++;
        if (rule.enabled) {
          stats[type].enabled++;
        }
        stats[type].rules.push(rule);
      }
    });

    return stats;
  };

  const categoryStats = getCategoryStats();

  // 规则分类配置
  const categoryConfigs = [
    {
      key: 'prompt_injection',
      name: '提示注入检测',
      icon: '🔍',
      description: '检测尝试绕过或修改原始指令的攻击',
      color: '#1890ff',
      stats: categoryStats.prompt_injection,
      recommended: true,
    },
    {
      key: 'jailbreak',
      name: '越狱攻击防护',
      icon: '🛡️',
      description: '识别DAN、角色扮演等越狱尝试',
      color: '#ff4d4f',
      stats: categoryStats.jailbreak,
      recommended: true,
    },
    {
      key: 'harmful_content',
      name: '有害内容过滤',
      icon: '⚠️',
      description: '拦截暴力、仇恨、非法内容',
      color: '#faad14',
      stats: categoryStats.harmful_content,
      recommended: true,
    },
    {
      key: 'sensitive_info',
      name: '敏感信息脱敏',
      icon: '🔒',
      description: '保护隐私数据和敏感信息',
      color: '#722ed1',
      stats: categoryStats.sensitive_info,
      recommended: false,
    },
    {
      key: 'compliance',
      name: '内容合规检查',
      icon: '📜',
      description: '确保内容符合GDPR、HIPAA等法规要求',
      color: '#52c41a',
      stats: categoryStats.compliance,
      recommended: false,
    },
  ];

  return (
    <div>
      <Alert
        message="模型配置套餐"
        description="为不同的大语言模型配置专门的安全防护套餐。每个套餐包含不同类别的规则组合，可根据需要调整各分类的规则强度。"
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      {/* 模型选择和套餐管理 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card title="选择模型" extra={<Tag color="blue">当前配置</Tag>}>
            <Select
              placeholder="选择要配置的模型"
              value={selectedModel}
              onChange={setSelectedModel}
              style={{ width: '100%' }}
              size="large"
            >
              {MODEL_TYPES.map(model => (
                <Option key={model.value} value={model.value}>
                  <Space>
                    <span style={{ fontSize: 18 }}>{model.icon}</span>
                    <span>{model.label}</span>
                  </Space>
                </Option>
              ))}
            </Select>
          </Card>
        </Col>

        <Col span={16}>
          <Card
            title="当前套餐配置"
            extra={
              <Space>
                <Button
                  type="primary"
                  icon={<CheckSquareOutlined />}
                  onClick={onApplyConfig}
                  disabled={Object.keys(pendingCategoryChanges).length === 0}
                >
                  应用配置
                  {Object.keys(pendingCategoryChanges).length > 0 && (
                    <Badge
                      count={Object.keys(pendingCategoryChanges).length}
                      style={{ marginLeft: 4 }}
                    />
                  )}
                </Button>
                <Button icon={<ExportOutlined />} onClick={onExportConfig}>
                  导出配置
                </Button>
              </Space>
            }
          >
            <Row gutter={16}>
              {categoryConfigs.map(cat => (
                <Col span={12} key={cat.key} style={{ marginBottom: 16 }}>
                  <Card
                    size="small"
                    style={{ borderColor: cat.color }}
                    title={
                      <Space>
                        <span style={{ fontSize: 16 }}>{cat.icon}</span>
                        <span>{cat.name}</span>
                        {cat.recommended && <Tag color="red">推荐</Tag>}
                      </Space>
                    }
                    extra={
                      <Switch
                        checked={
                          pendingCategoryChanges[cat.key] !== undefined
                            ? pendingCategoryChanges[cat.key]
                            : cat.stats.enabled > 0
                        }
                        onChange={(checked) => {
                          // 只更新pending状态，不立即应用
                          setPendingCategoryChanges((prev) => ({
                            ...prev,
                            [cat.key]: checked,
                          }));
                          message.info(
                            `${cat.name}已${checked ? '启用' : '禁用'}（待应用），请点击"应用配置"按钮保存`
                          );
                        }}
                      />
                    }
                  >
                    <div style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>
                      {cat.description}
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Text>总计: {cat.stats.total} 条</Text>
                      <Text
                        type={
                          pendingCategoryChanges[cat.key] !== undefined
                            ? pendingCategoryChanges[cat.key]
                              ? "success"
                              : "secondary"
                            : cat.stats.enabled > 0
                              ? "success"
                              : "secondary"
                        }
                      >
                        {pendingCategoryChanges[cat.key] !== undefined
                          ? `待应用: ${pendingCategoryChanges[cat.key] ? cat.stats.total : 0} 条`
                          : `已启用: ${cat.stats.enabled} 条`}
                      </Text>
                    </div>
                    <Progress
                      percent={
                        pendingCategoryChanges[cat.key] !== undefined
                          ? pendingCategoryChanges[cat.key]
                            ? 100
                            : 0
                          : cat.stats.total > 0
                            ? Math.round((cat.stats.enabled / cat.stats.total) * 100)
                            : 0
                      }
                      strokeColor={
                        pendingCategoryChanges[cat.key] !== undefined
                          ? pendingCategoryChanges[cat.key]
                            ? cat.color
                            : '#d9d9d9'
                          : cat.color
                      }
                      showInfo={false}
                      style={{ marginTop: 8 }}
                    />
                    {pendingCategoryChanges[cat.key] !== undefined && (
                      <div style={{ marginTop: 4, fontSize: 11, color: '#faad14' }}>
                        ⚠️ 配置变更待应用
                      </div>
                    )}
                  </Card>
                </Col>
              ))}
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  );
};


export default RulesManage;
