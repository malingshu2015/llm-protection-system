"""置信度评分计算器。"""

import re
from typing import Dict, List, Optional, Tuple, Any

from src.logger import logger
from src.models_interceptor import DetectionResult, DetectionType, Severity, SecurityRule


class ConfidenceScorer:
    """置信度评分计算器。"""

    def __init__(self):
        """初始化置信度评分计算器。"""
        # 上下文权重配置
        self.context_weights = {
            "test_context": -0.3,      # 测试相关上下文降低置信度
            "academic_context": -0.2,   # 学术讨论降低置信度
            "creative_context": -0.25,  # 创作相关降低置信度
            "normal_question": -0.15,   # 正常问题降低置信度
            "attack_indicators": 0.4,   # 攻击指示器增加置信度
            "repetition": 0.2,         # 重复模式增加置信度
            "length_factor": 0.1,      # 长度因子
        }

    def calculate_confidence(
        self, 
        text: str, 
        matched_text: str, 
        rule: SecurityRule,
        context_analysis: Optional[Dict[str, Any]] = None
    ) -> Tuple[float, str, str]:
        """计算检测结果的置信度评分。

        Args:
            text: 完整文本
            matched_text: 匹配的文本
            rule: 触发的安全规则
            context_analysis: 上下文分析结果

        Returns:
            元组包含: (置信度评分, 风险级别, 建议动作)
        """
        base_confidence = 0.8  # 基础置信度
        
        # 1. 基于规则严重程度的基础评分
        severity_scores = {
            Severity.LOW: 0.3,
            Severity.MEDIUM: 0.6,
            Severity.HIGH: 0.8,
            Severity.CRITICAL: 0.9,
        }
        base_confidence = severity_scores.get(rule.severity, 0.5)
        
        # 2. 上下文分析调整
        context_adjustments = self._analyze_context(text, matched_text, rule)
        
        # 3. 模式匹配质量评估
        pattern_quality = self._evaluate_pattern_quality(text, matched_text, rule)
        
        # 4. 文本特征分析
        text_features = self._analyze_text_features(text, matched_text)
        
        # 综合计算置信度
        final_confidence = base_confidence
        
        # 应用上下文调整
        for adjustment_type, adjustment_value in context_adjustments.items():
            weight = self.context_weights.get(adjustment_type, 0)
            final_confidence += weight * adjustment_value
            logger.debug(f"ConfidenceScorer: {adjustment_type} adjustment: {adjustment_value}, weighted: {weight * adjustment_value}")
        
        # 应用模式质量调整
        final_confidence += pattern_quality * 0.2
        
        # 应用文本特征调整
        final_confidence += text_features * 0.1
        
        # 确保置信度在合理范围内
        final_confidence = max(0.0, min(1.0, final_confidence))
        
        # 计算风险级别和建议动作
        risk_level = self._calculate_risk_level(final_confidence, rule.severity)
        suggested_action = self._suggest_action(final_confidence, risk_level, context_adjustments)
        
        logger.debug(f"ConfidenceScorer: Final confidence: {final_confidence:.3f}, risk: {risk_level}, action: {suggested_action}")
        
        return final_confidence, risk_level, suggested_action

    def _analyze_context(self, text: str, matched_text: str, rule: SecurityRule) -> Dict[str, float]:
        """分析文本上下文。

        Args:
            text: 完整文本
            matched_text: 匹配的文本
            rule: 安全规则

        Returns:
            上下文调整字典
        """
        adjustments = {}
        text_lower = text.lower()
        
        # 1. 检测测试/示例上下文
        test_indicators = [
            "test", "testing", "example", "demo", "sample", "mock", "fake", "dummy",
            "测试", "示例", "演示", "样例", "模拟", "虚拟", "假", "例子",
            "for testing", "for example", "just an example", "this is a test",
            "仅供测试", "仅作示例", "这是测试", "这是示例", "举例说明"
        ]
        test_score = sum(1 for indicator in test_indicators if indicator in text_lower)
        if test_score > 0:
            adjustments["test_context"] = min(test_score * 0.3, 1.0)

        # 2. 检测学术/研究上下文
        academic_indicators = [
            "research", "study", "analysis", "academic", "scholarly", "paper",
            "understanding", "explain", "definition", "meaning",
            "研究", "学习", "分析", "学术", "论文", "理解", "解释", "定义", "含义"
        ]
        academic_score = sum(1 for indicator in academic_indicators if indicator in text_lower)
        if academic_score > 0:
            adjustments["academic_context"] = min(academic_score * 0.25, 1.0)

        # 3. 检测创作/虚构上下文
        creative_indicators = [
            "story", "novel", "fiction", "character", "roleplay", "creative writing",
            "script", "dialogue", "narrative", "plot", "game", "simulation",
            "故事", "小说", "虚构", "角色", "角色扮演", "创意写作", "剧本", "对话", "叙述", "游戏", "模拟"
        ]
        creative_score = sum(1 for indicator in creative_indicators if indicator in text_lower)
        if creative_score > 0:
            adjustments["creative_context"] = min(creative_score * 0.3, 1.0)

        # 4. 检测正常问题模式
        question_patterns = [
            r"\b(what|how|why|when|where|who)\b",
            r"\b(什么|如何|为什么|什么时候|哪里|谁)\b",
            r"\?",  # 问号
            r"can you", r"could you", r"would you", r"你能", r"你可以"
        ]
        question_score = sum(1 for pattern in question_patterns if re.search(pattern, text_lower))
        if question_score > 0:
            adjustments["normal_question"] = min(question_score * 0.2, 1.0)

        # 5. 检测明显的攻击指示器
        attack_indicators = [
            "bypass", "override", "ignore safety", "disable filter", "jailbreak",
            "developer mode", "unrestricted", "remove restrictions", "bypass security",
            "绕过", "覆盖", "忽略安全", "禁用过滤", "越狱", "开发者模式", "无限制", "移除限制"
        ]
        attack_score = sum(1 for indicator in attack_indicators if indicator in text_lower)
        if attack_score > 0:
            adjustments["attack_indicators"] = min(attack_score * 0.5, 1.0)

        # 6. 检测重复模式（可能表示尝试绕过）
        words = text_lower.split()
        word_counts = {}
        for word in words:
            if len(word) > 3:  # 忽略短词
                word_counts[word] = word_counts.get(word, 0) + 1
        
        max_repetition = max(word_counts.values()) if word_counts else 1
        if max_repetition > 3:
            adjustments["repetition"] = min((max_repetition - 2) * 0.2, 1.0)

        return adjustments

    def _evaluate_pattern_quality(self, text: str, matched_text: str, rule: SecurityRule) -> float:
        """评估模式匹配质量。

        Args:
            text: 完整文本
            matched_text: 匹配的文本
            rule: 安全规则

        Returns:
            质量评分 (-1.0 到 1.0)
        """
        quality_score = 0.0
        
        # 1. 匹配长度评估
        match_ratio = len(matched_text) / len(text) if text else 0
        if match_ratio > 0.1:  # 匹配部分占比较大
            quality_score += 0.3
        
        # 2. 完整单词匹配
        if re.search(r'\b' + re.escape(matched_text) + r'\b', text, re.IGNORECASE):
            quality_score += 0.2
        
        # 3. 上下文相关性
        context_start = max(0, text.lower().find(matched_text.lower()) - 50)
        context_end = min(len(text), text.lower().find(matched_text.lower()) + len(matched_text) + 50)
        context = text[context_start:context_end].lower()
        
        # 检查是否在句子中间被截断
        if context.count('.') > 0 or context.count('!') > 0 or context.count('?') > 0:
            quality_score += 0.1
        
        return min(max(quality_score, -1.0), 1.0)

    def _analyze_text_features(self, text: str, matched_text: str) -> float:
        """分析文本特征。

        Args:
            text: 完整文本
            matched_text: 匹配的文本

        Returns:
            特征评分 (-1.0 到 1.0)
        """
        feature_score = 0.0
        
        # 1. 文本长度分析
        if len(text) < 50:  # 很短的文本
            feature_score -= 0.2
        elif len(text) > 500:  # 很长的文本，可能是复杂攻击
            feature_score += 0.1
        
        # 2. 特殊字符密度
        special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace())
        special_ratio = special_chars / len(text) if text else 0
        if special_ratio > 0.2:  # 特殊字符过多
            feature_score += 0.1
        
        # 3. 大写字母密度
        upper_chars = sum(1 for c in text if c.isupper())
        upper_ratio = upper_chars / len(text) if text else 0
        if upper_ratio > 0.3:  # 大写字母过多，可能是尝试绕过
            feature_score += 0.15
        
        return min(max(feature_score, -1.0), 1.0)

    def _calculate_risk_level(self, confidence: float, severity: Severity) -> str:
        """计算风险级别。

        Args:
            confidence: 置信度评分
            severity: 规则严重程度

        Returns:
            风险级别字符串
        """
        # 结合置信度和严重程度计算风险级别
        if confidence >= 0.8 and severity in [Severity.HIGH, Severity.CRITICAL]:
            return "critical"
        elif confidence >= 0.7 and severity in [Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]:
            return "high"
        elif confidence >= 0.5:
            return "medium"
        else:
            return "low"

    def _suggest_action(self, confidence: float, risk_level: str, context_adjustments: Dict[str, float]) -> str:
        """建议处理动作。

        Args:
            confidence: 置信度评分
            risk_level: 风险级别
            context_adjustments: 上下文调整

        Returns:
            建议的动作字符串
        """
        # 检查是否有强烈的良性上下文指示器
        has_strong_benign_context = (
            context_adjustments.get("test_context", 0) > 0.5 or
            context_adjustments.get("academic_context", 0) > 0.3 or
            context_adjustments.get("creative_context", 0) > 0.4
        )
        
        # 检查是否有明显的攻击指示器
        has_attack_indicators = context_adjustments.get("attack_indicators", 0) > 0.3
        
        if has_attack_indicators and confidence >= 0.7:
            return "block"
        elif has_strong_benign_context and confidence < 0.6:
            return "allow"
        elif confidence >= 0.8:
            return "block"
        elif confidence >= 0.5:
            return "warn"
        else:
            return "allow"


# 创建全局实例
confidence_scorer = ConfidenceScorer()