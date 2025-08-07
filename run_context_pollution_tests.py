#!/usr/bin/env python3
"""
上下文污染修复测试执行器
Context Pollution Fix Test Executor

统一执行所有测试套件并生成综合报告
"""

import subprocess
import sys
import time
import json
from datetime import datetime
from pathlib import Path
import argparse


class TestExecutor:
    """测试执行器"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = datetime.now()
        
    def check_server_health(self, max_retries=5, retry_interval=2):
        """检查服务器健康状态"""
        print("🔍 检查服务器状态...")
        
        import requests
        
        for attempt in range(max_retries):
            try:
                response = requests.get("http://localhost:8081/health", timeout=5)
                if response.status_code == 200:
                    print("  ✅ 服务器运行正常")
                    return True
            except Exception as e:
                print(f"  ❌ 尝试 {attempt + 1}/{max_retries}: 服务器连接失败 - {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_interval)
        
        print("  ❌ 服务器未响应，请确保LLM防护系统正在运行")
        print("     启动命令: python -m src.main")
        return False
    
    def run_basic_test(self):
        """运行基础测试"""
        print("\n🧪 运行基础上下文污染测试...")
        
        try:
            result = subprocess.run([
                sys.executable, "test_context_pollution_fix.py"
            ], capture_output=True, text=True, timeout=300)
            
            self.test_results["basic_test"] = {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            }
            
            if result.returncode == 0:
                print("  ✅ 基础测试通过")
            else:
                print("  ❌ 基础测试失败")
                print(f"  错误: {result.stderr[:200]}...")
            
        except subprocess.TimeoutExpired:
            print("  ⏰ 基础测试超时")
            self.test_results["basic_test"] = {
                "success": False,
                "error": "timeout"
            }
        except Exception as e:
            print(f"  💥 基础测试执行失败: {e}")
            self.test_results["basic_test"] = {
                "success": False,
                "error": str(e)
            }
    
    def run_comprehensive_test(self):
        """运行综合测试"""
        print("\n🔬 运行综合上下文污染测试...")
        
        try:
            result = subprocess.run([
                sys.executable, "test_context_pollution_comprehensive.py"
            ], capture_output=True, text=True, timeout=600)
            
            self.test_results["comprehensive_test"] = {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            }
            
            if result.returncode == 0:
                print("  ✅ 综合测试通过")
            else:
                print("  ❌ 综合测试失败")
                print(f"  错误: {result.stderr[:200]}...")
            
        except subprocess.TimeoutExpired:
            print("  ⏰ 综合测试超时")
            self.test_results["comprehensive_test"] = {
                "success": False,
                "error": "timeout"
            }
        except Exception as e:
            print(f"  💥 综合测试执行失败: {e}")
            self.test_results["comprehensive_test"] = {
                "success": False,
                "error": str(e)
            }
    
    def run_stress_test(self):
        """运行压力测试"""
        print("\n🔥 运行压力测试...")
        
        try:
            result = subprocess.run([
                sys.executable, "test_context_pollution_stress.py"
            ], capture_output=True, text=True, timeout=900)
            
            self.test_results["stress_test"] = {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            }
            
            if result.returncode == 0:
                print("  ✅ 压力测试通过")
            else:
                print("  ❌ 压力测试失败")
                print(f"  错误: {result.stderr[:200]}...")
            
        except subprocess.TimeoutExpired:
            print("  ⏰ 压力测试超时")
            self.test_results["stress_test"] = {
                "success": False,
                "error": "timeout"
            }
        except Exception as e:
            print(f"  💥 压力测试执行失败: {e}")
            self.test_results["stress_test"] = {
                "success": False,
                "error": str(e)
            }
    
    def collect_test_reports(self):
        """收集测试报告文件"""
        print("\n📁 收集测试报告文件...")
        
        report_files = {
            "comprehensive_reports": list(Path(".").glob("context_pollution_test_report_*.json")),
            "stress_reports": list(Path(".").glob("context_pollution_stress_test_*.json"))
        }
        
        for report_type, files in report_files.items():
            if files:
                latest_file = max(files, key=lambda f: f.stat().st_mtime)
                print(f"  📄 {report_type}: {latest_file}")
                
                try:
                    with open(latest_file, 'r', encoding='utf-8') as f:
                        report_data = json.load(f)
                    self.test_results[f"{report_type}_data"] = report_data
                except Exception as e:
                    print(f"    ❌ 无法读取报告文件: {e}")
        
    def generate_final_report(self):
        """生成最终综合报告"""
        print("\n📊 生成最终综合报告...")
        
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        # 统计测试结果
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() 
                          if isinstance(result, dict) and result.get("success", False))
        
        # 创建综合报告
        final_report = {
            "test_execution_summary": {
                "start_time": self.start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_minutes": duration.total_seconds() / 60,
                "total_test_suites": total_tests,
                "passed_test_suites": passed_tests,
                "failed_test_suites": total_tests - passed_tests,
                "overall_success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0
            },
            "test_suite_results": {
                "basic_test": self.test_results.get("basic_test", {}),
                "comprehensive_test": self.test_results.get("comprehensive_test", {}),
                "stress_test": self.test_results.get("stress_test", {})
            },
            "detailed_reports": {
                key: value for key, value in self.test_results.items()
                if key.endswith("_data")
            }
        }
        
        # 保存综合报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"context_pollution_final_report_{timestamp}.json"
        
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(final_report, f, indent=2, ensure_ascii=False)
        
        print(f"  💾 最终报告已保存: {report_filename}")
        
        return final_report, report_filename
    
    def print_final_summary(self, final_report):
        """打印最终总结"""
        print("\n" + "="*80)
        print("🎯 上下文污染修复测试 - 最终总结报告")
        print("="*80)
        
        summary = final_report["test_execution_summary"]
        
        print(f"测试执行时间: {summary['start_time']} ~ {summary['end_time']}")
        print(f"总执行时长: {summary['duration_minutes']:.1f} 分钟")
        print()
        
        print("📈 测试套件执行结果:")
        print(f"  总测试套件数: {summary['total_test_suites']}")
        print(f"  通过套件数: {summary['passed_test_suites']} ✅")
        print(f"  失败套件数: {summary['failed_test_suites']} ❌")
        print(f"  整体成功率: {summary['overall_success_rate']:.1f}%")
        print()
        
        # 各测试套件状态
        suite_results = final_report["test_suite_results"]
        print("🔍 各测试套件详情:")
        
        for suite_name, result in suite_results.items():
            status = "✅ 通过" if result.get("success", False) else "❌ 失败"
            print(f"  {suite_name}: {status}")
            
            if not result.get("success", False) and "error" in result:
                print(f"    错误: {result['error']}")
        
        print()
        
        # 从详细报告中提取关键指标
        if "comprehensive_reports_data" in final_report["detailed_reports"]:
            comp_data = final_report["detailed_reports"]["comprehensive_reports_data"]
            if "summary" in comp_data:
                comp_summary = comp_data["summary"]
                print("📊 综合测试关键指标:")
                print(f"  总测试用例: {comp_summary.get('total_tests', 'N/A')}")
                print(f"  成功率: {comp_summary.get('success_rate', 'N/A'):.1f}%")
                print(f"  平均响应时间: {comp_summary.get('average_response_time_ms', 'N/A'):.1f}ms")
                print()
        
        if "stress_reports_data" in final_report["detailed_reports"]:
            stress_data = final_report["detailed_reports"]["stress_reports_data"]
            if "results" in stress_data:
                total_requests = sum(r.get("total_requests", 0) for r in stress_data["results"])
                total_pollution_failures = sum(r.get("context_pollution_failures", 0) for r in stress_data["results"])
                pollution_rate = (total_pollution_failures / total_requests * 100) if total_requests > 0 else 0
                
                print("🔥 压力测试关键指标:")
                print(f"  总压力测试请求: {total_requests:,}")
                print(f"  上下文污染失败: {total_pollution_failures}")
                print(f"  污染失败率: {pollution_rate:.2f}%")
                print()
        
        # 最终结论
        print("🏆 最终结论:")
        
        overall_success = summary["overall_success_rate"] >= 80
        
        if overall_success:
            if summary["overall_success_rate"] >= 95:
                print("  ✅ 优秀! 上下文污染修复效果显著，系统运行稳定。")
            else:
                print("  🟡 良好! 上下文污染问题基本解决，仍有小幅优化空间。")
        else:
            print("  ❌ 需要改进! 上下文污染问题仍然存在，需要进一步修复。")
        
        # 推荐操作
        print("\n💡 推荐后续操作:")
        if overall_success:
            print("  1. 可以将修复版本部署到生产环境")
            print("  2. 继续监控生产环境中的上下文隔离效果")
            print("  3. 定期执行回归测试确保修复效果持续有效")
        else:
            print("  1. 分析失败的测试用例，定位根本原因")
            print("  2. 优化上下文隔离机制")
            print("  3. 重新执行测试验证修复效果")
        
        print("\n📋 相关文件:")
        print("  - 基础测试: test_context_pollution_fix.py")
        print("  - 综合测试: test_context_pollution_comprehensive.py")
        print("  - 压力测试: test_context_pollution_stress.py")
        print("  - 最终报告: 见上述JSON文件")
        
        print("="*80)
        
        return overall_success
    
    def run_all_tests(self, include_stress=True):
        """运行所有测试"""
        print("🚀 开始执行上下文污染修复完整测试套件")
        print("="*80)
        
        # 1. 检查服务器状态
        if not self.check_server_health():
            return False
        
        # 2. 运行基础测试
        self.run_basic_test()
        
        # 3. 运行综合测试
        self.run_comprehensive_test()
        
        # 4. 运行压力测试（可选）
        if include_stress:
            self.run_stress_test()
        
        # 5. 收集测试报告
        self.collect_test_reports()
        
        # 6. 生成最终报告
        final_report, report_filename = self.generate_final_report()
        
        # 7. 打印最终总结
        overall_success = self.print_final_summary(final_report)
        
        return overall_success


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="上下文污染修复测试执行器")
    parser.add_argument("--no-stress", action="store_true", help="跳过压力测试")
    parser.add_argument("--quick", action="store_true", help="快速测试模式（仅基础测试）")
    
    args = parser.parse_args()
    
    executor = TestExecutor()
    
    if args.quick:
        print("🏃 快速测试模式")
        if not executor.check_server_health():
            return False
        executor.run_basic_test()
        success = executor.test_results.get("basic_test", {}).get("success", False)
    else:
        include_stress = not args.no_stress
        success = executor.run_all_tests(include_stress=include_stress)
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)