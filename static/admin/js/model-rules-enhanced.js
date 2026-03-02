// 规则配置页面增强脚本 - 版本 1.0.1

class ModelRulesManager {
    constructor() {
        this.currentFilter = 'all';
        this.viewMode = 'grid'; // grid 或 table
        this.batchMode = false;
        this.selectedModels = new Set();
        this.modelsData = [];
        this.templatesData = [];
        this.isLoading = false;

        this.init();
    }

    init() {
        this.bindEvents();
        this.loadInitialData();
        this.updateCurrentTime();
        setInterval(() => this.updateCurrentTime(), 60000);
    }

    bindEvents() {
        // 页面操作按钮
        document.getElementById('refresh-btn')?.addEventListener('click', () => this.refreshData());
        document.getElementById('create-template-btn')?.addEventListener('click', () => this.openCreateTemplateModal());
        document.getElementById('batch-apply-template-btn')?.addEventListener('click', () => this.openBatchApplyModal());
        document.getElementById('auto-recommend-btn')?.addEventListener('click', () => this.autoRecommendConfig());
        document.getElementById('batch-config-btn')?.addEventListener('click', () => this.enableBatchMode());
        document.getElementById('check-all-btn')?.addEventListener('click', () => this.checkAllConfigurations());

        // 工具栏事件
        document.querySelectorAll('.filter-tab').forEach(tab => {
            tab.addEventListener('click', (e) => this.switchFilter(e.target.dataset.filter));
        });

        document.getElementById('model-search')?.addEventListener('input', (e) => this.handleSearch(e.target.value));
        document.getElementById('view-toggle')?.addEventListener('click', () => this.toggleView());

        // 批量操作事件
        document.getElementById('clear-selection')?.addEventListener('click', () => this.clearSelection());
        document.getElementById('batch-apply-template')?.addEventListener('click', () => this.openBatchApplyModal());

        // 全选复选框
        document.getElementById('select-all-models')?.addEventListener('change', (e) => this.toggleSelectAll(e.target.checked));
    }

    async loadInitialData() {
        this.showLoading(true);
        try {
            await Promise.all([
                this.loadModelsData(),
                this.loadTemplatesData()
            ]);
            this.updateStatistics();
            this.renderModels();
            this.renderTemplates();
        } catch (error) {
            console.error('加载数据失败:', error);
            this.showError('加载数据失败: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }

    async loadModelsData() {
        try {
            // NOTE: 使用 /api/v1/model-rules 聚合摘要接口，一次获取所有模型规则配置摘要
            // 避免使用 /api/v1/ollama/models + 逐模型配置查询（会触发大量请求和速率限制）
            const summariesResponse = await authManager.authenticatedFetch('/api/v1/model-rules', {
                headers: { 'Authorization': 'Bearer cherry-studio-key' }
            });

            if (!summariesResponse.ok) {
                const errText = await summariesResponse.text().catch(() => '');
                throw new Error(`获取模型摘要列表失败 (${summariesResponse.status}): ${errText.slice(0, 100)}`);
            }

            const summaries = await summariesResponse.json();
            console.log('获取到模型摘要数据:', summaries);

            // 将 ModelRuleSummary 格式转换为前端展示格式
            this.modelsData = (summaries || []).map(summary => {
                const securityScore = summary.security_score || this.calculateSecurityScore(summary.enabled_rules_count || 0);
                return {
                    id: summary.model_id,
                    name: summary.model_name || summary.model_id,
                    size: 0,
                    modified_at: summary.last_updated,
                    template: summary.template_id || null,
                    rulesCount: summary.rules_count || 0,
                    enabledRulesCount: summary.enabled_rules_count || 0,
                    securityScore: securityScore,
                    lastUpdated: summary.last_updated || new Date().toISOString(),
                    isConfigured: (summary.rules_count || 0) > 0,
                    riskLevel: this.calculateRiskLevel(securityScore)
                };
            });
            console.log('处理后的模型数据:', this.modelsData);
        } catch (error) {
            console.error('加载模型数据失败:', error);
            this.showError('加载模型数据失败: ' + error.message);
            this.modelsData = [];
        }
    }

    async loadTemplatesData() {
        try {
            const response = await authManager.authenticatedFetch('/api/v1/rule-templates');
            if (!response.ok) throw new Error('获取模板列表失败');

            const data = await response.json();
            console.log('获取到模板数据:', data);

            // 直接使用返回的数组数据
            this.templatesData = data.map(template => ({
                id: template.id,
                name: template.name,
                description: template.description,
                category: template.category || 'custom',
                rulesCount: template.rules ? template.rules.length : 0,
                createdAt: template.created_at || new Date().toISOString(),
                isDefault: template.is_default || false,
                usageCount: template.usage_count || 0
            }));
            console.log('处理后的模板数据:', this.templatesData);
        } catch (error) {
            console.error('加载模板数据失败:', error);
            // 使用默认模板数据
            this.templatesData = [
                {
                    id: 'security-strict',
                    name: '严格安全模板',
                    description: '适用于高安全要求环境，包含全面的安全检测规则',
                    category: 'security',
                    rulesCount: 15,
                    createdAt: new Date().toISOString(),
                    isDefault: true,
                    usageCount: 5
                },
                {
                    id: 'balanced-template',
                    name: '平衡模式模板',
                    description: '在安全性和可用性之间取得平衡的规则配置',
                    category: 'security',
                    rulesCount: 9,
                    createdAt: new Date().toISOString(),
                    isDefault: true,
                    usageCount: 8
                },
                {
                    id: 'research-template',
                    name: '研究用途模板',
                    description: '适用于学术研究环境，规则相对宽松',
                    category: 'research',
                    rulesCount: 6,
                    createdAt: new Date().toISOString(),
                    isDefault: true,
                    usageCount: 3
                }
            ];
        }
    }

    updateStatistics() {
        const configuredCount = this.modelsData.filter(m => m.isConfigured).length;
        const avgSecurityScore = this.modelsData.length > 0
            ? Math.round(this.modelsData.reduce((sum, m) => sum + m.securityScore, 0) / this.modelsData.length)
            : 0;

        document.getElementById('configured-models-count').textContent = configuredCount;
        document.getElementById('unconfigured-models-count').textContent = this.modelsData.length - configuredCount;
        document.getElementById('templates-count').textContent = this.templatesData.length;
        document.getElementById('avg-security-score').textContent = avgSecurityScore;
    }

    renderModels() {
        const container = document.getElementById('models-grid');
        const emptyState = document.getElementById('empty-state');

        if (!container) return;

        const filteredModels = this.filterModels();

        if (filteredModels.length === 0) {
            container.style.display = 'none';
            emptyState.style.display = 'block';
            return;
        }

        container.style.display = 'grid';
        emptyState.style.display = 'none';

        container.innerHTML = filteredModels.map(model => this.createModelCard(model)).join('');

        // 绑定事件
        this.bindModelCardEvents();
    }

    createModelCard(model) {
        const securityScoreClass = this.getSecurityScoreClass(model.securityScore);
        const statusBadgeClass = model.isConfigured ? 'configured' : 'unconfigured';
        const lastUpdated = new Date(model.lastUpdated).toLocaleDateString();
        const isSelected = this.selectedModels.has(model.id);

        return `
            <div class="model-config-card ${this.batchMode ? 'batch-mode' : ''} ${isSelected ? 'selected' : ''}" 
                 data-model-id="${model.id}" data-configured="${model.isConfigured}" data-risk="${model.riskLevel}">
                <div class="model-config-header">
                    <div class="model-config-title">
                        <h3 class="model-config-name">${model.name}</h3>
                        <span class="model-status-badge ${statusBadgeClass}">
                            ${model.isConfigured ? '已配置' : '未配置'}
                        </span>
                    </div>
                    <div class="model-config-meta">
                        <span><i class="fas fa-calendar"></i> ${lastUpdated}</span>
                        <span><i class="fas fa-layer-group"></i> ${model.template || '无模板'}</span>
                    </div>
                </div>
                <div class="model-config-body">
                    <div class="model-config-stats">
                        <div class="config-stat">
                            <div class="config-stat-label">规则数量</div>
                            <div class="config-stat-value">${model.rulesCount}</div>
                        </div>
                        <div class="config-stat">
                            <div class="config-stat-label">已启用</div>
                            <div class="config-stat-value">${model.enabledRulesCount}</div>
                        </div>
                    </div>
                    <div class="security-score-indicator">
                        <div class="security-score-circle ${securityScoreClass}">
                            ${model.securityScore}
                        </div>
                    </div>
                    <div class="model-config-actions">
                        ${this.batchMode ?
                `<button class="btn btn-secondary btn-sm" onclick="modelRulesManager.toggleModelSelection('${model.id}')">
                                <i class="fas fa-${isSelected ? 'check-square' : 'square'}"></i> ${isSelected ? '已选择' : '选择'}
                            </button>` : ''
            }
                        <button class="btn btn-primary btn-sm" onclick="modelRulesManager.configureModel('${model.id}')">
                            <i class="fas fa-cog"></i> 配置
                        </button>
                        <button class="btn btn-secondary btn-sm" onclick="modelRulesManager.viewModelDetails('${model.id}')">
                            <i class="fas fa-info-circle"></i> 详情
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    renderTemplates() {
        const container = document.getElementById('templates-grid');
        if (!container) return;

        container.innerHTML = this.templatesData.map(template => this.createTemplateCard(template)).join('');

        // 绑定模板卡片事件
        this.bindTemplateCardEvents();
    }

    createTemplateCard(template) {
        const createdDate = new Date(template.createdAt).toLocaleDateString();
        const categoryText = this.getCategoryText(template.category);

        return `
            <div class="template-card ${template.isDefault ? 'featured' : ''}" data-template-id="${template.id}">
                <div class="template-header">
                    <h3 class="template-title">${template.name}</h3>
                    <span class="template-category">${categoryText}</span>
                </div>
                <div class="template-body">
                    <p class="template-description">${template.description}</p>
                    <div class="template-stats">
                        <span class="template-stat">
                            <i class="fas fa-shield-alt"></i> ${template.rulesCount} 规则
                        </span>
                        <span class="template-stat">
                            <i class="fas fa-users"></i> ${template.usageCount} 使用
                        </span>
                        <span class="template-stat">
                            <i class="fas fa-clock"></i> ${createdDate}
                        </span>
                    </div>
                    <div class="template-actions">
                        <button class="btn btn-primary btn-sm" onclick="modelRulesManager.applyTemplate('${template.id}')">
                            <i class="fas fa-check"></i> 应用
                        </button>
                        <button class="btn btn-secondary btn-sm" onclick="modelRulesManager.editTemplate('${template.id}')">
                            <i class="fas fa-edit"></i> 编辑
                        </button>
                        <button class="btn btn-secondary btn-sm" onclick="modelRulesManager.duplicateTemplate('${template.id}')">
                            <i class="fas fa-copy"></i> 复制
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    bindModelCardEvents() {
        if (!this.batchMode) return;

        document.querySelectorAll('.model-config-card.batch-mode').forEach(card => {
            card.addEventListener('click', (event) => {
                if (event.target.closest('button')) return;

                const modelId = card.dataset.modelId;
                this.toggleModelSelection(modelId);
            });
        });
    }

    bindTemplateCardEvents() {
        // 模板卡片的事件绑定在创建时已通过onclick处理
    }

    filterModels() {
        let filtered = [...this.modelsData];

        // 按状态过滤
        switch (this.currentFilter) {
            case 'configured':
                filtered = filtered.filter(m => m.isConfigured);
                break;
            case 'unconfigured':
                filtered = filtered.filter(m => !m.isConfigured);
                break;
            case 'high-risk':
                filtered = filtered.filter(m => m.riskLevel === 'high');
                break;
        }

        // 搜索过滤
        const searchTerm = document.getElementById('model-search')?.value.toLowerCase() || '';
        if (searchTerm) {
            filtered = filtered.filter(m =>
                m.name.toLowerCase().includes(searchTerm) ||
                (m.template && m.template.toLowerCase().includes(searchTerm))
            );
        }

        return filtered;
    }

    switchFilter(filter) {
        this.currentFilter = filter;

        // 更新UI状态
        document.querySelectorAll('.filter-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.filter === filter);
        });

        this.renderModels();
    }

    handleSearch(searchTerm) {
        this.renderModels();
    }

    toggleView() {
        this.viewMode = this.viewMode === 'grid' ? 'table' : 'grid';

        const gridView = document.getElementById('models-grid');
        const tableView = document.getElementById('models-table');
        const toggleBtn = document.getElementById('view-toggle');

        if (this.viewMode === 'grid') {
            gridView.style.display = 'grid';
            tableView.style.display = 'none';
            toggleBtn.innerHTML = '<i class="fas fa-th-large"></i>';
        } else {
            gridView.style.display = 'none';
            tableView.style.display = 'block';
            toggleBtn.innerHTML = '<i class="fas fa-list"></i>';
            this.renderModelsTable();
        }
    }

    enableBatchMode() {
        this.batchMode = !this.batchMode;
        this.selectedModels.clear();

        const batchToolbar = document.getElementById('batch-toolbar');
        if (this.batchMode) {
            batchToolbar.style.display = 'flex';
        } else {
            batchToolbar.style.display = 'none';
        }

        this.renderModels();
        this.updateBatchCount();
    }

    toggleModelSelection(modelId) {
        if (this.selectedModels.has(modelId)) {
            this.selectedModels.delete(modelId);
        } else {
            this.selectedModels.add(modelId);
        }

        // 更新UI
        const card = document.querySelector(`[data-model-id="${modelId}"]`);
        if (card) {
            card.classList.toggle('selected', this.selectedModels.has(modelId));

            const button = card.querySelector('.btn-secondary');
            if (button) {
                const isSelected = this.selectedModels.has(modelId);
                button.innerHTML = `<i class="fas fa-${isSelected ? 'check-square' : 'square'}"></i> ${isSelected ? '已选择' : '选择'}`;
            }
        }

        this.updateBatchCount();
    }

    toggleSelectAll(checked) {
        if (checked) {
            this.filterModels().forEach(model => this.selectedModels.add(model.id));
        } else {
            this.selectedModels.clear();
        }

        this.renderModels();
        this.updateBatchCount();
    }

    clearSelection() {
        this.selectedModels.clear();
        this.renderModels();
        this.updateBatchCount();
    }

    updateBatchCount() {
        const countElement = document.getElementById('selected-models-count');
        if (countElement) {
            countElement.textContent = this.selectedModels.size;
        }
    }

    // 工具方法
    calculateSecurityScore(enabledRulesCount) {
        // 根据启用规则数量计算安全评分
        return Math.min(100, Math.max(0, enabledRulesCount * 7));
    }

    calculateRiskLevel(securityScore) {
        if (securityScore >= 80) return 'low';
        if (securityScore >= 60) return 'medium';
        return 'high';
    }

    getSecurityScoreClass(score) {
        if (score >= 80) return 'high-score';
        if (score >= 60) return 'medium-score';
        return 'low-score';
    }

    getCategoryText(category) {
        const categoryMap = {
            security: '安全',
            compliance: '合规',
            research: '研究',
            custom: '自定义'
        };
        return categoryMap[category] || '未知';
    }

    showLoading(show) {
        this.isLoading = show;
        let overlay = document.getElementById('loading-overlay');

        if (show) {
            if (!overlay) {
                overlay = document.createElement('div');
                overlay.id = 'loading-overlay';
                overlay.className = 'loading-overlay';
                overlay.innerHTML = '<div class="loading-spinner"></div>';
                document.body.appendChild(overlay);
            }
            overlay.style.display = 'flex';
        } else if (overlay) {
            overlay.style.display = 'none';
        }
    }

    showError(message) {
        console.error(message);

        // 创建错误提示
        const alert = document.createElement('div');
        alert.className = 'alert alert-error';
        alert.innerHTML = `
            <i class="fas fa-exclamation-circle"></i>
            <span>${message}</span>
            <button class="alert-close" onclick="this.parentElement.remove()">&times;</button>
        `;
        alert.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--danger-color);
            color: white;
            padding: 12px 16px;
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            z-index: 10000;
            display: flex;
            align-items: center;
            gap: 8px;
            max-width: 400px;
        `;

        const closeBtn = alert.querySelector('.alert-close');
        closeBtn.style.cssText = `
            background: none;
            border: none;
            color: white;
            font-size: 18px;
            cursor: pointer;
            margin-left: auto;
        `;

        document.body.appendChild(alert);

        // 自动隐藏
        setTimeout(() => {
            if (alert.parentElement) {
                alert.remove();
            }
        }, 5000);
    }

    updateCurrentTime() {
        const timeElement = document.getElementById('current-time');
        if (timeElement) {
            const now = new Date();
            const options = {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            };
            timeElement.textContent = now.toLocaleDateString('zh-CN', options);
        }
    }

    // 公共方法供外部调用
    async refreshData() {
        await this.loadInitialData();
    }

    async configureModel(modelId) {
        console.log('🔧 配置模型被调用:', modelId);
        console.log('🔧 当前modelRulesManager实例:', this);

        try {
            // 获取模型详细信息
            const model = this.modelsData.find(m => m.id === modelId);
            if (!model) {
                this.showError('未找到指定模型');
                return;
            }

            // 获取模型当前配置
            let currentConfig = null;
            try {
                const configResponse = await authManager.authenticatedFetch(`/api/v1/model-rules/${modelId}`, {
                    headers: {
                        'Authorization': 'Bearer cherry-studio-key'
                    }
                });
                if (configResponse.ok) {
                    currentConfig = await configResponse.json();
                }
            } catch (error) {
                console.warn('获取模型配置失败，将使用默认配置:', error);
            }

            // 获取可用规则列表
            let availableRules = [];
            try {
                const rulesResponse = await authManager.authenticatedFetch('/api/v1/rules', {
                    headers: {
                        'Authorization': 'Bearer cherry-studio-key'
                    }
                });
                if (rulesResponse.ok) {
                    availableRules = await rulesResponse.json();
                }
            } catch (error) {
                console.warn('获取可用规则失败:', error);
            }

            // 打开配置模态框
            this.openModelConfigModal(model, currentConfig, availableRules);

        } catch (error) {
            console.error('打开模型配置失败:', error);
            this.showError('打开模型配置失败: ' + error.message);
        }
    }

    openModelConfigModal(model, currentConfig, availableRules) {
        const modal = document.getElementById('model-rules-config-modal');
        if (!modal) {
            console.error('未找到模型配置模态框');
            return;
        }

        // 更新模态框标题和基本信息
        document.getElementById('model-rules-config-title').textContent = `配置模型: ${model.name}`;
        document.getElementById('config-model-name').textContent = model.name;
        document.getElementById('config-template-name').textContent = model.template || '无模板';
        document.getElementById('config-rules-count').textContent = currentConfig?.rules?.length || 0;
        document.getElementById('config-security-score').textContent = model.securityScore || 0;

        // 渲染规则配置表格
        this.renderModelConfigRulesTable(currentConfig, availableRules);

        // 绑定模态框内的事件
        this.bindModelConfigEvents(model.id, currentConfig, availableRules);

        // 显示模态框
        this.showModal('model-rules-config-modal');
    }

    renderModelConfigRulesTable(currentConfig, availableRules) {
        const tableBody = document.getElementById('model-config-rules-body');
        if (!tableBody) return;

        // 合并当前配置的规则和可用规则
        const configuredRules = currentConfig?.rules || [];
        const allRuleIds = new Set([
            ...configuredRules.map(r => r.id),
            ...availableRules.map(r => r.id)
        ]);

        const rulesData = Array.from(allRuleIds).map(ruleId => {
            const configuredRule = configuredRules.find(r => r.id === ruleId);
            const availableRule = availableRules.find(r => r.id === ruleId);

            return {
                id: ruleId,
                name: configuredRule?.name || availableRule?.name || ruleId,
                type: configuredRule?.type || availableRule?.type || 'unknown',
                severity: configuredRule?.severity || availableRule?.severity || 'medium',
                priority: configuredRule?.priority || availableRule?.priority || 50,
                enabled: configuredRule ? configuredRule.enabled : false,
                description: configuredRule?.description || availableRule?.description || '无描述'
            };
        });

        // 渲染表格行
        tableBody.innerHTML = rulesData.map(rule => {
            const severityClass = this.getSeverityClass(rule.severity);
            const statusClass = rule.enabled ? 'enabled' : 'disabled';

            return `
                <tr data-rule-id="${rule.id}" class="rule-row">
                    <td>
                        <input type="checkbox" class="rule-checkbox" ${rule.enabled ? 'checked' : ''}>
                    </td>
                    <td class="rule-id">${rule.id}</td>
                    <td class="rule-name">${rule.name}</td>
                    <td class="rule-type">
                        <span class="type-badge ${rule.type}">${this.getTypeDisplayName(rule.type)}</span>
                    </td>
                    <td class="rule-severity">
                        <span class="severity-badge ${severityClass}">${this.getSeverityDisplayName(rule.severity)}</span>
                    </td>
                    <td class="rule-priority">${rule.priority}</td>
                    <td class="rule-status">
                        <span class="status-badge ${statusClass}">${rule.enabled ? '已启用' : '已禁用'}</span>
                    </td>
                    <td class="rule-actions">
                        <button class="btn btn-secondary btn-sm toggle-rule-btn" 
                                onclick="modelRulesManager.toggleRule('${rule.id}')"
                                title="${rule.enabled ? '禁用规则' : '启用规则'}">
                            <i class="fas fa-${rule.enabled ? 'toggle-off' : 'toggle-on'}"></i>
                        </button>
                        <button class="btn btn-secondary btn-sm edit-rule-btn" 
                                onclick="modelRulesManager.editRule('${rule.id}')"
                                title="编辑规则">
                            <i class="fas fa-edit"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

        // 绑定表格事件
        this.bindRulesTableEvents();
    }

    bindModelConfigEvents(modelId, currentConfig, availableRules) {
        // 应用模板按钮
        const applyTemplateBtn = document.getElementById('apply-template-btn');
        if (applyTemplateBtn) {
            applyTemplateBtn.onclick = () => this.showApplyTemplateModal(modelId);
        }

        // 添加规则按钮  
        const addRulesBtn = document.getElementById('add-rules-btn');
        if (addRulesBtn) {
            addRulesBtn.onclick = () => this.showAddRulesModal(modelId, availableRules);
        }

        // 批量操作按钮
        const batchToggleBtn = document.getElementById('batch-toggle-btn');
        if (batchToggleBtn) {
            batchToggleBtn.onclick = () => this.showBatchToggleDialog();
        }

        // 检查冲突按钮
        const checkConflictsBtn = document.getElementById('check-conflicts-btn');
        if (checkConflictsBtn) {
            checkConflictsBtn.onclick = () => this.checkRuleConflicts(modelId);
        }

        // 保存配置按钮
        const saveConfigBtn = document.getElementById('save-config-btn');
        if (saveConfigBtn) {
            saveConfigBtn.onclick = () => this.saveModelConfiguration(modelId);
        }

        // 过滤器事件
        this.bindConfigFilters();
    }

    bindRulesTableEvents() {
        // 全选复选框
        const selectAllRules = document.getElementById('select-all-rules');
        if (selectAllRules) {
            selectAllRules.onchange = (e) => {
                const checkboxes = document.querySelectorAll('.rule-checkbox');
                checkboxes.forEach(cb => {
                    cb.checked = e.target.checked;
                    const row = cb.closest('.rule-row');
                    row.classList.toggle('selected', cb.checked);
                });
            };
        }

        // 单个规则复选框
        document.querySelectorAll('.rule-checkbox').forEach(checkbox => {
            checkbox.onchange = (e) => {
                const row = e.target.closest('.rule-row');
                row.classList.toggle('selected', e.target.checked);
            };
        });
    }

    bindConfigFilters() {
        // 规则类型过滤器
        const typeFilter = document.getElementById('rules-type-filter');
        if (typeFilter) {
            typeFilter.onchange = () => this.applyRulesFilters();
        }

        // 规则状态过滤器
        const statusFilter = document.getElementById('rules-status-filter');
        if (statusFilter) {
            statusFilter.onchange = () => this.applyRulesFilters();
        }

        // 搜索框
        const searchInput = document.getElementById('rules-search');
        if (searchInput) {
            searchInput.oninput = () => this.applyRulesFilters();
        }
    }

    applyRulesFilters() {
        const typeFilter = document.getElementById('rules-type-filter').value;
        const statusFilter = document.getElementById('rules-status-filter').value;
        const searchTerm = document.getElementById('rules-search').value.toLowerCase();

        document.querySelectorAll('.rule-row').forEach(row => {
            const ruleType = row.querySelector('.rule-type .type-badge').textContent.toLowerCase();
            const ruleStatus = row.querySelector('.rule-status .status-badge').textContent.toLowerCase();
            const ruleName = row.querySelector('.rule-name').textContent.toLowerCase();
            const ruleId = row.querySelector('.rule-id').textContent.toLowerCase();

            let visible = true;

            // 类型过滤
            if (typeFilter && !ruleType.includes(typeFilter)) {
                visible = false;
            }

            // 状态过滤
            if (statusFilter) {
                if (statusFilter === 'enabled' && !ruleStatus.includes('已启用')) {
                    visible = false;
                }
                if (statusFilter === 'disabled' && !ruleStatus.includes('已禁用')) {
                    visible = false;
                }
            }

            // 搜索过滤
            if (searchTerm && !ruleName.includes(searchTerm) && !ruleId.includes(searchTerm)) {
                visible = false;
            }

            row.style.display = visible ? '' : 'none';
        });
    }

    toggleRule(ruleId) {
        const row = document.querySelector(`[data-rule-id="${ruleId}"]`);
        if (!row) return;

        const checkbox = row.querySelector('.rule-checkbox');
        const statusBadge = row.querySelector('.status-badge');
        const toggleBtn = row.querySelector('.toggle-rule-btn i');

        // 切换状态
        checkbox.checked = !checkbox.checked;

        if (checkbox.checked) {
            statusBadge.textContent = '已启用';
            statusBadge.className = 'status-badge enabled';
            toggleBtn.className = 'fas fa-toggle-off';
        } else {
            statusBadge.textContent = '已禁用';
            statusBadge.className = 'status-badge disabled';
            toggleBtn.className = 'fas fa-toggle-on';
        }
    }

    async saveModelConfiguration(modelId) {
        try {
            // 收集当前配置
            const rules = [];
            document.querySelectorAll('.rule-row').forEach(row => {
                const ruleId = row.dataset.ruleId;
                const enabled = row.querySelector('.rule-checkbox').checked;
                const name = row.querySelector('.rule-name').textContent;
                const type = row.querySelector('.rule-type .type-badge').className.split(' ')[1];
                const severity = row.querySelector('.rule-severity .severity-badge').className.split(' ')[1];
                const priority = parseInt(row.querySelector('.rule-priority').textContent);

                rules.push({
                    id: ruleId,
                    name: name,
                    type: type,
                    severity: severity,
                    priority: priority,
                    enabled: enabled
                });
            });

            const configData = {
                model_id: modelId,
                rules: rules,
                updated_at: new Date().toISOString()
            };

            // 保存配置
            const response = await authManager.authenticatedFetch(`/api/v1/model-rules/${modelId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer cherry-studio-key'
                },
                body: JSON.stringify(configData)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || '保存配置失败');
            }

            this.showSuccess('模型配置保存成功');

            // 关闭模态框并刷新数据
            this.hideModal('model-rules-config-modal');
            await this.refreshData();

        } catch (error) {
            console.error('保存模型配置失败:', error);
            this.showError('保存配置失败: ' + error.message);
        }
    }

    // 辅助方法
    getSeverityClass(severity) {
        const severityMap = {
            high: 'high-severity',
            medium: 'medium-severity',
            low: 'low-severity'
        };
        return severityMap[severity] || 'medium-severity';
    }

    getSeverityDisplayName(severity) {
        const severityMap = {
            high: '高',
            medium: '中',
            low: '低'
        };
        return severityMap[severity] || '中';
    }

    getTypeDisplayName(type) {
        const typeMap = {
            prompt_injection: '提示注入',
            jailbreak: '越狱检测',
            harmful_content: '有害内容',
            sensitive_info: '敏感信息',
            compliance_violation: '合规违规'
        };
        return typeMap[type] || type;
    }

    showModal(modalId) {
        console.log('🔍 尝试显示模态框:', modalId);
        const modal = document.getElementById(modalId);
        console.log('🔍 找到的模态框元素:', modal);
        if (modal) {
            // 使用CSS类控制显示，同时强制覆盖内联样式（包括 !important）
            modal.style.setProperty('display', 'flex', 'important');

            // 稍后添加show类以触发任何过渡动画
            setTimeout(() => {
                modal.classList.add('show');
            }, 10);

            document.body.classList.add('modal-open');
            console.log('✅ 模态框显示成功，已添加show类并设置display: flex !important');

            // 确保模态框在最顶层
            modal.style.zIndex = '9999';
        } else {
            console.error('❌ 未找到模态框元素:', modalId);
        }
    }

    hideModal(modalId) {
        console.log('🔍 尝试隐藏模态框:', modalId);
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('show');
            document.body.classList.remove('modal-open');

            // 等待动画结束后隐藏
            setTimeout(() => {
                modal.style.display = 'none';
            }, 300);
            console.log('✅ 模态框已隐藏，移除show类');
        }
    }

    showSuccess(message) {
        // 创建成功提示
        const alert = document.createElement('div');
        alert.className = 'alert alert-success';
        alert.innerHTML = `
            <i class="fas fa-check-circle"></i>
            <span>${message}</span>
        `;
        alert.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--success-color);
            color: white;
            padding: 12px 16px;
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            z-index: 10000;
            display: flex;
            align-items: center;
            gap: 8px;
        `;

        document.body.appendChild(alert);

        setTimeout(() => {
            alert.remove();
        }, 3000);
    }

    async editRule(ruleId) {
        try {
            console.log('开始编辑规则:', ruleId);
            this.showLoading(true);

            // 获取规则详情
            const response = await authManager.authenticatedFetch(`/api/v1/rules/${encodeURIComponent(ruleId)}`);
            if (!response.ok) {
                throw new Error('获取规则详情失败');
            }

            const ruleData = await response.json();
            console.log('获取到的规则数据:', ruleData);

            // 确保数据格式正确
            const rule = ruleData.data || ruleData; // 处理可能的包装格式
            console.log('处理后的规则数据:', rule);

            this._populateRuleEditForm(rule);
            console.log('准备显示模态框: rule-edit-modal');
            this.showModal('rule-edit-modal');
            console.log('模态框显示完成');

        } catch (e) {
            console.error('编辑规则失败:', e);
            this.showError(`编辑规则失败: ${e.message}`);
        } finally {
            this.showLoading(false);
        }
    }

    _populateRuleEditForm(rule) {
        console.log('开始填充规则编辑表单，规则数据:', rule);

        // 存储当前编辑的规则ID
        this.currentEditingRuleId = rule.id;
        console.log('设置当前编辑规则ID:', this.currentEditingRuleId);

        // 填充表单字段
        const nameField = document.getElementById('rule-name');
        const descField = document.getElementById('rule-description');
        const typeField = document.getElementById('rule-type');
        const severityField = document.getElementById('rule-severity');
        const priorityField = document.getElementById('rule-priority');
        const enabledField = document.getElementById('rule-enabled');
        const patternsField = document.getElementById('rule-patterns');
        const whitelistField = document.getElementById('rule-whitelist');

        console.log('表单字段元素:', {
            nameField, descField, typeField, severityField,
            priorityField, enabledField, patternsField, whitelistField
        });

        if (nameField) nameField.value = rule.name || '';
        if (descField) descField.value = rule.description || '';
        if (typeField) typeField.value = rule.detection_type || '';
        if (severityField) severityField.value = rule.severity || '';
        if (priorityField) priorityField.value = rule.priority || '';
        if (enabledField) enabledField.checked = rule.enabled || false;

        // 填充模式（patterns）
        const patterns = rule.patterns || [];
        if (patternsField) patternsField.value = patterns.join('\n');

        // 填充白名单（如果有的话）- 检查多个可能的字段名
        const whitelist = rule.whitelist || rule.keywords || [];
        if (whitelistField) whitelistField.value = whitelist.join('\n');

        console.log('表单填充完成');
    }

    async saveRule() {
        try {
            this.showLoading(true);

            if (!this.currentEditingRuleId) {
                throw new Error('没有正在编辑的规则');
            }

            // 收集表单数据
            const formData = {
                name: document.getElementById('rule-name').value.trim(),
                description: document.getElementById('rule-description').value.trim(),
                detection_type: document.getElementById('rule-type').value,
                severity: document.getElementById('rule-severity').value,
                priority: parseInt(document.getElementById('rule-priority').value) || 1,
                enabled: document.getElementById('rule-enabled').checked,
                patterns: document.getElementById('rule-patterns').value
                    .split('\n')
                    .map(p => p.trim())
                    .filter(p => p.length > 0),
                whitelist: document.getElementById('rule-whitelist').value
                    .split('\n')
                    .map(w => w.trim())
                    .filter(w => w.length > 0)
            };

            // 验证必填字段
            if (!formData.name) {
                throw new Error('规则名称不能为空');
            }

            // 发送更新请求
            const response = await authManager.authenticatedFetch(`/api/v1/rules/${encodeURIComponent(this.currentEditingRuleId)}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '保存规则失败');
            }

            this.showSuccess('规则保存成功');
            this.hideModal('rule-edit-modal');
            this.refreshData(); // 刷新页面数据

        } catch (e) {
            console.error('保存规则失败:', e);
            this.showError(`保存规则失败: ${e.message}`);
        } finally {
            this.showLoading(false);
        }
    }

    viewModelDetails(modelId) {
        console.log('查看模型详情:', modelId);
        // TODO: 打开模型详情modal
        alert(`模型详情功能开发中...\n\n模型ID: ${modelId}\n\n将显示模型的详细信息和配置历史。`);
    }

    applyTemplate(templateId) {
        console.log('应用模板:', templateId);
        // TODO: 打开应用模板modal
    }

    editTemplate(templateId) {
        console.log('编辑模板:', templateId);

        // 查找模板数据
        const template = this.templates.find(t => t.id === templateId);
        if (!template) {
            console.error('模板未找到:', templateId);
            return;
        }

        // 打开编辑模态框
        this.openEditTemplateModal(template);
    }

    openEditTemplateModal(template) {
        // 填充模态框表单
        document.getElementById('edit-template-id').value = template.id;
        document.getElementById('edit-template-name').value = template.name;
        document.getElementById('edit-template-description').value = template.description || '';
        document.getElementById('edit-template-rules').value = JSON.stringify(template.rules, null, 2);

        // 显示模态框
        $('#editTemplateModal').modal('show');
    }

    async saveTemplateEdit() {
        const templateId = document.getElementById('edit-template-id').value;
        const name = document.getElementById('edit-template-name').value;
        const description = document.getElementById('edit-template-description').value;
        const rulesJson = document.getElementById('edit-template-rules').value;

        try {
            // 验证JSON格式
            const rules = JSON.parse(rulesJson);

            // 更新模板
            const template = this.templates.find(t => t.id === templateId);
            if (template) {
                template.name = name;
                template.description = description;
                template.rules = rules;

                // 保存到服务器
                await this.saveTemplateToServer(template);

                // 刷新界面
                this.renderTemplates();

                // 关闭模态框
                $('#editTemplateModal').modal('hide');

                // 显示成功消息
                this.showToast('模板更新成功', 'success');
            }
        } catch (error) {
            console.error('保存模板失败:', error);
            this.showToast('保存失败: JSON格式错误', 'error');
        }
    }

    duplicateTemplate(templateId) {
        console.log('复制模板:', templateId);
        // TODO: 实现模板复制功能
    }

    openCreateTemplateModal() {
        console.log('打开创建模板modal');
        // TODO: 实现创建模板modal
    }

    openBatchApplyModal() {
        console.log('打开批量应用模板modal');
        // TODO: 实现批量应用modal
    }

    // ===== 智能推荐配置：弹窗交互 =====
    async autoRecommendConfig() {
        try {
            console.log('🚀 开始智能推荐配置...');
            this.showLoading(true);

            // 检查按钮点击是否被触发
            const button = document.getElementById('auto-recommend-btn');
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 推荐中...';
            }

            const recResp = await authManager.authenticatedFetch('/api/v1/model-rules-recommend', {
                headers: {
                    'Authorization': 'Bearer cherry-studio-key'
                }
            });
            console.log('📡 推荐API响应状态:', recResp.status);

            if (!recResp.ok) {
                const errorText = await recResp.text();
                console.error('❌ 推荐API响应错误:', errorText);
                throw new Error(`获取推荐配置失败 (${recResp.status}): ${errorText}`);
            }

            const recData = await recResp.json();
            console.log('✅ 推荐API响应数据:', recData);
            const recs = recData.recommendations || [];

            if (recs.length === 0) {
                // 显示推荐模态框，但显示空状态
                this._renderRecommendModal([]);
                this.showModal('recommend-modal');
                return;
            }

            this._renderRecommendModal(recs);
            this.showModal('recommend-modal');
        } catch (e) {
            console.error('❌ 自动推荐失败:', e);
            // 提供更详细的错误信息
            let errorMessage = `自动推荐失败: ${e.message}`;

            if (e.message.includes('Failed to fetch')) {
                errorMessage = '无法连接到服务器，请确保服务正在运行';
            } else if (e.message.includes('500')) {
                errorMessage = '服务器内部错误，请检查后端服务状态';
            } else if (e.message.includes('11434')) {
                errorMessage = '无法连接到Ollama服务，请确保Ollama正在运行';
            }

            this.showError(errorMessage);
        } finally {
            this.showLoading(false);

            // 恢复按钮状态
            const button = document.getElementById('auto-recommend-btn');
            if (button) {
                button.disabled = false;
                button.innerHTML = '<i class="fas fa-arrow-right"></i> 开始推荐';
            }
        }
    }

    _renderRecommendModal(recs) {
        const empty = document.getElementById('recommend-empty');
        const controls = document.getElementById('recommend-controls');
        const list = document.getElementById('recommend-list');
        const selectAll = document.getElementById('select-all-recommend');
        const confirmBtn = document.getElementById('confirm-recommend-btn');
        const cancelBtn = document.getElementById('cancel-recommend-btn');

        if (!recs || recs.length === 0) {
            empty.style.display = 'block';
            controls.style.display = 'none';
            confirmBtn.disabled = true;

            // 更新空状态的文本内容
            const alertDiv = empty.querySelector('.alert');
            if (alertDiv) {
                alertDiv.innerHTML = '<i class="fas fa-check-circle" style="color: #28a745; margin-right: 8px;"></i>所有模型均已配置规则模板，无需进行推荐。';
                alertDiv.style.backgroundColor = '#d4edda';
                alertDiv.style.borderColor = '#c3e6cb';
                alertDiv.style.color = '#155724';
            }
            return;
        }

        empty.style.display = 'none';
        controls.style.display = 'block';
        confirmBtn.disabled = false;

        list.innerHTML = recs.map(r => `
            <label class="checkbox-item">
                <input type="checkbox" class="recommend-checkbox" data-model-id="${r.model_id}" checked>
                <span>
                    <strong>${r.model_id}</strong>
                    <span style="color:var(--text-secondary);margin-left:8px;">→ ${r.template_name}</span>
                </span>
            </label>
        `).join('');

        // 绑定全选
        selectAll.checked = true;
        selectAll.onchange = (e) => {
            document.querySelectorAll('.recommend-checkbox').forEach(cb => cb.checked = e.target.checked);
        };

        // 绑定按钮
        cancelBtn.onclick = () => this.hideModal('recommend-modal');
        confirmBtn.onclick = async () => {
            const checked = Array.from(document.querySelectorAll('.recommend-checkbox'))
                .filter(cb => cb.checked)
                .map(cb => cb.dataset.modelId);
            if (checked.length === 0) {
                this.showError('请至少选择一个模型');
                return;
            }
            try {
                this.showLoading(true);
                const applyResp = await authManager.authenticatedFetch('/api/v1/model-rules-recommend/apply', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer cherry-studio-key'
                    },
                    body: JSON.stringify({ model_ids: checked })
                });
                if (!applyResp.ok) {
                    const err = await applyResp.json().catch(() => ({}));
                    throw new Error(err.detail || '应用推荐失败');
                }
                const applyData = await applyResp.json();
                this.showSuccess(`已为 ${applyData.applied} 个模型应用推荐`);
                this.hideModal('recommend-modal');
                await this.refreshData();
            } catch (e) {
                console.error('应用推荐失败:', e);
                this.showError(`应用推荐失败: ${e.message}`);
            } finally {
                this.showLoading(false);
            }
        };
    }

    async checkAllConfigurations() {
        console.log('🔍 开始全面检查配置...');

        try {
            this.showLoading(true);

            // 更新按钮状态
            const button = document.getElementById('check-all-btn');
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 检查中...';
            }

            // 1. 获取所有模型配置
            console.log('📡 开始获取模型配置数据...');
            const modelsResponse = await authManager.authenticatedFetch('/api/v1/model-rules', {
                headers: {
                    'Authorization': 'Bearer cherry-studio-key'
                }
            });

            if (!modelsResponse.ok) {
                throw new Error(`获取模型配置失败 (${modelsResponse.status})`);
            }

            const models = await modelsResponse.json();
            console.log('📊 获取到的模型配置:', models);
            console.log('📊 模型数量:', models.length);

            // 2. 检查各种配置问题
            console.log('🔍 开始分析配置问题...');
            const issues = [];
            const summary = {
                totalModels: models.length,
                configuredModels: 0,
                unconfiguredModels: 0,
                lowSecurityModels: 0,
                conflictingModels: 0,
                outdatedConfigs: 0,
                totalRules: 0
            };

            for (const model of models) {
                try {
                    console.log(`🔍 分析模型: ${model.model_id}`);

                    const rulesCount = model.rules_count || 0;
                    const securityScore = model.security_score || 0;

                    summary.totalRules += rulesCount;

                    if (rulesCount > 0) {
                        summary.configuredModels++;
                    } else {
                        summary.unconfiguredModels++;
                        issues.push({
                            type: 'warning',
                            model: model.model_id,
                            issue: '未配置安全规则',
                            description: '该模型没有配置任何安全规则，存在安全风险',
                            suggestion: '建议应用适当的规则模板'
                        });
                    }

                    // 检查安全评分
                    if (securityScore < 40) {
                        summary.lowSecurityModels++;
                        issues.push({
                            type: 'error',
                            model: model.model_id,
                            issue: '安全评分过低',
                            description: `安全评分仅为 ${securityScore}，低于推荐值(60)`,
                            suggestion: '建议增加更多安全规则或应用更严格的模板'
                        });
                    } else if (securityScore < 60) {
                        issues.push({
                            type: 'warning',
                            model: model.model_id,
                            issue: '安全评分偏低',
                            description: `安全评分为 ${securityScore}，建议提升至60以上`,
                            suggestion: '考虑添加额外的安全规则'
                        });
                    }

                    // 检查配置时间
                    if (model.last_updated) {
                        try {
                            const lastUpdated = new Date(model.last_updated);
                            if (!isNaN(lastUpdated.getTime())) {
                                const daysDiff = (new Date() - lastUpdated) / (1000 * 60 * 60 * 24);
                                if (daysDiff > 30) {
                                    summary.outdatedConfigs++;
                                    issues.push({
                                        type: 'info',
                                        model: model.model_id,
                                        issue: '配置较久未更新',
                                        description: `配置最后更新时间：${lastUpdated.toLocaleDateString()}`,
                                        suggestion: '建议检查并更新配置以确保最新的安全标准'
                                    });
                                }
                            }
                        } catch (dateError) {
                            console.warn(`模型 ${model.model_id} 的last_updated时间格式无效:`, model.last_updated, dateError);
                        }
                    }
                } catch (modelError) {
                    console.error(`处理模型 ${model.model_id || '未知'} 时发生错误:`, modelError);
                    // 继续处理其他模型
                }
            }

            console.log('📈 分析完成，汇总信息:', summary);
            console.log('⚠️ 发现问题数量:', issues.length);

            // 3. 显示检查结果
            console.log('🎨 开始显示检查结果...');
            this.showConfigCheckResults(summary, issues);
            console.log('✅ 配置检查完成！');

        } catch (error) {
            console.error('❌ 配置检查失败:', error);
            console.error('❌ 错误堆栈:', error.stack);
            this.showError(`配置检查失败: ${error.message}`);
        } finally {
            console.log('🧹 清理加载状态...');
            this.showLoading(false);

            // 恢复按钮状态
            const button = document.getElementById('check-all-btn');
            if (button) {
                button.disabled = false;
                button.innerHTML = '<i class="fas fa-check-double"></i> 全面检查';
                console.log('🔄 按钮状态已恢复');
            }
        }
    }

    showConfigCheckResults(summary, issues) {
        try {
            console.log('🎨 开始生成检查结果模态框...');
            console.log('📊 摘要数据:', summary);
            console.log('⚠️ 问题数据:', issues);

            // 创建检查结果模态框
            const modalHtml = `
                <div class="modal-backdrop" id="config-check-modal" style="display: flex;">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h3 class="modal-title">
                                    <i class="fas fa-search"></i> 配置检查报告
                                </h3>
                                <button type="button" class="modal-close" onclick="document.getElementById('config-check-modal').remove()">
                                    <i class="fas fa-times"></i>
                                </button>
                            </div>
                            <div class="modal-body" style="max-height: 600px; overflow-y: auto;">
                                <!-- 总体概况 -->
                                <div style="margin-bottom: 24px;">
                                    <h4 style="margin: 0 0 16px 0; color: #333; font-size: 16px;">📊 检查概况</h4>
                                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px;">
                                        <div style="background: #f8f9fa; padding: 12px; border-radius: 8px; text-align: center;">
                                            <div style="font-size: 24px; font-weight: bold; color: #007AFF;">${summary.totalModels || 0}</div>
                                            <div style="font-size: 12px; color: #666;">总模型数</div>
                                        </div>
                                        <div style="background: #d4edda; padding: 12px; border-radius: 8px; text-align: center;">
                                            <div style="font-size: 24px; font-weight: bold; color: #28a745;">${summary.configuredModels || 0}</div>
                                            <div style="font-size: 12px; color: #666;">已配置</div>
                                        </div>
                                        <div style="background: #fff3cd; padding: 12px; border-radius: 8px; text-align: center;">
                                            <div style="font-size: 24px; font-weight: bold; color: #ffc107;">${summary.unconfiguredModels || 0}</div>
                                            <div style="font-size: 12px; color: #666;">未配置</div>
                                        </div>
                                        <div style="background: #f8d7da; padding: 12px; border-radius: 8px; text-align: center;">
                                            <div style="font-size: 24px; font-weight: bold; color: #dc3545;">${summary.lowSecurityModels || 0}</div>
                                            <div style="font-size: 12px; color: #666;">低安全评分</div>
                                        </div>
                                        <div style="background: #e2e3e5; padding: 12px; border-radius: 8px; text-align: center;">
                                            <div style="font-size: 24px; font-weight: bold; color: #6c757d;">${summary.totalRules || 0}</div>
                                            <div style="font-size: 12px; color: #666;">总规则数</div>
                                        </div>
                                        <div style="background: #cce5ff; padding: 12px; border-radius: 8px; text-align: center;">
                                            <div style="font-size: 24px; font-weight: bold; color: #0066cc;">${summary.outdatedConfigs || 0}</div>
                                            <div style="font-size: 12px; color: #666;">过期配置</div>
                                        </div>
                                    </div>
                                </div>

                                <!-- 问题列表 -->
                                <div style="margin-bottom: 24px;">
                                    <h4 style="margin: 0 0 16px 0; color: #333; font-size: 16px;">
                                        ⚠️ 发现的问题 (${(issues || []).length})
                                    </h4>
                                    ${!issues || issues.length === 0 ?
                    '<div style="text-align: center; padding: 40px; color: #28a745;"><i class="fas fa-check-circle" style="font-size: 48px; margin-bottom: 16px;"></i><br>🎉 恭喜！没有发现任何配置问题</div>' :
                    issues.map(issue => {
                        try {
                            return `
                                                    <div style="border: 1px solid ${issue.type === 'error' ? '#f5c6cb' : issue.type === 'warning' ? '#ffeaa7' : '#bee5eb'}; 
                                                                background-color: ${issue.type === 'error' ? '#f8d7da' : issue.type === 'warning' ? '#fff3cd' : '#d4edda'}; 
                                                                border-radius: 8px; padding: 16px; margin-bottom: 12px;">
                                                        <div style="display: flex; align-items: start; gap: 12px;">
                                                            <div style="color: ${issue.type === 'error' ? '#721c24' : issue.type === 'warning' ? '#856404' : '#155724'};">
                                                                <i class="fas fa-${issue.type === 'error' ? 'exclamation-circle' : issue.type === 'warning' ? 'exclamation-triangle' : 'info-circle'}" style="font-size: 18px;"></i>
                                                            </div>
                                                            <div style="flex: 1;">
                                                                <h5 style="margin: 0 0 8px 0; color: ${issue.type === 'error' ? '#721c24' : issue.type === 'warning' ? '#856404' : '#155724'};">
                                                                    ${issue.model || '未知模型'} - ${issue.issue || '未知问题'}
                                                                </h5>
                                                                <p style="margin: 0 0 8px 0; color: #666; font-size: 14px;">${issue.description || '无描述'}</p>
                                                                <p style="margin: 0; color: ${issue.type === 'error' ? '#721c24' : issue.type === 'warning' ? '#856404' : '#155724'}; font-size: 13px; font-style: italic;">
                                                                    💡 ${issue.suggestion || '暂无建议'}
                                                                </p>
                                                            </div>
                                                        </div>
                                                    </div>
                                                `;
                        } catch (issueError) {
                            console.error('生成问题项时发生错误:', issueError, issue);
                            return `<div style="padding: 8px; background: #ffe6e6; border-radius: 4px; color: #cc0000;">显示问题时出错</div>`;
                        }
                    }).join('')
                }
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" onclick="document.getElementById('config-check-modal').remove()">
                                    关闭
                                </button>
                                ${issues && issues.length > 0 ? `
                                    <button type="button" class="btn btn-primary" onclick="modelRulesManager.fixConfigIssues(); document.getElementById('config-check-modal').remove();">
                                        <i class="fas fa-wrench"></i> 一键修复
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                </div>
            `;

            console.log('📝 模态框HTML生成完成，长度:', modalHtml.length);

            // 移除现有的模态框
            const existingModal = document.getElementById('config-check-modal');
            if (existingModal) {
                console.log('🗑️ 移除现有模态框');
                existingModal.remove();
            }

            // 添加新的模态框
            console.log('➕ 添加新模态框到页面');
            document.body.insertAdjacentHTML('beforeend', modalHtml);

            // 验证模态框是否正确添加
            const newModal = document.getElementById('config-check-modal');
            if (newModal) {
                console.log('✅ 模态框成功添加到页面');
                // 确保模态框可见
                newModal.style.display = 'flex';
                newModal.style.zIndex = '9999';
                console.log('✅ 模态框显示状态已设置');
            } else {
                console.error('❌ 模态框添加失败');
                this.showError('显示检查结果时发生错误');
            }

        } catch (error) {
            console.error('❌ 生成检查结果模态框时发生错误:', error);
            console.error('❌ 错误堆栈:', error.stack);
            this.showError(`显示检查结果失败: ${error.message}`);
        }
    }

    async fixConfigIssues() {
        console.log('🔧 开始一键修复配置问题...');

        try {
            this.showLoading(true);

            // 获取推荐配置
            const recResponse = await authManager.authenticatedFetch('/api/v1/model-rules-recommend', {
                headers: {
                    'Authorization': 'Bearer cherry-studio-key'
                }
            });

            if (recResponse.ok) {
                const recData = await recResponse.json();
                if (recData.recommendations && recData.recommendations.length > 0) {
                    // 应用推荐配置
                    const applyResponse = await authManager.authenticatedFetch('/api/v1/model-rules-recommend/apply', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': 'Bearer cherry-studio-key'
                        },
                        body: JSON.stringify({})
                    });

                    if (applyResponse.ok) {
                        const result = await applyResponse.json();
                        this.showSuccess(`已为 ${result.applied} 个模型应用推荐配置`);
                        await this.refreshData();
                    }
                } else {
                    this.showSuccess('所有模型已是最优配置，无需修复');
                }
            }

        } catch (error) {
            console.error('❌ 修复配置问题失败:', error);
            this.showError(`修复失败: ${error.message}`);
        } finally {
            this.showLoading(false);
        }
    }
}

// 初始化管理器
let modelRulesManager;

// 初始化认证和页面
document.addEventListener('DOMContentLoaded', async function () {
    // 等待authManager可用(由auth-check.js提供)
    const checkAuthManager = () => {
        return new Promise((resolve) => {
            if (window.authManager) {
                resolve();
            } else {
                const interval = setInterval(() => {
                    if (window.authManager) {
                        clearInterval(interval);
                        resolve();
                    }
                }, 100);
            }
        });
    };

    await checkAuthManager();

    // 先进行认证和权限检查
    const authenticated = await authManager.init({
        userElementId: 'currentUser',
        autoRefresh: true,
        requiredRole: 'security_analyst',
        onAuthSuccess: (user) => {
            console.log('用户认证成功:', user.username);
            // 认证成功后初始化页面管理器
            console.log('🚀 初始化ModelRulesManager...');
            modelRulesManager = new ModelRulesManager();
            // 将管理器设置为全局变量,以便HTML中的onclick可以访问
            window.modelRulesManager = modelRulesManager;
            console.log('✅ ModelRulesManager初始化完成,已设置为全局变量');
        }
    });

    if (!authenticated) {
        return; // 认证失败会自动跳转到登录页
    }

    // 添加测试函数到全局作用域
    window.testConfigureModel = function (modelId) {
        console.log('🧪 测试配置模型:', modelId);
        if (window.modelRulesManager) {
            console.log('✅ modelRulesManager 可访问');
            window.modelRulesManager.configureModel(modelId || 'phi3:latest');
        } else {
            console.error('❌ modelRulesManager 不可访问');
        }
    };

    // 添加全局hideModal函数，供HTML中的onclick使用
    window.hideModal = function (modalId) {
        if (window.modelRulesManager) {
            window.modelRulesManager.hideModal(modalId);
        }
    };

    console.log('🧪 测试函数已添加，可在控制台运行: testConfigureModel()');

    // 添加推荐功能测试
    window.testAutoRecommend = function () {
        console.log('🧪 测试智能推荐功能...');
        if (window.modelRulesManager) {
            console.log('✅ modelRulesManager 可访问');
            window.modelRulesManager.autoRecommendConfig();
        } else {
            console.error('❌ modelRulesManager 不可访问');
        }
    };

    console.log('🧪 推荐测试函数已添加，可在控制台运行: testAutoRecommend()');

    // 添加模板保存功能到类
    ModelRulesManager.prototype.saveTemplateToServer = async function (template) {
        try {
            const response = await authManager.authenticatedFetch(`/api/v1/rule-templates/${template.id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer cherry-studio-key'
                },
                body: JSON.stringify({
                    name: template.name,
                    description: template.description,
                    rules: template.rules,
                    category: template.category || 'security'
                })
            });

            if (!response.ok) {
                throw new Error(`保存失败: ${response.status} ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('保存模板到服务器失败:', error);
            throw error;
        }
    };

    console.log('💾 模板保存函数已添加到类: saveTemplateToServer()');
});