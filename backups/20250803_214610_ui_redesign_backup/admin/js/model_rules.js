// 模型安全规则配置页面脚本

// 全局变量
let allModels = [];          // 所有模型摘要
let allTemplates = [];       // 所有规则集模板
let allRules = [];           // 所有安全规则
let currentModelId = null;   // 当前选中的模型ID
let currentModelConfig = null; // 当前模型的规则配置
let availableRules = [];     // 可添加的规则列表

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 初始化页面
    initPage();

    // 绑定事件
    bindEvents();

    // 加载数据
    loadData();
});

// 初始化页面
function initPage() {
    // 隐藏所有模态框
    document.querySelectorAll('.modal-backdrop').forEach(modal => {
        modal.classList.remove('show');
    });
}

// 绑定事件
function bindEvents() {
    // 刷新按钮
    document.getElementById('refresh-btn').addEventListener('click', loadData);

    // 批量应用模板按钮
    document.getElementById('batch-apply-template-btn').addEventListener('click', showBatchApplyTemplateModal);

    // 创建模板按钮
    document.getElementById('create-template-btn').addEventListener('click', showCreateTemplateModal);

    // 模态框关闭按钮
    document.querySelectorAll('.modal-close').forEach(closeBtn => {
        closeBtn.addEventListener('click', function() {
            const modal = this.closest('.modal-backdrop');
            hideModal(modal.id);
        });
    });

    // 批量应用模板模态框按钮
    document.getElementById('cancel-batch-apply-btn').addEventListener('click', () => hideModal('batch-apply-template-modal'));
    document.getElementById('confirm-batch-apply-btn').addEventListener('click', batchApplyTemplate);

    // 创建模板模态框按钮
    document.getElementById('cancel-create-template-btn').addEventListener('click', () => hideModal('create-template-modal'));
    document.getElementById('confirm-create-template-btn').addEventListener('click', createTemplate);

    // 模板来源选择变化事件
    document.getElementById('template-source').addEventListener('change', function() {
        const sourceValue = this.value;
        document.getElementById('source-model-group').style.display = sourceValue === 'model' ? 'block' : 'none';
        document.getElementById('source-template-group').style.display = sourceValue === 'template' ? 'block' : 'none';
    });

    // 模型规则配置模态框按钮
    document.getElementById('close-config-btn').addEventListener('click', () => hideModal('model-rules-config-modal'));
    document.getElementById('save-config-btn').addEventListener('click', saveModelRuleConfig);

    // 应用模板按钮
    document.getElementById('apply-template-btn').addEventListener('click', showApplyTemplateModal);

    // 应用模板模态框按钮
    document.getElementById('cancel-apply-template-btn').addEventListener('click', () => hideModal('apply-template-modal'));
    document.getElementById('confirm-apply-template-btn').addEventListener('click', applyTemplateToModel);

    // 添加规则按钮
    document.getElementById('add-rules-btn').addEventListener('click', showAddRulesModal);

    // 添加规则模态框按钮
    document.getElementById('cancel-add-rules-btn').addEventListener('click', () => hideModal('add-rules-modal'));
    document.getElementById('confirm-add-rules-btn').addEventListener('click', addSelectedRulesToModel);

    // 检查冲突按钮
    document.getElementById('check-conflicts-btn').addEventListener('click', checkRuleConflicts);

    // 冲突模态框按钮
    document.getElementById('close-conflicts-btn').addEventListener('click', () => hideModal('conflicts-modal'));

    // 批量启用/禁用按钮
    document.getElementById('batch-toggle-btn').addEventListener('click', batchToggleRules);

    // 全选模型复选框
    document.getElementById('select-all-models').addEventListener('change', function() {
        const checkboxes = document.querySelectorAll('#model-rules-body input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            checkbox.checked = this.checked;
        });
    });

    // 全选规则复选框
    document.getElementById('select-all-rules').addEventListener('change', function() {
        const checkboxes = document.querySelectorAll('#model-config-rules-body input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            checkbox.checked = this.checked;
        });
    });

    // 全选可用规则复选框
    document.getElementById('select-all-available-rules').addEventListener('change', function() {
        const checkboxes = document.querySelectorAll('#available-rules-body input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            checkbox.checked = this.checked;
        });
    });

    // 模型搜索框
    document.getElementById('model-search').addEventListener('input', filterModels);

    // 规则搜索框
    document.getElementById('rules-search').addEventListener('input', filterModelRules);

    // 规则类型过滤器
    document.getElementById('rules-type-filter').addEventListener('change', filterModelRules);

    // 规则状态过滤器
    document.getElementById('rules-status-filter').addEventListener('change', filterModelRules);

    // 可用规则搜索框
    document.getElementById('available-rules-search').addEventListener('input', filterAvailableRules);

    // 可用规则类型过滤器
    document.getElementById('available-rules-type-filter').addEventListener('change', filterAvailableRules);
}

// 加载数据
async function loadData() {
    try {
        // 显示加载状态
        showLoading();

        // 并行加载数据
        const [modelRulesResponse, templatesResponse, rulesResponse] = await Promise.all([
            fetch('/api/v1/model-rules'),
            fetch('/api/v1/rule-templates'),
            fetch('/api/v1/rules')
        ]);

        // 检查响应状态
        if (!modelRulesResponse.ok || !templatesResponse.ok || !rulesResponse.ok) {
            throw new Error('加载数据失败');
        }

        // 解析响应数据
        allModels = await modelRulesResponse.json();
        allTemplates = await templatesResponse.json();
        allRules = await rulesResponse.json();

        // 渲染数据
        renderModelRulesSummary();
        renderTemplates();

        // 隐藏加载状态
        hideLoading();
    } catch (error) {
        console.error('加载数据失败:', error);
        alert('加载数据失败: ' + error.message);
        hideLoading();
    }
}

// 渲染模型规则摘要
function renderModelRulesSummary() {
    const tableBody = document.getElementById('model-rules-body');
    tableBody.innerHTML = '';

    if (allModels.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="8" class="text-center">暂无数据</td>';
        tableBody.appendChild(row);
        return;
    }

    allModels.forEach(model => {
        const row = document.createElement('tr');

        // 安全评分样式
        let scoreClass = 'low';
        if (model.security_score >= 70) {
            scoreClass = 'high';
        } else if (model.security_score >= 40) {
            scoreClass = 'medium';
        }

        // 格式化日期
        const lastUpdated = new Date(model.last_updated).toLocaleString();

        row.innerHTML = `
            <td class="checkbox-column"><input type="checkbox" data-model-id="${model.model_id}"></td>
            <td class="model-name-column">${model.model_name}</td>
            <td class="template-column">${model.template_name || '无'}</td>
            <td class="rules-count-column text-center">${model.rules_count}</td>
            <td class="enabled-rules-column text-center">${model.enabled_rules_count}</td>
            <td class="security-score-column text-center"><span class="security-score ${scoreClass}">${model.security_score}</span></td>
            <td class="last-updated-column">${lastUpdated}</td>
            <td class="actions-column text-right">
                <button class="button small" onclick="showModelRuleConfig('${model.model_id}', '${model.model_name}')">配置</button>
            </td>
        `;

        tableBody.appendChild(row);
    });
}

// 渲染规则集模板
function renderTemplates() {
    const tableBody = document.getElementById('templates-body');
    tableBody.innerHTML = '';

    if (allTemplates.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="6" class="text-center">暂无数据</td>';
        tableBody.appendChild(row);
        return;
    }

    allTemplates.forEach(template => {
        const row = document.createElement('tr');

        // 格式化日期
        const createdAt = new Date(template.created_at).toLocaleString();

        row.innerHTML = `
            <td class="template-name-column">${template.name}</td>
            <td class="description-column">${template.description}</td>
            <td class="rules-count-column text-center">${template.rules.length}</td>
            <td class="category-column">${template.category}</td>
            <td class="created-at-column">${createdAt}</td>
            <td class="actions-column text-right">
                <button class="button small" onclick="viewTemplate('${template.id}')">查看</button>
                <button class="button small" onclick="editTemplate('${template.id}')">编辑</button>
                <button class="button small danger" onclick="deleteTemplate('${template.id}')">删除</button>
            </td>
        `;

        tableBody.appendChild(row);
    });

    // 更新模板选择下拉框
    updateTemplateSelects();
}

// 更新模板选择下拉框
function updateTemplateSelects() {
    const templateSelects = [
        document.getElementById('template-select'),
        document.getElementById('single-template-select'),
        document.getElementById('source-template')
    ];

    templateSelects.forEach(select => {
        if (select) {
            select.innerHTML = '';

            // 添加默认选项
            if (select.id === 'source-template') {
                const defaultOption = document.createElement('option');
                defaultOption.value = '';
                defaultOption.textContent = '请选择模板';
                select.appendChild(defaultOption);
            }

            // 添加模板选项
            allTemplates.forEach(template => {
                const option = document.createElement('option');
                option.value = template.id;
                option.textContent = `${template.name} (${template.category})`;
                select.appendChild(option);
            });
        }
    });

    // 更新模型选择下拉框
    const sourceModelSelect = document.getElementById('source-model');
    if (sourceModelSelect) {
        sourceModelSelect.innerHTML = '';

        // 添加默认选项
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = '请选择模型';
        sourceModelSelect.appendChild(defaultOption);

        // 添加模型选项
        allModels.forEach(model => {
            const option = document.createElement('option');
            option.value = model.model_id;
            option.textContent = model.model_name;
            sourceModelSelect.appendChild(option);
        });
    }
}

// 显示模态框
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('show');
    }
}

// 隐藏模态框
function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
    }
}

// 显示加载状态
function showLoading() {
    // 可以添加加载指示器
    document.body.style.cursor = 'wait';
}

// 隐藏加载状态
function hideLoading() {
    document.body.style.cursor = 'default';
}

// 过滤模型列表
function filterModels() {
    const searchText = document.getElementById('model-search').value.toLowerCase();
    const rows = document.querySelectorAll('#model-rules-body tr');

    rows.forEach(row => {
        const modelName = row.cells[1].textContent.toLowerCase();
        if (modelName.includes(searchText)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

// 显示批量应用模板模态框
function showBatchApplyTemplateModal() {
    // 更新模型选择列表
    const modelSelectionList = document.getElementById('model-selection-list');
    modelSelectionList.innerHTML = '';

    allModels.forEach(model => {
        const item = document.createElement('div');
        item.className = 'model-selection-item';
        item.innerHTML = `
            <input type="checkbox" id="model-${model.model_id}" value="${model.model_id}">
            <label for="model-${model.model_id}">${model.model_name}</label>
        `;
        modelSelectionList.appendChild(item);
    });

    // 显示模态框
    showModal('batch-apply-template-modal');
}

// 显示创建模板模态框
function showCreateTemplateModal() {
    // 重置表单
    document.getElementById('create-template-form').reset();
    document.getElementById('source-model-group').style.display = 'none';
    document.getElementById('source-template-group').style.display = 'none';

    // 显示模态框
    showModal('create-template-modal');
}

// 显示模型规则配置
async function showModelRuleConfig(modelId, modelName) {
    try {
        showLoading();
        currentModelId = modelId;

        // 获取模型规则配置
        const response = await fetch(`/api/v1/model-rules/${modelId}`);

        if (response.status === 404) {
            // 如果配置不存在，创建一个空配置
            currentModelConfig = {
                model_id: modelId,
                template_id: null,
                rules: []
            };
        } else if (response.ok) {
            currentModelConfig = await response.json();
        } else {
            throw new Error('获取模型规则配置失败');
        }

        // 更新模态框标题和模型信息
        document.getElementById('model-rules-config-title').textContent = `模型规则配置: ${modelName}`;
        document.getElementById('config-model-name').textContent = modelName;

        // 获取模型摘要信息
        const modelSummary = allModels.find(m => m.model_id === modelId);
        if (modelSummary) {
            document.getElementById('config-template-name').textContent = modelSummary.template_name || '无';
            document.getElementById('config-rules-count').textContent = modelSummary.rules_count;
            document.getElementById('config-security-score').textContent = modelSummary.security_score;
        }

        // 渲染规则列表
        renderModelRules();

        // 显示模态框
        showModal('model-rules-config-modal');
        hideLoading();
    } catch (error) {
        console.error('显示模型规则配置失败:', error);
        alert('显示模型规则配置失败: ' + error.message);
        hideLoading();
    }
}

// 渲染模型规则列表
function renderModelRules() {
    const tableBody = document.getElementById('model-config-rules-body');
    tableBody.innerHTML = '';

    if (!currentModelConfig || !currentModelConfig.rules || currentModelConfig.rules.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="8" class="text-center">暂无规则配置</td>';
        tableBody.appendChild(row);
        return;
    }

    // 创建规则ID到规则的映射
    const rulesMap = {};
    allRules.forEach(rule => {
        rulesMap[rule.id] = rule;
    });

    // 渲染规则列表
    currentModelConfig.rules.forEach(ruleAssoc => {
        const rule = rulesMap[ruleAssoc.rule_id];
        if (!rule) return; // 跳过找不到的规则

        const row = document.createElement('tr');

        // 根据规则类型和严重程度设置样式
        let typeClass = '';
        switch (rule.detection_type) {
            case 'prompt_injection':
                typeClass = 'bg-warning';
                break;
            case 'jailbreak':
                typeClass = 'bg-danger';
                break;
            case 'harmful_content':
                typeClass = 'bg-danger';
                break;
            case 'sensitive_info':
                typeClass = 'bg-info';
                break;
            case 'compliance_violation':
                typeClass = 'bg-warning';
                break;
        }

        row.innerHTML = `
            <td style="width: 40px; text-align: center;"><input type="checkbox" data-rule-id="${rule.id}"></td>
            <td style="width: 100px;">${rule.id}</td>
            <td style="width: 20%;">${rule.name}</td>
            <td style="width: 12%;" class="${typeClass}">${rule.detection_type}</td>
            <td style="width: 10%;">${rule.severity}</td>
            <td style="width: 80px; text-align: center;">
                <input type="number" class="form-control priority-input"
                       value="${ruleAssoc.priority}" min="1" max="1000"
                       data-rule-id="${rule.id}" style="width: 60px; margin: 0 auto;">
            </td>
            <td style="width: 80px; text-align: center;">
                <label class="toggle-switch">
                    <input type="checkbox" class="rule-enabled-toggle"
                           data-rule-id="${rule.id}" ${ruleAssoc.enabled ? 'checked' : ''}>
                    <span class="toggle-slider"></span>
                </label>
            </td>
            <td style="width: 120px; text-align: center;">
                <button class="button small danger" onclick="removeRule('${rule.id}')">移除</button>
            </td>
        `;

        tableBody.appendChild(row);
    });

    // 绑定规则启用状态切换事件
    document.querySelectorAll('.rule-enabled-toggle').forEach(toggle => {
        toggle.addEventListener('change', function() {
            const ruleId = this.getAttribute('data-rule-id');
            updateRuleEnabled(ruleId, this.checked);
        });
    });

    // 绑定规则优先级输入事件
    document.querySelectorAll('.priority-input').forEach(input => {
        input.addEventListener('change', function() {
            const ruleId = this.getAttribute('data-rule-id');
            const priority = parseInt(this.value);
            updateRulePriority(ruleId, priority);
        });
    });
}

// 更新规则启用状态
function updateRuleEnabled(ruleId, enabled) {
    if (!currentModelConfig) return;

    const rule = currentModelConfig.rules.find(r => r.rule_id === ruleId);
    if (rule) {
        rule.enabled = enabled;
    }
}

// 更新规则优先级
function updateRulePriority(ruleId, priority) {
    if (!currentModelConfig) return;

    const rule = currentModelConfig.rules.find(r => r.rule_id === ruleId);
    if (rule) {
        rule.priority = priority;
    }
}

// 移除规则
function removeRule(ruleId) {
    if (!currentModelConfig) return;

    if (confirm(`确定要移除规则 ${ruleId} 吗？`)) {
        currentModelConfig.rules = currentModelConfig.rules.filter(r => r.rule_id !== ruleId);
        renderModelRules();
    }
}

// 保存模型规则配置
async function saveModelRuleConfig() {
    try {
        showLoading();

        if (!currentModelConfig || !currentModelId) {
            throw new Error('当前没有选中的模型');
        }

        // 构建请求数据
        const requestData = {
            template_id: currentModelConfig.template_id,
            rules: currentModelConfig.rules.map(rule => ({
                rule_id: rule.rule_id,
                enabled: rule.enabled,
                priority: rule.priority,
                override_params: rule.override_params || {}
            }))
        };

        // 发送请求
        const response = await fetch(`/api/v1/model-rules/${currentModelId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            throw new Error('保存模型规则配置失败');
        }

        // 更新配置
        currentModelConfig = await response.json();

        // 重新加载数据
        await loadData();

        // 隐藏模态框
        hideModal('model-rules-config-modal');

        alert('保存成功');
        hideLoading();
    } catch (error) {
        console.error('保存模型规则配置失败:', error);
        alert('保存模型规则配置失败: ' + error.message);
        hideLoading();
    }
}

// 显示应用模板模态框
function showApplyTemplateModal() {
    if (!currentModelId) return;

    // 显示模态框
    showModal('apply-template-modal');
}

// 应用模板到模型
async function applyTemplateToModel() {
    try {
        showLoading();

        if (!currentModelId) {
            throw new Error('当前没有选中的模型');
        }

        const templateId = document.getElementById('single-template-select').value;
        if (!templateId) {
            throw new Error('请选择模板');
        }

        // 发送请求
        const response = await fetch(`/api/v1/models/${currentModelId}/apply-template/${templateId}`, {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error('应用模板失败');
        }

        // 更新配置
        currentModelConfig = await response.json();

        // 重新加载数据
        await loadData();

        // 更新模型规则列表
        renderModelRules();

        // 隐藏模态框
        hideModal('apply-template-modal');

        // 更新模型信息
        const modelSummary = allModels.find(m => m.model_id === currentModelId);
        if (modelSummary) {
            const template = allTemplates.find(t => t.id === templateId);
            document.getElementById('config-template-name').textContent = template ? template.name : '无';
            document.getElementById('config-rules-count').textContent = currentModelConfig.rules.length;
        }

        alert('应用模板成功');
        hideLoading();
    } catch (error) {
        console.error('应用模板失败:', error);
        alert('应用模板失败: ' + error.message);
        hideLoading();
    }
}

// 显示添加规则模态框
async function showAddRulesModal() {
    try {
        if (!currentModelId) return;

        showLoading();

        // 获取所有规则
        if (!allRules || allRules.length === 0) {
            const response = await fetch('/api/v1/rules');
            if (!response.ok) {
                throw new Error('获取规则列表失败');
            }
            allRules = await response.json();
        }

        // 过滤出当前模型中不存在的规则
        availableRules = [];
        const currentRuleIds = new Set();

        if (currentModelConfig && currentModelConfig.rules) {
            currentModelConfig.rules.forEach(rule => {
                currentRuleIds.add(rule.rule_id);
            });
        }

        allRules.forEach(rule => {
            if (!currentRuleIds.has(rule.id)) {
                availableRules.push(rule);
            }
        });

        // 渲染可用规则列表
        renderAvailableRules();

        // 显示模态框
        showModal('add-rules-modal');
        hideLoading();
    } catch (error) {
        console.error('显示添加规则模态框失败:', error);
        alert('显示添加规则模态框失败: ' + error.message);
        hideLoading();
    }
}

// 渲染可用规则列表
function renderAvailableRules() {
    const tableBody = document.getElementById('available-rules-body');
    tableBody.innerHTML = '';

    if (!availableRules || availableRules.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="7" class="text-center">没有可添加的规则</td>';
        tableBody.appendChild(row);
        return;
    }

    availableRules.forEach(rule => {
        const row = document.createElement('tr');

        // 根据规则类型和严重程度设置样式
        let typeClass = '';
        switch (rule.detection_type) {
            case 'prompt_injection':
                typeClass = 'bg-warning';
                break;
            case 'jailbreak':
                typeClass = 'bg-danger';
                break;
            case 'harmful_content':
                typeClass = 'bg-danger';
                break;
            case 'sensitive_info':
                typeClass = 'bg-info';
                break;
            case 'compliance_violation':
                typeClass = 'bg-warning';
                break;
        }

        row.innerHTML = `
            <td><input type="checkbox" data-rule-id="${rule.id}"></td>
            <td>${rule.id}</td>
            <td>${rule.name}</td>
            <td class="${typeClass}">${rule.detection_type}</td>
            <td>${rule.severity}</td>
            <td>${rule.description}</td>
            <td>
                <button class="button small" onclick="addRuleToModel('${rule.id}')">添加</button>
            </td>
        `;

        tableBody.appendChild(row);
    });
}

// 添加规则到模型
function addRuleToModel(ruleId) {
    if (!currentModelConfig) return;

    // 检查规则是否已存在
    const existingRule = currentModelConfig.rules.find(r => r.rule_id === ruleId);
    if (existingRule) {
        alert(`规则 ${ruleId} 已存在于当前模型中`);
        return;
    }

    // 添加规则
    const newRule = {
        id: `${currentModelId}_${ruleId}`,
        model_id: currentModelId,
        rule_id: ruleId,
        enabled: true,
        priority: 100,
        override_params: {}
    };

    currentModelConfig.rules.push(newRule);

    // 从可用规则列表中移除
    availableRules = availableRules.filter(rule => rule.id !== ruleId);

    // 更新规则列表
    renderAvailableRules();

    alert(`规则 ${ruleId} 已添加到模型中`);
}

// 添加选中的规则到模型
function addSelectedRulesToModel() {
    if (!currentModelConfig) return;

    // 获取选中的规则ID
    const selectedRuleIds = [];
    document.querySelectorAll('#available-rules-body input[type="checkbox"]:checked').forEach(checkbox => {
        selectedRuleIds.push(checkbox.getAttribute('data-rule-id'));
    });

    if (selectedRuleIds.length === 0) {
        alert('请选择要添加的规则');
        return;
    }

    // 添加选中的规则
    let addedCount = 0;
    selectedRuleIds.forEach(ruleId => {
        // 检查规则是否已存在
        const existingRule = currentModelConfig.rules.find(r => r.rule_id === ruleId);
        if (!existingRule) {
            // 添加规则
            const newRule = {
                id: `${currentModelId}_${ruleId}`,
                model_id: currentModelId,
                rule_id: ruleId,
                enabled: true,
                priority: 100,
                override_params: {}
            };

            currentModelConfig.rules.push(newRule);
            addedCount++;
        }
    });

    // 隐藏模态框
    hideModal('add-rules-modal');

    // 更新模型规则列表
    renderModelRules();

    alert(`成功添加 ${addedCount} 条规则`);
}

// 检查规则冲突
async function checkRuleConflicts() {
    try {
        if (!currentModelId) return;

        showLoading();

        // 发送请求
        const response = await fetch(`/api/v1/model-rules/${currentModelId}/conflicts`);

        if (!response.ok) {
            throw new Error('检查规则冲突失败');
        }

        const conflicts = await response.json();

        // 渲染冲突列表
        const conflictsContainer = document.getElementById('conflicts-container');
        conflictsContainer.innerHTML = '';

        if (conflicts.length === 0) {
            conflictsContainer.innerHTML = '<div class="alert success">未检测到规则冲突</div>';
        } else {
            conflicts.forEach(conflict => {
                const conflictItem = document.createElement('div');
                conflictItem.className = 'conflict-item';
                conflictItem.innerHTML = `
                    <div class="conflict-title">规则冲突: ${conflict.rule1_id} 与 ${conflict.rule2_id}</div>
                    <div class="conflict-description">冲突类型: ${conflict.conflict_type}</div>
                    <div class="conflict-description">描述: ${conflict.description}</div>
                    <div class="conflict-suggestion">建议: ${conflict.suggestion}</div>
                `;
                conflictsContainer.appendChild(conflictItem);
            });
        }

        // 显示模态框
        showModal('conflicts-modal');
        hideLoading();
    } catch (error) {
        console.error('检查规则冲突失败:', error);
        alert('检查规则冲突失败: ' + error.message);
        hideLoading();
    }
}

// 批量启用/禁用规则
function batchToggleRules() {
    if (!currentModelConfig) return;

    // 获取选中的规则ID
    const selectedRuleIds = [];
    document.querySelectorAll('#model-config-rules-body input[type="checkbox"]:checked').forEach(checkbox => {
        selectedRuleIds.push(checkbox.getAttribute('data-rule-id'));
    });

    if (selectedRuleIds.length === 0) {
        alert('请选择要操作的规则');
        return;
    }

    // 询问操作类型
    const action = confirm('点击确定启用选中规则，点击取消禁用选中规则') ? true : false;

    // 更新规则状态
    let updatedCount = 0;
    selectedRuleIds.forEach(ruleId => {
        const rule = currentModelConfig.rules.find(r => r.rule_id === ruleId);
        if (rule && rule.enabled !== action) {
            rule.enabled = action;
            updatedCount++;
        }
    });

    // 更新规则列表
    renderModelRules();

    alert(`成功${action ? '启用' : '禁用'} ${updatedCount} 条规则`);
}

// 批量应用模板
async function batchApplyTemplate() {
    try {
        showLoading();

        // 获取选中的模型ID
        const selectedModelIds = [];
        document.querySelectorAll('#model-selection-list input[type="checkbox"]:checked').forEach(checkbox => {
            selectedModelIds.push(checkbox.value);
        });

        if (selectedModelIds.length === 0) {
            throw new Error('请选择要应用模板的模型');
        }

        const templateId = document.getElementById('template-select').value;
        if (!templateId) {
            throw new Error('请选择模板');
        }

        // 发送请求
        const response = await fetch('/api/v1/models/batch/apply-template', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model_ids: selectedModelIds,
                template_id: templateId
            })
        });

        if (!response.ok) {
            throw new Error('批量应用模板失败');
        }

        const result = await response.json();

        // 重新加载数据
        await loadData();

        // 隐藏模态框
        hideModal('batch-apply-template-modal');

        alert(result.message || '批量应用模板成功');
        hideLoading();
    } catch (error) {
        console.error('批量应用模板失败:', error);
        alert('批量应用模板失败: ' + error.message);
        hideLoading();
    }
}

// 创建模板
async function createTemplate() {
    try {
        showLoading();

        // 获取表单数据
        const name = document.getElementById('template-name').value.trim();
        const description = document.getElementById('template-description').value.trim();
        const category = document.getElementById('template-category').value;
        const source = document.getElementById('template-source').value;

        if (!name) {
            throw new Error('请输入模板名称');
        }

        if (!description) {
            throw new Error('请输入模板描述');
        }

        let rules = [];

        // 根据来源获取规则
        if (source === 'model') {
            // 从模型创建
            const modelId = document.getElementById('source-model').value;
            if (!modelId) {
                throw new Error('请选择源模型');
            }

            // 发送请求创建模板
            const templateId = `template-${Date.now()}`;
            const response = await fetch('/api/v1/rule-templates/create-from-model', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    model_id: modelId,
                    template_id: templateId,
                    name: name,
                    description: description,
                    category: category
                })
            });

            if (!response.ok) {
                throw new Error('从模型创建模板失败');
            }

            // 重新加载数据
            await loadData();

            // 隐藏模态框
            hideModal('create-template-modal');

            alert('模板创建成功');
            hideLoading();
            return;
        } else if (source === 'template') {
            // 从现有模板复制
            const sourceTemplateId = document.getElementById('source-template').value;
            if (!sourceTemplateId) {
                throw new Error('请选择源模板');
            }

            // 获取源模板
            const sourceTemplate = allTemplates.find(t => t.id === sourceTemplateId);
            if (sourceTemplate) {
                rules = [...sourceTemplate.rules];
            }
        }

        // 发送请求
        const response = await fetch('/api/v1/rule-templates', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                description: description,
                rules: rules,
                category: category
            })
        });

        if (!response.ok) {
            throw new Error('创建模板失败');
        }

        // 重新加载数据
        await loadData();

        // 隐藏模态框
        hideModal('create-template-modal');

        alert('模板创建成功');
        hideLoading();
    } catch (error) {
        console.error('创建模板失败:', error);
        alert('创建模板失败: ' + error.message);
        hideLoading();
    }
}

// 查看模板
function viewTemplate(templateId) {
    const template = allTemplates.find(t => t.id === templateId);
    if (!template) {
        alert('模板不存在');
        return;
    }

    // 创建模板详情内容
    let content = `
        <h3>模板详情: ${template.name}</h3>
        <p><strong>描述:</strong> ${template.description}</p>
        <p><strong>分类:</strong> ${template.category}</p>
        <p><strong>创建时间:</strong> ${new Date(template.created_at).toLocaleString()}</p>
        <p><strong>规则数量:</strong> ${template.rules.length}</p>

        <h4>规则列表:</h4>
        <ul>
    `;

    // 创建规则ID到规则的映射
    const rulesMap = {};
    allRules.forEach(rule => {
        rulesMap[rule.id] = rule;
    });

    // 添加规则详情
    template.rules.forEach(ruleInfo => {
        const rule = rulesMap[ruleInfo.rule_id];
        if (rule) {
            content += `
                <li>
                    <strong>${rule.name}</strong> (${rule.id})<br>
                    类型: ${rule.detection_type}, 严重程度: ${rule.severity}<br>
                    优先级: ${ruleInfo.priority}, 状态: ${ruleInfo.enabled ? '启用' : '禁用'}
                </li>
            `;
        } else {
            content += `<li>规则 ${ruleInfo.rule_id} (不存在)</li>`;
        }
    });

    content += '</ul>';

    // 显示模板详情
    alert(content);
}

// 编辑模板
async function editTemplate(templateId) {
    try {
        showLoading();

        const template = allTemplates.find(t => t.id === templateId);
        if (!template) {
            throw new Error('模板不存在');
        }

        // 打开编辑模板对话框
        document.getElementById('template-name').value = template.name;
        document.getElementById('template-description').value = template.description;
        document.getElementById('template-category').value = template.category;
        document.getElementById('template-source').value = 'empty';
        document.getElementById('source-model-group').style.display = 'none';
        document.getElementById('source-template-group').style.display = 'none';

        // 显示模态框
        showModal('create-template-modal');

        // 设置编辑模式
        document.getElementById('confirm-create-template-btn').onclick = async function() {
            try {
                showLoading();

                // 获取表单数据
                const name = document.getElementById('template-name').value.trim();
                const description = document.getElementById('template-description').value.trim();
                const category = document.getElementById('template-category').value;

                if (!name) {
                    throw new Error('请输入模板名称');
                }

                if (!description) {
                    throw new Error('请输入模板描述');
                }

                // 发送请求
                const response = await fetch(`/api/v1/rule-templates/${templateId}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        name: name,
                        description: description,
                        rules: template.rules,
                        category: category
                    })
                });

                if (!response.ok) {
                    throw new Error('更新模板失败');
                }

                // 重新加载数据
                await loadData();

                // 隐藏模态框
                hideModal('create-template-modal');

                alert('模板更新成功');
                hideLoading();

                // 恢复按钮事件
                document.getElementById('confirm-create-template-btn').onclick = createTemplate;
            } catch (error) {
                console.error('更新模板失败:', error);
                alert('更新模板失败: ' + error.message);
                hideLoading();
            }
        };

        hideLoading();
    } catch (error) {
        console.error('编辑模板失败:', error);
        alert('编辑模板失败: ' + error.message);
        hideLoading();
    }
}

// 删除模板
async function deleteTemplate(templateId) {
    try {
        if (!confirm(`确定要删除模板 ${templateId} 吗？`)) {
            return;
        }

        showLoading();

        // 发送请求
        const response = await fetch(`/api/v1/rule-templates/${templateId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('删除模板失败');
        }

        // 重新加载数据
        await loadData();

        alert('模板删除成功');
        hideLoading();
    } catch (error) {
        console.error('删除模板失败:', error);
        alert('删除模板失败: ' + error.message);
        hideLoading();
    }
}

// 过滤模型规则
function filterModelRules() {
    const searchText = document.getElementById('rules-search').value.toLowerCase();
    const typeFilter = document.getElementById('rules-type-filter').value;
    const statusFilter = document.getElementById('rules-status-filter').value;

    const rows = document.querySelectorAll('#model-config-rules-body tr');

    rows.forEach(row => {
        if (row.cells.length <= 1) return; // 跳过空行

        const ruleName = row.cells[2].textContent.toLowerCase();
        const ruleType = row.cells[3].textContent.toLowerCase();
        const ruleEnabled = row.querySelector('.rule-enabled-toggle').checked;

        // 检查搜索文本
        const matchesSearch = searchText === '' ||
                             ruleName.includes(searchText) ||
                             row.cells[1].textContent.toLowerCase().includes(searchText);

        // 检查类型过滤器
        const matchesType = typeFilter === '' || ruleType.includes(typeFilter);

        // 检查状态过滤器
        const matchesStatus = statusFilter === '' ||
                             (statusFilter === 'enabled' && ruleEnabled) ||
                             (statusFilter === 'disabled' && !ruleEnabled);

        // 显示或隐藏行
        if (matchesSearch && matchesType && matchesStatus) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

// 过滤可用规则
function filterAvailableRules() {
    const searchText = document.getElementById('available-rules-search').value.toLowerCase();
    const typeFilter = document.getElementById('available-rules-type-filter').value;

    const rows = document.querySelectorAll('#available-rules-body tr');

    rows.forEach(row => {
        if (row.cells.length <= 1) return; // 跳过空行

        const ruleName = row.cells[2].textContent.toLowerCase();
        const ruleType = row.cells[3].textContent.toLowerCase();

        // 检查搜索文本
        const matchesSearch = searchText === '' ||
                             ruleName.includes(searchText) ||
                             row.cells[1].textContent.toLowerCase().includes(searchText) ||
                             row.cells[5].textContent.toLowerCase().includes(searchText);

        // 检查类型过滤器
        const matchesType = typeFilter === '' || ruleType.includes(typeFilter);

        // 显示或隐藏行
        if (matchesSearch && matchesType) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}
