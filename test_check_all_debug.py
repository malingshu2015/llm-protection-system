#!/usr/bin/env python3
"""
调试全面检查按钮问题
"""
import requests
import json

def test_check_all_api():
    """测试全面检查功能使用的API"""
    
    print("=== 🔍 调试全面检查按钮问题 ===")
    
    headers = {'Authorization': 'Bearer cherry-studio-key'}
    
    try:
        # 1. 测试模型规则API
        print("\n1️⃣ 测试 /api/v1/model-rules API...")
        response = requests.get('http://localhost:8081/api/v1/model-rules', headers=headers)
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   响应数据类型: {type(data)}")
            print(f"   模型数量: {len(data) if isinstance(data, list) else 'N/A'}")
            
            if isinstance(data, list) and len(data) > 0:
                print(f"   第一个模型数据结构:")
                model = data[0]
                for key in ['model_id', 'rules_count', 'security_score', 'last_updated']:
                    print(f"     {key}: {model.get(key, 'MISSING')}")
                
                # 模拟JavaScript处理逻辑
                print(f"\n2️⃣ 模拟JavaScript处理逻辑...")
                issues = []
                summary = {
                    'totalModels': len(data),
                    'configuredModels': 0,
                    'unconfiguredModels': 0,
                    'lowSecurityModels': 0,
                    'outdatedConfigs': 0,
                    'totalRules': 0
                }
                
                for model in data:
                    rules_count = model.get('rules_count', 0)
                    security_score = model.get('security_score', 0)
                    model_id = model.get('model_id', 'unknown')
                    
                    summary['totalRules'] += rules_count
                    
                    if rules_count > 0:
                        summary['configuredModels'] += 1
                    else:
                        summary['unconfiguredModels'] += 1
                        issues.append({
                            'type': 'warning',
                            'model': model_id,
                            'issue': '未配置安全规则',
                            'description': '该模型没有配置任何安全规则，存在安全风险',
                            'suggestion': '建议应用适当的规则模板'
                        })
                    
                    # 检查安全评分
                    if security_score < 40:
                        summary['lowSecurityModels'] += 1
                        issues.append({
                            'type': 'error',
                            'model': model_id,
                            'issue': '安全评分过低',
                            'description': f'安全评分仅为 {security_score}，低于推荐值(60)',
                            'suggestion': '建议增加更多安全规则或应用更严格的模板'
                        })
                    elif security_score < 60:
                        issues.append({
                            'type': 'warning',
                            'model': model_id,
                            'issue': '安全评分偏低',
                            'description': f'安全评分为 {security_score}，建议提升至60以上',
                            'suggestion': '考虑添加额外的安全规则'
                        })
                
                print(f"   ✅ 处理摘要:")
                for key, value in summary.items():
                    print(f"     {key}: {value}")
                
                print(f"   ✅ 发现问题数量: {len(issues)}")
                for i, issue in enumerate(issues[:3]):  # 只显示前3个问题
                    print(f"     问题 {i+1}: {issue['model']} - {issue['issue']}")
                
                print(f"\n3️⃣ 测试模态框HTML生成...")
                # 模拟生成模态框HTML（简化版本）
                modal_content_length = 1000 + len(str(summary)) + len(str(issues))
                print(f"   预估模态框内容长度: {modal_content_length} 字符")
                
                # 检查是否有可能导致JavaScript错误的数据
                problematic_data = []
                for model in data:
                    if not model.get('model_id'):
                        problematic_data.append("missing model_id")
                    if model.get('last_updated') and not isinstance(model.get('last_updated'), str):
                        problematic_data.append("invalid last_updated format")
                
                if problematic_data:
                    print(f"   ⚠️  发现潜在问题数据: {problematic_data}")
                else:
                    print(f"   ✅ 数据格式看起来正常")
                    
        else:
            print(f"   ❌ API调用失败: {response.text}")
            
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
    
    print(f"\n4️⃣ 建议的排查步骤:")
    print(f"   1. 打开浏览器开发者工具")
    print(f"   2. 切换到Console标签")
    print(f"   3. 点击全面检查按钮")
    print(f"   4. 观察是否有JavaScript错误输出")
    print(f"   5. 检查Network标签中的API调用")
    print(f"   6. 如果有错误，检查具体的错误位置")

if __name__ == "__main__":
    test_check_all_api()