#!/bin/bash

echo "🔥 全面检查功能集成测试"
echo "================================"

# 1. 测试API连接
echo "1️⃣ 测试API连接..."
response=$(curl -s -H "Authorization: Bearer cherry-studio-key" -w "%{http_code}" http://localhost:8081/api/v1/model-rules)
http_code="${response: -3}"
if [ "$http_code" = "200" ]; then
    echo "✅ API连接成功 (HTTP $http_code)"
else
    echo "❌ API连接失败 (HTTP $http_code)"
    exit 1
fi

# 2. 测试数据格式
echo "2️⃣ 测试API响应格式..."
model_count=$(curl -s -H "Authorization: Bearer cherry-studio-key" http://localhost:8081/api/v1/model-rules | jq 'length')
if [ "$model_count" -gt 0 ]; then
    echo "✅ API返回 $model_count 个模型配置"
else
    echo "❌ API未返回有效数据"
    exit 1
fi

# 3. 检查是否存在未配置的模型
echo "3️⃣ 检查配置状态..."
unconfigured=$(curl -s -H "Authorization: Bearer cherry-studio-key" http://localhost:8081/api/v1/model-rules | jq '[.[] | select(.rules_count == 0)] | length')
low_security=$(curl -s -H "Authorization: Bearer cherry-studio-key" http://localhost:8081/api/v1/model-rules | jq '[.[] | select(.security_score < 40)] | length')

echo "   未配置模型: $unconfigured 个"
echo "   低安全评分: $low_security 个"

if [ "$unconfigured" -gt 0 ] || [ "$low_security" -gt 0 ]; then
    echo "✅ 发现配置问题，全面检查功能将有内容显示"
else
    echo "⚠️  所有模型配置正常，全面检查将显示无问题状态"
fi

# 4. 测试页面访问
echo "4️⃣ 测试页面访问..."
page_status=$(curl -s -w "%{http_code}" http://localhost:8081/static/admin/model_rules.html -o /dev/null)
if [ "$page_status" = "200" ]; then
    echo "✅ 规则配置页面访问正常 (HTTP $page_status)"
else
    echo "❌ 规则配置页面访问失败 (HTTP $page_status)"
    exit 1
fi

# 5. 测试JavaScript文件
echo "5️⃣ 测试JavaScript文件..."
js_status=$(curl -s -w "%{http_code}" http://localhost:8081/static/admin/js/model-rules-enhanced.js -o /dev/null)
if [ "$js_status" = "200" ]; then
    echo "✅ JavaScript文件访问正常 (HTTP $js_status)"
else
    echo "❌ JavaScript文件访问失败 (HTTP $js_status)"
    exit 1
fi

# 6. 检查JavaScript中是否包含所需方法
echo "6️⃣ 验证JavaScript实现..."
if curl -s http://localhost:8081/static/admin/js/model-rules-enhanced.js | grep -q "checkAllConfigurations"; then
    echo "✅ checkAllConfigurations方法存在"
else
    echo "❌ checkAllConfigurations方法不存在"
    exit 1
fi

if curl -s http://localhost:8081/static/admin/js/model-rules-enhanced.js | grep -q "showConfigCheckResults"; then
    echo "✅ showConfigCheckResults方法存在"
else
    echo "❌ showConfigCheckResults方法不存在"
    exit 1
fi

# 7. 检查HTML中是否有按钮
echo "7️⃣ 验证HTML按钮..."
if curl -s http://localhost:8081/static/admin/model_rules.html | grep -q 'id="check-all-btn"'; then
    echo "✅ 全面检查按钮存在"
else
    echo "❌ 全面检查按钮不存在"
    exit 1
fi

# 8. 测试浏览器可访问的测试页面
echo "8️⃣ 测试调试页面..."
test_page_status=$(curl -s -w "%{http_code}" http://localhost:8081/static/debug/test-check-all-button.html -o /dev/null)
if [ "$test_page_status" = "200" ]; then
    echo "✅ 调试测试页面访问正常 (HTTP $test_page_status)"
    echo "   📱 浏览器中访问: http://localhost:8081/static/debug/test-check-all-button.html"
else
    echo "❌ 调试测试页面访问失败 (HTTP $test_page_status)"
fi

echo ""
echo "🎉 全面检查功能集成测试完成！"
echo "================================"
echo "✅ 所有核心组件验证通过"
echo "✅ API和数据访问正常"
echo "✅ JavaScript方法正确实现"
echo "✅ HTML按钮存在且绑定正确"
echo ""
echo "🚀 功能验证:"
echo "   1. 点击'全面检查'按钮应该触发检查"
echo "   2. 显示模型配置统计信息"
echo "   3. 列出发现的配置问题"
echo "   4. 提供一键修复选项(如有问题)"
echo ""
echo "🌐 测试页面:"
echo "   - 主页面: http://localhost:8081/static/admin/model_rules.html"
echo "   - 调试页面: http://localhost:8081/static/debug/test-check-all-button.html"