"""自适应学习模块 - 实时学习和模式更新系统"""

import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import numpy as np
from collections import defaultdict, deque
import pickle

from src.logger import logger
from src.models_interceptor import DetectionResult, DetectionType, Severity


@dataclass
class LearningData:
    """学习数据点"""
    text: str
    features: List[float]
    label: str  # 'threat', 'benign', 'uncertain'
    confidence: float
    timestamp: datetime
    source: str  # 'human_feedback', 'auto_detection', 'pattern_analysis'
    metadata: Dict[str, Any]


@dataclass
class AttackPattern:
    """攻击模式"""
    pattern_id: str
    pattern_text: str
    pattern_type: str
    similarity_threshold: float
    confidence: float
    frequency: int
    first_seen: datetime
    last_seen: datetime
    effectiveness: float  # 成功率
    variants: List[str]


class PatternLearner:
    """模式学习器 - 从新攻击中学习并更新检测规则"""

    def __init__(self):
        self.learned_patterns = {}
        self.learning_buffer = deque(maxlen=1000)  # 学习缓冲区
        self.pattern_file = "data/learned_patterns.json"
        self.min_pattern_frequency = 3  # 最小模式频率
        self.similarity_threshold = 0.8
        self.effectiveness_threshold = 0.6
        self._load_patterns()

    def _load_patterns(self):
        """加载已学习的模式"""
        try:
            if os.path.exists(self.pattern_file):
                with open(self.pattern_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for pattern_id, pattern_data in data.items():
                        pattern_data['first_seen'] = datetime.fromisoformat(pattern_data['first_seen'])
                        pattern_data['last_seen'] = datetime.fromisoformat(pattern_data['last_seen'])
                        self.learned_patterns[pattern_id] = AttackPattern(**pattern_data)
                logger.info(f"已加载 {len(self.learned_patterns)} 个学习模式")
        except Exception as e:
            logger.error(f"加载学习模式失败: {e}")

    def save_patterns(self):
        """保存学习的模式"""
        try:
            os.makedirs(os.path.dirname(self.pattern_file), exist_ok=True)
            data = {}
            for pattern_id, pattern in self.learned_patterns.items():
                pattern_dict = asdict(pattern)
                pattern_dict['first_seen'] = pattern.first_seen.isoformat()
                pattern_dict['last_seen'] = pattern.last_seen.isoformat()
                data[pattern_id] = pattern_dict

            with open(self.pattern_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info("已保存学习模式")
        except Exception as e:
            logger.error(f"保存学习模式失败: {e}")

    async def learn_from_detection(self, text: str, detection_result: DetectionResult, feedback: str = None):
        """从检测结果中学习"""
        learning_data = LearningData(
            text=text,
            features=self._extract_features(text),
            label=self._determine_label(detection_result, feedback),
            confidence=detection_result.confidence_score if hasattr(detection_result, 'confidence_score') else 0.5,
            timestamp=datetime.now(),
            source='auto_detection',
            metadata={
                'detection_type': detection_result.detection_type.value if detection_result.detection_type else 'unknown',
                'severity': detection_result.severity.value if detection_result.severity else 'low',
                'is_allowed': detection_result.is_allowed
            }
        )

        self.learning_buffer.append(learning_data)

        # 定期分析模式
        if len(self.learning_buffer) % 50 == 0:
            await self._analyze_patterns()

    async def learn_from_feedback(self, text: str, human_label: str, confidence: float = 1.0):
        """从人工反馈中学习"""
        learning_data = LearningData(
            text=text,
            features=self._extract_features(text),
            label=human_label,
            confidence=confidence,
            timestamp=datetime.now(),
            source='human_feedback',
            metadata={'validated': True}
        )

        self.learning_buffer.append(learning_data)
        await self._analyze_patterns()

    def _extract_features(self, text: str) -> List[float]:
        """提取文本特征"""
        features = [
            len(text),
            len(text.split()),
            text.count('!'),
            text.count('?'),
            text.lower().count('ignore'),
            text.lower().count('bypass'),
            text.lower().count('override'),
            len([c for c in text if c.isupper()]) / max(len(text), 1),
            len([c for c in text if not c.isalnum() and not c.isspace()]) / max(len(text), 1)
        ]
        return features

    def _determine_label(self, detection_result: DetectionResult, feedback: str = None) -> str:
        """确定标签"""
        if feedback:
            return feedback

        if not detection_result.is_allowed:
            if detection_result.severity in [Severity.HIGH, Severity.CRITICAL]:
                return 'threat'
            else:
                return 'uncertain'
        else:
            return 'benign'

    async def _analyze_patterns(self):
        """分析学习缓冲区中的模式"""
        if len(self.learning_buffer) < 10:
            return

        # 聚类相似的威胁文本
        threat_texts = [data.text for data in self.learning_buffer if data.label == 'threat']

        if len(threat_texts) < self.min_pattern_frequency:
            return

        # 简单的模式提取（基于n-gram相似性）
        patterns = self._extract_ngram_patterns(threat_texts)

        for pattern_text, frequency in patterns.items():
            if frequency >= self.min_pattern_frequency:
                await self._register_new_pattern(pattern_text, frequency)

    def _extract_ngram_patterns(self, texts: List[str]) -> Dict[str, int]:
        """提取n-gram模式"""
        ngram_counts = defaultdict(int)

        for text in texts:
            # 提取3-gram和4-gram
            words = text.lower().split()
            for n in [3, 4]:
                for i in range(len(words) - n + 1):
                    ngram = ' '.join(words[i:i+n])
                    ngram_counts[ngram] += 1

        # 过滤低频模式
        return {pattern: count for pattern, count in ngram_counts.items()
                if count >= self.min_pattern_frequency}

    async def _register_new_pattern(self, pattern_text: str, frequency: int):
        """注册新的攻击模式"""
        pattern_id = f"learned_{hash(pattern_text) % 100000}"

        if pattern_id in self.learned_patterns:
            # 更新现有模式
            pattern = self.learned_patterns[pattern_id]
            pattern.frequency += frequency
            pattern.last_seen = datetime.now()
        else:
            # 创建新模式
            now = datetime.now()
            self.learned_patterns[pattern_id] = AttackPattern(
                pattern_id=pattern_id,
                pattern_text=pattern_text,
                pattern_type='learned_ngram',
                similarity_threshold=self.similarity_threshold,
                confidence=0.7,
                frequency=frequency,
                first_seen=now,
                last_seen=now,
                effectiveness=0.0,
                variants=[]
            )
            logger.info(f"学习到新攻击模式: {pattern_text}")

    async def check_learned_patterns(self, text: str) -> Optional[AttackPattern]:
        """检查文本是否匹配学习的模式"""
        text_lower = text.lower()

        for pattern in self.learned_patterns.values():
            if pattern.pattern_text in text_lower:
                # 更新模式统计
                pattern.last_seen = datetime.now()
                return pattern

        return None


class AdaptiveThresholdManager:
    """自适应阈值管理器 - 根据历史性能动态调整检测阈值"""

    def __init__(self):
        self.threshold_history = defaultdict(list)
        self.performance_metrics = defaultdict(dict)
        self.adjustment_interval = timedelta(hours=1)
        self.last_adjustment = defaultdict(lambda: datetime.min)

        # 阈值配置
        self.thresholds = {
            'semantic_similarity': 0.7,
            'anomaly_detection': 0.5,
            'behavior_risk': 0.8,
            'confidence_threshold': 0.6
        }

        # 性能目标
        self.target_metrics = {
            'false_positive_rate': 0.05,  # 目标误报率5%
            'false_negative_rate': 0.02,  # 目标漏报率2%
            'precision': 0.95,
            'recall': 0.98
        }

    async def record_detection_result(self, detector_type: str, score: float,
                                    actual_threat: bool, predicted_threat: bool):
        """记录检测结果"""
        result = {
            'score': score,
            'actual': actual_threat,
            'predicted': predicted_threat,
            'timestamp': datetime.now(),
            'threshold': self.thresholds.get(detector_type, 0.5)
        }

        self.threshold_history[detector_type].append(result)

        # 保持最近1000条记录
        if len(self.threshold_history[detector_type]) > 1000:
            self.threshold_history[detector_type] = self.threshold_history[detector_type][-1000:]

        # 定期调整阈值
        if self._should_adjust_threshold(detector_type):
            await self._adjust_threshold(detector_type)

    def _should_adjust_threshold(self, detector_type: str) -> bool:
        """判断是否应该调整阈值"""
        if len(self.threshold_history[detector_type]) < 50:
            return False

        last_adj = self.last_adjustment[detector_type]
        return datetime.now() - last_adj > self.adjustment_interval

    async def _adjust_threshold(self, detector_type: str):
        """调整检测阈值"""
        try:
            history = self.threshold_history[detector_type]
            if len(history) < 50:
                return

            # 计算当前性能指标
            metrics = self._calculate_metrics(history)
            self.performance_metrics[detector_type] = metrics

            current_threshold = self.thresholds[detector_type]
            new_threshold = self._calculate_optimal_threshold(history, metrics)

            # 限制阈值调整幅度
            max_adjustment = 0.1
            adjustment = max(-max_adjustment, min(max_adjustment, new_threshold - current_threshold))

            self.thresholds[detector_type] = current_threshold + adjustment
            self.thresholds[detector_type] = max(0.1, min(0.95, self.thresholds[detector_type]))

            self.last_adjustment[detector_type] = datetime.now()

            logger.info(f"调整 {detector_type} 阈值: {current_threshold:.3f} -> {self.thresholds[detector_type]:.3f}")
            logger.info(f"性能指标: {metrics}")

        except Exception as e:
            logger.error(f"阈值调整失败 {detector_type}: {e}")

    def _calculate_metrics(self, history: List[Dict]) -> Dict[str, float]:
        """计算性能指标"""
        if not history:
            return {}

        true_positives = sum(1 for h in history if h['actual'] and h['predicted'])
        false_positives = sum(1 for h in history if not h['actual'] and h['predicted'])
        true_negatives = sum(1 for h in history if not h['actual'] and not h['predicted'])
        false_negatives = sum(1 for h in history if h['actual'] and not h['predicted'])

        total = len(history)

        metrics = {
            'precision': true_positives / max(true_positives + false_positives, 1),
            'recall': true_positives / max(true_positives + false_negatives, 1),
            'false_positive_rate': false_positives / max(false_positives + true_negatives, 1),
            'false_negative_rate': false_negatives / max(false_negatives + true_positives, 1),
            'accuracy': (true_positives + true_negatives) / total
        }

        return metrics

    def _calculate_optimal_threshold(self, history: List[Dict], current_metrics: Dict[str, float]) -> float:
        """计算最优阈值"""
        # 尝试不同的阈值，找到最优的
        thresholds_to_try = np.arange(0.1, 0.95, 0.05)
        best_threshold = self.thresholds.get('default', 0.5)
        best_score = float('-inf')

        for threshold in thresholds_to_try:
            # 模拟在此阈值下的性能
            simulated_predictions = [h['score'] >= threshold for h in history]
            actual_labels = [h['actual'] for h in history]

            # 计算F1分数作为优化目标
            tp = sum(1 for i in range(len(history)) if actual_labels[i] and simulated_predictions[i])
            fp = sum(1 for i in range(len(history)) if not actual_labels[i] and simulated_predictions[i])
            fn = sum(1 for i in range(len(history)) if actual_labels[i] and not simulated_predictions[i])

            precision = tp / max(tp + fp, 1)
            recall = tp / max(tp + fn, 1)
            f1_score = 2 * precision * recall / max(precision + recall, 1)

            # 考虑误报率惩罚
            fpr = fp / max(fp + sum(1 for i in range(len(history)) if not actual_labels[i]), 1)
            fpr_penalty = max(0, fpr - self.target_metrics['false_positive_rate']) * 2

            score = f1_score - fpr_penalty

            if score > best_score:
                best_score = score
                best_threshold = threshold

        return float(best_threshold)

    def get_threshold(self, detector_type: str) -> float:
        """获取当前阈值"""
        return self.thresholds.get(detector_type, 0.5)


class FeedbackLearning:
    """反馈学习系统 - 从用户反馈中持续改进"""

    def __init__(self):
        self.feedback_data = []
        self.feedback_file = "data/feedback_learning.json"
        self.model_update_threshold = 100  # 累积多少反馈后更新模型
        self._load_feedback()

    def _load_feedback(self):
        """加载反馈数据"""
        try:
            if os.path.exists(self.feedback_file):
                with open(self.feedback_file, 'r', encoding='utf-8') as f:
                    self.feedback_data = json.load(f)
                logger.info(f"已加载 {len(self.feedback_data)} 条反馈数据")
        except Exception as e:
            logger.error(f"加载反馈数据失败: {e}")

    def save_feedback(self):
        """保存反馈数据"""
        try:
            os.makedirs(os.path.dirname(self.feedback_file), exist_ok=True)
            with open(self.feedback_file, 'w', encoding='utf-8') as f:
                json.dump(self.feedback_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存反馈数据失败: {e}")

    async def record_feedback(self, text: str, predicted_threat: bool,
                            actual_threat: bool, confidence: float,
                            user_feedback: str = None):
        """记录用户反馈"""
        feedback_entry = {
            'text': text,
            'predicted_threat': predicted_threat,
            'actual_threat': actual_threat,
            'confidence': confidence,
            'user_feedback': user_feedback,
            'timestamp': datetime.now().isoformat(),
            'is_correct': predicted_threat == actual_threat
        }

        self.feedback_data.append(feedback_entry)

        # 定期保存
        if len(self.feedback_data) % 10 == 0:
            self.save_feedback()

        # 检查是否需要更新模型
        if len(self.feedback_data) % self.model_update_threshold == 0:
            await self._trigger_model_update()

    async def _trigger_model_update(self):
        """触发模型更新"""
        logger.info("触发模型更新，基于反馈数据")

        # 分析反馈数据
        correct_predictions = sum(1 for f in self.feedback_data if f['is_correct'])
        total_feedback = len(self.feedback_data)
        accuracy = correct_predictions / total_feedback if total_feedback > 0 else 0

        logger.info(f"当前模型准确率: {accuracy:.2%} ({correct_predictions}/{total_feedback})")

        # 如果准确率低于阈值，触发重训练
        if accuracy < 0.85:
            await self._retrain_models()

    async def _retrain_models(self):
        """重新训练模型"""
        logger.info("开始重新训练模型")

        # 这里可以集成到增强检测器的ML模型重训练
        # 实际实现中会调用MLThreatDetector的训练方法

        # 准备训练数据
        training_texts = []
        training_labels = []

        for feedback in self.feedback_data[-1000:]:  # 使用最近1000条反馈
            training_texts.append(feedback['text'])
            training_labels.append(1 if feedback['actual_threat'] else 0)

        if len(training_texts) >= 50:
            logger.info(f"使用 {len(training_texts)} 条反馈数据重新训练")
            # 这里会调用实际的模型训练逻辑
            # await self.ml_detector.retrain(training_texts, training_labels)


class AdaptiveLearningSystem:
    """自适应学习系统 - 整合所有学习组件"""

    def __init__(self):
        self.pattern_learner = PatternLearner()
        self.threshold_manager = AdaptiveThresholdManager()
        self.feedback_learning = FeedbackLearning()

        # 学习配置
        self.learning_enabled = True
        self.auto_update_enabled = True
        self.learning_rate = 0.01

    async def process_detection_result(self, text: str, detection_result: DetectionResult,
                                     user_feedback: str = None, actual_threat: bool = None):
        """处理检测结果并进行学习"""
        if not self.learning_enabled:
            return

        try:
            # 模式学习
            await self.pattern_learner.learn_from_detection(text, detection_result, user_feedback)

            # 阈值自适应
            if actual_threat is not None:
                predicted_threat = not detection_result.is_allowed
                confidence = getattr(detection_result, 'confidence_score', 0.5)

                await self.threshold_manager.record_detection_result(
                    'enhanced_detector', confidence, actual_threat, predicted_threat
                )

                # 反馈学习
                await self.feedback_learning.record_feedback(
                    text, predicted_threat, actual_threat, confidence, user_feedback
                )

        except Exception as e:
            logger.error(f"自适应学习处理失败: {e}")

    async def get_adaptive_threshold(self, detector_type: str) -> float:
        """获取自适应阈值"""
        return self.threshold_manager.get_threshold(detector_type)

    async def check_learned_patterns(self, text: str) -> Optional[AttackPattern]:
        """检查学习的攻击模式"""
        return await self.pattern_learner.check_learned_patterns(text)

    def save_all_learning_data(self):
        """保存所有学习数据"""
        try:
            self.pattern_learner.save_patterns()
            self.feedback_learning.save_feedback()
            logger.info("已保存所有学习数据")
        except Exception as e:
            logger.error(f"保存学习数据失败: {e}")


# 创建全局自适应学习系统实例
adaptive_learning_system = AdaptiveLearningSystem()