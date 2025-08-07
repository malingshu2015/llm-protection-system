#!/usr/bin/env python3
"""
上下文污染修复补丁
Context Pollution Fix Patch

解决两个关键问题：
1. 前端消息历史污染
2. 错误消息显示混乱
"""

# 首先，让我们修复后端的检测逻辑，确保只检测当前用户输入
def create_backend_fix():
    backend_fix = '''
# 修复src/web/ollama_proxy_api.py中的检测逻辑

在第150-200行左右，找到检测请求的代码段，添加以下逻辑：

def extract_current_user_input(request_body):
    """从请求中提取当前用户输入，忽略历史消息"""
    if not isinstance(request_body, dict):
        return ""
    
    messages = request_body.get("messages", [])
    if not messages:
        return ""
    
    # 只检测最后一条用户消息（当前输入）
    for message in reversed(messages):
        if isinstance(message, dict) and message.get("role") == "user":
            return message.get("content", "")
    
    return ""

# 然后在安全检测部分使用这个函数：
current_user_input = extract_current_user_input(request.body)
# 只对当前用户输入进行安全检测，而不是整个对话历史
'''
    return backend_fix

def create_frontend_fix():
    frontend_fix = '''
# 修复static/index.html中的前端逻辑

在sendMessageToServer函数中（约650行），修改请求数据：

// 原代码：
const requestData = {
    model: modelSelect.value,
    messages: messages,  // ❌ 这里发送了完整历史
    stream: streamCheckbox.checked,
    temperature: parseFloat(temperatureInput.value),
    max_tokens: parseInt(maxTokensInput.value)
};

// 修复后：
const requestData = {
    model: modelSelect.value,
    messages: filterSafeMessages(messages),  // ✅ 过滤后的安全消息
    stream: streamCheckbox.checked,
    temperature: parseFloat(temperatureInput.value),
    max_tokens: parseInt(maxTokensInput.value)
};

// 添加消息过滤函数：
function filterSafeMessages(allMessages) {
    // 方案1：只发送最后一条用户消息和最近的助手回复
    const filteredMessages = [];
    let lastUserMessage = null;
    let lastAssistantMessage = null;
    
    // 从后往前找最后一条用户消息
    for (let i = allMessages.length - 1; i >= 0; i--) {
        if (allMessages[i].role === 'user' && !lastUserMessage) {
            lastUserMessage = allMessages[i];
        } else if (allMessages[i].role === 'assistant' && !lastAssistantMessage && lastUserMessage) {
            lastAssistantMessage = allMessages[i];
            break;
        }
    }
    
    if (lastAssistantMessage) {
        filteredMessages.push(lastAssistantMessage);
    }
    if (lastUserMessage) {
        filteredMessages.push(lastUserMessage);
    }
    
    return filteredMessages;
}

// 方案2：移除被拦截的危险消息
function filterSafeMessages(allMessages) {
    return allMessages.filter(message => {
        // 如果消息曾经被标记为危险，就不包含在历史中
        return !message.blocked && !message.dangerous;
    });
}
'''
    return frontend_fix

if __name__ == "__main__":
    print("🔧 上下文污染修复补丁")
    print("="*50)
    
    print("问题分析:")
    print("1. ❌ 前端发送完整消息历史，包含被拦截的危险内容")
    print("2. ❌ 后端检测整个对话历史，而非当前用户输入")
    print("3. ❌ 错误信息显示历史匹配内容，用户混淆")
    
    print(f"\n修复方案:")
    print("1. ✅ 后端只检测当前用户输入")
    print("2. ✅ 前端过滤危险历史消息")
    print("3. ✅ 改进错误消息显示")
    
    print(f"\n后端修复代码:")
    print(create_backend_fix())
    
    print(f"\n前端修复代码:")
    print(create_frontend_fix())
    
    print(f"\n实施步骤:")
    print("1. 修改 src/web/ollama_proxy_api.py - 只检测当前用户输入")
    print("2. 修改 static/index.html - 过滤消息历史")
    print("3. 重启系统并测试")
    print("4. 验证修复效果")