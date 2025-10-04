// API密钥管理页面JavaScript逻辑

// API基础URL
const API_BASE_URL = window.location.origin;

// 全局变量
let apiKeys = [];
let currentUser = null;
let deleteKeyId = null;

// 页面加载时初始化
window.addEventListener('DOMContentLoaded', async () => {
    await checkAuth();
    await loadCurrentUser();
    await loadApiKeys();
});

// 检查认证状态
async function checkAuth() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/static/admin/login.html';
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            localStorage.removeItem('user');
            window.location.href = '/static/admin/login.html';
        }
    } catch (error) {
        console.error('认证检查失败:', error);
        window.location.href = '/static/admin/login.html';
    }
}

// 加载当前用户信息
async function loadCurrentUser() {
    const token = localStorage.getItem('access_token');
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            currentUser = await response.json();
            document.getElementById('currentUser').innerHTML = `
                <i class="fas fa-user-circle"></i>
                <span>${currentUser.username}</span>
            `;
        }
    } catch (error) {
        console.error('加载用户信息失败:', error);
    }
}

// 加载API密钥列表
async function loadApiKeys() {
    const token = localStorage.getItem('access_token');
    const grid = document.getElementById('keysGrid');

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/api-keys`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error('获取API密钥列表失败');
        }

        apiKeys = await response.json();
        displayApiKeys(apiKeys);

    } catch (error) {
        console.error('加载API密钥失败:', error);
        grid.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-exclamation-circle"></i>
                <h3>加载失败</h3>
                <p>${error.message}</p>
            </div>
        `;
    }
}

// 显示API密钥列表
function displayApiKeys(keys) {
    const grid = document.getElementById('keysGrid');
    const keyCount = document.getElementById('keyCount');

    if (keys.length === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-key"></i>
                <h3>还没有API密钥</h3>
                <p>点击"创建密钥"按钮来创建您的第一个API密钥</p>
            </div>
        `;
        keyCount.textContent = '0 个密钥';
        return;
    }

    grid.innerHTML = keys.map(key => `
        <div class="key-card">
            <div class="key-card-header">
                <div class="key-card-title">
                    <h3>${escapeHtml(key.name)}</h3>
                    ${key.description ? `<p>${escapeHtml(key.description)}</p>` : ''}
                </div>
                <div class="key-card-status">
                    <span class="badge ${key.is_active ? 'badge-success' : 'badge-secondary'}">
                        ${key.is_active ? '激活' : '禁用'}
                    </span>
                </div>
            </div>

            <div class="key-prefix">${escapeHtml(key.key_prefix)}</div>

            <div class="key-meta">
                <div class="key-meta-item">
                    <span class="key-meta-label">使用次数</span>
                    <span class="key-meta-value">${key.usage_count || 0} 次</span>
                </div>
                <div class="key-meta-item">
                    <span class="key-meta-label">速率限制</span>
                    <span class="key-meta-value">${key.rate_limit || '-'}/小时</span>
                </div>
                <div class="key-meta-item">
                    <span class="key-meta-label">创建时间</span>
                    <span class="key-meta-value">${formatDate(key.created_at)}</span>
                </div>
                <div class="key-meta-item">
                    <span class="key-meta-label">过期时间</span>
                    <span class="key-meta-value ${isExpired(key.expires_at) ? 'text-danger' : ''}">
                        ${key.expires_at ? formatDate(key.expires_at) : '永不过期'}
                        ${isExpired(key.expires_at) ? ' (已过期)' : ''}
                    </span>
                </div>
            </div>

            ${key.scopes && key.scopes.length > 0 ? `
                <div class="key-scopes">
                    ${key.scopes.map(scope => `<span class="scope-tag">${escapeHtml(scope)}</span>`).join('')}
                </div>
            ` : ''}

            ${key.last_used_at ? `
                <div style="font-size: 13px; color: #6e6e73; margin-bottom: 16px;">
                    <i class="fas fa-clock"></i> 最后使用: ${formatDateTime(key.last_used_at)}
                </div>
            ` : ''}

            <div class="key-card-footer">
                <button class="btn btn-sm btn-secondary" onclick="regenerateKey('${key.id}', '${escapeHtml(key.name)}')">
                    <i class="fas fa-sync-alt"></i>
                    重新生成
                </button>
                <button class="btn btn-sm btn-danger" onclick="showDeleteKeyConfirm('${key.id}', '${escapeHtml(key.name)}')">
                    <i class="fas fa-trash"></i>
                    删除
                </button>
            </div>
        </div>
    `).join('');

    keyCount.textContent = `${keys.length} 个密钥`;
}

// 显示创建密钥模态框
function showCreateKeyModal() {
    const modal = document.getElementById('createKeyModal');
    const form = document.getElementById('createKeyForm');
    form.reset();
    modal.classList.add('show');
}

// 关闭创建密钥模态框
function closeCreateKeyModal() {
    document.getElementById('createKeyModal').classList.remove('show');
}

// 处理创建密钥
async function handleCreateKey(event) {
    event.preventDefault();

    const token = localStorage.getItem('access_token');
    const form = event.target;
    const formData = new FormData(form);

    // 获取选中的权限范围
    const scopes = Array.from(form.querySelectorAll('input[name="scope"]:checked'))
        .map(input => input.value);

    // 构建请求数据
    const keyData = {
        name: formData.get('name'),
        description: formData.get('description') || undefined,
        scopes: scopes,
        rate_limit: parseInt(formData.get('rate_limit')) || 1000,
        expires_days: formData.get('expires_days') ? parseInt(formData.get('expires_days')) : undefined
    };

    // 处理IP白名单
    const ipWhitelist = formData.get('ip_whitelist');
    if (ipWhitelist && ipWhitelist.trim()) {
        keyData.ip_whitelist = ipWhitelist.split(',').map(ip => ip.trim()).filter(ip => ip);
    }

    const submitBtn = form.querySelector('button[type="submit"]');
    setButtonLoading(submitBtn, true);

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/api-keys`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(keyData)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || '创建密钥失败');
        }

        closeCreateKeyModal();
        showNewKey(data.api_key, data.key_info);
        await loadApiKeys();

    } catch (error) {
        console.error('创建密钥失败:', error);
        showToast('error', error.message);
    } finally {
        setButtonLoading(submitBtn, false);
    }
}

// 显示新创建的密钥
function showNewKey(apiKey, keyInfo) {
    const modal = document.getElementById('showKeyModal');
    document.getElementById('newApiKey').textContent = apiKey;

    document.getElementById('newKeyInfo').innerHTML = `
        <div class="key-info-item">
            <span class="key-info-label">密钥名称</span>
            <span class="key-info-value">${escapeHtml(keyInfo.name)}</span>
        </div>
        <div class="key-info-item">
            <span class="key-info-label">密钥前缀</span>
            <span class="key-info-value">${escapeHtml(keyInfo.key_prefix)}</span>
        </div>
        <div class="key-info-item">
            <span class="key-info-label">速率限制</span>
            <span class="key-info-value">${keyInfo.rate_limit}/小时</span>
        </div>
        <div class="key-info-item">
            <span class="key-info-label">过期时间</span>
            <span class="key-info-value">${keyInfo.expires_at ? formatDate(keyInfo.expires_at) : '永不过期'}</span>
        </div>
    `;

    modal.classList.add('show');
}

// 关闭显示密钥模态框
function closeShowKeyModal() {
    document.getElementById('showKeyModal').classList.remove('show');
}

// 复制API密钥
function copyApiKey() {
    const apiKey = document.getElementById('newApiKey').textContent;
    navigator.clipboard.writeText(apiKey).then(() => {
        showToast('success', '密钥已复制到剪贴板');
    }).catch(err => {
        console.error('复制失败:', err);
        showToast('error', '复制失败');
    });
}

// 复制代码
function copyCode(button) {
    const codeBlock = button.previousElementSibling;
    const code = codeBlock.textContent;

    navigator.clipboard.writeText(code).then(() => {
        const originalHTML = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check"></i> 已复制';
        button.classList.add('copied');

        setTimeout(() => {
            button.innerHTML = originalHTML;
            button.classList.remove('copied');
        }, 2000);
    }).catch(err => {
        console.error('复制失败:', err);
        showToast('error', '复制失败');
    });
}

// 重新生成密钥
async function regenerateKey(keyId, keyName) {
    if (!confirm(`确定要重新生成密钥"${keyName}"吗?\n旧密钥将立即失效!`)) {
        return;
    }

    const token = localStorage.getItem('access_token');

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/api-keys/${keyId}/regenerate`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || '重新生成密钥失败');
        }

        showNewKey(data.api_key, data.key_info);
        await loadApiKeys();

    } catch (error) {
        console.error('重新生成密钥失败:', error);
        showToast('error', error.message);
    }
}

// 显示删除确认
function showDeleteKeyConfirm(keyId, keyName) {
    deleteKeyId = keyId;
    document.getElementById('deleteKeyName').textContent = keyName;
    document.getElementById('deleteKeyModal').classList.add('show');
}

// 关闭删除模态框
function closeDeleteKeyModal() {
    document.getElementById('deleteKeyModal').classList.remove('show');
    deleteKeyId = null;
}

// 确认删除密钥
async function confirmDeleteKey() {
    if (!deleteKeyId) return;

    const token = localStorage.getItem('access_token');

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/api-keys/${deleteKeyId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || '删除密钥失败');
        }

        showToast('success', '密钥删除成功');
        closeDeleteKeyModal();
        await loadApiKeys();

    } catch (error) {
        console.error('删除密钥失败:', error);
        showToast('error', error.message);
    }
}

// 退出登录
function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    window.location.href = '/static/admin/login.html';
}

// 工具函数

// 检查是否过期
function isExpired(expiresAt) {
    if (!expiresAt) return false;
    return new Date(expiresAt) < new Date();
}

// 格式化日期
function formatDate(dateString) {
    if (!dateString) return '-';

    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');

    return `${year}-${month}-${day}`;
}

// 格式化日期时间
function formatDateTime(dateString) {
    if (!dateString) return '-';

    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');

    return `${year}-${month}-${day} ${hours}:${minutes}`;
}

// HTML转义
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 设置按钮加载状态
function setButtonLoading(button, isLoading) {
    const btnText = button.querySelector('.btn-text');
    const btnLoader = button.querySelector('.btn-loader');

    if (isLoading) {
        btnText.style.display = 'none';
        btnLoader.style.display = 'inline-block';
        button.disabled = true;
    } else {
        btnText.style.display = 'inline';
        btnLoader.style.display = 'none';
        button.disabled = false;
    }
}

// 显示提示消息
function showToast(type, message) {
    const colors = {
        'success': '#34C759',
        'error': '#FF3B30',
        'warning': '#FF9500',
        'info': '#007AFF'
    };

    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${colors[type]};
        color: white;
        padding: 16px 24px;
        border-radius: 12px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
        z-index: 10000;
        animation: slideInRight 0.3s ease-out;
        max-width: 320px;
        font-size: 15px;
        font-weight: 500;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 3000);
}

// 点击模态框外部关闭
window.addEventListener('click', (event) => {
    if (event.target.classList.contains('modal')) {
        event.target.classList.remove('show');
    }
});

// 添加动画样式
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            opacity: 0;
            transform: translateX(100px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }

    @keyframes slideOutRight {
        from {
            opacity: 1;
            transform: translateX(0);
        }
        to {
            opacity: 0;
            transform: translateX(100px);
        }
    }
`;
document.head.appendChild(style);
