# 增强安全检测算法部署指南

## 概述

本文档介绍如何部署和配置增强版的安全检测算法，该算法集成了机器学习、语义分析、行为分析和自适应学习等先进技术。

## 核心特性

### 🔍 多层检测架构
- **语义分析器**: 基于TF-IDF和余弦相似度的深层语义检测
- **机器学习检测器**: 集成异常检测、随机森林、朴素贝叶斯和SVM
- **行为分析器**: 用户长期行为模式分析和风险评估
- **自适应学习**: 从检测结果和用户反馈中持续学习

### 🧠 智能特性
- **实时模式学习**: 自动识别新的攻击模式
- **自适应阈值**: 根据历史性能动态调整检测阈值
- **性能优化**: 自动优化检测性能和准确率
- **故障降级**: 增强检测失败时自动降级到基础检测

## 安装步骤

### 1. 安装增强依赖

```bash
# 安装增强检测所需的依赖包
pip install -r requirements-enhanced.txt

# 或者只安装核心依赖
pip install numpy scikit-learn jieba nltk pandas
```

### 2. 下载中文分词模型

```bash
python -c "import jieba; print('jieba ready')"
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"
```

### 3. 验证安装

```python
from src.security.enhanced_config import EnvironmentValidator

if EnvironmentValidator.validate_dependencies():
    print("✅ 增强检测环境验证通过")
else:
    print("❌ 环境验证失败，请检查依赖安装")
```

## 配置说明

### 基础配置

创建配置文件 `config/enhanced_detection.json`:

```json
{
  "ml_config": {
    "enabled": true,
    "model_update_threshold": 100,
    "target_precision": 0.95,
    "target_recall": 0.90
  },
  "adaptive_config": {
    "enabled": true,
    "pattern_learning_enabled": true,
    "min_pattern_frequency": 3,
    "learning_rate": 0.01
  },
  "performance_config": {
    "enhanced_detection_timeout": 5.0,
    "cache_ttl_seconds": 300,
    "auto_fallback_enabled": true
  },
  "security_config": {
    "enhanced_detection_enabled": true,
    "semantic_analysis_enabled": true,
    "behavior_analysis_enabled": true,
    "threat_thresholds": {
      "low": 0.3,
      "medium": 0.5,
      "high": 0.7,
      "critical": 0.9
    }
  }
}
```

### 环境变量配置

```bash
# 启用增强检测
export ENHANCED_DETECTION_ENABLED=true

# ML模型路径
export ML_MODELS_PATH=data/ml_models/

# 性能监控
export PERFORMANCE_MONITORING=true

# 调试模式
export ENHANCED_DETECTION_DEBUG=false
```

## 集成到现有系统

### 方法1: 替换现有检测器

```python
# 在 src/main.py 或相关模块中
from src.security.integrated_detector import integrated_detector

# 替换原有的安全检测器
app.security_detector = integrated_detector
```

### 方法2: 渐进式集成

```python
# 保留原有检测器作为后备
from src.security.detector import SecurityDetector
from src.security.integrated_detector import integrated_detector

# 根据配置选择检测器
if settings.enhanced_detection_enabled:
    app.security_detector = integrated_detector
else:
    app.security_detector = SecurityDetector()
```

### 方法3: A/B测试集成

```python
import random
from src.security.detector import SecurityDetector
from src.security.integrated_detector import integrated_detector

class ABTestDetector:
    def __init__(self, enhanced_ratio=0.5):
        self.enhanced_ratio = enhanced_ratio
        self.basic_detector = SecurityDetector()
        self.enhanced_detector = integrated_detector

    async def check_request(self, request):
        if random.random() < self.enhanced_ratio:
            return await self.enhanced_detector.check_request(request)
        else:
            return await self.basic_detector.check_request(request)
```

## 性能调优

### 1. 内存优化

```python
# 调整模型缓存大小
from src.security.enhanced_config import config_manager

config_manager.update_config('performance',
    cache_ttl_seconds=600,  # 增加缓存时间
    max_concurrent_detections=50  # 限制并发数
)
```

### 2. 检测延迟优化

```python
# 调整超时设置
config_manager.update_config('performance',
    enhanced_detection_timeout=3.0,  # 降低超时时间
    auto_fallback_enabled=True  # 启用自动降级
)
```

### 3. 准确率调优

```python
# 调整检测阈值
config_manager.update_config('security',
    threat_thresholds={
        'low': 0.2,     # 降低低威胁阈值，减少漏报
        'medium': 0.4,
        'high': 0.6,
        'critical': 0.8
    }
)
```

## 监控和维护

### 1. 性能监控

```python
# 获取性能统计
from src.security.integrated_detector import integrated_detector

stats = integrated_detector.get_performance_stats()
print(f"检测准确率: {1 - stats.get('error_rate', 0):.2%}")
print(f"平均检测时间: {stats.get('avg_detection_time', 0):.3f}s")
print(f"增强检测使用率: {stats.get('enhanced_usage_rate', 0):.2%}")
```

### 2. 学习数据管理

```python
# 保存学习数据
from src.security.adaptive_learning import adaptive_learning_system

adaptive_learning_system.save_all_learning_data()

# 查看学习模式
patterns = adaptive_learning_system.pattern_learner.learned_patterns
print(f"已学习攻击模式数量: {len(patterns)}")
```

### 3. 模型更新

```python
# 手动触发模型重训练
from src.security.enhanced_detector import enhanced_detector

await enhanced_detector.ml_detector.retrain_models()
```

## 故障排除

### 常见问题

1. **依赖包冲突**
   ```bash
   # 解决scikit-learn版本冲突
   pip install --upgrade scikit-learn==1.0.2
   ```

2. **内存不足**
   ```python
   # 降低模型复杂度
   config_manager.update_config('ml',
       model_path="data/ml_models_lite/",
       ensemble_voting="hard"  # 使用硬投票减少内存
   )
   ```

3. **检测超时**
   ```python
   # 调整超时配置
   config_manager.update_config('performance',
       enhanced_detection_timeout=10.0,
       auto_fallback_enabled=True
   )
   ```

### 日志分析

增强检测器的日志包含以下关键信息：

```
INFO - 增强检测完成，耗时: 1.234s
WARNING - 增强检测超时，使用基础检测结果
ERROR - 增强检测失败: [错误详情]
INFO - 学习到新攻击模式: [模式内容]
INFO - 调整 semantic_similarity 阈值: 0.700 -> 0.750
```

## 安全建议

### 1. 生产环境部署

- 🔒 始终启用自动降级机制
- 📊 定期监控性能指标
- 🔄 定期备份学习数据
- 🚨 设置告警阈值

### 2. 数据隐私

```python
# 配置敏感数据脱敏
from src.security.enhanced_config import config_manager

config_manager.update_config('security',
    anonymize_user_data=True,
    log_detection_content=False  # 生产环境禁用内容日志
)
```

### 3. 访问控制

```python
# 限制管理接口访问
config_manager.update_config('security',
    admin_api_enabled=False,  # 生产环境禁用管理API
    feedback_api_auth_required=True
)
```

## 版本升级

### 从基础版本升级

1. **备份现有配置**
   ```bash
   cp -r config/ config_backup/
   cp -r data/ data_backup/
   ```

2. **安装新依赖**
   ```bash
   pip install -r requirements-enhanced.txt
   ```

3. **迁移配置**
   ```python
   # 自动迁移配置
   from src.security.enhanced_config import config_manager
   config_manager.load_config()  # 自动处理配置兼容性
   ```

4. **验证升级**
   ```bash
   python -c "from src.security.integrated_detector import integrated_detector; print('升级成功')"
   ```

## 支持和社区

- 📖 [详细API文档](./api_documentation.md)
- 🐛 [问题报告](https://github.com/malingshu2015/llm-protection-system/issues)
- 💡 [功能建议](https://github.com/malingshu2015/llm-protection-system/discussions)
- 📧 联系支持: support@llm-protection.com

---

> 💡 **提示**: 增强检测算法需要一定的学习时间来达到最佳性能。建议在部署后观察1-2周，让系统自适应学习你的具体使用场景。