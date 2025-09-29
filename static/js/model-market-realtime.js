/**
 * 模型市场实时更新集成
 */

class ModelMarketRealtime {
    constructor() {
        this.realtimeClient = null;
        this.isConnected = false;
        this.updateCallbacks = new Set();
    }

    // 初始化实时更新
    async init() {
        try {
            // 创建实时客户端实例
            this.realtimeClient = new RealtimeUpdateClient({
                serverUrl: window.location.origin.replace(/^http/, 'ws'),
                reconnectInterval: 3000,
                maxReconnectAttempts: 5,
                pollingFallback: true,
                pollingInterval: 15000
            });

            // 注册事件处理器
            this.realtimeClient.on('modelUpdate', (update) => this.handleModelUpdate(update));
            this.realtimeClient.on('updateAvailable', (info) => this.handleUpdateAvailable(info));
            this.realtimeClient.on('syncComplete', (data) => this.handleSyncComplete(data));

            // 连接服务器
            await this.realtimeClient.connect();
            this.isConnected = true;
            
            console.log('模型市场实时更新已启用');
            this.showConnectionStatus('connected');

        } catch (error) {
            console.log('实时连接失败，使用轮询模式:', error);
            this.isConnected = false;
            this.showConnectionStatus('polling');
            
            // 启动轮询检查
            this.startPolling();
        }
    }

    // 处理模型更新
    handleModelUpdate(update) {
        console.log('收到模型更新:', update);
        
        const { action, model, version, timestamp } = update;
        
        // 显示更新通知
        this.showUpdateNotification(action, model, version);
        
        // 刷新模型数据
        this.refreshModelData();
        
        // 调用所有注册的回调函数
        this.updateCallbacks.forEach(callback => {
            try {
                callback(update);
            } catch (error) {
                console.error('Update callback error:', error);
            }
        });
    }

    // 处理版本更新可用
    handleUpdateAvailable(info) {
        console.log('有可用更新:', info);
        this.showUpdateAvailableNotification(info);
    }

    // 处理同步完成
    handleSyncComplete(data) {
        console.log('同步完成:', data);
        this.showSyncCompleteNotification(data);
    }

    // 显示更新通知
    showUpdateNotification(action, model, version) {
        const messages = {
            'add': `新模型添加: ${model} v${version}`,
            'update': `模型更新: ${model} v${version}`,
            'remove': `模型移除: ${model}`,
            'recommend': `推荐模型: ${model} v${version}`
        };

        const message = messages[action] || `模型变更: ${model} v${version}`;
        
        this.showNotification('模型更新', message, 'info');
    }

    // 显示更新可用通知
    showUpdateAvailableNotification(info) {
        const { currentVersion, latestVersion } = info;
        this.showNotification(
            '版本更新', 
            `新版本可用: ${currentVersion} → ${latestVersion}`, 
            'warning'
        );
    }

    // 显示同步完成通知
    showSyncCompleteNotification(data) {
        this.showNotification(
            '同步完成', 
            `已同步 ${data.updatedCount} 个模型`, 
            'success'
        );
    }

    // 显示通用通知
    showNotification(title, message, type = 'info') {
        // 检查是否支持Notification API
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(title, {
                body: message,
                icon: '/static/images/shield-icon.svg'
            });
        }
        
        // 在页面显示Toast通知
        this.showToast(message, type);
    }

    // 显示Toast通知
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `realtime-toast realtime-toast-${type}`;
        toast.innerHTML = `
            <div class="realtime-toast-content">
                <span class="realtime-toast-message">${message}</span>
                <button class="realtime-toast-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;

        // 添加样式
        if (!document.querySelector('#realtime-toast-style')) {
            const style = document.createElement('style');
            style.id = 'realtime-toast-style';
            style.textContent = `
                .realtime-toast {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    z-index: 10000;
                    min-width: 300px;
                    max-width: 400px;
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
                    border: 1px solid #e5e5e5;
                    animation: slideInRight 0.3s ease;
                }
                
                .realtime-toast-info { border-left: 4px solid #007AFF; }
                .realtime-toast-success { border-left: 4px solid #34C759; }
                .realtime-toast-warning { border-left: 4px solid #FF9500; }
                .realtime-toast-error { border-left: 4px solid #FF3B30; }
                
                .realtime-toast-content {
                    padding: 16px;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                }
                
                .realtime-toast-message {
                    font-size: 14px;
                    color: #333;
                    flex: 1;
                }
                
                .realtime-toast-close {
                    background: none;
                    border: none;
                    font-size: 18px;
                    color: #999;
                    cursor: pointer;
                    padding: 0;
                    margin-left: 12px;
                }
                
                @keyframes slideInRight {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
            `;
            document.head.appendChild(style);
        }

        document.body.appendChild(toast);

        // 自动移除
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 5000);
    }

    // 显示连接状态
    showConnectionStatus(status) {
        const statusElement = document.getElementById('realtime-status') || this.createStatusElement();
        
        const statusConfig = {
            'connected': { text: '实时连接', class: 'connected', icon: '🔗' },
            'polling': { text: '轮询模式', class: 'polling', icon: '🔄' },
            'disconnected': { text: '连接断开', class: 'disconnected', icon: '❌' }
        };
        
        const config = statusConfig[status] || statusConfig.disconnected;
        
        statusElement.className = `realtime-status realtime-status-${config.class}`;
        statusElement.innerHTML = `${config.icon} ${config.text}`;
    }

    // 创建状态元素
    createStatusElement() {
        const statusElement = document.createElement('div');
        statusElement.id = 'realtime-status';
        statusElement.className = 'realtime-status';
        
        // 添加样式
        if (!document.querySelector('#realtime-status-style')) {
            const style = document.createElement('style');
            style.id = 'realtime-status-style';
            style.textContent = `
                .realtime-status {
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    padding: 8px 16px;
                    border-radius: 20px;
                    font-size: 12px;
                    font-weight: 500;
                    z-index: 9999;
                    backdrop-filter: blur(10px);
                    border: 1px solid rgba(255,255,255,0.2);
                }
                
                .realtime-status-connected {
                    background: rgba(52, 199, 89, 0.1);
                    color: #34C759;
                    border-color: rgba(52, 199, 89, 0.3);
                }
                
                .realtime-status-polling {
                    background: rgba(255, 149, 0, 0.1);
                    color: #FF9500;
                    border-color: rgba(255, 149, 0, 0.3);
                }
                
                .realtime-status-disconnected {
                    background: rgba(255, 59, 48, 0.1);
                    color: #FF3B30;
                    border-color: rgba(255, 59, 48, 0.3);
                }
            `;
            document.head.appendChild(style);
        }
        
        document.body.appendChild(statusElement);
        return statusElement;
    }

    // 启动轮询检查
    startPolling() {
        // 每15秒检查一次更新
        setInterval(() => {
            this.checkForModelUpdates();
        }, 15000);
    }

    // 检查模型更新
    async checkForModelUpdates() {
        try {
            const response = await fetch('/api/models/check-updates', {
                headers: {
                    'Accept': 'application/json'
                }
            });
            
            if (response.ok) {
                const updates = await response.json();
                if (updates && updates.length > 0) {
                    updates.forEach(update => this.handleModelUpdate(update));
                }
            }
        } catch (error) {
            console.error('轮询检查失败:', error);
        }
    }

    // 刷新模型数据
    refreshModelData() {
        // 调用全局刷新函数（如果存在）
        if (typeof window.refreshModelMarket === 'function') {
            window.refreshModelMarket();
        }
        
        // 触发自定义事件
        const event = new CustomEvent('modelMarketRefresh');
        window.dispatchEvent(event);
        
        console.log('模型数据已刷新');
    }

    // 注册更新回调
    onUpdate(callback) {
        this.updateCallbacks.add(callback);
        return () => this.updateCallbacks.delete(callback);
    }

    // 手动请求同步
    async requestSync() {
        if (this.realtimeClient && this.isConnected) {
            return await this.realtimeClient.requestSync();
        } else {
            // 使用HTTP API进行同步
            const response = await fetch('/api/models/sync', { method: 'POST' });
            return await response.json();
        }
    }

    // 断开连接
    disconnect() {
        if (this.realtimeClient) {
            this.realtimeClient.disconnect();
        }
        this.isConnected = false;
        this.showConnectionStatus('disconnected');
    }
}

// 全局实例
window.modelMarketRealtime = new ModelMarketRealtime();

// 自动初始化
document.addEventListener('DOMContentLoaded', () => {
    // 只在模型市场页面启用实时更新
    if (window.location.pathname.includes('/market') || 
        window.location.pathname.includes('/models')) {
        
        // 请求通知权限
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
        
        // 初始化实时更新
        window.modelMarketRealtime.init().catch(console.error);
    }
});