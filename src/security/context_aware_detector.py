"""上下文感知检测器模块。"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from src.logger import logger
from src.models_interceptor import DetectionResult, DetectionType, Severity
from src.security.conversation_tracker import Conversation


@dataclass
class ContextScore:
    """上下文评分结果。"""
    score: float  # 0.0 - 1.0，越高越可能是攻击
    confidence: float  # 0.0 - 1.0，置信度
    reason: str  # 评分原因


class ContextAwareDetector:
    """上下文感知检测器。"""
    
    def __init__(self):
        """初始化上下文感知检测器。"""
        self.escalation_patterns = self._load_escalation_patterns()
        self.conversation_anomaly_threshold = 0.7
        self.pattern_repetition_threshold = 3
        
    def _load_escalation_patterns(self) -> List[str]:
        """加载升级模式。"""
        return [
            # 逐步升级的攻击模式
            r"(?i)let\s+me\s+try\s+(?:again|differently)",
            r"(?i)what\s+if\s+i\s+asked?",
            r"(?i)can\s+you\s+at\s+least\s+tell\s+me",
            r"(?i)just\s+(?:give|tell)\s+me\s+a\s+hint",
            r"(?i)i\s+promise\s+(?:not\s+to|i\s+won't)",
            r"(?i)this\s+is\s+(?:just|only)\s+for\s+(?:research|education)",
            
            # 中文升级模式
            r"让我重新问一下",
            r"那如果我这样问",
            r"你至少可以告诉我",
            r"给我一个提示",
            r"我保证不会",
            r"这只是为了(?:研究|学习)",
        ]
    
    def detect(self, conversation: Conversation) -> DetectionResult:
        """基于对话上下文进行检测。
        
        Args:
            conversation: 对话对象
            
        Returns:
            检测结果
        """
        if len(conversation.messages) < 2:
            return DetectionResult(is_allowed=True)
        
        # 分析对话模式
        escalation_score = self._analyze_escalation_patterns(conversation)
        repetition_score = self._analyze_pattern_repetition(conversation)
        topic_drift_score = self._analyze_topic_drift(conversation)
        persistence_score = self._analyze_persistence_patterns(conversation)
        
        # 计算综合得分
        total_score = (escalation_score.score * 0.3 + 
                      repetition_score.score * 0.25 + 
                      topic_drift_score.score * 0.25 + 
                      persistence_score.score * 0.2)
        
        # 计算置信度
        confidence = max(escalation_score.confidence, repetition_score.confidence, 
                        topic_drift_score.confidence, persistence_score.confidence)
        
        logger.debug(f"ContextAwareDetector: 总分={total_score:.2f}, 置信度={confidence:.2f}")
        logger.debug(f"  升级模式: {escalation_score.score:.2f}")
        logger.debug(f"  重复模式: {repetition_score.score:.2f}")
        logger.debug(f"  话题漂移: {topic_drift_score.score:.2f}")
        logger.debug(f"  持续性: {persistence_score.score:.2f}")
        
        if total_score > self.conversation_anomaly_threshold:
            return DetectionResult(
                is_allowed=False,
                detection_type=DetectionType.JAILBREAK,
                severity=Severity.HIGH,
                reason=f"上下文感知检测：可疑的对话模式 (得分: {total_score:.2f})",
                details={
                    "total_score": total_score,
                    "confidence": confidence,
                    "escalation_score": escalation_score.score,
                    "repetition_score": repetition_score.score,
                    "topic_drift_score": topic_drift_score.score,
                    "persistence_score": persistence_score.score,
                    "conversation_length": len(conversation.messages)
                }
            )
        
        return DetectionResult(is_allowed=True)
    
    def _analyze_escalation_patterns(self, conversation: Conversation) -> ContextScore:
        """分析升级模式。"""
        if len(conversation.messages) < 3:
            return ContextScore(0.0, 0.0, "对话太短")
        
        escalation_count = 0
        total_user_messages = 0
        
        for message in conversation.messages:
            if message.role == "user":
                total_user_messages += 1
                content = message.content.lower()
                
                # 检查升级模式
                for pattern in self.escalation_patterns:
                    if re.search(pattern, content):
                        escalation_count += 1
                        break
        
        if total_user_messages == 0:
            return ContextScore(0.0, 0.0, "没有用户消息")
        
        escalation_ratio = escalation_count / total_user_messages
        score = min(escalation_ratio * 2, 1.0)  # 最大为1.0
        confidence = 0.8 if escalation_count >= 2 else 0.5
        
        return ContextScore(
            score=score,
            confidence=confidence,
            reason=f"发现{escalation_count}个升级模式，共{total_user_messages}个用户消息"
        )
    
    def _analyze_pattern_repetition(self, conversation: Conversation) -> ContextScore:
        """分析模式重复。"""
        user_messages = [msg.content.lower() for msg in conversation.messages if msg.role == "user"]
        
        if len(user_messages) < 2:
            return ContextScore(0.0, 0.0, "用户消息太少")
        
        # 检查相似的询问模式
        repetition_patterns = [
            r"(?i)(?:can|could|would)\s+you\s+(?:please\s+)?(?:tell|give|show)",
            r"(?i)(?:what|how)\s+(?:about|if)",
            r"(?i)just\s+(?:tell|give|show)\s+me",
            r"(?i)i\s+(?:need|want)\s+(?:to\s+)?(?:know|understand)",
            r"能否告诉我",
            r"可以说一下",
            r"我想知道",
            r"给我说说",
        ]
        
        pattern_counts = {}
        for pattern in repetition_patterns:
            count = sum(1 for msg in user_messages if re.search(pattern, msg))
            if count > 0:
                pattern_counts[pattern] = count
        
        max_repetitions = max(pattern_counts.values()) if pattern_counts else 0
        
        if max_repetitions >= self.pattern_repetition_threshold:
            score = min(max_repetitions / 5.0, 1.0)
            confidence = 0.7
        else:
            score = max_repetitions / 10.0
            confidence = 0.4
        
        return ContextScore(
            score=score,
            confidence=confidence,
            reason=f"最高重复次数: {max_repetitions}"
        )
    
    def _analyze_topic_drift(self, conversation: Conversation) -> ContextScore:
        """分析话题漂移。"""
        user_messages = [msg.content for msg in conversation.messages if msg.role == "user"]
        
        if len(user_messages) < 3:
            return ContextScore(0.0, 0.0, "消息太少无法分析话题漂移")
        
        # 检查话题突然转向敏感内容
        sensitive_topics = [
            "password", "secret", "confidential", "private", "internal",
            "admin", "root", "privilege", "bypass", "override", "hack",
            "密码", "秘密", "机密", "私有", "内部", "管理员", "权限", "绕过", "覆盖"
        ]
        
        topic_shifts = 0
        for i in range(1, len(user_messages)):
            current_msg = user_messages[i].lower()
            previous_msg = user_messages[i-1].lower()
            
            # 检查是否从正常话题突然转向敏感话题
            current_has_sensitive = any(topic in current_msg for topic in sensitive_topics)
            previous_has_sensitive = any(topic in previous_msg for topic in sensitive_topics)
            
            if current_has_sensitive and not previous_has_sensitive:
                topic_shifts += 1
        
        if topic_shifts >= 2:
            score = min(topic_shifts / 3.0, 1.0)
            confidence = 0.6
        else:
            score = topic_shifts / 5.0
            confidence = 0.3
        
        return ContextScore(
            score=score,
            confidence=confidence,
            reason=f"话题转向次数: {topic_shifts}"
        )
    
    def _analyze_persistence_patterns(self, conversation: Conversation) -> ContextScore:
        """分析持续性模式。"""
        user_messages = [msg.content for msg in conversation.messages if msg.role == "user"]
        assistant_messages = [msg.content for msg in conversation.messages if msg.role == "assistant"]
        
        if len(user_messages) < 2 or len(assistant_messages) < 1:
            return ContextScore(0.0, 0.0, "对话太短")
        
        # 检查用户是否在助手拒绝后继续尝试
        persistence_indicators = [
            r"(?i)but\s+(?:what|how)\s+(?:if|about)",
            r"(?i)(?:come\s+on|please)",
            r"(?i)just\s+(?:this\s+)?(?:once|one\s+time)",
            r"(?i)i\s+(?:won't|promise)",
            r"(?i)nobody\s+will\s+know",
            r"但是如果",
            r"拜托",
            r"就这一次",
            r"我保证",
            r"没人会知道",
        ]
        
        refusal_indicators = [
            r"(?i)(?:i\s+)?(?:can't|cannot|won't|will\s+not)\s+(?:help|assist|provide)",
            r"(?i)(?:i'm\s+)?(?:not\s+able|unable)\s+to",
            r"(?i)(?:that's\s+)?(?:not\s+)?(?:appropriate|allowed)",
            r"(?i)i\s+(?:don't|do\s+not)\s+(?:have|provide)",
            r"我不能",
            r"无法提供",
            r"不合适",
            r"不被允许",
        ]
        
        persistence_count = 0
        for i in range(1, len(user_messages)):
            # 检查前一个助手消息是否包含拒绝
            if i <= len(assistant_messages):
                prev_assistant = assistant_messages[i-1].lower()
                if any(re.search(pattern, prev_assistant) for pattern in refusal_indicators):
                    # 检查当前用户消息是否显示持续性
                    current_user = user_messages[i].lower()
                    if any(re.search(pattern, current_user) for pattern in persistence_indicators):
                        persistence_count += 1
        
        if persistence_count >= 2:
            score = min(persistence_count / 3.0, 1.0)
            confidence = 0.8
        else:
            score = persistence_count / 5.0
            confidence = 0.4
        
        return ContextScore(
            score=score,
            confidence=confidence,
            reason=f"持续性尝试次数: {persistence_count}"
        )


# 创建全局上下文感知检测器实例
context_aware_detector = ContextAwareDetector()