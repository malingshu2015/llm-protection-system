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
        
        # 检查当前请求是否独立无害（排除历史污染）
        current_message = conversation.messages[-1]  # 最新的用户消息
        if current_message.role == "user":
            if self._is_current_request_benign(current_message.content):
                logger.debug("当前请求本身是无害的，允许通过")
                return DetectionResult(is_allowed=True)
        
        # 分析对话模式（仅针对真正可疑的模式）
        escalation_score = self._analyze_escalation_patterns(conversation)
        repetition_score = self._analyze_pattern_repetition(conversation)
        topic_drift_score = self._analyze_topic_drift(conversation)
        persistence_score = self._analyze_persistence_patterns(conversation)
        
        # 调整权重：降低话题漂移权重，提高升级和持续性权重
        total_score = (escalation_score.score * 0.4 + 
                      repetition_score.score * 0.2 + 
                      topic_drift_score.score * 0.1 +  # 降低话题漂移权重
                      persistence_score.score * 0.3)   # 提高持续性权重
        
        # 计算置信度
        confidence = max(escalation_score.confidence, repetition_score.confidence, 
                        topic_drift_score.confidence, persistence_score.confidence)
        
        logger.debug(f"ContextAwareDetector: 总分={total_score:.2f}, 置信度={confidence:.2f}")
        logger.debug(f"  当前消息: {current_message.content[:50]}...")
        logger.debug(f"  升级模式: {escalation_score.score:.2f}")
        logger.debug(f"  重复模式: {repetition_score.score:.2f}")
        logger.debug(f"  话题漂移: {topic_drift_score.score:.2f}")
        logger.debug(f"  持续性: {persistence_score.score:.2f}")
        
        # 提高阈值，减少误报
        adjusted_threshold = 0.8  # 从0.7提高到0.8
        
        if total_score > adjusted_threshold:
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
                    "conversation_length": len(conversation.messages),
                    "current_message": current_message.content[:100]
                }
            )
        
        return DetectionResult(is_allowed=True)
    
    def _is_current_request_benign(self, content: str) -> bool:
        """检查当前请求是否本身无害。
        
        Args:
            content: 当前请求内容
            
        Returns:
            如果当前请求本身无害则返回True
        """
        content_lower = content.lower()
        
        # 明显无害的问题类型
        benign_patterns = [
            # 知识性问题
            r"(?i)what\s+(?:is|are|does|means?)",
            r"(?i)how\s+(?:to|do|does|can)",
            r"(?i)why\s+(?:is|are|do|does)",
            r"(?i)when\s+(?:is|are|do|does)",
            r"(?i)where\s+(?:is|are|can)",
            r"(?i)who\s+(?:is|are|was)",
            r"(?i)explain\s+(?:what|how|why)",
            r"(?i)tell\s+me\s+about",
            r"(?i)describe\s+(?:the|how|what)",
            
            # 中文知识性问题
            r"什么是",
            r"如何.*(?:做|实现|完成|操作)",
            r"怎么.*(?:做|用|实现|操作)",
            r"为什么",
            r"哪里.*(?:可以|能够)",
            r"谁是",
            r"请介绍",
            r"请解释",
            r"请说明",
            r"告诉我.*(?:关于|什么)",
            r"解释一下",
            
            # 特定中国文化和历史问题
            r".*是.*(?:成语|典故|俗语|谚语)",
            r".*出五服.*",  # 专门处理"不出五服"这类问题
            r".*(?:朝代|历史|古代|传统)",
            r".*(?:文化|习俗|风俗)",
            
            # 特定无害词汇
            r"(?i)(?:definition|meaning|concept|idea)",
            r"(?i)(?:learn|study|understand|know)",
            r"(?i)(?:help|assist|support|guide)",
            r"定义",
            r"含义",
            r"概念",
            r"学习",
            r"了解",
            r"理解",
            r"帮助",
        ]
        
        # 检查是否匹配无害模式
        for pattern in benign_patterns:
            if re.search(pattern, content):
                logger.debug(f"匹配到无害模式: {pattern}")
                return True
        
        # 检查是否包含明显的敏感词汇（如果包含则不认为无害）
        sensitive_keywords = [
            "bomb", "explosive", "weapon", "kill", "attack", "hack", "bypass",
            "炸弹", "爆炸", "武器", "杀", "攻击", "黑客", "绕过", "破解"
        ]
        
        for keyword in sensitive_keywords:
            if keyword in content_lower:
                logger.debug(f"当前请求包含敏感词汇: {keyword}")
                return False
        
        # 如果请求很短且简单，也认为是无害的
        if len(content.strip()) < 50 and not any(char in content for char in ['!', '?', '*', '#']):
            logger.debug("当前请求简短且简单，认为无害")
            return True
            
        return False
    
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