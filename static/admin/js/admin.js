/**
 * 管理控制台通用 JavaScript 函数
 */

// 显示提示消息
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert ${type}`;
    alertDiv.textContent = message;

    // 添加到页面顶部
    const mainContent = document.querySelector('.main-content');
    mainContent.insertBefore(alertDiv, mainContent.firstChild);

    // 5秒后自动消失
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// 显示加载中状态
function showLoading(container) {
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'loading';
    loadingDiv.innerHTML = '<div class="loading-spinner"></div>';

    container.innerHTML = '';
    container.appendChild(loadingDiv);
}

// 隐藏加载中状态
function hideLoading(container) {
    const loadingDiv = container.querySelector('.loading');
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

// 格式化日期时间
function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

// 根据严重程度获取对应的 badge 类名
function getSeverityBadgeClass(severity) {
    switch (severity.toLowerCase()) {
        case 'critical':
            return 'danger';
        case 'high':
            return 'danger';
        case 'medium':
            return 'warning';
        case 'low':
            return 'info';
        default:
            return 'info';
    }
}

// 根据严重程度获取对应的中文名称
function getSeverityName(severity) {
    switch (severity.toLowerCase()) {
        case 'critical':
            return '严重';
        case 'high':
            return '高';
        case 'medium':
            return '中';
        case 'low':
            return '低';
        default:
            return '未知';
    }
}

// 根据检测类型获取对应的中文名称
function getDetectionTypeName(type) {
    switch (type) {
        case 'prompt_injection':
            return '提示注入';
        case 'jailbreak':
            return '越狱尝试';
        case 'role_play':
            return '角色扮演';
        case 'sensitive_info':
            return '敏感信息';
        case 'harmful_content':
            return '有害内容';
        case 'compliance_violation':
            return '合规违规';
        case 'custom':
            return '自定义';
        default:
            return '未知';
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

// 初始化模态框关闭按钮
function initModalClose() {
    document.querySelectorAll('.modal-close').forEach(closeBtn => {
        closeBtn.addEventListener('click', function() {
            const modal = this.closest('.modal-backdrop');
            if (modal) {
                hideModal(modal.id);
            }
        });
    });

    // 点击模态框外部关闭
    document.querySelectorAll('.modal-backdrop').forEach(modal => {
        modal.addEventListener('click', function(event) {
            if (event.target === this) {
                hideModal(this.id);
            }
        });
    });
}

// 显示创建规则模态框
function showCreateRuleModal() {
    // 重置表单
    if (document.getElementById('rule-form')) {
        document.getElementById('rule-form').reset();
    }

    // 设置模态框标题
    if (document.getElementById('rule-modal-title')) {
        document.getElementById('rule-modal-title').textContent = '创建新规则';
    }

    // 清空规则ID
    if (document.getElementById('rule-id')) {
        document.getElementById('rule-id').value = '';
    }

    // 设置默认状态
    if (document.getElementById('block-status')) {
        document.getElementById('block-status').textContent = '启用';
    }

    if (document.getElementById('enabled-status')) {
        document.getElementById('enabled-status').textContent = '启用';
    }

    // 清空模式和关键词
    window.patterns = [];
    window.keywords = [];

    // 清空模式列表
    if (document.getElementById('pattern-list')) {
        document.getElementById('pattern-list').innerHTML = '';
    }

    // 清空关键词标签
    if (document.getElementById('keyword-tags')) {
        document.getElementById('keyword-tags').innerHTML = '';
    }

    // 显示模态框
    showModal('rule-modal');
}

// 文档加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 初始化模态框关闭按钮
    initModalClose();

    // 初始化全局变量
    window.patterns = [];
    window.keywords = [];
});
