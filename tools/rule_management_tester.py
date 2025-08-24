#!/usr/bin/env python3
"""
规则管理页面功能测试脚本
用于全面测试规则管理页面的各项功能
"""

import requests
import json
import time
from typing import Dict, List, Any
import sys
import os

class RuleManagementTester:
    def __init__(self, base_url: str = "http://localhost:8081"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, message: str = "", data: Any = None):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "success": success,
            "message": message,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "data": data
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        
    def test_api_health(self):
        """测试API健康状态"""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/health/status")
            success = response.status_code == 200
            self.log_test("API健康检查", success, f"状态码: {response.status_code}")
            return success
        except Exception as e:
            self.log_test("API健康检查", False, f"连接失败: {str(e)}")
            return False
    
    def test_get_rules_list(self):
        """测试获取规则列表"""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/rules")
            success = response.status_code == 200
            if success:
                rules = response.json()
                self.log_test("获取规则列表", True, f"成功获取 {len(rules)} 个规则", rules)
                return rules
            else:
                self.log_test("获取规则列表", False, f"状态码: {response.status_code}")
                return []
        except Exception as e:
            self.log_test("获取规则列表", False, f"请求失败: {str(e)}")
            return []
    
    def test_get_rule_detail(self, rule_id: str):
        """测试获取单个规则详情"""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/rules/{rule_id}")
            success = response.status_code == 200
            if success:
                rule = response.json()
                required_fields = ['id', 'name', 'description', 'detection_type', 'severity']
                missing_fields = [field for field in required_fields if field not in rule]
                if missing_fields:
                    self.log_test(f"规则详情-{rule_id}", False, f"缺少字段: {missing_fields}")
                else:
                    self.log_test(f"规则详情-{rule_id}", True, "所有必需字段都存在", rule)
                return rule
            else:
                self.log_test(f"规则详情-{rule_id}", False, f"状态码: {response.status_code}")
                return None
        except Exception as e:
            self.log_test(f"规则详情-{rule_id}", False, f"请求失败: {str(e)}")
            return None
    
    def test_get_models_list(self):
        """测试获取模型列表"""
        try:
            headers = {'Authorization': 'Bearer cherry-studio-key'}
            response = self.session.get(f"{self.base_url}/api/v1/ollama/models", headers=headers)
            success = response.status_code == 200
            if success:
                models = response.json()
                self.log_test("获取模型列表", True, f"成功获取模型数据", models)
                return models
            else:
                self.log_test("获取模型列表", False, f"状态码: {response.status_code}")
                return None
        except Exception as e:
            self.log_test("获取模型列表", False, f"请求失败: {str(e)}")
            return None
    
    def test_get_rule_templates(self):
        """测试获取规则模板"""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/rule-templates")
            success = response.status_code == 200
            if success:
                templates = response.json()
                self.log_test("获取规则模板", True, f"成功获取 {len(templates)} 个模板", templates)
                return templates
            else:
                self.log_test("获取规则模板", False, f"状态码: {response.status_code}")
                return []
        except Exception as e:
            self.log_test("获取规则模板", False, f"请求失败: {str(e)}")
            return []
    
    def test_get_model_rules(self, model_id: str):
        """测试获取模型规则配置"""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/model-rules/{model_id}")
            success = response.status_code in [200, 404]  # 404也是正常的，表示模型未配置
            if response.status_code == 200:
                config = response.json()
                self.log_test(f"模型规则配置-{model_id}", True, "已配置", config)
                return config
            elif response.status_code == 404:
                self.log_test(f"模型规则配置-{model_id}", True, "未配置（正常）")
                return None
            else:
                self.log_test(f"模型规则配置-{model_id}", False, f"状态码: {response.status_code}")
                return None
        except Exception as e:
            self.log_test(f"模型规则配置-{model_id}", False, f"请求失败: {str(e)}")
            return None
    
    def test_page_accessibility(self):
        """测试页面可访问性"""
        try:
            response = self.session.get(f"{self.base_url}/static/admin/model_rules.html")
            success = response.status_code == 200
            if success:
                content = response.text
                # 检查关键元素是否存在
                required_elements = [
                    'models-grid',
                    'rule-edit-modal',
                    'model-rules-config-modal',
                    'model-rules-enhanced.js'
                ]
                missing_elements = [elem for elem in required_elements if elem not in content]
                if missing_elements:
                    self.log_test("页面可访问性", False, f"缺少元素: {missing_elements}")
                else:
                    self.log_test("页面可访问性", True, "所有关键元素都存在")
            else:
                self.log_test("页面可访问性", False, f"状态码: {response.status_code}")
        except Exception as e:
            self.log_test("页面可访问性", False, f"请求失败: {str(e)}")
    
    def test_javascript_resources(self):
        """测试JavaScript资源"""
        js_files = [
            "/static/admin/js/model-rules-enhanced.js",
            "/static/admin/js/apple-ui.js"
        ]
        
        for js_file in js_files:
            try:
                response = self.session.get(f"{self.base_url}{js_file}")
                success = response.status_code == 200
                self.log_test(f"JS资源-{js_file}", success, f"状态码: {response.status_code}")
            except Exception as e:
                self.log_test(f"JS资源-{js_file}", False, f"请求失败: {str(e)}")
    
    def test_css_resources(self):
        """测试CSS资源"""
        css_files = [
            "/static/admin/css/model-rules-enhanced.css",
            "/static/admin/css/apple-main.css"
        ]
        
        for css_file in css_files:
            try:
                response = self.session.get(f"{self.base_url}{css_file}")
                success = response.status_code == 200
                self.log_test(f"CSS资源-{css_file}", success, f"状态码: {response.status_code}")
            except Exception as e:
                self.log_test(f"CSS资源-{css_file}", False, f"请求失败: {str(e)}")
    
    def run_comprehensive_test(self):
        """运行全面测试"""
        print("🚀 开始规则管理页面全面功能测试")
        print("=" * 60)
        
        # 1. 基础连接测试
        print("\n📡 基础连接测试")
        if not self.test_api_health():
            print("❌ API服务不可用，停止测试")
            return
        
        # 2. 资源文件测试
        print("\n📁 静态资源测试")
        self.test_page_accessibility()
        self.test_javascript_resources()
        self.test_css_resources()
        
        # 3. API功能测试
        print("\n🔧 API功能测试")
        rules = self.test_get_rules_list()
        self.test_get_rule_templates()
        models_data = self.test_get_models_list()
        
        # 4. 规则详情测试
        print("\n📋 规则详情测试")
        if rules:
            # 测试前5个规则的详情
            for rule in rules[:5]:
                if isinstance(rule, dict) and 'id' in rule:
                    self.test_get_rule_detail(rule['id'])
        
        # 5. 模型规则配置测试
        print("\n⚙️ 模型规则配置测试")
        if models_data and 'models' in models_data:
            # 测试前3个模型的规则配置
            for model in models_data['models'][:3]:
                model_id = model.get('model') or model.get('id')
                if model_id:
                    self.test_get_model_rules(model_id)
        
        # 6. 生成测试报告
        self.generate_report()
    
    def generate_report(self):
        """生成测试报告"""
        print("\n" + "=" * 60)
        print("📊 测试报告")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['success']])
        failed_tests = total_tests - passed_tests
        
        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests} ✅")
        print(f"失败: {failed_tests} ❌")
        print(f"成功率: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            print("\n❌ 失败的测试:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test_name']}: {result['message']}")
        
        # 保存详细报告到文件
        report_file = f"rule_management_test_report_{int(time.time())}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)
        print(f"\n📄 详细报告已保存到: {report_file}")

if __name__ == "__main__":
    tester = RuleManagementTester()
    tester.run_comprehensive_test()
