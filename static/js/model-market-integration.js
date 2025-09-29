// 模型市场集成功能
class ModelMarketIntegration {
    constructor() {
        this.currentTab = 'local-models';
        this.marketPage = 1;
        this.pageSize = 12;
        this.init();
    }

    init() {
        this.setupTabNavigation();
        this.setupSearchAndFilters();
        this.loadInitialData();
        
        // 如果URL包含model-market参数，自动切换到模型市场标签页
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.has('model-market')) {
            console.log('检测到model-market参数，自动切换到模型市场');
            // 立即切换到模型市场标签页
            this.switchTab('model-market');
        }
    }

    // 设置标签页导航
    setupTabNavigation() {
        const tabs = document.querySelectorAll('.market-tab');
        if (!tabs.length) return;
        
        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                const tabId = e.currentTarget.getAttribute('data-tab');
                this.switchTab(tabId);
            });
        });
    }

    // 切换标签页
    switchTab(tabId) {
        // 更新活动标签
        const tabs = document.querySelectorAll('.market-tab');
        tabs.forEach(tab => {
            tab.classList.remove('active');
        });
        
        const activeTab = document.querySelector(`[data-tab="${tabId}"]`);
        if (activeTab) {
            activeTab.classList.add('active');
        }

        // 更新活动内容
        const contents = document.querySelectorAll('.market-content');
        contents.forEach(content => {
            content.classList.remove('active');
        });
        
        const activeContent = document.getElementById(`${tabId}-content`);
        if (activeContent) {
            activeContent.classList.add('active');
        }

        this.currentTab = tabId;

        // 加载对应内容
        if (tabId === 'model-market') {
            this.loadModelMarket();
        } else if (tabId === 'new-models') {
            this.loadNewModels();
        }
    }

    // 设置搜索和筛选
    setupSearchAndFilters() {
        // 只在模型市场内容区域中查找元素
        const marketContent = document.getElementById('model-market-content');
        if (!marketContent) return;
        
        const searchInput = marketContent.querySelector('#market-search-input');
        const frameworkFilter = marketContent.querySelector('#framework-filter');
        const domainFilter = marketContent.querySelector('#domain-filter');
        const sortBy = marketContent.querySelector('#sort-by');
        const sortOrder = marketContent.querySelector('#sort-order');

        const filters = [searchInput, frameworkFilter, domainFilter, sortBy, sortOrder].filter(Boolean);
        
        if (filters.length === 0) return;

        filters.forEach(filter => {
            if (filter) {
                filter.addEventListener('change', () => {
                    this.debouncedUpdateFilters();
                });
            }
        });

        if (searchInput) {
            searchInput.addEventListener('input', () => {
                this.debouncedUpdateFilters();
            });
        }
    }

    // 防抖更新筛选器
    debouncedUpdateFilters = this.debounce(() => {
        this.updateMarketFilters();
    }, 300);

    // 加载初始数据
    async loadInitialData() {
        await this.updateModelCounts();
    }

    // 加载模型市场
    async loadModelMarket() {
        const grid = document.getElementById('market-models-grid');
        grid.innerHTML = '<div class="loading">正在加载模型市场...</div>';

        try {
            const [stats, models] = await Promise.all([
                this.fetchMarketStats(),
                this.fetchMarketModels()
            ]);

            this.updateMarketStats(stats);
            this.displayMarketModels(models);
        } catch (error) {
            console.error('加载模型市场失败:', error);
            grid.innerHTML = '<div class="error">加载模型市场失败</div>';
        }
    }

    // 加载新模型
    async loadNewModels() {
        const grid = document.getElementById('new-models-grid');
        grid.innerHTML = '<div class="loading">正在获取最新推荐...</div>';

        try {
            const models = await this.fetchNewModels();
            this.displayNewModels(models);
        } catch (error) {
            console.error('加载新模型失败:', error);
            grid.innerHTML = '<div class="error">加载推荐失败</div>';
        }
    }

    // 获取市场统计
    async fetchMarketStats() {
        const response = await fetch('/api/v1/models/stats/summary');
        return await response.json();
    }

    // 获取市场模型
    async fetchMarketModels() {
        const params = this.buildQueryParams();
        const response = await fetch(`/api/v1/models?${params}`);
        return await response.json();
    }

    // 获取新模型
    async fetchNewModels() {
        const response = await fetch('/api/v1/models?sort_by=date&sort_order=desc&page=1&page_size=6');
        return await response.json();
    }

    // 构建查询参数
    buildQueryParams() {
        // 只在模型市场内容区域中查找元素
        const marketContent = document.getElementById('model-market-content');
        if (!marketContent) return new URLSearchParams();
        
        const frameworkFilter = marketContent.querySelector('#framework-filter');
        const domainFilter = marketContent.querySelector('#domain-filter');
        const sortBy = marketContent.querySelector('#sort-by');
        const sortOrder = marketContent.querySelector('#sort-order');
        const searchInput = marketContent.querySelector('#market-search-input');

        const params = new URLSearchParams({
            framework: frameworkFilter ? frameworkFilter.value : '',
            domain: domainFilter ? domainFilter.value : '',
            sort_by: sortBy ? sortBy.value : 'downloads',
            sort_order: sortOrder ? sortOrder.value : 'desc',
            page: this.marketPage,
            page_size: this.pageSize
        });

        if (searchInput) {
            const search = searchInput.value;
            if (search) {
                params.append('search', search);
            }
        }

        return params;
    }

    // 更新市场统计
    updateMarketStats(stats) {
        const marketContent = document.getElementById('model-market-content');
        if (!marketContent) return;
        
        const updateElement = (id, value) => {
            const element = marketContent.querySelector(`#${id}`);
            if (element) {
                element.textContent = value;
            }
        };

        updateElement('total-models', stats.total_models.toLocaleString());
        updateElement('total-downloads', stats.total_downloads.toLocaleString());
        updateElement('total-likes', stats.total_likes.toLocaleString());
        updateElement('new-this-week', stats.new_this_week || '0');
    }

    // 显示市场模型
    displayMarketModels(models) {
        const grid = document.getElementById('market-models-grid');
        
        if (!models || models.length === 0) {
            grid.innerHTML = '<div class="error">没有找到模型</div>';
            return;
        }

        const modelsHtml = models.map(model => this.createModelCard(model)).join('');
        grid.innerHTML = modelsHtml;
    }

    // 显示新模型
    displayNewModels(models) {
        const grid = document.getElementById('new-models-grid');
        const modelsHtml = models.map(model => this.createNewModelCard(model)).join('');
        grid.innerHTML = modelsHtml;
    }

    // 创建模型卡片
    createModelCard(model) {
        return `
            <div class="model-card">
                <div class="model-card-header">
                    <h3 class="model-card-name">${this.escapeHtml(model.name)}</h3>
                    <p class="model-card-description">${this.escapeHtml(model.description)}</p>
                    <div class="model-card-meta">
                        <span>作者: ${this.escapeHtml(model.author)}</span>
                        <span>许可: ${this.escapeHtml(model.license)}</span>
                    </div>
                </div>
                <div class="model-card-body">
                    <div class="model-card-stats">
                        <div class="model-stat">
                            <span class="model-stat-value">${model.downloads.toLocaleString()}</span>
                            <span class="model-stat-label">下载</span>
                        </div>
                        <div class="model-stat">
                            <span class="model-stat-value">${model.likes.toLocaleString()}</span>
                            <span class="model-stat-label">点赞</span>
                        </div>
                        <div class="model-stat">
                            <span class="model-stat-value">${model.community_rating || 0}/5</span>
                            <span class="model-stat-label">评分</span>
                        </div>
                    </div>
                    <div class="model-card-tags">
                        <span class="model-tag">${this.escapeHtml(model.framework)}</span>
                        <span class="model-tag">${this.escapeHtml(model.domain)}</span>
                        ${model.tags.map(tag => `<span class="model-tag">${this.escapeHtml(tag)}</span>`).join('')}
                    </div>
                    <div class="model-card-actions">
                        <button class="btn btn-primary" onclick="modelMarket.viewModelDetail('${model.id}')">查看详情</button>
                        <button class="btn btn-secondary" onclick="modelMarket.downloadModel('${model.id}')">下载</button>
                        <button class="btn btn-secondary" onclick="modelMarket.likeModel('${model.id}')">点赞</button>
                    </div>
                </div>
            </div>
        `;
    }

    // 创建新模型卡片
    createNewModelCard(model) {
        return `
            <div class="new-model-card">
                <span class="new-model-badge">NEW</span>
                <h4>${this.escapeHtml(model.name)}</h4>
                <p>${this.escapeHtml(model.description.substring(0, 100))}...</p>
                <div class="model-card-meta">
                    <span>${this.escapeHtml(model.framework)}</span>
                    <span>${this.escapeHtml(model.domain)}</span>
                </div>
                <button class="btn btn-primary" onclick="modelMarket.viewModelDetail('${model.id}')">查看详情</button>
            </div>
        `;
    }

    // 更新筛选器
    updateMarketFilters() {
        this.marketPage = 1;
        this.loadModelMarket();
    }

    // 更新模型计数
    async updateModelCounts() {
        try {
            // 获取本地模型数量
            const localResponse = await fetch('/api/v1/ollama/models', {
                headers: { 'Authorization': 'Bearer cherry-studio-key' }
            });
            const localData = await localResponse.json();
            const localCount = localData.data?.length || 0;
            
            const localCountElement = document.getElementById('local-models-count');
            if (localCountElement) {
                localCountElement.textContent = localCount;
            }

            // 获取市场模型数量
            const marketResponse = await fetch('/api/v1/models/stats/summary');
            const marketStats = await marketResponse.json();
            
            const marketCountElement = document.getElementById('market-models-count');
            if (marketCountElement) {
                marketCountElement.textContent = marketStats.total_models.toLocaleString();
            }
            
            const newModelsElement = document.getElementById('new-models-count');
            if (newModelsElement) {
                newModelsElement.textContent = marketStats.new_this_week || '0';
            }

        } catch (error) {
            console.error('更新模型计数失败:', error);
        }
    }

    // 查看模型详情
    async viewModelDetail(modelId) {
        try {
            const response = await fetch(`/api/v1/models/${modelId}`);
            const model = await response.json();
            this.showModelDetailModal(model);
        } catch (error) {
            console.error('获取模型详情失败:', error);
            alert('获取模型详情失败');
        }
    }

    // 下载模型
    async downloadModel(modelId) {
        try {
            const response = await fetch(`/api/v1/models/${modelId}/download`, {
                method: 'POST'
            });
            const result = await response.json();
            
            if (result.status === 'success') {
                alert('开始下载模型');
                this.loadModelMarket(); // 刷新市场
            } else {
                alert('下载失败');
            }
        } catch (error) {
            console.error('下载模型失败:', error);
            alert('下载模型失败');
        }
    }

    // 点赞模型
    async likeModel(modelId) {
        try {
            const response = await fetch(`/api/v1/models/${modelId}/like`, {
                method: 'POST'
            });
            const result = await response.json();
            
            if (result.status === 'success') {
                alert('点赞成功');
                this.loadModelMarket(); // 刷新市场
            } else {
                alert('点赞失败');
            }
        } catch (error) {
            console.error('点赞失败:', error);
            alert('点赞失败');
        }
    }

    // 显示模型详情模态框
    showModelDetailModal(model) {
        // 实现模态框显示逻辑
        const modalContent = `
            <h2>${this.escapeHtml(model.metadata.name)}</h2>
            <p><strong>描述:</strong> ${this.escapeHtml(model.metadata.description)}</p>
            <p><strong>作者:</strong> ${this.escapeHtml(model.metadata.author)}</p>
            <p><strong>许可证:</strong> ${this.escapeHtml(model.metadata.license)}</p>
            <p><strong>框架:</strong> ${this.escapeHtml(model.metadata.framework)}</p>
            <p><strong>领域:</strong> ${this.escapeHtml(model.metadata.domain)}</p>
            <p><strong>大小:</strong> ${this.escapeHtml(model.metadata.size)}</p>
            <p><strong>评分:</strong> ${model.community_rating}/5</p>
        `;
        
        // 这里可以集成现有的模态框组件
        alert(modalContent);
    }

    // 防抖函数
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // HTML转义
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// 全局实例
const modelMarket = new ModelMarketIntegration();

// 导出供其他脚本使用
window.modelMarket = modelMarket;