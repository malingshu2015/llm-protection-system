// 测试推荐按钮修复的脚本
// 在浏览器控制台中运行此脚本来测试修复效果

console.log('🧪 开始测试推荐按钮修复...');

// 1. 检查按钮是否存在
const button = document.getElementById('auto-recommend-btn');
if (button) {
    console.log('✅ 推荐按钮存在');
    
    // 2. 检查按钮是否有事件监听器
    const eventListeners = getEventListeners ? getEventListeners(button) : '无法检查';
    console.log('📡 按钮事件监听器:', eventListeners);
    
    // 3. 检查modelRulesManager是否可用
    if (window.modelRulesManager) {
        console.log('✅ modelRulesManager 可用');
        
        // 4. 测试按钮点击
        console.log('🔘 模拟点击推荐按钮...');
        button.click();
        
        // 5. 检查按钮状态变化
        setTimeout(() => {
            console.log('📊 按钮状态:', {
                disabled: button.disabled,
                innerHTML: button.innerHTML
            });
        }, 100);
        
    } else {
        console.error('❌ modelRulesManager 不可用');
    }
} else {
    console.error('❌ 推荐按钮不存在');
}

// 6. 测试手动调用
console.log('🔧 测试手动调用推荐功能...');
if (window.testAutoRecommend) {
    window.testAutoRecommend();
} else {
    console.error('❌ testAutoRecommend 函数不可用');
}

console.log('📋 测试完成，请查看控制台输出以确认修复效果');