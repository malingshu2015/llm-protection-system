/**
 * 统一认证检查模块
 * 为所有管理页面提供认证验证、自动刷新和用户信息展示
 */

class AuthManager {
    constructor() {
        this.API_BASE_URL = window.location.origin;
        this.currentUser = null;
        this.refreshTimer = null;
    }

    /**
     * 初始化认证检查
     * @param {Object} options - 配置选项
     * @param {string} options.userElementId - 显示用户信息的元素ID
     * @param {boolean} options.autoRefresh - 是否自动刷新token (默认true)
     * @param {Function} options.onAuthSuccess - 认证成功回调
     * @param {Function} options.onAuthFailure - 认证失败回调
     * @param {string} options.requiredRole - 访问此页面所需的最低角色
     */
    async init(options = {}) {
        const {
            userElementId = 'currentUser',
            autoRefresh = true,
            onAuthSuccess = null,
            onAuthFailure = null,
            requiredRole = null
        } = options;

        // 检查认证状态
        const isAuthenticated = await this.checkAuth();

        if (!isAuthenticated) {
            if (onAuthFailure) {
                onAuthFailure();
            } else {
                this.redirectToLogin();
            }
            return false;
        }

        // 加载用户信息
        await this.loadCurrentUser(userElementId);

        // 检查页面访问权限
        if (requiredRole && !this.hasRole(requiredRole)) {
            this.showAccessDenied(requiredRole);
            return false;
        }

        // 设置自动刷新
        if (autoRefresh) {
            this.setupAutoRefresh();
        }

        if (onAuthSuccess) {
            onAuthSuccess(this.currentUser);
        }

        return true;
    }

    /**
     * 检查认证状态
     */
    async checkAuth() {
        const token = localStorage.getItem('access_token');
        if (!token) {
            return false;
        }

        try {
            const response = await fetch(`${this.API_BASE_URL}/api/v1/auth/me`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                // Token无效,尝试刷新
                const refreshed = await this.refreshToken();
                return refreshed;
            }

            return true;
        } catch (error) {
            console.error('认证检查失败:', error);
            return false;
        }
    }

    /**
     * 刷新访问令牌
     */
    async refreshToken() {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
            return false;
        }

        try {
            const response = await fetch(`${this.API_BASE_URL}/api/v1/auth/refresh`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ refresh_token: refreshToken })
            });

            if (!response.ok) {
                this.clearAuth();
                return false;
            }

            const data = await response.json();
            localStorage.setItem('access_token', data.access_token);

            if (data.refresh_token) {
                localStorage.setItem('refresh_token', data.refresh_token);
            }

            return true;
        } catch (error) {
            console.error('令牌刷新失败:', error);
            this.clearAuth();
            return false;
        }
    }

    /**
     * 设置自动刷新定时器
     * Access token有效期15分钟,在12分钟时自动刷新
     */
    setupAutoRefresh() {
        // 清除旧的定时器
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }

        // 每12分钟刷新一次
        this.refreshTimer = setInterval(async () => {
            const refreshed = await this.refreshToken();
            if (!refreshed) {
                console.warn('自动刷新失败,需要重新登录');
                this.redirectToLogin();
            }
        }, 12 * 60 * 1000); // 12分钟
    }

    /**
     * 加载当前用户信息
     */
    async loadCurrentUser(elementId) {
        const token = localStorage.getItem('access_token');

        try {
            const response = await fetch(`${this.API_BASE_URL}/api/v1/auth/me`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                this.currentUser = await response.json();

                // 更新用户信息显示
                if (elementId) {
                    const userElement = document.getElementById(elementId);
                    if (userElement) {
                        userElement.innerHTML = this.renderUserInfo();
                    }
                }

                return this.currentUser;
            }
        } catch (error) {
            console.error('加载用户信息失败:', error);
        }

        return null;
    }

    /**
     * 渲染用户信息HTML
     */
    renderUserInfo() {
        if (!this.currentUser) {
            return '';
        }

        const roleNames = {
            'super_admin': '超级管理员',
            'admin': '管理员',
            'security_analyst': '安全分析师',
            'developer': '开发者',
            'viewer': '查看者'
        };

        return `
            <div class="user-info">
                <i class="fas fa-user-circle"></i>
                <span class="user-name">${this.escapeHtml(this.currentUser.username)}</span>
                <span class="user-role">${roleNames[this.currentUser.role] || this.currentUser.role}</span>
                <button class="logout-btn" onclick="authManager.logout()" title="退出登录">
                    <i class="fas fa-sign-out-alt"></i>
                </button>
            </div>
        `;
    }

    /**
     * 检查用户角色权限
     * @param {string|string[]} requiredRole - 需要的角色(可以是数组)
     */
    hasRole(requiredRole) {
        if (!this.currentUser) {
            return false;
        }

        const roleHierarchy = {
            'viewer': 1,
            'developer': 2,
            'security_analyst': 3,
            'admin': 4,
            'super_admin': 5
        };

        const userLevel = roleHierarchy[this.currentUser.role] || 0;

        if (Array.isArray(requiredRole)) {
            return requiredRole.some(role => {
                const requiredLevel = roleHierarchy[role] || 0;
                return userLevel >= requiredLevel;
            });
        }

        const requiredLevel = roleHierarchy[requiredRole] || 0;
        return userLevel >= requiredLevel;
    }

    /**
     * 根据权限显示/隐藏元素
     * @param {string} selector - 元素选择器
     * @param {string|string[]} requiredRole - 需要的角色
     */
    showForRole(selector, requiredRole) {
        const elements = document.querySelectorAll(selector);
        const hasPermission = this.hasRole(requiredRole);

        elements.forEach(element => {
            element.style.display = hasPermission ? '' : 'none';
        });
    }

    /**
     * 退出登录
     */
    async logout() {
        const token = localStorage.getItem('access_token');

        try {
            // 调用后端退出接口
            await fetch(`${this.API_BASE_URL}/api/v1/auth/logout`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
        } catch (error) {
            console.error('退出登录失败:', error);
        }

        // 清除本地数据
        this.clearAuth();

        // 跳转到登录页
        this.redirectToLogin();
    }

    /**
     * 清除认证信息
     */
    clearAuth() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        this.currentUser = null;

        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    }

    /**
     * 跳转到登录页
     */
    redirectToLogin() {
        const currentPath = window.location.pathname;
        const returnUrl = encodeURIComponent(currentPath);
        window.location.href = `/static/admin/login.html?return=${returnUrl}`;
    }

    /**
     * 显示权限不足页面
     */
    showAccessDenied(requiredRole) {
        const roleNames = {
            'viewer': '查看者',
            'developer': '开发者',
            'security_analyst': '安全分析师',
            'admin': '管理员',
            'super_admin': '超级管理员'
        };

        const requiredRoleName = roleNames[requiredRole] || requiredRole;
        const userRoleName = roleNames[this.currentUser?.role] || this.currentUser?.role;

        // 创建权限不足提示页面
        document.body.innerHTML = `
            <div style="
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                margin: 0;
                padding: 20px;
            ">
                <div style="
                    background: white;
                    border-radius: 20px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    padding: 60px 80px;
                    text-align: center;
                    max-width: 600px;
                ">
                    <div style="
                        width: 100px;
                        height: 100px;
                        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                        border-radius: 50%;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        margin: 0 auto 30px;
                        box-shadow: 0 10px 30px rgba(245, 87, 108, 0.3);
                    ">
                        <svg width="50" height="50" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
                            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                            <path d="M12 8v4"></path>
                            <path d="M12 16h.01"></path>
                        </svg>
                    </div>

                    <h1 style="
                        font-size: 32px;
                        font-weight: 700;
                        color: #2d3748;
                        margin: 0 0 16px 0;
                    ">访问权限不足</h1>

                    <p style="
                        font-size: 16px;
                        color: #718096;
                        line-height: 1.6;
                        margin: 0 0 12px 0;
                    ">
                        您当前的角色是 <strong style="color: #4a5568;">${userRoleName}</strong>
                    </p>

                    <p style="
                        font-size: 16px;
                        color: #718096;
                        line-height: 1.6;
                        margin: 0 0 32px 0;
                    ">
                        此页面需要 <strong style="color: #e53e3e;">${requiredRoleName}</strong> 或更高权限才能访问
                    </p>

                    <div style="display: flex; gap: 16px; justify-content: center;">
                        <button onclick="window.history.back()" style="
                            padding: 12px 32px;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            color: white;
                            border: none;
                            border-radius: 10px;
                            font-size: 16px;
                            font-weight: 600;
                            cursor: pointer;
                            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
                            transition: all 0.3s ease;
                        " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 20px rgba(102, 126, 234, 0.5)'"
                           onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(102, 126, 234, 0.4)'">
                            返回上一页
                        </button>

                        <button onclick="window.location.href='/static/admin/monitor.html'" style="
                            padding: 12px 32px;
                            background: white;
                            color: #667eea;
                            border: 2px solid #667eea;
                            border-radius: 10px;
                            font-size: 16px;
                            font-weight: 600;
                            cursor: pointer;
                            transition: all 0.3s ease;
                        " onmouseover="this.style.background='#f7fafc'"
                           onmouseout="this.style.background='white'">
                            返回首页
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * HTML转义
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * 获取认证头
     */
    getAuthHeaders() {
        const token = localStorage.getItem('access_token');
        return {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        };
    }

    /**
     * 带认证的fetch封装
     */
    async authenticatedFetch(url, options = {}) {
        const headers = {
            ...this.getAuthHeaders(),
            ...options.headers
        };

        const response = await fetch(url, {
            ...options,
            headers
        });

        // 如果401,尝试刷新token后重试
        if (response.status === 401) {
            const refreshed = await this.refreshToken();
            if (refreshed) {
                // 重试请求
                const newHeaders = {
                    ...this.getAuthHeaders(),
                    ...options.headers
                };
                return fetch(url, {
                    ...options,
                    headers: newHeaders
                });
            } else {
                this.redirectToLogin();
                throw new Error('认证失败,请重新登录');
            }
        }

        return response;
    }
}

// 创建全局实例
const authManager = new AuthManager();

// 导出供其他模块使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AuthManager, authManager };
}
