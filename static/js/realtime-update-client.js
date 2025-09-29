/**
 * 实时更新客户端 - 用于模型市场的实时同步
 */
class RealtimeUpdateClient {
    constructor(options = {}) {
        this.options = {
            serverUrl: window.location.origin.replace(/^http/, 'ws'),
            reconnectInterval: 3000,
            maxReconnectAttempts: 10,
            pollingFallback: true,
            pollingInterval: 10000,
            ...options
        };

        this.ws = null;
        this.reconnectAttempts = 0;
        this.isConnected = false;
        this.pendingRequests = new Map();
        this.eventHandlers = new Map();
        this.pollingTimer = null;
    }

    // 连接WebSocket服务器
    async connect() {
        try {
            const wsUrl = `${this.options.serverUrl}/ws/models/updates`;
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => this.handleOpen();
            this.ws.onmessage = (event) => this.handleMessage(event);
            this.ws.onclose = (event) => this.handleClose(event);
            this.ws.onerror = (error) => this.handleError(error);
            
            return new Promise((resolve, reject) => {
                this.connectionResolve = resolve;
                this.connectionReject = reject;
                setTimeout(() => reject(new Error('Connection timeout')), 5000);
            });
        } catch (error) {
            console.error('WebSocket connection failed:', error);
            this.fallbackToPolling();
            throw error;
        }
    }

    handleOpen() {
        console.log('WebSocket connected successfully');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        
        if (this.connectionResolve) {
            this.connectionResolve();
            this.connectionResolve = null;
            this.connectionReject = null;
        }

        // 发送认证信息（如果需要）
        this.send({
            type: 'auth',
            token: localStorage.getItem('auth_token')
        });

        // 订阅模型更新
        this.subscribeToModelUpdates();
    }

    handleMessage(event) {
        try {
            const data = JSON.parse(event.data);
            this.processMessage(data);
        } catch (error) {
            console.error('Failed to parse message:', error, event.data);
        }
    }

    handleClose(event) {
        console.log('WebSocket disconnected:', event.code, event.reason);
        this.isConnected = false;
        this.attemptReconnect();
    }

    handleError(error) {
        console.error('WebSocket error:', error);
        if (this.connectionReject) {
            this.connectionReject(error);
            this.connectionResolve = null;
            this.connectionReject = null;
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
            console.log('Max reconnection attempts reached, falling back to polling');
            this.fallbackToPolling();
            return;
        }

        this.reconnectAttempts++;
        const delay = Math.min(30000, this.options.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1));
        
        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
        
        setTimeout(() => {
            if (!this.isConnected) {
                this.connect().catch(() => this.attemptReconnect());
            }
        }, delay);
    }

    fallbackToPolling() {
        if (!this.options.pollingFallback) return;
        
        console.log('Falling back to polling mode');
        this.startPolling();
    }

    startPolling() {
        if (this.pollingTimer) clearInterval(this.pollingTimer);
        
        this.pollingTimer = setInterval(() => {
            this.checkForUpdates();
        }, this.options.pollingInterval);
    }

    stopPolling() {
        if (this.pollingTimer) {
            clearInterval(this.pollingTimer);
            this.pollingTimer = null;
        }
    }

    async checkForUpdates() {
        try {
            const response = await fetch('/api/models/updates', {
                headers: {
                    'Accept': 'application/json'
                }
            });
            
            if (response.ok) {
                const updates = await response.json();
                this.processUpdates(updates);
            }
        } catch (error) {
            console.error('Polling request failed:', error);
        }
    }

    processMessage(data) {
        switch (data.type) {
            case 'model_update':
                this.handleModelUpdate(data);
                break;
            case 'version_check':
                this.handleVersionCheck(data);
                break;
            case 'sync_complete':
                this.handleSyncComplete(data);
                break;
            case 'error':
                this.handleError(data);
                break;
            default:
                console.warn('Unknown message type:', data.type);
        }
    }

    handleModelUpdate(update) {
        console.log('Received model update:', update);
        
        // 触发模型更新事件
        this.emit('modelUpdate', update);
        
        // 如果当前在模型市场页面，刷新数据
        if (window.location.pathname.includes('/market')) {
            this.refreshMarketData();
        }
    }

    handleVersionCheck(data) {
        const { currentVersion, latestVersion, updateAvailable } = data;
        
        if (updateAvailable) {
            console.log(`Update available: ${currentVersion} -> ${latestVersion}`);
            this.emit('updateAvailable', { currentVersion, latestVersion });
        }
    }

    handleSyncComplete(data) {
        console.log('Sync completed:', data);
        this.emit('syncComplete', data);
    }

    refreshMarketData() {
        // 触发自定义事件或调用页面刷新函数
        if (typeof window.refreshModelMarket === 'function') {
            window.refreshModelMarket();
        } else {
            // 发送自定义事件
            const event = new CustomEvent('modelMarketRefresh');
            window.dispatchEvent(event);
        }
    }

    subscribeToModelUpdates() {
        this.send({
            type: 'subscribe',
            channel: 'model_updates'
        });
    }

    requestSync() {
        return this.sendWithResponse({
            type: 'sync_request',
            timestamp: Date.now()
        });
    }

    send(message) {
        if (!this.isConnected || !this.ws) {
            throw new Error('WebSocket not connected');
        }

        this.ws.send(JSON.stringify(message));
    }

    sendWithResponse(message, timeout = 10000) {
        return new Promise((resolve, reject) => {
            const requestId = this.generateRequestId();
            const request = { ...message, requestId };
            
            this.pendingRequests.set(requestId, { resolve, reject });
            
            setTimeout(() => {
                if (this.pendingRequests.has(requestId)) {
                    this.pendingRequests.delete(requestId);
                    reject(new Error('Request timeout'));
                }
            }, timeout);
            
            this.send(request);
        });
    }

    generateRequestId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }

    on(event, handler) {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, new Set());
        }
        this.eventHandlers.get(event).add(handler);
    }

    off(event, handler) {
        if (this.eventHandlers.has(event)) {
            this.eventHandlers.get(event).delete(handler);
        }
    }

    emit(event, data) {
        if (this.eventHandlers.has(event)) {
            this.eventHandlers.get(event).forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`Error in event handler for ${event}:`, error);
                }
            });
        }
    }

    disconnect() {
        this.stopPolling();
        
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        
        this.isConnected = false;
        this.pendingRequests.clear();
    }
}

// 全局实例
window.realtimeClient = new RealtimeUpdateClient();

// 自动连接
document.addEventListener('DOMContentLoaded', () => {
    if (window.location.pathname.includes('/market') || 
        window.location.pathname.includes('/models')) {
        window.realtimeClient.connect().catch(error => {
            console.log('WebSocket connection failed, using polling mode:', error);
        });
    }
});

// 导出模块
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RealtimeUpdateClient;
}