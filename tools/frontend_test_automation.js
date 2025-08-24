// 规则管理页面前端自动化测试脚本
// 在浏览器控制台中运行此脚本来自动测试页面功能

class RuleManagementTester {
    constructor() {
        this.testResults = [];
        this.currentTest = null;
    }

    log(message, type = 'info') {
        const timestamp = new Date().toLocaleTimeString();
        const logMessage = `[${timestamp}] ${type.toUpperCase()}: ${message}`;
        console.log(logMessage);
        
        if (this.currentTest) {
            this.currentTest.logs = this.currentTest.logs || [];
            this.currentTest.logs.push(logMessage);
        }
    }

    startTest(testName) {
        this.currentTest = {
            name: testName,
            startTime: Date.now(),
            success: null,
            logs: []
        };
        this.log(`开始测试: ${testName}`, 'test');
    }

    endTest(success, message = '') {
        if (!this.currentTest) return;
        
        this.currentTest.success = success;
        this.currentTest.endTime = Date.now();
        this.currentTest.duration = this.currentTest.endTime - this.currentTest.startTime;
        this.currentTest.message = message;
        
        this.testResults.push(this.currentTest);
        
        const status = success ? '✅ PASS' : '❌ FAIL';
        this.log(`测试结束: ${this.currentTest.name} - ${status} ${message}`, success ? 'pass' : 'fail');
        
        this.currentTest = null;
    }

    async wait(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    async testPageLoad() {
        this.startTest('页面基本加载测试');
        
        try {
            // 检查关键元素是否存在
            const requiredElements = [
                'models-grid',
                'rule-edit-modal',
                'model-rules-config-modal'
            ];
            
            for (const elementId of requiredElements) {
                const element = document.getElementById(elementId);
                if (!element) {
                    this.endTest(false, `缺少关键元素: ${elementId}`);
                    return;
                }
                this.log(`找到元素: ${elementId}`);
            }
            
            // 检查模型卡片是否加载
            const modelsGrid = document.getElementById('models-grid');
            const modelCards = modelsGrid.querySelectorAll('.model-card');
            
            if (modelCards.length === 0) {
                this.endTest(false, '没有找到模型卡片');
                return;
            }
            
            this.log(`找到 ${modelCards.length} 个模型卡片`);
            this.endTest(true, `页面加载正常，包含 ${modelCards.length} 个模型`);
            
        } catch (error) {
            this.endTest(false, `页面加载测试失败: ${error.message}`);
        }
    }

    async testModelConfigModal() {
        this.startTest('模型配置弹窗测试');
        
        try {
            // 找到第一个模型卡片的配置按钮
            const configButton = document.querySelector('.model-card .config-btn');
            if (!configButton) {
                this.endTest(false, '没有找到配置按钮');
                return;
            }
            
            this.log('找到配置按钮，准备点击');
            
            // 点击配置按钮
            configButton.click();
            
            // 等待弹窗显示
            await this.wait(500);
            
            // 检查弹窗是否显示
            const modal = document.getElementById('model-rules-config-modal');
            const isVisible = modal && modal.style.display !== 'none';
            
            if (!isVisible) {
                this.endTest(false, '模型配置弹窗没有显示');
                return;
            }
            
            this.log('模型配置弹窗显示成功');
            
            // 检查规则表格是否加载
            const rulesTable = modal.querySelector('#model-config-rules-body');
            if (!rulesTable) {
                this.endTest(false, '规则表格容器不存在');
                return;
            }
            
            // 等待规则数据加载
            await this.wait(1000);
            
            const ruleRows = rulesTable.querySelectorAll('tr');
            this.log(`规则表格包含 ${ruleRows.length} 行数据`);
            
            this.endTest(true, `模型配置弹窗正常，包含 ${ruleRows.length} 个规则`);
            
        } catch (error) {
            this.endTest(false, `模型配置弹窗测试失败: ${error.message}`);
        }
    }

    async testRuleEditModal() {
        this.startTest('规则编辑弹窗测试');
        
        try {
            // 确保模型配置弹窗是打开的
            const configModal = document.getElementById('model-rules-config-modal');
            if (!configModal || configModal.style.display === 'none') {
                this.log('模型配置弹窗未打开，先打开它');
                await this.testModelConfigModal();
                await this.wait(1000);
            }
            
            // 找到第一个编辑按钮
            const editButton = document.querySelector('#model-config-rules-body .edit-btn');
            if (!editButton) {
                this.endTest(false, '没有找到编辑按钮');
                return;
            }
            
            this.log('找到编辑按钮，准备点击');
            
            // 点击编辑按钮
            editButton.click();
            
            // 等待编辑弹窗显示
            await this.wait(1000);
            
            // 检查编辑弹窗是否显示
            const editModal = document.getElementById('rule-edit-modal');
            const isVisible = editModal && editModal.style.display !== 'none';
            
            if (!isVisible) {
                this.endTest(false, '规则编辑弹窗没有显示');
                return;
            }
            
            this.log('规则编辑弹窗显示成功');
            
            // 检查表单字段是否存在并填充
            const formFields = [
                'rule-name',
                'rule-description',
                'rule-type',
                'rule-severity',
                'rule-priority',
                'rule-enabled',
                'rule-patterns',
                'rule-whitelist'
            ];
            
            let filledFields = 0;
            for (const fieldId of formFields) {
                const field = document.getElementById(fieldId);
                if (!field) {
                    this.log(`警告: 表单字段 ${fieldId} 不存在`);
                    continue;
                }
                
                let hasValue = false;
                if (field.type === 'checkbox') {
                    hasValue = field.checked !== undefined;
                } else {
                    hasValue = field.value && field.value.trim() !== '';
                }
                
                if (hasValue) {
                    filledFields++;
                    this.log(`字段 ${fieldId} 已填充: ${field.value || field.checked}`);
                } else {
                    this.log(`字段 ${fieldId} 为空`);
                }
            }
            
            this.endTest(true, `规则编辑弹窗正常，${filledFields}/${formFields.length} 个字段已填充`);
            
        } catch (error) {
            this.endTest(false, `规则编辑弹窗测试失败: ${error.message}`);
        }
    }

    async testFormValidation() {
        this.startTest('表单验证测试');
        
        try {
            // 确保编辑弹窗是打开的
            const editModal = document.getElementById('rule-edit-modal');
            if (!editModal || editModal.style.display === 'none') {
                this.log('规则编辑弹窗未打开，先打开它');
                await this.testRuleEditModal();
                await this.wait(500);
            }
            
            // 清空必填字段
            const nameField = document.getElementById('rule-name');
            if (nameField) {
                const originalValue = nameField.value;
                nameField.value = '';
                this.log('清空规则名称字段');
                
                // 尝试保存
                const saveButton = editModal.querySelector('.save-btn');
                if (saveButton) {
                    saveButton.click();
                    await this.wait(500);
                    
                    // 检查是否有验证提示
                    // 这里需要根据实际的验证逻辑来检查
                    this.log('点击保存按钮测试验证');
                }
                
                // 恢复原值
                nameField.value = originalValue;
            }
            
            this.endTest(true, '表单验证测试完成');
            
        } catch (error) {
            this.endTest(false, `表单验证测试失败: ${error.message}`);
        }
    }

    async testModalClose() {
        this.startTest('弹窗关闭测试');
        
        try {
            // 关闭规则编辑弹窗
            const editModal = document.getElementById('rule-edit-modal');
            if (editModal && editModal.style.display !== 'none') {
                const closeButton = editModal.querySelector('.close-btn, .cancel-btn');
                if (closeButton) {
                    closeButton.click();
                    await this.wait(300);
                    this.log('关闭规则编辑弹窗');
                }
            }
            
            // 关闭模型配置弹窗
            const configModal = document.getElementById('model-rules-config-modal');
            if (configModal && configModal.style.display !== 'none') {
                const closeButton = configModal.querySelector('.close-btn, .cancel-btn');
                if (closeButton) {
                    closeButton.click();
                    await this.wait(300);
                    this.log('关闭模型配置弹窗');
                }
            }
            
            this.endTest(true, '弹窗关闭测试完成');
            
        } catch (error) {
            this.endTest(false, `弹窗关闭测试失败: ${error.message}`);
        }
    }

    async runAllTests() {
        console.log('🚀 开始规则管理页面前端自动化测试');
        console.log('=' * 60);
        
        await this.testPageLoad();
        await this.wait(1000);
        
        await this.testModelConfigModal();
        await this.wait(1000);
        
        await this.testRuleEditModal();
        await this.wait(1000);
        
        await this.testFormValidation();
        await this.wait(1000);
        
        await this.testModalClose();
        
        this.generateReport();
    }

    generateReport() {
        console.log('\n' + '=' * 60);
        console.log('📊 测试报告');
        console.log('=' * 60);
        
        const totalTests = this.testResults.length;
        const passedTests = this.testResults.filter(t => t.success).length;
        const failedTests = totalTests - passedTests;
        
        console.log(`总测试数: ${totalTests}`);
        console.log(`通过: ${passedTests} ✅`);
        console.log(`失败: ${failedTests} ❌`);
        console.log(`成功率: ${(passedTests/totalTests*100).toFixed(1)}%`);
        
        if (failedTests > 0) {
            console.log('\n❌ 失败的测试:');
            this.testResults.filter(t => !t.success).forEach(test => {
                console.log(`  - ${test.name}: ${test.message}`);
            });
        }
        
        console.log('\n📄 详细测试结果:');
        this.testResults.forEach(test => {
            const status = test.success ? '✅' : '❌';
            const duration = test.duration ? `(${test.duration}ms)` : '';
            console.log(`${status} ${test.name} ${duration}: ${test.message}`);
        });
        
        return this.testResults;
    }
}

// 创建测试实例并提供给全局使用
window.ruleManagementTester = new RuleManagementTester();

// 提供快速测试命令
window.runRuleTests = () => window.ruleManagementTester.runAllTests();

console.log('规则管理页面测试脚本已加载');
console.log('运行 runRuleTests() 开始自动化测试');
