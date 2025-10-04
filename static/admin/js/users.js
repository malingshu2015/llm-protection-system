// 用户管理页面JavaScript逻辑

// API基础URL
const API_BASE_URL = window.location.origin;

// 全局变量
let allUsers = [];
let currentUser = null;
let deleteUserId = null;

// 角色中文映射
const ROLE_NAMES = {
    'super_admin': '超级管理员',
    'admin': '管理员',
    'security_analyst': '安全分析师',
    'developer': '开发者',
    'viewer': '查看者'
};

// 角色徽章样式
const ROLE_BADGES = {
    'super_admin': 'badge-danger',
    'admin': 'badge-warning',
    'security_analyst': 'badge-primary',
    'developer': 'badge-success',
    'viewer': 'badge-secondary'
};

// 页面加载时初始化
window.addEventListener('DOMContentLoaded', async () => {
    await checkAuth();
    await loadCurrentUser();
    await loadUsers();
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

// 加载用户列表
async function loadUsers() {
    const token = localStorage.getItem('access_token');
    const tbody = document.getElementById('usersTableBody');

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/users`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error('获取用户列表失败');
        }

        allUsers = await response.json();
        displayUsers(allUsers);

    } catch (error) {
        console.error('加载用户列表失败:', error);
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; color: #FF3B30;">
                    <i class="fas fa-exclamation-circle"></i> 加载失败: ${error.message}
                </td>
            </tr>
        `;
    }
}

// 显示用户列表
function displayUsers(users) {
    const tbody = document.getElementById('usersTableBody');
    const userCount = document.getElementById('userCount');

    if (users.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; color: #6e6e73;">
                    <i class="fas fa-users"></i> 暂无用户
                </td>
            </tr>
        `;
        userCount.textContent = '0 个用户';
        return;
    }

    tbody.innerHTML = users.map(user => `
        <tr>
            <td><strong>${escapeHtml(user.username)}</strong></td>
            <td>${escapeHtml(user.email)}</td>
            <td>
                <span class="badge ${ROLE_BADGES[user.role]}">${ROLE_NAMES[user.role]}</span>
            </td>
            <td>
                <span class="badge ${user.is_active ? 'badge-success' : 'badge-secondary'}">
                    ${user.is_active ? '激活' : '未激活'}
                </span>
            </td>
            <td>${formatDateTime(user.created_at)}</td>
            <td>${user.last_login_at ? formatDateTime(user.last_login_at) : '<span class="text-muted">从未登录</span>'}</td>
            <td>
                <div class="action-buttons">
                    <button class="action-btn" onclick="viewUser('${user.id}')" title="查看详情">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="action-btn" onclick="editUser('${user.id}')" title="编辑">
                        <i class="fas fa-edit"></i>
                    </button>
                    ${currentUser && currentUser.id !== user.id ? `
                        <button class="action-btn danger" onclick="showDeleteConfirm('${user.id}', '${escapeHtml(user.username)}')" title="删除">
                            <i class="fas fa-trash"></i>
                        </button>
                    ` : ''}
                </div>
            </td>
        </tr>
    `).join('');

    userCount.textContent = `${users.length} 个用户`;
}

// 筛选用户
function filterUsers() {
    const searchText = document.getElementById('searchInput').value.toLowerCase();
    const roleFilter = document.getElementById('roleFilter').value;
    const statusFilter = document.getElementById('statusFilter').value;

    const filtered = allUsers.filter(user => {
        const matchSearch = !searchText ||
            user.username.toLowerCase().includes(searchText) ||
            user.email.toLowerCase().includes(searchText);

        const matchRole = !roleFilter || user.role === roleFilter;

        const matchStatus = !statusFilter ||
            (statusFilter === 'active' && user.is_active) ||
            (statusFilter === 'inactive' && !user.is_active);

        return matchSearch && matchRole && matchStatus;
    });

    displayUsers(filtered);
}

// 显示创建用户模态框
function showCreateUserModal() {
    const modal = document.getElementById('userModal');
    const form = document.getElementById('userForm');

    document.getElementById('modalTitle').textContent = '创建用户';
    document.getElementById('userId').value = '';
    form.reset();

    // 显示密码字段
    document.getElementById('passwordGroup').style.display = 'block';
    document.getElementById('password').required = true;

    modal.classList.add('show');
}

// 编辑用户
async function editUser(userId) {
    const token = localStorage.getItem('access_token');
    const modal = document.getElementById('userModal');

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/users/${userId}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error('获取用户信息失败');
        }

        const user = await response.json();

        document.getElementById('modalTitle').textContent = '编辑用户';
        document.getElementById('userId').value = user.id;
        document.getElementById('username').value = user.username;
        document.getElementById('email').value = user.email;
        document.getElementById('role').value = user.role;
        document.getElementById('isActive').checked = user.is_active;

        // 隐藏密码字段(编辑时不需要)
        document.getElementById('passwordGroup').style.display = 'none';
        document.getElementById('password').required = false;
        document.getElementById('password').value = '';

        modal.classList.add('show');

    } catch (error) {
        console.error('加载用户信息失败:', error);
        showToast('error', error.message);
    }
}

// 查看用户详情
async function viewUser(userId) {
    const token = localStorage.getItem('access_token');
    const modal = document.getElementById('userDetailModal');
    const content = document.getElementById('userDetailContent');

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/users/${userId}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error('获取用户信息失败');
        }

        const user = await response.json();

        content.innerHTML = `
            <div class="detail-grid">
                <div class="detail-item">
                    <div class="detail-label">用户ID</div>
                    <div class="detail-value">${user.id}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">用户名</div>
                    <div class="detail-value">${escapeHtml(user.username)}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">邮箱</div>
                    <div class="detail-value">${escapeHtml(user.email)}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">角色</div>
                    <div class="detail-value">
                        <span class="badge ${ROLE_BADGES[user.role]}">${ROLE_NAMES[user.role]}</span>
                    </div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">状态</div>
                    <div class="detail-value">
                        <span class="badge ${user.is_active ? 'badge-success' : 'badge-secondary'}">
                            ${user.is_active ? '激活' : '未激活'}
                        </span>
                    </div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">邮箱验证</div>
                    <div class="detail-value">
                        <span class="badge ${user.email_verified ? 'badge-success' : 'badge-warning'}">
                            ${user.email_verified ? '已验证' : '未验证'}
                        </span>
                    </div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">创建时间</div>
                    <div class="detail-value">${formatDateTime(user.created_at)}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">更新时间</div>
                    <div class="detail-value">${formatDateTime(user.updated_at)}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">最后登录</div>
                    <div class="detail-value">${user.last_login_at ? formatDateTime(user.last_login_at) : '从未登录'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">登录次数</div>
                    <div class="detail-value">${user.login_count || 0} 次</div>
                </div>
            </div>
        `;

        modal.classList.add('show');

    } catch (error) {
        console.error('加载用户详情失败:', error);
        showToast('error', error.message);
    }
}

// 处理用户表单提交
async function handleUserSubmit(event) {
    event.preventDefault();

    const token = localStorage.getItem('access_token');
    const userId = document.getElementById('userId').value;
    const isEdit = !!userId;

    const formData = {
        username: document.getElementById('username').value.trim(),
        email: document.getElementById('email').value.trim(),
        role: document.getElementById('role').value,
        is_active: document.getElementById('isActive').checked
    };

    // 创建用户时需要密码
    if (!isEdit) {
        formData.password = document.getElementById('password').value;
    }

    const submitBtn = event.target.querySelector('button[type="submit"]');
    setButtonLoading(submitBtn, true);

    try {
        const url = isEdit
            ? `${API_BASE_URL}/api/v1/users/${userId}`
            : `${API_BASE_URL}/api/v1/users`;

        const method = isEdit ? 'PUT' : 'POST';

        const response = await fetch(url, {
            method,
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || (isEdit ? '更新用户失败' : '创建用户失败'));
        }

        showToast('success', isEdit ? '用户更新成功' : '用户创建成功');
        closeUserModal();
        await loadUsers();

    } catch (error) {
        console.error('保存用户失败:', error);
        showToast('error', error.message);
    } finally {
        setButtonLoading(submitBtn, false);
    }
}

// 显示删除确认
function showDeleteConfirm(userId, username) {
    deleteUserId = userId;
    document.getElementById('deleteUsername').textContent = username;
    document.getElementById('deleteModal').classList.add('show');
}

// 确认删除
async function confirmDelete() {
    if (!deleteUserId) return;

    const token = localStorage.getItem('access_token');

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/users/${deleteUserId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || '删除用户失败');
        }

        showToast('success', '用户删除成功');
        closeDeleteModal();
        await loadUsers();

    } catch (error) {
        console.error('删除用户失败:', error);
        showToast('error', error.message);
    }
}

// 关闭模态框
function closeUserModal() {
    document.getElementById('userModal').classList.remove('show');
    document.getElementById('userForm').reset();
}

function closeUserDetailModal() {
    document.getElementById('userDetailModal').classList.remove('show');
}

function closeDeleteModal() {
    document.getElementById('deleteModal').classList.remove('show');
    deleteUserId = null;
}

// 切换密码可见性
function togglePasswordVisibility(inputId) {
    const input = document.getElementById(inputId);
    const icon = event.currentTarget.querySelector('i');

    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    }
}

// 退出登录
function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    window.location.href = '/static/admin/login.html';
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
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
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
