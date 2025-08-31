/**
 * 智能配置向导组件
 * 提供多步骤的模型安全配置流程
 */

class ModelConfigWizard {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 4;
        this.wizardData = {
            selectedModel: null,
            category: null,
            template: null,
            customRules: [],
            tags: []
        };
        this.templates = [];
        this.models = [];
        
        this.init();
    }

    async init() {
        try {
            await this.loadTemplates();
            await this.loadModels();
            this.bindEvents();
        } catch (error) {
            console.error('初始化配置向导失败:', error);
        }
    }

    async loadTemplates() {
        try {
            const response = await fetch('/api/v1/enhanced-models/templates');
            if (response.ok) {
                const rawTemplates = await response.json();
                // 增强模板数据
                this.templates = rawTemplates.map(template => ({
                    ...template,
                    icon: this.getTemplateIcon(template.security_level),
                    risk_score: this.calculateRiskScore(template.security_level, template.enabled_rules),
                    use_cases: this.getUseCases(template.security_level)
                }));
            }
        } catch (error) {
            console.error('加载模板失败:', error);
            this.templates = this.getDefaultTemplates();
        }
    }

    getTemplateIcon(securityLevel) {
        const icons = {
            'strict': '🛡️',
            'balanced': '⚖️',
            'relaxed': '🔓'
        };
        return icons[securityLevel] || '⚙️';
    }

    calculateRiskScore(securityLevel, enabledRules) {
        const baseScores = {
            'strict': 90,
            'balanced': 70,
            'relaxed': 40
        };
        const baseScore = baseScores[securityLevel] || 50;
        const ruleBonus = (enabledRules?.length || 0) * 2;
        return Math.min(100, baseScore + ruleBonus);
    }

    getUseCases(securityLevel) {
        const useCases = {
            'strict': ['生产环境', '对外服务', '高敏感度应用'],
            'balanced': ['内部工具', '一般业务', '开发测试'],
            'relaxed': ['开发环境', '实验项目', '原型验证']
        };
        return useCases[securityLevel] || ['通用用途'];
    }

    async loadModels() {
        try {
            const response = await fetch('/v1/models', {
                headers: {
                    'Authorization': 'Bearer cherry-studio-key'
                }
            });
            if (response.ok) {
                const data = await response.json();
                console.log('加载的模型数据:', data);
                
                // 兼容OpenAI格式和Ollama格式
                this.models = data.data || data.models || [];
                
                // 如果是OpenAI格式，转换为内部格式
                if (data.data) {
                    this.models = data.data.map(model => ({
                        model: model.id,
                        name: model.id,
                        size: 0, // 占位值，实际大小需要从其他API获取
                        modified_at: new Date(model.created * 1000).toISOString(),
                        details: {
                            family: model.owned_by || 'unknown'
                        }
                    }));
                }
                
                console.log('转换后的模型列表:', this.models);
            } else {
                console.error('加载模型失败:', response.status, response.statusText);
            }
        } catch (error) {
            console.error('加载模型失败:', error);
            this.models = [];
        }
    }

    getDefaultTemplates() {
        return [
            {
                id: 'strict-production',
                name: '严格生产模式',
                description: '适用于生产环境的高安全级别配置，启用所有安全检测规则',
                security_level: 'strict',
                enabled_rules: ['hc-001', 'hc-002', 'hc-003', 'hc-004', 'hc-005', 'hc-011', 'pi-001', 'ji-001'],
                icon: '🛡️',
                risk_score: 90,
                use_cases: ['生产环境', '对外服务', '高敏感度应用']
            },
            {
                id: 'balanced-general',
                name: '平衡通用模式',
                description: '推荐用于一般用途的平衡配置，兼顾安全性和可用性',
                security_level: 'balanced',
                enabled_rules: ['hc-001', 'hc-003', 'hc-004', 'hc-011', 'pi-001'],
                icon: '⚖️',
                risk_score: 70,
                use_cases: ['内部工具', '一般业务', '开发测试']
            },
            {
                id: 'relaxed-development',
                name: '宽松开发模式',
                description: '适用于开发测试的宽松配置，减少不必要的限制',
                security_level: 'relaxed',
                enabled_rules: ['hc-004', 'hc-011'],
                icon: '🔓',
                risk_score: 40,
                use_cases: ['开发环境', '实验项目', '原型验证']
            }
        ];
    }

    bindEvents() {
        // 绑定向导控制事件
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-wizard-action]')) {
                const action = e.target.dataset.wizardAction;
                this.handleWizardAction(action, e.target);
            }
        });

        // 绑定表单变化事件
        document.addEventListener('change', (e) => {
            if (e.target.matches('[data-wizard-field]')) {
                this.handleFieldChange(e.target);
            }
        });

        // 绑定选项卡点击事件 - 修复版本
        document.addEventListener('click', (e) => {
            const optionCard = e.target.closest('.wizard-option-card');
            if (optionCard) {
                this.handleOptionSelect(optionCard);
            }
        });
    }

    handleWizardAction(action, element) {
        switch (action) {
            case 'open':
                this.open();
                break;
            case 'close':
                this.close();
                break;
            case 'next':
                this.nextStep();
                break;
            case 'prev':
                this.previousStep();
                break;
            case 'apply':
                this.applyConfiguration();
                break;
            case 'reset':
                this.reset();
                break;
        }
    }

    handleFieldChange(field) {
        const fieldName = field.dataset.wizardField;
        const value = field.type === 'checkbox' ? field.checked : field.value;
        
        if (fieldName.includes('.')) {
            const [parent, child] = fieldName.split('.');
            if (!this.wizardData[parent]) this.wizardData[parent] = {};
            this.wizardData[parent][child] = value;
        } else {
            this.wizardData[fieldName] = value;
        }

        this.updateStepValidation();
    }

    handleOptionSelect(card) {
        const container = card.parentElement;
        const stepType = container.dataset.stepType;
        const value = card.dataset.value;

        console.log('选择选项:', { stepType, value });

        if (!stepType || !value) {
            console.warn('选项卡片缺少必要的数据属性');
            return;
        }

        // 清除同组其他选中状态
        container.querySelectorAll('.wizard-option-card').forEach(c => 
            c.classList.remove('selected')
        );
        
        // 设置当前选中
        card.classList.add('selected');
        
        // 更新数据
        this.wizardData[stepType] = value;
        console.log('更新向导数据:', this.wizardData);
        
        // 更新步骤验证状态
        this.updateStepValidation();

        // 自动进入下一步（可选）
        if (this.shouldAutoAdvance(stepType)) {
            console.log('自动进入下一步');
            setTimeout(() => this.nextStep(), 500);
        }
    }

    shouldAutoAdvance(stepType) {
        // 只有选择使用场景时才自动进入下一步，模型选择需要用户手动点击下一步
        return ['category'].includes(stepType);
    }

    async open() {
        this.reset();
        const overlay = document.getElementById('config-wizard');
        if (overlay) {
            overlay.classList.add('active');
            
            // 显示加载状态
            const contentContainer = document.getElementById('wizard-content');
            if (contentContainer) {
                contentContainer.innerHTML = `
                    <div class="wizard-step-content">
                        <div style="text-align: center; padding: 40px;">
                            <div class="loading-spinner" style="margin: 0 auto 16px auto;"></div>
                            <p>正在加载模型和配置信息...</p>
                        </div>
                    </div>
                `;
            }
            
            try {
                // 重新加载数据
                await Promise.all([
                    this.loadTemplates(),
                    this.loadModels()
                ]);
                
                // 渲染第一步
                this.renderCurrentStep();
            } catch (error) {
                console.error('初始化向导失败:', error);
                if (contentContainer) {
                    contentContainer.innerHTML = `
                        <div class="wizard-step-content">
                            <div style="text-align: center; padding: 40px;">
                                <i class="fas fa-exclamation-triangle" style="font-size: 48px; color: #FF3B30; margin-bottom: 16px;"></i>
                                <h4>初始化失败</h4>
                                <p>无法加载配置向导，请检查网络连接或刷新页面重试。</p>
                                <button class="btn btn-primary" onclick="window.location.reload()">
                                    <i class="fas fa-sync-alt"></i> 刷新页面
                                </button>
                            </div>
                        </div>
                    `;
                }
            }
        }
    }

    close() {
        const overlay = document.getElementById('config-wizard');
        if (overlay) {
            overlay.classList.remove('active');
        }
    }

    reset() {
        this.currentStep = 1;
        this.wizardData = {
            selectedModel: null,
            category: null,
            template: null,
            customRules: [],
            tags: []
        };
    }

    nextStep() {
        if (!this.validateCurrentStep()) {
            this.showStepError();
            return;
        }

        if (this.currentStep < this.totalSteps) {
            this.currentStep++;
            this.renderCurrentStep();
        } else {
            this.applyConfiguration();
        }
    }

    previousStep() {
        if (this.currentStep > 1) {
            this.currentStep--;
            this.renderCurrentStep();
        }
    }

    validateCurrentStep() {
        switch (this.currentStep) {
            case 1:
                return !!this.wizardData.selectedModel;
            case 2:
                return !!this.wizardData.category;
            case 3:
                return !!this.wizardData.template;
            case 4:
                return true; // 总结步骤总是有效
            default:
                return false;
        }
    }

    updateStepValidation() {
        const nextBtn = document.getElementById('wizard-next');
        const isValid = this.validateCurrentStep();
        
        console.log('验证当前步骤:', { 
            currentStep: this.currentStep, 
            isValid, 
            wizardData: this.wizardData 
        });
        
        if (nextBtn) {
            nextBtn.disabled = !isValid;
            nextBtn.classList.toggle('disabled', !isValid);
            
            // 视觉反馈
            if (isValid) {
                nextBtn.style.opacity = '1';
                nextBtn.style.cursor = 'pointer';
            } else {
                nextBtn.style.opacity = '0.6';
                nextBtn.style.cursor = 'not-allowed';
            }
        }
    }

    showStepError() {
        const errorMessages = {
            1: '请选择一个模型',
            2: '请选择使用场景',
            3: '请选择安全策略模板'
        };

        const message = errorMessages[this.currentStep] || '请完成当前步骤';
        this.showNotification(message, 'error');
    }

    renderCurrentStep() {
        this.updateStepIndicators();
        this.updateButtons();
        this.renderStepContent();
        this.updateStepValidation();
        
        // 确保底部按钮可见 - 调试用
        setTimeout(() => {
            const footer = document.querySelector('.wizard-footer');
            const nextBtn = document.getElementById('wizard-next');
            if (footer && nextBtn) {
                console.log('向导底部状态:', {
                    footerVisible: footer.offsetHeight > 0,
                    nextBtnVisible: nextBtn.offsetHeight > 0,
                    footerHeight: footer.offsetHeight,
                    nextBtnHeight: nextBtn.offsetHeight
                });
            }
        }, 100);
    }

    updateStepIndicators() {
        document.querySelectorAll('.wizard-step').forEach((step, index) => {
            const stepNumber = index + 1;
            step.classList.toggle('active', stepNumber === this.currentStep);
            step.classList.toggle('completed', stepNumber < this.currentStep);
        });
    }

    updateButtons() {
        const prevBtn = document.getElementById('wizard-prev');
        const nextBtn = document.getElementById('wizard-next');

        console.log('更新按钮状态:', { currentStep: this.currentStep, prevBtn: !!prevBtn, nextBtn: !!nextBtn });

        if (prevBtn) {
            prevBtn.style.display = this.currentStep === 1 ? 'none' : 'inline-flex';
        }

        if (nextBtn) {
            // 确保按钮可见
            nextBtn.style.display = 'inline-flex';
            
            const isLastStep = this.currentStep === this.totalSteps;
            nextBtn.innerHTML = isLastStep 
                ? '<i class="fas fa-check"></i> 完成配置'
                : '下一步 <i class="fas fa-arrow-right"></i>';
            nextBtn.dataset.wizardAction = isLastStep ? 'apply' : 'next';
            
            // 初始化按钮状态
            const isValid = this.validateCurrentStep();
            nextBtn.disabled = !isValid;
            nextBtn.classList.toggle('disabled', !isValid);
            
            console.log('下一步按钮状态:', { isValid, disabled: nextBtn.disabled });
        }
    }

    renderStepContent() {
        const contentContainer = document.getElementById('wizard-content');
        if (!contentContainer) return;

        const stepContent = this.getStepContent(this.currentStep);
        contentContainer.innerHTML = stepContent;

        // 恢复已选择的值
        this.restoreStepValues();
    }

    getStepContent(step) {
        switch (step) {
            case 1:
                return this.renderModelSelectionStep();
            case 2:
                return this.renderCategorySelectionStep();
            case 3:
                return this.renderTemplateSelectionStep();
            case 4:
                return this.renderSummaryStep();
            default:
                return '<div>未知步骤</div>';
        }
    }

    renderModelSelectionStep() {
        if (!this.models || this.models.length === 0) {
            console.warn('没有可用的模型数据');
            return `
                <div class="wizard-step-content">
                    <h3 class="wizard-step-title">选择要配置的模型</h3>
                    <p class="wizard-step-description">从已安装的模型中选择一个进行安全配置</p>
                    
                    <div class="empty-message">
                        <div style="text-align: center; padding: 40px;">
                            <i class="fas fa-exclamation-triangle" style="font-size: 48px; color: #FF9500; margin-bottom: 16px;"></i>
                            <h4>没有找到已安装的模型</h4>
                            <p>请确保Ollama服务正在运行并且已安装模型。</p>
                            <button class="btn btn-primary" onclick="window.location.reload()">
                                <i class="fas fa-sync-alt"></i> 重新加载
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }

        const modelOptions = this.models.map(model => {
            const sizeText = this.formatSize(model.size);
            const dateText = new Date(model.modified_at).toLocaleDateString();
            
            return `
                <div class="wizard-option-card" data-value="${model.model}">
                    <div class="wizard-option-header">
                        <div class="wizard-option-icon">
                            <i class="fas fa-brain"></i>
                        </div>
                        <div class="wizard-option-info">
                            <div class="wizard-option-title">${model.model}</div>
                            <div class="wizard-option-meta">
                                ${model.size > 0 ? `<span><i class="fas fa-hdd"></i> ${sizeText}</span>` : ''}
                                <span><i class="fas fa-calendar"></i> ${dateText}</span>
                            </div>
                        </div>
                    </div>
                    <div class="wizard-option-description">
                        ${model.details?.family ? `模型家族: ${model.details.family}` : ''}
                        ${model.details?.quantization_level ? `<br>量化级别: ${model.details.quantization_level}` : ''}
                    </div>
                </div>
            `;
        }).join('');

        return `
            <div class="wizard-step-content">
                <h3 class="wizard-step-title">选择要配置的模型</h3>
                <p class="wizard-step-description">从已安装的模型中选择一个进行安全配置</p>
                
                <div class="wizard-options-container" data-step-type="selectedModel">
                    ${modelOptions}
                </div>
                
                <div style="margin-top: 16px; padding: 12px; background: rgba(0, 122, 255, 0.05); border-radius: 8px; border-left: 4px solid #007AFF;">
                    <p style="margin: 0; font-size: 14px; color: #007AFF;">
                        <i class="fas fa-info-circle"></i> 
                        找到 ${this.models.length} 个可配置的模型
                    </p>
                </div>
            </div>
        `;
    }

    renderCategorySelectionStep() {
        const categories = [
            {
                value: 'production',
                icon: '🏢',
                title: '生产环境',
                description: '对外提供服务，需要最高安全级别',
                features: ['最严格的安全检测', '完整的日志记录', '实时监控告警']
            },
            {
                value: 'testing',
                icon: '🧪',
                title: '测试环境',
                description: '内部测试使用，平衡安全性和便利性',
                features: ['适度的安全检测', '详细的测试日志', '灵活的配置选项']
            },
            {
                value: 'development',
                icon: '💻',
                title: '开发环境',
                description: '开发调试使用，较少的限制',
                features: ['基础安全检测', '开发友好配置', '快速迭代支持']
            },
            {
                value: 'research',
                icon: '🔬',
                title: '研究用途',
                description: '学术研究和实验，特殊配置',
                features: ['研究场景优化', '实验数据保护', '学术合规支持']
            }
        ];

        const categoryOptions = categories.map(category => `
            <div class="wizard-option-card" data-value="${category.value}">
                <div class="wizard-option-icon-large">${category.icon}</div>
                <div class="wizard-option-title">${category.title}</div>
                <div class="wizard-option-description">${category.description}</div>
                <div class="wizard-option-features">
                    ${category.features.map(feature => `<span class="feature-tag">${feature}</span>`).join('')}
                </div>
            </div>
        `).join('');

        return `
            <div class="wizard-step-content">
                <h3 class="wizard-step-title">选择使用场景</h3>
                <p class="wizard-step-description">根据模型的使用场景，我们将为您推荐合适的安全策略</p>
                
                <div class="wizard-options-grid" data-step-type="category">
                    ${categoryOptions}
                </div>
            </div>
        `;
    }

    renderTemplateSelectionStep() {
        const recommendedTemplate = this.getRecommendedTemplate();
        
        const templateOptions = this.templates.map(template => {
            const isRecommended = template.id === recommendedTemplate;
            
            return `
                <div class="wizard-option-card ${isRecommended ? 'recommended' : ''}" data-value="${template.id}">
                    ${isRecommended ? '<div class="recommended-badge">推荐</div>' : ''}
                    <div class="wizard-option-icon-large">${template.icon}</div>
                    <div class="wizard-option-title">${template.name}</div>
                    <div class="wizard-option-description">${template.description}</div>
                    <div class="wizard-option-stats">
                        <div class="stat-item">
                            <span class="stat-label">安全评分</span>
                            <span class="stat-value">${template.risk_score}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">规则数量</span>
                            <span class="stat-value">${template.enabled_rules.length}</span>
                        </div>
                    </div>
                    <div class="wizard-option-use-cases">
                        <strong>适用场景：</strong>
                        ${template.use_cases.map(useCase => `<span class="use-case-tag">${useCase}</span>`).join('')}
                    </div>
                </div>
            `;
        }).join('');

        return `
            <div class="wizard-step-content">
                <h3 class="wizard-step-title">选择安全策略模板</h3>
                <p class="wizard-step-description">根据您的使用场景，我们为您推荐了最适合的安全策略</p>
                
                <div class="wizard-options-grid" data-step-type="template">
                    ${templateOptions}
                </div>
                
                <div class="wizard-advanced-options">
                    <details>
                        <summary>高级选项</summary>
                        <div class="advanced-options-content">
                            <div class="form-group">
                                <label class="form-label">自定义标签</label>
                                <input type="text" class="form-control" data-wizard-field="customTags" 
                                       placeholder="输入标签，用逗号分隔">
                                <div class="form-help">为模型添加自定义标签，便于管理和分类</div>
                            </div>
                        </div>
                    </details>
                </div>
            </div>
        `;
    }

    renderSummaryStep() {
        const selectedModel = this.models.find(m => m.model === this.wizardData.selectedModel);
        const selectedTemplate = this.templates.find(t => t.id === this.wizardData.template);
        const categoryName = this.getCategoryName(this.wizardData.category);

        return `
            <div class="wizard-step-content summary-step">
                <div class="summary-icon">
                    <i class="fas fa-check-circle"></i>
                </div>
                <h3 class="wizard-step-title">配置确认</h3>
                <p class="wizard-step-description">请确认以下配置信息，点击完成配置开始应用设置</p>
                
                <div class="configuration-summary">
                    <div class="summary-section">
                        <h4><i class="fas fa-brain"></i> 目标模型</h4>
                        <div class="summary-item">
                            <span class="item-label">模型名称</span>
                            <span class="item-value">${selectedModel?.model || 'Unknown'}</span>
                        </div>
                        <div class="summary-item">
                            <span class="item-label">模型大小</span>
                            <span class="item-value">${this.formatSize(selectedModel?.size)}</span>
                        </div>
                    </div>
                    
                    <div class="summary-section">
                        <h4><i class="fas fa-tag"></i> 使用场景</h4>
                        <div class="summary-item">
                            <span class="item-label">环境类型</span>
                            <span class="item-value">${categoryName}</span>
                        </div>
                    </div>
                    
                    <div class="summary-section">
                        <h4><i class="fas fa-shield-alt"></i> 安全策略</h4>
                        <div class="summary-item">
                            <span class="item-label">策略模板</span>
                            <span class="item-value">${selectedTemplate?.name || 'Unknown'}</span>
                        </div>
                        <div class="summary-item">
                            <span class="item-label">安全级别</span>
                            <span class="item-value">${this.getSecurityLevelName(selectedTemplate?.security_level)}</span>
                        </div>
                        <div class="summary-item">
                            <span class="item-label">启用规则</span>
                            <span class="item-value">${selectedTemplate?.enabled_rules.length || 0} 条</span>
                        </div>
                    </div>
                </div>
                
                <div class="configuration-preview">
                    <h4>预期效果</h4>
                    <ul class="preview-list">
                        <li><i class="fas fa-check text-success"></i> 安全评分将达到 ${selectedTemplate?.risk_score || 0} 分</li>
                        <li><i class="fas fa-check text-success"></i> 启用 ${selectedTemplate?.enabled_rules.length || 0} 项安全检测规则</li>
                        <li><i class="fas fa-check text-success"></i> 自动应用 ${categoryName} 环境优化配置</li>
                        <li><i class="fas fa-check text-success"></i> 开启实时安全监控和日志记录</li>
                    </ul>
                </div>
            </div>
        `;
    }

    restoreStepValues() {
        // 恢复当前步骤已选择的值
        if (this.currentStep === 1 && this.wizardData.selectedModel) {
            const selected = document.querySelector(`[data-value="${this.wizardData.selectedModel}"]`);
            if (selected) selected.classList.add('selected');
        }
        
        if (this.currentStep === 2 && this.wizardData.category) {
            const selected = document.querySelector(`[data-value="${this.wizardData.category}"]`);
            if (selected) selected.classList.add('selected');
        }
        
        if (this.currentStep === 3 && this.wizardData.template) {
            const selected = document.querySelector(`[data-value="${this.wizardData.template}"]`);
            if (selected) selected.classList.add('selected');
        }
    }

    getRecommendedTemplate() {
        const categoryTemplateMap = {
            'production': 'strict-production',
            'testing': 'balanced-general',
            'development': 'relaxed-development',
            'research': 'balanced-general'
        };
        
        return categoryTemplateMap[this.wizardData.category] || 'balanced-general';
    }

    getCategoryName(category) {
        const names = {
            production: '生产环境',
            testing: '测试环境',
            development: '开发环境',
            research: '研究用途'
        };
        return names[category] || '未知';
    }

    getSecurityLevelName(level) {
        const names = {
            strict: '严格模式',
            balanced: '平衡模式',
            relaxed: '宽松模式'
        };
        return names[level] || '未知';
    }

    formatSize(bytes) {
        if (!bytes) return '未知';
        const mb = bytes / (1024 * 1024);
        return mb > 1024 ? `${(mb / 1024).toFixed(2)} GB` : `${mb.toFixed(2)} MB`;
    }

    async applyConfiguration() {
        const applyBtn = document.getElementById('wizard-next');
        const originalBtnText = applyBtn.innerHTML;
        
        try {
            // 更新按钮状态
            applyBtn.disabled = true;
            applyBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 正在应用配置...';
            
            // 构建配置请求
            const configRequest = {
                model_names: [this.wizardData.selectedModel],
                template_id: this.wizardData.template,
                category: this.wizardData.category,
                tags: this.parseCustomTags()
            };

            console.log('发送配置请求:', configRequest);

            // 发送批量配置请求
            const response = await fetch('/api/v1/enhanced-models/batch-config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(configRequest)
            });

            const result = await response.json();
            console.log('配置结果:', result);

            if (!response.ok) {
                throw new Error(result.detail || result.message || '配置应用失败');
            }
            
            // 显示成功消息
            this.showNotification(`模型 ${this.wizardData.selectedModel} 配置已成功应用！`, 'success');
            
            // 延迟关闭，让用户看到成功消息
            setTimeout(() => {
                this.close();
                
                // 触发页面刷新事件
                window.dispatchEvent(new CustomEvent('modelConfigurationApplied', {
                    detail: { modelName: this.wizardData.selectedModel, result }
                }));
            }, 1500);
            
        } catch (error) {
            console.error('应用配置失败:', error);
            this.showNotification('配置应用失败: ' + error.message, 'error');
            
            // 恢复按钮状态
            applyBtn.disabled = false;
            applyBtn.innerHTML = originalBtnText;
        }
    }

    parseCustomTags() {
        const customTags = document.querySelector('[data-wizard-field="customTags"]')?.value || '';
        return customTags.split(',').map(tag => tag.trim()).filter(tag => tag.length > 0);
    }

    showLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) overlay.style.display = 'flex';
    }

    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) overlay.style.display = 'none';
    }

    showNotification(message, type = 'info') {
        // 这里可以集成通知系统
        console.log(`${type.toUpperCase()}: ${message}`);
        
        // 简单的临时通知实现
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            z-index: 10000;
            background: ${type === 'success' ? '#34C759' : type === 'error' ? '#FF3B30' : '#007AFF'};
            transform: translateX(100%);
            transition: transform 0.3s ease;
        `;
        
        document.body.appendChild(notification);
        
        // 动画显示
        setTimeout(() => notification.style.transform = 'translateX(0)', 100);
        
        // 自动移除
        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
}

// 初始化配置向导
document.addEventListener('DOMContentLoaded', () => {
    window.modelConfigWizard = new ModelConfigWizard();
});

// 导出供其他脚本使用
window.ModelConfigWizard = ModelConfigWizard;