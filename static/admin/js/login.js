// 登录页面JavaScript逻辑

// API基础URL
const API_BASE_URL = window.location.origin;

// 获取返回URL参数
const urlParams = new URLSearchParams(window.location.search);
const returnUrl = urlParams.get('return') || '/static/admin/index.html';

// DOM元素
const tabBtns = document.querySelectorAll('.tab-btn');
const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');
const loginError = document.getElementById('loginError');
const registerError = document.getElementById('registerError');
const togglePasswordBtns = document.querySelectorAll('.toggle-password');
const registerPassword = document.getElementById('registerPassword');

// 标签切换
tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;

        // 更新标签状态
        tabBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        // 显示对应表单
        if (tab === 'login') {
            loginForm.classList.add('active');
            registerForm.classList.remove('active');
            hideError(loginError);
        } else {
            registerForm.classList.add('active');
            loginForm.classList.remove('active');
            hideError(registerError);
        }
    });
});

// 密码显示/隐藏
togglePasswordBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        const targetId = btn.dataset.target;
        const input = document.getElementById(targetId);

        if (input.type === 'password') {
            input.type = 'text';
            btn.querySelector('.eye-icon').style.opacity = '0.5';
        } else {
            input.type = 'password';
            btn.querySelector('.eye-icon').style.opacity = '1';
        }
    });
});

// 密码强度检测
if (registerPassword) {
    registerPassword.addEventListener('input', (e) => {
        const password = e.target.value;
        const strengthBar = document.querySelector('.strength-bar');
        const strengthText = document.querySelector('.strength-text');

        if (!password) {
            strengthBar.className = 'strength-bar';
            strengthText.textContent = '';
            return;
        }

        const strength = calculatePasswordStrength(password);

        strengthBar.className = 'strength-bar';
        if (strength >= 80) {
            strengthBar.classList.add('strong');
            strengthText.textContent = '强';
            strengthText.style.color = 'var(--success-color)';
        } else if (strength >= 50) {
            strengthBar.classList.add('medium');
            strengthText.textContent = '中等';
            strengthText.style.color = 'var(--warning-color)';
        } else {
            strengthBar.classList.add('weak');
            strengthText.textContent = '弱';
            strengthText.style.color = 'var(--error-color)';
        }
    });
}

// 计算密码强度
function calculatePasswordStrength(password) {
    let strength = 0;

    // 长度
    if (password.length >= 8) strength += 20;
    if (password.length >= 12) strength += 10;
    if (password.length >= 16) strength += 10;

    // 包含小写字母
    if (/[a-z]/.test(password)) strength += 15;

    // 包含大写字母
    if (/[A-Z]/.test(password)) strength += 15;

    // 包含数字
    if (/[0-9]/.test(password)) strength += 15;

    // 包含特殊字符
    if (/[^a-zA-Z0-9]/.test(password)) strength += 15;

    return strength;
}

// 登录表单提交
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value;
    const rememberMe = document.getElementById('rememberMe').checked;

    // 验证
    if (!username || !password) {
        showError(loginError, '请填写用户名和密码');
        return;
    }

    // 显示加载状态
    const submitBtn = loginForm.querySelector('.submit-btn');
    setButtonLoading(submitBtn, true);
    hideError(loginError);

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username,
                password,
                remember_me: rememberMe
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || '登录失败');
        }

        // 保存 Token (临时)
        const accessToken = data.access_token;
        const refreshToken = data.refresh_token;

        // 检查用户是否启用了 2FA
        const twoFactorResponse = await fetch(`${API_BASE_URL}/api/v1/2fa/status`, {
            headers: {
                'Authorization': `Bearer ${accessToken}`
            }
        });

        if (twoFactorResponse.ok) {
            const twoFactorStatus = await twoFactorResponse.json();

            if (twoFactorStatus.is_enabled) {
                // 用户启用了 2FA,需要验证
                // 保存临时登录信息
                localStorage.setItem('pending_2fa_login', JSON.stringify({
                    username: username,
                    access_token: accessToken,
                    refresh_token: refreshToken,
                    tempToken: accessToken
                }));

                // 跳转到 2FA 验证页面
                window.location.href = '/static/admin/2fa-verify.html';
                return;
            }
        }

        // 没有启用 2FA,直接登录
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('refresh_token', refreshToken);
        localStorage.setItem('user', JSON.stringify(data.user));

        // 登录成功,跳转到管理页面或返回URL
        window.location.href = returnUrl;

    } catch (error) {
        showError(loginError, error.message);
        setButtonLoading(submitBtn, false);
    }
});

// 注册表单提交
registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const username = document.getElementById('registerUsername').value.trim();
    const email = document.getElementById('registerEmail').value.trim();
    const password = document.getElementById('registerPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;

    // 验证
    if (!username || !email || !password || !confirmPassword) {
        showError(registerError, '请填写所有必填字段');
        return;
    }

    if (username.length < 3 || username.length > 50) {
        showError(registerError, '用户名长度应为3-50个字符');
        return;
    }

    if (!/^[a-zA-Z0-9_-]+$/.test(username)) {
        showError(registerError, '用户名只能包含字母、数字、下划线和连字符');
        return;
    }

    if (password.length < 8) {
        showError(registerError, '密码长度至少为8个字符');
        return;
    }

    if (!/[a-z]/.test(password) || !/[A-Z]/.test(password) || !/[0-9]/.test(password)) {
        showError(registerError, '密码必须包含大写字母、小写字母和数字');
        return;
    }

    if (password !== confirmPassword) {
        showError(registerError, '两次输入的密码不一致');
        return;
    }

    // 显示加载状态
    const submitBtn = registerForm.querySelector('.submit-btn');
    setButtonLoading(submitBtn, true);
    hideError(registerError);

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username,
                email,
                password,
                role: 'viewer'  // 默认角色
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || '注册失败');
        }

        // 注册成功,自动切换到登录标签
        tabBtns[0].click();

        // 预填用户名
        document.getElementById('loginUsername').value = username;

        // 显示成功提示
        showSuccess('注册成功!请登录');

    } catch (error) {
        showError(registerError, error.message);
    } finally {
        setButtonLoading(submitBtn, false);
    }
});

// 显示错误信息
function showError(element, message) {
    element.textContent = message;
    element.classList.add('show');
}

// 隐藏错误信息
function hideError(element) {
    element.classList.remove('show');
}

// 显示成功提示
function showSuccess(message) {
    // 创建临时提示元素
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: var(--success-color);
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        z-index: 1000;
        animation: slideInRight 0.3s ease-out;
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

// 检查是否已登录
function checkAuth() {
    const token = localStorage.getItem('access_token');
    if (token) {
        // 验证Token是否有效
        fetch(`${API_BASE_URL}/api/v1/auth/me`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        })
        .then(response => {
            if (response.ok) {
                // Token有效,跳转到管理页面或返回URL
                window.location.href = returnUrl;
            } else {
                // Token无效,清除
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                localStorage.removeItem('user');
            }
        })
        .catch(() => {
            // 网络错误,清除Token
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            localStorage.removeItem('user');
        });
    }
}

// 页面加载时检查登录状态
window.addEventListener('DOMContentLoaded', checkAuth);

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

// OAuth 登录函数
async function loginWithOAuth(provider) {
    try {
        // 获取授权 URL
        const response = await fetch(`/api/v1/oauth/authorize/${provider}`);

        if (!response.ok) {
            throw new Error('获取授权链接失败');
        }

        const data = await response.json();

        // 重定向到 OAuth 提供商
        window.location.href = data.authorization_url;
    } catch (error) {
        showError('loginError', error.message);
    }
}

// 处理 OAuth 回调
function handleOAuthCallback() {
    const urlParams = new URLSearchParams(window.location.search);
    const accessToken = urlParams.get('access_token');
    const refreshToken = urlParams.get('refresh_token');
    const isNewUser = urlParams.get('is_new_user');
    const error = urlParams.get('error');

    if (error) {
        showError('loginError', `登录失败: ${error}`);
        // 清除 URL 参数
        window.history.replaceState({}, '', window.location.pathname);
        return;
    }

    if (accessToken && refreshToken) {
        // 保存令牌
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('refresh_token', refreshToken);

        // 清除 URL 参数
        window.history.replaceState({}, '', window.location.pathname);

        // 显示欢迎消息
        if (isNewUser === 'true') {
            alert('欢迎! 您的账户已创建并登录成功。');
        }

        // 重定向到首页
        window.location.href = '/static/index.html';
    }
}

// 页面加载时检查 OAuth 回调
handleOAuthCallback();

// WebAuthn 无密码登录 (使用专业库)
async function loginWithWebAuthn() {
    try {
        // 1. 请求认证挑战 (专业库返回标准 JSON)
        const challengeResponse = await fetch(`${API_BASE_URL}/api/v1/webauthn/authenticate/challenge`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });

        if (!challengeResponse.ok) throw new Error('获取认证挑战失败');

        const options = await challengeResponse.json();

        // 2. 转换 Base64URL 字段为 ArrayBuffer
        const publicKeyCredentialRequestOptions = {
            ...options,
            challenge: base64urlToArrayBuffer(options.challenge),
            allowCredentials: options.allowCredentials ? options.allowCredentials.map(cred => ({
                ...cred,
                id: base64urlToArrayBuffer(cred.id)
            })) : []
        };

        // 3. 调用 WebAuthn API
        const assertion = await navigator.credentials.get({
            publicKey: publicKeyCredentialRequestOptions
        });

        if (!assertion) throw new Error('认证被取消');

        // 4. 提取认证数据
        const credentialId = arrayBufferToBase64(assertion.rawId);
        const authenticatorData = arrayBufferToBase64(assertion.response.authenticatorData);
        const clientDataJSON = arrayBufferToBase64(assertion.response.clientDataJSON);
        const signature = arrayBufferToBase64(assertion.response.signature);
        const userHandle = assertion.response.userHandle ? arrayBufferToBase64(assertion.response.userHandle) : null;

        // 5. 发送到服务器验证 (专业库验证)
        const authResponse = await fetch(`${API_BASE_URL}/api/v1/webauthn/authenticate/verify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                credential_id: credentialId,
                authenticator_data: authenticatorData,
                client_data_json: clientDataJSON,
                signature: signature,
                user_handle: userHandle,
                challenge: options.challenge  // 传递原始 challenge
            })
        });

        if (!authResponse.ok) {
            const error = await authResponse.json();
            throw new Error(error.detail || '认证失败');
        }

        const data = await authResponse.json();

        // 保存令牌
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
        localStorage.setItem('user', JSON.stringify(data.user));

        // 登录成功
        window.location.href = returnUrl;

    } catch (error) {
        if (error.name === 'NotAllowedError') {
            showError('loginError', '认证被取消或超时');
        } else if (error.name === 'NotSupportedError') {
            showError('loginError', '您的浏览器不支持 WebAuthn');
        } else {
            showError('loginError', '登录失败: ' + error.message);
        }
    }
}

// 工具函数: ArrayBuffer 转 Base64URL
function arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

// 工具函数: Base64URL 转 ArrayBuffer
function base64urlToArrayBuffer(base64url) {
    // 补充 padding
    const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/');
    const padLength = (4 - (base64.length % 4)) % 4;
    const padded = base64 + '='.repeat(padLength);

    const binary = atob(padded);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
}

