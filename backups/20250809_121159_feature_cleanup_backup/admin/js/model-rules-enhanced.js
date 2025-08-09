// 规则配置页面增强脚本

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
            // 先获取已安装的模型列表
            const modelsResponse = await fetch('/api/v1/ollama/models', {
                headers: {
                    'Authorization': 'Bearer cherry-studio-key'
                }
            });
            if (!modelsResponse.ok) throw new Error('获取模型列表失败');
            
            const modelsData = await modelsResponse.json();
            console.log('获取到模型数据:', modelsData);
            
            // 然后获取每个模型的规则配置
            const models = modelsData.models || modelsData.data || [];
            console.log('处理模型数量:', models.length);
            this.modelsData = await Promise.all(models.map(async (model) => {
                try {
                    const configResponse = await fetch(`/api/v1/model-rules/${model.model || model.id}`);
                    const configData = configResponse.ok ? await configResponse.json() : null;
                    
                    const enabledRulesCount = configData?.rules ? 
                        configData.rules.filter(rule => rule.enabled).length : 0;
                    const totalRulesCount = configData?.rules ? configData.rules.length : 0;
                    
                    return {
                        id: model.model || model.id,
                        name: model.model || model.id,
                        size: model.size || 0,
                        modified_at: model.modified_at || model.created,
                        template: configData?.template_id || null,
                        rulesCount: totalRulesCount,
                        enabledRulesCount: enabledRulesCount,
                        securityScore: this.calculateSecurityScore(enabledRulesCount),
                        lastUpdated: configData?.updated_at || model.modified_at || new Date().toISOString(),
                        isConfigured: !!(totalRulesCount > 0),
                        riskLevel: this.calculateRiskLevel(this.calculateSecurityScore(enabledRulesCount))
                    };
                } catch (error) {
                    console.warn(`获取模型 ${model.model || model.id} 配置失败:`, error);
                    return {
                        id: model.model || model.id,
                        name: model.model || model.id,
                        size: model.size || 0,
                        modified_at: model.modified_at || model.created,
                        template: null,
                        rulesCount: 0,
                        enabledRulesCount: 0,
                        securityScore: 0,
                        lastUpdated: model.modified_at || new Date().toISOString(),
                        isConfigured: false,
                        riskLevel: 'high'
                    };
                }
            }));
            console.log('处理后的模型数据:', this.modelsData);
        } catch (error) {
            console.error('加载模型数据失败:', error);
            this.modelsData = [];
        }
    }

    async loadTemplatesData() {
        try {
            const response = await fetch('/api/v1/rule-templates');
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
        console.log('配置模型:', modelId);
        
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
                const configResponse = await fetch(`/api/v1/model-rules/${modelId}`, {
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
                const rulesResponse = await fetch('/api/v1/rules', {
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
            const response = await fetch(`/api/v1/model-rules/${modelId}`, {
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
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'block';
            document.body.classList.add('modal-open');
        }
    }

    hideModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'none';
            document.body.classList.remove('modal-open');
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

    editRule(ruleId) {
        console.log('编辑规则:', ruleId);
        // TODO: 实现规则编辑功能
        alert(`编辑规则功能开发中...\n\n规则ID: ${ruleId}\n\n将提供规则详细配置界面。`);
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
        // TODO: 打开编辑模板modal
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

    autoRecommendConfig() {
        console.log('开始自动推荐配置');
        // TODO: 实现自动推荐逻辑
    }

    checkAllConfigurations() {
        console.log('开始全面检查配置');
        // TODO: 实现配置检查逻辑
    }
}

// 初始化管理器
let modelRulesManager;

document.addEventListener('DOMContentLoaded', function() {
    modelRulesManager = new ModelRulesManager();
});