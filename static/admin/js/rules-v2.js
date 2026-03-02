/**
 * 规则管理页面交互逻辑 (rules-v2.js)
 * 适配 monitor-modern.css 风格
 */

// 全局状态
let allRules = [];
let filteredRules = [];
let selectedRules = new Set();
let batchMode = false;

// 初始化
document.addEventListener('DOMContentLoaded', async function () {
    // 认证检查
    if (typeof authManager !== 'undefined') {
        await authManager.init({
            userElementId: 'currentUser',
            onAuthSuccess: () => {
                loadRules();
            }
        });
    } else {
        loadRules(); // 开发环境
    }

    // 绑定事件
    setupEventListeners();
});

function setupEventListeners() {
    // 搜索
    document.getElementById('search-input').addEventListener('input', (e) => {
        filterRulesUI('search', e.target.value);
    });

    // 筛选标签
    document.querySelectorAll('.filter-tab').forEach(tab => {
        tab.addEventListener('click', (e) => {
            document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
            e.target.classList.add('active');
            filterRulesUI('tag', e.target.dataset.filter);
        });
    });

    // 刷新按钮
    document.getElementById('refresh-btn').addEventListener('click', loadRules);

    // 批量操作按钮
    document.getElementById('batch-mode-btn').addEventListener('click', toggleBatchMode);

    // 批量操作栏按钮
    document.getElementById('batch-cancel').addEventListener('click', toggleBatchMode);
    document.getElementById('batch-delete').addEventListener('click', () => batchAction('delete'));
    document.getElementById('batch-enable').addEventListener('click', () => batchAction('enable'));
    document.getElementById('batch-disable').addEventListener('click', () => batchAction('disable'));
}

async function loadRules() {
    const grid = document.getElementById('rules-grid');
    grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-secondary);"><i class="fas fa-circle-notch fa-spin"></i> 正在加载规则...</div>';

    try {
        // 尝试从 API 获取
        // 注意：这里需要替换为真实的后端 API
        const res = await fetch('/api/v1/rules');

        if (res.ok) {
            const data = await res.json();
            allRules = data; // 假设返回直接是数组
        } else {
            console.warn("API failed, using mock data");
            allRules = generateMockRules();
        }

        // 如果后端返回结构不同，请在此处适配
        if (allRules.rules) allRules = allRules.rules;

        filteredRules = [...allRules];
        updateDashboard();
        renderRules();

    } catch (e) {
        console.error("Load rules failed", e);
        grid.innerHTML = `<div class="error-state"><h3>加载失败</h3><p>${e.message}</p></div>`;
        // Fallback for demo
        allRules = generateMockRules();
        filteredRules = [...allRules];
        updateDashboard();
        renderRules();
    }
}

function renderRules() {
    const grid = document.getElementById('rules-grid');
    const empty = document.getElementById('empty-state');

    if (filteredRules.length === 0) {
        grid.innerHTML = '';
        empty.style.display = 'block';
        return;
    }

    empty.style.display = 'none';

    grid.innerHTML = filteredRules.map(rule => {
        const isSelected = selectedRules.has(rule.id);
        const statusClass = rule.enabled ? 'success' : 'secondary';
        const statusText = rule.enabled ? '已启用' : '已禁用';

        return `
            <div class="rule-card content-grid-item ${batchMode ? 'batch-mode' : ''} ${isSelected ? 'selected' : ''}" 
                 onclick="handleCardClick('${rule.id}')">
                
                ${batchMode ? `<div class="rule-checkbox"><i class="fas fa-${isSelected ? 'check-square' : 'square'}" style="color: ${isSelected ? 'var(--primary-color)' : 'var(--text-secondary)'}"></i></div>` : ''}
                
                <div class="rule-card-header">
                    <div class="rule-card-title">
                        <span class="rule-name">${rule.name}</span>
                        <span class="rule-tag severity-${rule.severity}">${rule.severity.toUpperCase()}</span>
                    </div>
                    <div class="rule-meta">
                        <span class="rule-id">ID: ${rule.id}</span>
                        <span style="font-size: 12px; color: ${rule.enabled ? 'var(--success-color)' : 'var(--text-secondary)'}">
                            <i class="fas fa-circle" style="font-size: 8px;"></i> ${statusText}
                        </span>
                    </div>
                </div>
                
                <div class="rule-card-body">
                    <p class="rule-description" title="${rule.description || ''}">${rule.description || '无描述'}</p>
                    
                    <div class="rule-tags">
                        <span class="rule-tag type">${rule.detection_type || 'Custom'}</span>
                        ${(rule.keywords || []).slice(0, 3).map(k => `<span class="rule-tag">${k}</span>`).join('')}
                    </div>
                    
                    ${!batchMode ? `
                    <div class="rule-card-actions">
                        <button class="btn btn-secondary btn-sm" style="flex: 1;" onclick="event.stopPropagation(); editRule('${rule.id}')">编辑</button>
                        <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); deleteRule('${rule.id}')" style="color: var(--danger-color);"><i class="fas fa-trash"></i></button>
                    </div>
                    ` : ''}
                </div>
            </div>
        `;
    }).join('');
}

function updateDashboard() {
    document.getElementById('total-rules').innerText = allRules.length;
    document.getElementById('enabled-rules').innerText = allRules.filter(r => r.enabled).length;
    document.getElementById('critical-rules').innerText = allRules.filter(r => ['critical', 'high'].includes(r.severity)).length;

    const types = new Set(allRules.map(r => r.detection_type));
    document.getElementById('rule-types').innerText = types.size;
}

function filterRulesUI(type, value) {
    if (type === 'search') {
        const term = value.toLowerCase();
        filteredRules = allRules.filter(r =>
            r.name.toLowerCase().includes(term) ||
            r.description.toLowerCase().includes(term) ||
            r.id.toLowerCase().includes(term)
        );
    } else if (type === 'tag') {
        if (value === 'all') {
            filteredRules = [...allRules];
        } else if (value === 'enabled') {
            filteredRules = allRules.filter(r => r.enabled);
        } else if (value === 'disabled') {
            filteredRules = allRules.filter(r => !r.enabled);
        } else if (value === 'critical' || value === 'high') {
            filteredRules = allRules.filter(r => r.severity === value);
        } else {
            // By type
            filteredRules = allRules.filter(r => r.detection_type === value);
        }
    }
    renderRules();
}

// 批量操作逻辑
function toggleBatchMode() {
    batchMode = !batchMode;
    const batchBar = document.getElementById('batch-actions');
    const batchBtn = document.getElementById('batch-mode-btn');

    if (batchMode) {
        batchBar.style.display = 'flex'; // Flex to show
        batchBar.classList.add('active');
        batchBtn.classList.add('active'); // Style the trigger button
        document.getElementById('rules-grid').classList.add('batch-mode');
    } else {
        batchBar.style.display = 'none';
        batchBar.classList.remove('active');
        batchBtn.classList.remove('active');
        document.getElementById('rules-grid').classList.remove('batch-mode');
        selectedRules.clear();
        updateBatchUI();
    }
    renderRules();
}

function handleCardClick(id) {
    if (!batchMode) return;

    if (selectedRules.has(id)) {
        selectedRules.delete(id);
    } else {
        selectedRules.add(id);
    }
    updateBatchUI();
    renderRules(); // Re-render to show selection
}

function updateBatchUI() {
    document.getElementById('selected-count').innerText = selectedRules.size;
}

async function batchAction(action) {
    if (selectedRules.size === 0) return;

    if (!confirm(`确定对选中的 ${selectedRules.size} 个规则执行 ${action} 操作吗？`)) return;

    // Simulate API call
    console.log(`Executing batch ${action} on`, Array.from(selectedRules));

    // Optimistic update
    if (action === 'delete') {
        allRules = allRules.filter(r => !selectedRules.has(r.id));
    } else if (action === 'enable') {
        allRules.forEach(r => { if (selectedRules.has(r.id)) r.enabled = true; });
    } else if (action === 'disable') {
        allRules.forEach(r => { if (selectedRules.has(r.id)) r.enabled = false; });
    }

    filteredRules = [...allRules];
    selectedRules.clear();
    updateBatchUI();
    renderRules();
    updateDashboard();
    toggleBatchMode(); // Exit batch mode

    // Show notification (mock)
    alert('操作成功');
}

// 单个规则操作
function deleteRule(id) {
    if (confirm(`确定删除规则 ${id} 吗？`)) {
        allRules = allRules.filter(r => r.id !== id);
        filteredRules = [...allRules]; // Reset filter
        renderRules();
        updateDashboard();
    }
}

function editRule(id) {
    const rule = allRules.find(r => r.id === id);
    if (!rule) { alert('规则不存在'); return; }

    // 构建模态框 HTML
    const existing = document.getElementById('edit-rule-modal');
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.id = 'edit-rule-modal';
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:9999;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px)';
    modal.innerHTML = `
        <div style="background:var(--bg-card);border-radius:12px;width:90%;max-width:640px;max-height:90vh;overflow-y:auto;padding:32px;box-shadow:var(--shadow-md);">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;">
                <h2 style="margin:0;font-size:1.25rem;font-weight:700;">编辑规则 <code style="font-size:1rem;color:var(--accent-color);">${rule.id}</code></h2>
                <button onclick="document.getElementById('edit-rule-modal').remove()" style="background:none;border:none;font-size:24px;cursor:pointer;color:var(--text-secondary);">&times;</button>
            </div>
            <div style="display:flex;flex-direction:column;gap:16px;">
                <div>
                    <label style="display:block;font-weight:600;margin-bottom:6px;">规则名称</label>
                    <input id="edit-rule-name" type="text" value="${rule.name || ''}" class="select-modern" style="width:100%;cursor:text;">
                </div>
                <div>
                    <label style="display:block;font-weight:600;margin-bottom:6px;">描述</label>
                    <textarea id="edit-rule-desc" rows="3" class="select-modern" style="width:100%;cursor:text;resize:vertical;">${rule.description || ''}</textarea>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                    <div>
                        <label style="display:block;font-weight:600;margin-bottom:6px;">严重程度</label>
                        <select id="edit-rule-severity" class="select-modern" style="width:100%;">
                            <option value="low" ${rule.severity === 'low' ? 'selected' : ''}>低 (Low)</option>
                            <option value="medium" ${rule.severity === 'medium' ? 'selected' : ''}>中 (Medium)</option>
                            <option value="high" ${rule.severity === 'high' ? 'selected' : ''}>高 (High)</option>
                            <option value="critical" ${rule.severity === 'critical' ? 'selected' : ''}>严重 (Critical)</option>
                        </select>
                    </div>
                    <div>
                        <label style="display:block;font-weight:600;margin-bottom:6px;">状态</label>
                        <select id="edit-rule-enabled" class="select-modern" style="width:100%;">
                            <option value="true" ${rule.enabled ? 'selected' : ''}>启用</option>
                            <option value="false" ${!rule.enabled ? 'selected' : ''}>禁用</option>
                        </select>
                    </div>
                </div>
                <div>
                    <label style="display:block;font-weight:600;margin-bottom:6px;">关键词 (每行一个)</label>
                    <textarea id="edit-rule-keywords" rows="4" class="select-modern" style="width:100%;cursor:text;resize:vertical;font-family:monospace;">${(rule.keywords || []).join('\n')}</textarea>
                </div>
                <div>
                    <label style="display:block;font-weight:600;margin-bottom:6px;">正则模式 (每行一个)</label>
                    <textarea id="edit-rule-patterns" rows="4" class="select-modern" style="width:100%;cursor:text;resize:vertical;font-family:monospace;">${(rule.patterns || []).join('\n')}</textarea>
                </div>
            </div>
            <div style="display:flex;justify-content:flex-end;gap:12px;margin-top:24px;">
                <button onclick="document.getElementById('edit-rule-modal').remove()" class="btn btn-secondary">取消</button>
                <button onclick="saveEditedRule('${rule.id}')" class="btn btn-primary" style="background:var(--accent-color);color:white;border:none;padding:8px 20px;border-radius:8px;cursor:pointer;font-weight:600;">保存修改</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

async function saveEditedRule(id) {
    const name = document.getElementById('edit-rule-name').value.trim();
    const description = document.getElementById('edit-rule-desc').value.trim();
    const severity = document.getElementById('edit-rule-severity').value;
    const enabled = document.getElementById('edit-rule-enabled').value === 'true';
    const keywords = document.getElementById('edit-rule-keywords').value.split('\n').filter(k => k.trim());
    const patterns = document.getElementById('edit-rule-patterns').value.split('\n').filter(p => p.trim());

    if (!name) { showNotification('输入错误', '规则名称不能为空', 'warning'); return; }

    try {
        const res = await fetch(`/api/v1/rules/${encodeURIComponent(id)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description, severity, enabled, keywords, patterns })
        });

        if (res.ok) {
            // 本地更新
            const idx = allRules.findIndex(r => r.id === id);
            if (idx !== -1) Object.assign(allRules[idx], { name, description, severity, enabled, keywords, patterns });
            filteredRules = [...allRules];
            renderRules();
            updateDashboard();
            document.getElementById('edit-rule-modal').remove();
            showNotification('成功', `规则 ${id} 已更新`, 'success');
        } else {
            const err = await res.json().catch(() => ({ detail: '请求失败' }));
            showNotification('保存失败', err.detail || '后端返回错误', 'error');
        }
    } catch (e) {
        showNotification('网络错误', e.message, 'error');
    }
}

// 向导管理
let currentWizardStep = 1;

function openCreateRuleWizard() {
    const wizard = document.getElementById('rule-wizard');
    if (wizard) {
        resetWizard();
        wizard.classList.add('active');
    } else {
        showNotification('错误', '向导组件未加载', 'error');
    }
}

function closeRuleWizard() {
    const wizard = document.getElementById('rule-wizard');
    if (wizard) wizard.classList.remove('active');
}

function resetWizard() {
    currentWizardStep = 1;
    document.getElementById('wizard-rule-name').value = '';
    document.getElementById('wizard-rule-description').value = '';
    document.getElementById('wizard-rule-keywords').value = '';
    document.getElementById('wizard-rule-patterns').value = '';
    updateWizardUI();
}

function changeWizardStep(delta) {
    const newStep = currentWizardStep + delta;
    if (newStep < 1 || newStep > 4) return;

    // 验证
    if (delta > 0 && !validateStep(currentWizardStep)) return;

    currentWizardStep = newStep;
    if (currentWizardStep === 4) generatePreview();
    updateWizardUI();
}

function validateStep(step) {
    if (step === 1) {
        if (!document.getElementById('wizard-rule-name').value.trim()) {
            showNotification('输入错误', '请输入规则名称', 'warning');
            return false;
        }
    }
    return true;
}

function updateWizardUI() {
    // 更新步骤指示
    document.querySelectorAll('.wizard-step').forEach(s => {
        const sNum = parseInt(s.dataset.step);
        s.classList.toggle('active', sNum === currentWizardStep);
        s.classList.toggle('completed', sNum < currentWizardStep);
    });

    // 更新内容显示
    document.querySelectorAll('.wizard-step-content').forEach(c => {
        c.classList.toggle('active', parseInt(c.dataset.step) === currentWizardStep);
    });

    // 更新进度条
    document.getElementById('wizard-progress').style.width = `${(currentWizardStep / 4) * 100}%`;

    // 更新按钮
    document.getElementById('wizard-prev').style.display = currentWizardStep > 1 ? 'block' : 'none';
    document.getElementById('wizard-next').style.display = currentWizardStep < 4 ? 'block' : 'none';
    document.getElementById('wizard-save').style.display = currentWizardStep === 4 ? 'block' : 'none';
}

function generatePreview() {
    const name = document.getElementById('wizard-rule-name').value;
    const type = document.getElementById('wizard-rule-type').value;
    const severity = document.getElementById('wizard-rule-severity').value;

    const preview = document.getElementById('wizard-preview');
    preview.innerHTML = `
        <div class="rule-card" style="margin: 0; box-shadow: none; border: 1px solid var(--border-color);">
            <div class="rule-card-header">
                <div class="rule-card-title">
                    <span class="rule-name">${name}</span>
                    <span class="rule-tag severity-${severity}">${severity.toUpperCase()}</span>
                </div>
            </div>
            <div class="rule-card-body">
                <p class="rule-description">${document.getElementById('wizard-rule-description').value || '无描述'}</p>
                <div class="rule-tags">
                    <span class="rule-tag type">${type}</span>
                </div>
            </div>
        </div>
        <div style="margin-top: 1rem; font-size: 13px; color: var(--text-secondary);">
            请确认以上信息无误后点击保存。
        </div>
    `;
}

async function saveNewRule() {
    const ruleData = {
        id: 'RULE-' + Math.floor(Math.random() * 1000).toString().padStart(3, '0'),
        name: document.getElementById('wizard-rule-name').value,
        description: document.getElementById('wizard-rule-description').value,
        detection_type: document.getElementById('wizard-rule-type').value,
        severity: document.getElementById('wizard-rule-severity').value,
        enabled: document.getElementById('wizard-rule-enabled').checked,
        keywords: document.getElementById('wizard-rule-keywords').value.split('\n').filter(k => k.trim()),
        patterns: document.getElementById('wizard-rule-patterns').value.split('\n').filter(p => p.trim()),
        priority: parseInt(document.getElementById('wizard-rule-priority').value) || 100
    };

    // 模拟保存
    allRules.unshift(ruleData);
    filteredRules = [...allRules];
    renderRules();
    updateDashboard();
    closeRuleWizard();
    showNotification('成功', '新规则已创建', 'success');
}

// 通知系统
function showNotification(title, message, type = 'info') {
    const container = document.getElementById('notification-container');
    if (!container) return;

    const id = 'notif-' + Date.now();
    const notification = document.createElement('div');
    notification.id = id;
    notification.className = `notification ${type} show`;

    let icon = 'info-circle';
    if (type === 'success') icon = 'check-circle';
    if (type === 'warning') icon = 'exclamation-triangle';
    if (type === 'error') icon = 'times-circle';

    notification.innerHTML = `
        <div class="notification-icon"><i class="fas fa-${icon}"></i></div>
        <div class="notification-content">
            <div class="notification-title">${title}</div>
            <div class="notification-message">${message}</div>
        </div>
        <button class="notification-close" onclick="this.parentElement.remove()">&times;</button>
        <div class="notification-progress" id="${id}-progress" style="width: 100%"></div>
    `;

    container.appendChild(notification);

    // 自动移除
    setTimeout(() => {
        notification.classList.add('hide');
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// Mock Data
function generateMockRules() {
    return [
        { id: 'PI-001', name: '通用 Prompt 注入防护', description: '检测常见的提示注入攻击模式，如 "ignore previous instructions"', severity: 'critical', enabled: true, detection_type: 'prompt_injection', keywords: ['ignore', 'system'] },
        { id: 'JB-002', name: 'DAN 模式检测', description: '检测尝试通过角色扮演绕过限制的 "Do Anything Now" 模式', severity: 'high', enabled: true, detection_type: 'jailbreak', keywords: ['DAN', 'unfiltered'] },
        { id: 'SI-003', name: 'API 密钥泄露', description: '阻止输出中包含常见的 API 密钥格式', severity: 'critical', enabled: true, detection_type: 'sensitive_info', keywords: ['sk-', 'key'] },
        { id: 'HC-004', name: '暴力内容过滤', description: '过滤涉及过度暴力的内容描述', severity: 'medium', enabled: false, detection_type: 'harmful_content', keywords: ['kill', 'weapon'] },
        { id: 'PI-005', name: '系统指令保护', description: '防止用户尝试修改系统预设指令', severity: 'high', enabled: true, detection_type: 'prompt_injection', keywords: ['system prompt'] },
    ];
}
