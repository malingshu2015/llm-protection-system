"""增强安全检测配置管理"""

import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from src.logger import logger


@dataclass
class MLConfig:
    """机器学习配置"""
    enabled: bool = True
    model_update_threshold: int = 100
    retraining_interval_hours: int = 24
    anomaly_contamination: float = 0.1
    feature_importance_threshold: float = 0.05
    ensemble_voting: str = "hard"  # "hard", "soft"

    # 模型文件路径
    model_path: str = "data/ml_models/"

    # 性能目标
    target_precision: float = 0.95
    target_recall: float = 0.90
    max_false_positive_rate: float = 0.05


@dataclass
class AdaptiveLearningConfig:
    """自适应学习配置"""
    enabled: bool = True
    pattern_learning_enabled: bool = True
    threshold_adaptation_enabled: bool = True
    feedback_learning_enabled: bool = True

    # 学习参数
    min_pattern_frequency: int = 3
    similarity_threshold: float = 0.8
    learning_rate: float = 0.01
    adaptation_interval_minutes: int = 60

    # 数据保存
    save_interval_minutes: int = 10
    max_learning_buffer_size: int = 1000


@dataclass
class PerformanceConfig:
    """性能配置"""
    enhanced_detection_timeout: float = 5.0
    cache_ttl_seconds: int = 300
    max_concurrent_detections: int = 100
    background_optimization_enabled: bool = True

    # 监控配置
    performance_monitoring_enabled: bool = True
    stats_report_interval_minutes: int = 30
    auto_fallback_enabled: bool = True

    # 阈值
    max_timeout_rate: float = 0.1
    max_error_rate: float = 0.05


@dataclass
class SecurityConfig:
    """安全检测配置"""
    # 检测器启用状态
    basic_detection_enabled: bool = True
    enhanced_detection_enabled: bool = True
    semantic_analysis_enabled: bool = True
    behavior_analysis_enabled: bool = True

    # 威胁阈值
    threat_thresholds: Dict[str, float] = None

    # 检测器权重
    detector_weights: Dict[str, float] = None

    def __post_init__(self):
        if self.threat_thresholds is None:
            self.threat_thresholds = {
                'low': 0.3,
                'medium': 0.5,
                'high': 0.7,
                'critical': 0.9
            }

        if self.detector_weights is None:
            self.detector_weights = {
                'semantic': 0.3,
                'ml_anomaly': 0.25,
                'ml_classification': 0.25,
                'behavior': 0.2
            }


@dataclass
class EnhancedDetectionConfig:
    """增强检测完整配置"""
    ml_config: MLConfig = None
    adaptive_config: AdaptiveLearningConfig = None
    performance_config: PerformanceConfig = None
    security_config: SecurityConfig = None

    def __post_init__(self):
        if self.ml_config is None:
            self.ml_config = MLConfig()
        if self.adaptive_config is None:
            self.adaptive_config = AdaptiveLearningConfig()
        if self.performance_config is None:
            self.performance_config = PerformanceConfig()
        if self.security_config is None:
            self.security_config = SecurityConfig()


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_file: str = "config/enhanced_detection.json"):
        self.config_file = config_file
        self.config = EnhancedDetectionConfig()
        self.load_config()

    def load_config(self):
        """加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self.config = self._dict_to_config(data)
                logger.info(f"已加载增强检测配置: {self.config_file}")
            else:
                logger.info("配置文件不存在，使用默认配置")
                self.save_config()  # 保存默认配置

        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            logger.info("使用默认配置")

    def save_config(self):
        """保存配置"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)

            data = self._config_to_dict(self.config)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"配置已保存: {self.config_file}")

        except Exception as e:
            logger.error(f"保存配置失败: {e}")

    def _config_to_dict(self, config: EnhancedDetectionConfig) -> Dict[str, Any]:
        """配置对象转字典"""
        return {
            'ml_config': asdict(config.ml_config),
            'adaptive_config': asdict(config.adaptive_config),
            'performance_config': asdict(config.performance_config),
            'security_config': asdict(config.security_config)
        }

    def _dict_to_config(self, data: Dict[str, Any]) -> EnhancedDetectionConfig:
        """字典转配置对象"""
        return EnhancedDetectionConfig(
            ml_config=MLConfig(**data.get('ml_config', {})),
            adaptive_config=AdaptiveLearningConfig(**data.get('adaptive_config', {})),
            performance_config=PerformanceConfig(**data.get('performance_config', {})),
            security_config=SecurityConfig(**data.get('security_config', {}))
        )

    def update_config(self, section: str, **kwargs):
        """更新配置"""
        try:
            if section == 'ml':
                for key, value in kwargs.items():
                    if hasattr(self.config.ml_config, key):
                        setattr(self.config.ml_config, key, value)
            elif section == 'adaptive':
                for key, value in kwargs.items():
                    if hasattr(self.config.adaptive_config, key):
                        setattr(self.config.adaptive_config, key, value)
            elif section == 'performance':
                for key, value in kwargs.items():
                    if hasattr(self.config.performance_config, key):
                        setattr(self.config.performance_config, key, value)
            elif section == 'security':
                for key, value in kwargs.items():
                    if hasattr(self.config.security_config, key):
                        setattr(self.config.security_config, key, value)

            self.save_config()
            logger.info(f"已更新 {section} 配置: {kwargs}")

        except Exception as e:
            logger.error(f"更新配置失败: {e}")

    def get_config(self) -> EnhancedDetectionConfig:
        """获取配置"""
        return self.config

    def reset_to_defaults(self):
        """重置为默认配置"""
        self.config = EnhancedDetectionConfig()
        self.save_config()
        logger.info("配置已重置为默认值")


class EnvironmentValidator:
    """环境验证器"""

    @staticmethod
    def validate_dependencies():
        """验证依赖项"""
        required_packages = [
            'numpy',
            'scikit-learn',
            'jieba'
        ]

        missing_packages = []
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)

        if missing_packages:
            logger.error(f"缺少必需的包: {missing_packages}")
            logger.info("请安装: pip install " + " ".join(missing_packages))
            return False

        logger.info("所有依赖项验证通过")
        return True

    @staticmethod
    def validate_directories(config: EnhancedDetectionConfig):
        """验证目录结构"""
        required_dirs = [
            config.ml_config.model_path,
            "data/behavior_profiles",
            "data/learned_patterns",
            "config"
        ]

        for dir_path in required_dirs:
            try:
                os.makedirs(dir_path, exist_ok=True)
                logger.debug(f"目录验证通过: {dir_path}")
            except Exception as e:
                logger.error(f"创建目录失败 {dir_path}: {e}")
                return False

        logger.info("目录结构验证通过")
        return True

    @staticmethod
    def validate_permissions():
        """验证文件权限"""
        test_file = "data/.permission_test"
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            logger.info("文件权限验证通过")
            return True
        except Exception as e:
            logger.error(f"文件权限验证失败: {e}")
            return False


# 创建全局配置管理器
config_manager = ConfigManager()

# 验证环境
if EnvironmentValidator.validate_dependencies():
    EnvironmentValidator.validate_directories(config_manager.get_config())
    EnvironmentValidator.validate_permissions()
else:
    logger.warning("环境验证失败，某些功能可能不可用")