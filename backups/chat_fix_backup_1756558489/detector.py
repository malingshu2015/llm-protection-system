"""Security detection module for identifying and mitigating security threats."""

import asyncio
import hashlib
import json
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from src.audit.event_logger import event_logger
from src.config import settings
from src.logger import logger
from src.models_interceptor import DetectionResult, DetectionType, InterceptedRequest, InterceptedResponse, SecurityRule, Severity
from src.security.detection_cache import CacheableDetectorMixin
from src.security.smart_cache import cache_manager


class PromptInjectionDetector(CacheableDetectorMixin):
    """Detector for prompt injection attacks."""

    def __init__(self):
        """Initialize the prompt injection detector."""
        super().__init__()
        self.rules = self._load_rules()
        # 预编译正则表达式
        self._compile_patterns()

    def _load_rules(self) -> List[SecurityRule]:
        """Load prompt injection rules from the rules file.

        Returns:
            A list of security rules.
        """
        rules_path = settings.security.prompt_injection_rules_path

        # Create default rules if file doesn't exist
        if not os.path.exists(rules_path):
            os.makedirs(os.path.dirname(rules_path), exist_ok=True)

            default_rules = [
                SecurityRule(
                    id="pi-001",
                    name="Ignore Previous Instructions",
                    description="Detects attempts to make the model ignore previous instructions",
                    detection_type=DetectionType.PROMPT_INJECTION,
                    severity=Severity.HIGH,
                    patterns=[
                        r"(?i)ignore\s+(?:all\s+)?(?:previous|above|earlier)\s+instructions",
                        r"(?i)disregard\s+(?:all\s+)?(?:previous|above|earlier)\s+instructions",
                    ],
                    keywords=["ignore", "disregard", "previous instructions"],
                    priority=10,  # 高优先级
                    categories=["prompt_injection"],
                    block=True,
                ),
                SecurityRule(
                    id="pi-002",
                    name="System Prompt Extraction",
                    description="Detects attempts to extract the system prompt",
                    detection_type=DetectionType.PROMPT_INJECTION,
                    severity=Severity.HIGH,
                    patterns=[
                        r"(?i)what\s+(?:was|were)\s+your\s+instructions",
                        r"(?i)tell\s+me\s+your\s+instructions",
                        r"(?i)what\s+(?:is|are)\s+your\s+system\s+prompt",
                    ],
                    keywords=["instructions", "system prompt"],
                    priority=20,
                    categories=["prompt_injection"],
                    block=True,
                ),
                SecurityRule(
                    id="pi-003",
                    name="DAN (Do Anything Now) Jailbreak",
                    description="Detects DAN jailbreak attempts",
                    detection_type=DetectionType.JAILBREAK,
                    severity=Severity.CRITICAL,
                    patterns=[
                        r"(?i)you\s+are\s+now\s+DAN",
                        r"(?i)DAN\s+mode\s+enabled",
                        r"(?i)Do\s+Anything\s+Now",
                    ],
                    keywords=["DAN", "Do Anything Now"],
                    priority=5,  # 最高优先级
                    categories=["jailbreak"],
                    block=True,
                ),
            ]

            with open(rules_path, "w") as f:
                json.dump([rule.model_dump() for rule in default_rules], f, indent=2)

            return default_rules

        # Load rules from file
        try:
            with open(rules_path, "r") as f:
                rules_data = json.load(f)

            rules = [SecurityRule(**rule) for rule in rules_data]
            # 按优先级排序
            rules.sort(key=lambda x: x.priority)
            return rules
        except Exception as e:
            logger.error(f"Error loading prompt injection rules: {e}")
            return []

    def _compile_patterns(self):
        """预编译正则表达式以提高性能。"""
        for rule in self.rules:
            rule.compiled_patterns = []
            for pattern in rule.patterns:
                try:
                    rule.compiled_patterns.append(re.compile(pattern, re.IGNORECASE))
                except re.error as e:
                    logger.error(f"正则表达式编译错误 (规则 {rule.id}): {pattern} - {e}")
                    # 添加一个不会匹配任何内容的正则表达式作为占位符
                    rule.compiled_patterns.append(re.compile(r"^\b$"))

    async def detect(self, text: str) -> DetectionResult:
        """Detect prompt injection in text.

        Args:
            text: The text to check.

        Returns:
            The detection result.
        """
        # 首先尝试从缓存获取结果
        cached_result = self.detect_with_cache(text)
        if cached_result:
            return cached_result
        
        text_lower = text.lower()  # 只转换一次小写

        for rule in self.rules:
            if not rule.enabled:
                continue

            # 使用预编译的正则表达式
            for i, compiled_pattern in enumerate(rule.compiled_patterns):
                match = compiled_pattern.search(text)
                if match:
                    matched_text = match.group(0)
                    
                    # 添加上下文检查，减少误报
                    if self._is_likely_false_positive(text, matched_text, rule):
                        logger.debug(f"PromptInjectionDetector: 跳过可能的误报: {rule.name} - {matched_text}")
                        continue
                    
                    # 计算置信度评分
                    from src.security.confidence_scorer import confidence_scorer
                    confidence, risk_level, suggested_action = confidence_scorer.calculate_confidence(
                        text, matched_text, rule
                    )
                    
                    result = DetectionResult(
                        is_allowed=not rule.block if suggested_action != "allow" else True,
                        detection_type=rule.detection_type,
                        severity=rule.severity,
                        reason=f"Detected {rule.name}: {matched_text}",
                        details={
                            "rule_id": rule.id,
                            "rule_name": rule.name,
                            "matched_pattern": rule.patterns[i],
                            "matched_text": matched_text,
                        },
                        confidence_score=confidence,
                        risk_level=risk_level,
                        suggested_action=suggested_action,
                        context_analysis={
                            "pattern_match": True,
                            "pattern_index": i,
                            "false_positive_check": False
                        }
                    )
                    
                    # 缓存结果
                    self.cache_result(text, result)
                    return result

            # 检查关键词（使用更精确的匹配）
            for keyword in rule.keywords:
                if self._keyword_matches_precisely(text_lower, keyword.lower()):
                    # 添加上下文检查
                    if self._is_likely_false_positive(text, keyword, rule):
                        logger.debug(f"PromptInjectionDetector: 跳过可能的误报关键词: {rule.name} - {keyword}")
                        continue
                    
                    # 计算置信度评分
                    from src.security.confidence_scorer import confidence_scorer
                    confidence, risk_level, suggested_action = confidence_scorer.calculate_confidence(
                        text, keyword, rule
                    )
                        
                    result = DetectionResult(
                        is_allowed=not rule.block if suggested_action != "allow" else True,
                        detection_type=rule.detection_type,
                        severity=rule.severity,
                        reason=f"Detected {rule.name}: {keyword}",
                        details={
                            "rule_id": rule.id,
                            "rule_name": rule.name,
                            "matched_keyword": keyword,
                        },
                        confidence_score=confidence,
                        risk_level=risk_level,
                        suggested_action=suggested_action,
                        context_analysis={
                            "keyword_match": True,
                            "false_positive_check": False
                        }
                    )
                    
                    # 缓存结果
                    self.cache_result(text, result)
                    return result

        # No detection - 缓存允许的结果
        result = DetectionResult(is_allowed=True)
        self.cache_result(text, result)
        return result

    def _keyword_matches_precisely(self, text: str, keyword: str) -> bool:
        """更精确的关键词匹配，考虑词边界。

        Args:
            text: 文本
            keyword: 关键词

        Returns:
            是否匹配
        """
        import re
        # 使用词边界匹配，避免部分匹配
        pattern = r'\b' + re.escape(keyword) + r'\b'
        return bool(re.search(pattern, text))

    def _is_likely_false_positive(self, text: str, matched_text: str, rule: SecurityRule) -> bool:
        """检查是否可能是误报。

        Args:
            text: 完整文本
            matched_text: 匹配的文本
            rule: 安全规则

        Returns:
            是否可能是误报
        """
        # 查找匹配文本在完整文本中的位置
        match_start = text.lower().find(matched_text.lower())
        if match_start == -1:
            return False

        # 获取匹配文本前后的上下文（各200个字符）
        context_start = max(0, match_start - 200)
        context_end = min(len(text), match_start + len(matched_text) + 200)
        context = text[context_start:context_end].lower()
        
        # 获取更大的上下文用于深度分析
        full_context = text.lower()

        # 1. 检查是否在正常对话或学术讨论中
        normal_context_indicators = [
            # 询问类
            "what is", "what are", "what does", "can you explain", "help me understand",
            "tell me about", "describe", "explain", "definition of", "meaning of",
            "how does", "how do", "how can", "why does", "why do",
            # 中文询问类
            "什么是", "你能解释", "帮我理解", "告诉我", "描述一下", "解释一下",
            "如何", "为什么", "怎么", "怎样", "请说明",
            # 学术讨论类
            "学习", "研究", "讨论", "分析", "understanding", "research", "study",
            "analysis", "academic", "scholarly", "educational", "learning",
            # 引用类
            "in literature", "in movies", "in fiction", "in stories", "in books",
            "在文学中", "在电影中", "在小说中", "在故事中", "在书中", "在游戏中",
            "according to", "based on", "references", "citations",
            # 假设类
            "hypothetically", "theoretically", "假设", "理论上", "假如", "如果",
            "suppose", "imagine", "what if", "in theory",
            # 示例类
            "for example", "for instance", "such as", "like", "including",
            "例如", "比如", "举例", "包括", "类似", "比方说"
        ]

        # 2. 检查创作和写作相关的上下文
        creative_context_indicators = [
            "write", "writing", "story", "novel", "character", "fiction",
            "script", "screenplay", "dialogue", "narrative", "creative",
            "写作", "创作", "故事", "小说", "角色", "剧本", "对话", "叙述",
            "roleplay", "role-play", "playing", "game", "simulation",
            "角色扮演", "扮演", "游戏", "模拟"
        ]

        # 3. 检查技术讨论和编程相关上下文
        technical_context_indicators = [
            "code", "programming", "software", "development", "algorithm",
            "function", "method", "class", "variable", "syntax",
            "代码", "编程", "程序", "开发", "算法", "函数", "方法",
            "debug", "testing", "example code", "tutorial", "documentation"
        ]

        # 检查所有上下文指示器
        all_indicators = normal_context_indicators + creative_context_indicators + technical_context_indicators
        for indicator in all_indicators:
            if indicator in context:
                logger.debug(f"PromptInjectionDetector: 发现正常上下文指示器: {indicator}")
                return True

        # 4. 特定规则的深度分析
        if rule.id == "pi-001" and "ignore" in matched_text.lower():
            # "ignore"相关检测的特殊处理
            normal_ignore_contexts = [
                # 正常使用ignore的情况
                "ignore the noise", "ignore this error", "ignore that",
                "can ignore", "should ignore", "will ignore", "might ignore",
                "don't ignore", "cannot ignore", "never ignore", "please ignore",
                "choose to ignore", "decide to ignore", "try to ignore",
                # 中文正常使用
                "忽略", "忽视", "不要理会", "可以忽略", "应该忽略",
                "选择忽略", "决定忽略", "尝试忽略",
                # 技术相关
                "ignore case", "ignore whitespace", "ignore errors",
                "git ignore", ".gitignore", "eslint ignore"
            ]
            for ctx in normal_ignore_contexts:
                if ctx in context:
                    return True
            
            # 检查是否包含明显的攻击意图
            attack_indicators = [
                "previous instructions", "above instructions", "system prompt",
                "earlier instructions", "initial prompt", "original instructions",
                "之前的指令", "上面的指令", "系统提示", "原始指令"
            ]
            for indicator in attack_indicators:
                if indicator in context:
                    return False  # 包含攻击指示器，不是误报

        # 5. 检查是否包含明显的良性意图指示器
        benign_intent_indicators = [
            "just curious", "out of curiosity", "wondering", "interested in",
            "for educational purposes", "for learning", "for research",
            "只是好奇", "出于好奇", "想知道", "感兴趣", "为了学习", "为了研究"
        ]
        
        for indicator in benign_intent_indicators:
            if indicator in full_context:
                logger.debug(f"PromptInjectionDetector: 发现良性意图指示器: {indicator}")
                return True

        # 6. 长度和复杂性检查
        if len(text) < 50:  # 很短的文本，可能是正常询问
            simple_patterns = [
                r"\b(what|how|why|when|where|who)\b",
                r"\b(什么|如何|为什么|什么时候|哪里|谁)\b"
            ]
            for pattern in simple_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return True

        return False


class SensitiveInfoDetector:
    """Detector for sensitive information."""

    def __init__(self):
        """Initialize the sensitive information detector."""
        self.patterns = self._load_patterns()
        # 预编译正则表达式
        self.compiled_patterns = self._compile_patterns()
        
        # 白名单机制
        self.whitelists = self._load_whitelists()

    def _load_patterns(self) -> Dict[str, List[str]]:
        """Load sensitive information patterns from the patterns file.

        Returns:
            A dictionary of pattern types and their regex patterns.
        """
        patterns_path = settings.security.sensitive_info_patterns_path
        logger.info(f"SensitiveInfoDetector: 加载模式文件: {patterns_path}")

        # Create default patterns if file doesn't exist
        if not os.path.exists(patterns_path):
            logger.warning(f"SensitiveInfoDetector: 模式文件不存在，创建默认模式: {patterns_path}")
            os.makedirs(os.path.dirname(patterns_path), exist_ok=True)

            default_patterns = {
                "credit_card": [
                    r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})\b"
                ],
                "ssn": [
                    r"\b(?!000|666|9\d{2})([0-8]\d{2}|7([0-6]\d|7[012]))([-]?|\s{1})(?!00)\d\d\2(?!0000)\d{4}\b"
                ],
                "email": [
                    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
                ],
                "phone": [
                    r"\b(?:\+\d{1,3}[-\.\s]?)?\(?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{4}\b"
                ],
                "api_key": [
                    r"\b(?:api[_-]?key|access[_-]?key|secret[_-]?key)[_-]?(?:id)?[:=]\s*['\"]?([a-zA-Z0-9]{16,})"
                ],
                "password": [
                    r"\b(?:password|passwd|pwd)[:=]\s*['\"]([^'\"]{8,})['\"]",
                    r"\b(?:password|passwd|pwd)[:=]\s*['\"]([^'\"]+)['\"]",
                    r"\b(?:password|passwd|pwd)\s+is\s+['\"]?([^'\"\s]+)['\"]?",
                    r"\b(?:我的|my)[.\s]*(?:密码|password)[.\s]*(?:是|is)[.\s]*([A-Za-z0-9!@#$%^&*()_+\-=\[\]{};:'\"\\|,.<>\/\?]{8,})",
                    r"\b(?:我的|my)[.\s]*(?:密码|password)[.\s]*(?:是|is)[.\s]*([A-Za-z0-9!@#$%^&*()_+\-=\[\]{};:'\"\\|,.<>\/\?]+)",
                    r"\b(?:我的|my)[.\s]*(?:密码|password)[.\s]*(?:是|is)[.\s]*([^\s]+)",
                    r"\b(?:我的|my)[.\s]*(?:密码|password)[.\s]*(?:是|is)[.\s]*Password123!",
                    r"\b(?:我的|my)[.\s]*(?:密码|password)[.\s]*(?:是|is)\s+Password123!",
                    r"\b(?:我的|my)[.\s]*(?:密码|password)\s+Password123!",
                    r"\b(?:我的|my)[.\s]*(?:密码|password)[.\s]*(?:是|is)[.\s]*Password123!，",
                    r"\b(?:我的|my)[.\s]*(?:密码|password)[.\s]*(?:是|is)\s+Password123!，",
                    r"\b(?:我的|my)[.\s]*(?:密码|password)\s+Password123!，",
                    r"\b(?:我的|my)[.\s]*(?:密码|password)[.\s]*(?:是|is)[.\s]*Password123!，请",
                    r"\b(?:我的|my)[.\s]*(?:密码|password)[.\s]*(?:是|is)\s+Password123!，请",
                    r"\b(?:我的|my)[.\s]*(?:密码|password)\s+Password123!，请",
                    r"\b(?:我的|my)[.\s]*(?:密码|password)[.\s]*(?:是|is)[.\s]*Password123!，请帮我记住",
                    r"\b(?:我的|my)[.\s]*(?:密码|password)[.\s]*(?:是|is)\s+Password123!，请帮我记住",
                    r"\b(?:我的|my)[.\s]*(?:密码|password)\s+Password123!，请帮我记住"
                ],
            }

            with open(patterns_path, "w") as f:
                json.dump(default_patterns, f, indent=2, ensure_ascii=False)

            return default_patterns

        # Load patterns from file
        try:
            logger.info(f"SensitiveInfoDetector: 尝试从文件加载模式: {patterns_path}")
            with open(patterns_path, "r") as f:
                patterns = json.load(f)

            logger.info(f"SensitiveInfoDetector: 成功加载模式数据，模式类型数量: {len(patterns)}")
            return patterns
        except Exception as e:
            logger.error(f"SensitiveInfoDetector: 加载敏感信息模式错误: {e}")
            # 返回默认模式作为备份
            return {
                "credit_card": [
                    r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})\b"
                ],
                "ssn": [
                    r"\b(?!000|666|9\d{2})([0-8]\d{2}|7([0-6]\d|7[012]))([-]?|\s{1})(?!00)\d\d\2(?!0000)\d{4}\b"
                ],
                "email": [
                    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
                ],
                "phone": [
                    r"\b(?:\+\d{1,3}[-\.\s]?)?\(?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{4}\b"
                ],
                "api_key": [
                    r"\b(?:api[_-]?key|access[_-]?key|secret[_-]?key)[_-]?(?:id)?[:=]\s*['\"]?([a-zA-Z0-9]{16,})"
                ],
                "password": [
                    r"\b(?:我的|my)[.\s]*(?:密码|password)[.\s]*(?:是|is)[.\s]*Password123!",
                    r"\b(?:我的|my)[.\s]*(?:密码|password)[.\s]*(?:是|is)\s+Password123!",
                    r"\b(?:我的|my)[.\s]*(?:密码|password)\s+Password123!",
                    r"\b(?:我的|my)[.\s]*(?:密码|password)[.\s]*(?:是|is)[.\s]*Password123!，请帮我记住",
                    r"\b(?:我的|my)[.\s]*(?:密码|password)[.\s]*(?:是|is)\s+Password123!，请帮我记住",
                    r"\b(?:我的|my)[.\s]*(?:密码|password)\s+Password123!，请帮我记住"
                ],
            }

    def _load_whitelists(self) -> Dict[str, List[str]]:
        """加载白名单配置。

        Returns:
            白名单字典，键为类型，值为白名单项列表。
        """
        # 定义默认白名单
        default_whitelists = {
            "credit_card": [
                "4111111111111111",  # 测试用Visa卡号
                "4000000000000002",  # 测试用Visa卡号
                "5555555555554444",  # 测试用万事达卡号
                "5105105105105100",  # 测试用万事达卡号
                "378282246310005",   # 测试用美国运通卡号
                "371449635398431",   # 测试用美国运通卡号
                "6011111111111117",  # 测试用Discover卡号
                "6011000990139424",  # 测试用Discover卡号
            ],
            "phone": [
                "911",               # 紧急电话
                "110",               # 中国报警电话
                "120",               # 中国急救电话
                "119",               # 中国消防电话
                "400-123-4567",      # 示例客服电话格式
                "800-123-4567",      # 示例免费电话格式
                "400-920-9200",      # 支付宝客服
                "95188",             # 支付宝客服
                "400-923-9699",      # 心理健康热线
                "400-161-9995",      # 心理危机干预热线
            ],
            "email": [
                "test@example.com",     # 测试邮箱
                "admin@example.com",    # 示例管理员邮箱
                "support@example.com",  # 示例支持邮箱
                "noreply@example.com",  # 示例无回复邮箱
                "example@test.com",     # 测试邮箱
                "demo@demo.com",        # 演示邮箱
            ],
            "password": [
                "password123",          # 示例密码
                "123456",              # 示例弱密码
                "admin123",            # 示例管理员密码
                "test123",             # 示例测试密码
                "demo123",             # 示例演示密码
            ],
            "api_key": [
                "demo_api_key_12345",           # 示例API密钥
                "test_key_abcdef123456",        # 示例测试密钥
                "example_api_key_1234567890",   # 示例API密钥
            ]
        }

        # 尝试从文件加载白名单
        whitelist_path = "rules/sensitive_info_whitelist.json"
        if os.path.exists(whitelist_path):
            try:
                with open(whitelist_path, "r") as f:
                    file_whitelists = json.load(f)
                # 合并默认白名单和文件白名单
                for category, items in file_whitelists.items():
                    if category in default_whitelists:
                        default_whitelists[category].extend(items)
                    else:
                        default_whitelists[category] = items
                logger.info(f"SensitiveInfoDetector: 成功加载白名单文件: {whitelist_path}")
            except Exception as e:
                logger.error(f"SensitiveInfoDetector: 加载白名单文件失败: {e}")
        else:
            # 创建默认白名单文件
            os.makedirs(os.path.dirname(whitelist_path), exist_ok=True)
            try:
                with open(whitelist_path, "w") as f:
                    json.dump(default_whitelists, f, indent=2, ensure_ascii=False)
                logger.info(f"SensitiveInfoDetector: 创建默认白名单文件: {whitelist_path}")
            except Exception as e:
                logger.error(f"SensitiveInfoDetector: 创建白名单文件失败: {e}")

        return default_whitelists

    def _is_whitelisted(self, pattern_type: str, matched_text: str) -> bool:
        """检查匹配的文本是否在白名单中。

        Args:
            pattern_type: 模式类型
            matched_text: 匹配的文本

        Returns:
            是否在白名单中
        """
        if pattern_type not in self.whitelists:
            return False

        # 清理匹配文本
        cleaned_text = matched_text.strip()
        
        # 检查是否在白名单中
        for whitelist_item in self.whitelists[pattern_type]:
            if cleaned_text.lower() == whitelist_item.lower():
                logger.debug(f"SensitiveInfoDetector: 匹配项在白名单中: {pattern_type} - {cleaned_text}")
                return True
        
        return False

    async def _is_whitelisted_async(self, pattern_type: str, matched_text: str) -> bool:
        """异步版本：检查匹配的文本是否在白名单中。
        
        Args:
            pattern_type: 模式类型
            matched_text: 匹配的文本
            
        Returns:
            是否在白名单中
        """
        # 对于白名单检查，实际上不需要I/O操作，但我们使用async来保持一致性
        return await asyncio.get_event_loop().run_in_executor(
            None, self._is_whitelisted, pattern_type, matched_text
        )

    def _has_context_indicators(self, text: str, matched_text: str) -> bool:
        """检查是否有上下文指示器表明这是测试/示例数据。

        Args:
            text: 完整文本
            matched_text: 匹配的文本

        Returns:
            是否有上下文指示器
        """
        # 查找匹配文本在完整文本中的位置
        match_start = text.find(matched_text)
        if match_start == -1:
            return False

        # 获取匹配文本前后的上下文（各100个字符）
        context_start = max(0, match_start - 100)
        context_end = min(len(text), match_start + len(matched_text) + 100)
        context = text[context_start:context_end].lower()

        # 检查测试/示例相关的关键词
        test_indicators = [
            "test", "testing", "example", "demo", "sample", "mock", "fake", "dummy",
            "测试", "示例", "演示", "样例", "模拟", "虚拟", "假", "例子",
            "for testing", "for example", "just an example", "this is a test",
            "仅供测试", "仅作示例", "这是测试", "这是示例", "举例说明"
        ]

        for indicator in test_indicators:
            if indicator in context:
                logger.debug(f"SensitiveInfoDetector: 发现测试指示器 '{indicator}' 在上下文中")
                return True

        return False

    async def _has_context_indicators_async(self, text: str, matched_text: str) -> bool:
        """异步版本：检查是否有上下文指示器表明这是测试/示例数据。
        
        Args:
            text: 完整文本
            matched_text: 匹配的文本
            
        Returns:
            是否有上下文指示器
        """
        # 对于上下文检查，我们可以将其包装为异步版本
        return await asyncio.get_event_loop().run_in_executor(
            None, self._has_context_indicators, text, matched_text
        )

    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """预编译正则表达式以提高性能。

        Returns:
            预编译的正则表达式字典。
        """
        compiled_patterns = {}

        for pattern_type, patterns in self.patterns.items():
            compiled_patterns[pattern_type] = []
            for pattern in patterns:
                try:
                    compiled_patterns[pattern_type].append(re.compile(pattern))
                except re.error as e:
                    logger.error(f"正则表达式编译错误 (类型 {pattern_type}): {pattern} - {e}")
                    # 添加一个不会匹配任何内容的正则表达式作为占位符
                    compiled_patterns[pattern_type].append(re.compile(r"^\b$"))

        return compiled_patterns

    async def detect(self, text: str) -> List[DetectionResult]:
        """Detect sensitive information in text.

        Args:
            text: The text to check.

        Returns:
            A list of detection results.
        """
        # 使用智能缓存
        cache_key = {
            'detector': 'sensitive_info',
            'text_hash': hashlib.md5(text.encode()).hexdigest(),
            'patterns_version': len(self.compiled_patterns)
        }
        
        async def compute_detection():
            return await self._compute_sensitive_detection(text)
        
        # 缓存检测结果，TTL为10分钟
        return await cache_manager.get_or_compute(
            key=cache_key,
            compute_func=compute_detection,
            ttl=600.0
        )
    
    async def _compute_sensitive_detection(self, text: str) -> List[DetectionResult]:
        """实际执行敏感信息检测"""
        results = []

        for pattern_type, compiled_patterns in self.compiled_patterns.items():
            for i, compiled_pattern in enumerate(compiled_patterns):
                matches = compiled_pattern.finditer(text)
                for match in matches:
                    matched_text = match.group(0)
                    
                    # 检查白名单
                    if await self._is_whitelisted_async(pattern_type, matched_text):
                        logger.debug(f"SensitiveInfoDetector: 跳过白名单项: {pattern_type} - {matched_text}")
                        continue
                    
                    # 检查上下文指示器
                    if await self._has_context_indicators_async(text, matched_text):
                        logger.debug(f"SensitiveInfoDetector: 跳过测试/示例数据: {pattern_type} - {matched_text}")
                        continue
                    
                    # 如果不在白名单中且没有上下文指示器，则添加到结果中
                    results.append(
                        DetectionResult(
                            is_allowed=False,
                            detection_type=DetectionType.SENSITIVE_INFO,
                            severity=Severity.HIGH,
                            reason=f"Detected sensitive information: {pattern_type}",
                            details={
                                "type": pattern_type,
                                "matched_pattern": self.patterns[pattern_type][i],
                                "matched_text": matched_text,
                            },
                        )
                    )

        return results


class HarmfulContentDetector:
    """Detector for harmful content."""

    def __init__(self):
        """Initialize the harmful content detector."""
        self.rules = self._load_rules()

        # 保留向后兼容的关键词字典
        self.keywords = {}
        for rule in self.rules:
            if not hasattr(rule, 'categories') or not rule.categories:
                continue

            for category in rule.categories:
                if category not in self.keywords:
                    self.keywords[category] = []
                self.keywords[category].extend(rule.keywords)

        # 预编译正则表达式
        self._compile_patterns()

        # 预编译关键词正则表达式
        self.keyword_patterns = {}
        for category, words in self.keywords.items():
            self.keyword_patterns[category] = [
                re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)
                for word in words
            ]

    def _load_rules(self) -> List[SecurityRule]:
        """Load harmful content rules from the rules file.

        Returns:
            A list of security rules.
        """
        rules_path = settings.security.harmful_content_rules_path

        # Create default rules if file doesn't exist
        if not os.path.exists(rules_path):
            os.makedirs(os.path.dirname(rules_path), exist_ok=True)

            default_rules = [
                SecurityRule(
                    id="hc-001",
                    name="Violence Content",
                    description="Detects violent content in text",
                    detection_type=DetectionType.HARMFUL_CONTENT,
                    severity=Severity.HIGH,
                    patterns=[
                        r"(?i)how\s+to\s+(?:kill|murder|harm|injure|attack)",
                        r"(?i)(?:make|build|create)\s+(?:a|an)?\s+(?:bomb|explosive|weapon)",
                    ],
                    keywords=[
                        "kill", "murder", "attack", "bomb", "shooting", "terrorist",
                        "assassination", "torture", "violent", "weapon", "gun", "explosive"
                    ],
                    priority=15,
                    categories=["violence"],
                    block=True,
                ),
                SecurityRule(
                    id="hc-002",
                    name="Hate Speech",
                    description="Detects hate speech and discriminatory content",
                    detection_type=DetectionType.HARMFUL_CONTENT,
                    severity=Severity.HIGH,
                    patterns=[
                        r"(?i)(?:all|every)\s+(?:\w+\s+)?(?:people|person|individual|member)\s+(?:is|are)\s+(?:bad|evil|inferior|stupid)",
                    ],
                    keywords=[
                        "hate", "racist", "sexist", "homophobic", "transphobic", "bigot",
                        "discrimination", "prejudice", "slur"
                    ],
                    priority=25,
                    categories=["hate_speech"],
                    block=True,
                ),
                SecurityRule(
                    id="hc-003",
                    name="Illegal Activities",
                    description="Detects content related to illegal activities",
                    detection_type=DetectionType.HARMFUL_CONTENT,
                    severity=Severity.MEDIUM,
                    patterns=[
                        r"(?i)how\s+to\s+(?:hack|crack|steal|launder|counterfeit)",
                    ],
                    keywords=[
                        "hack", "crack", "steal", "fraud", "illegal", "crime", "criminal",
                        "drug", "cocaine", "heroin", "meth", "launder", "counterfeit"
                    ],
                    priority=30,
                    categories=["illegal_activities"],
                    block=True,
                ),
            ]

            with open(rules_path, "w") as f:
                json.dump([rule.model_dump() for rule in default_rules], f, indent=2)

            return default_rules

        # Load rules from file
        try:
            with open(rules_path, "r") as f:
                rules_data = json.load(f)

            rules = [SecurityRule(**rule) for rule in rules_data]
            # 按优先级排序
            rules.sort(key=lambda x: x.priority)
            return rules
        except Exception as e:
            logger.error(f"Error loading harmful content rules: {e}")
            return []

    def _compile_patterns(self):
        """预编译正则表达式以提高性能。"""
        for rule in self.rules:
            rule.compiled_patterns = []
            for pattern in rule.patterns:
                try:
                    rule.compiled_patterns.append(re.compile(pattern, re.IGNORECASE))
                except re.error as e:
                    logger.error(f"正则表达式编译错误 (规则 {rule.id}): {pattern} - {e}")
                    # 添加一个不会匹配任何内容的正则表达式作为占位符
                    rule.compiled_patterns.append(re.compile(r"^\b$"))

            # 预编译关键词正则表达式
            rule.keyword_patterns = []
            for keyword in rule.keywords:
                try:
                    rule.keyword_patterns.append(re.compile(r"\b" + re.escape(keyword) + r"\b", re.IGNORECASE))
                except re.error as e:
                    logger.error(f"关键词正则表达式编译错误 (规则 {rule.id}): {keyword} - {e}")
                    # 添加一个不会匹配任何内容的正则表达式作为占位符
                    rule.keyword_patterns.append(re.compile(r"^\b$"))

    async def detect(self, text: str) -> DetectionResult:
        """Detect harmful content in text.

        Args:
            text: The text to check.

        Returns:
            The detection result.
        """
        # 使用智能缓存
        cache_key = {
            'detector': 'harmful_content',
            'text_hash': hashlib.md5(text.encode()).hexdigest(),
            'rules_version': len(self.rules)  # 简单的规则版本标识
        }
        
        async def compute_detection():
            return await self._compute_harmful_detection(text)
        
        # 缓存检测结果，TTL为5分钟
        return await cache_manager.get_or_compute(
            key=cache_key,
            compute_func=compute_detection,
            ttl=300.0
        )
    
    async def _compute_harmful_detection(self, text: str) -> DetectionResult:
        """实际执行有害内容检测"""
        # 首先使用规则进行检测
        for rule in self.rules:
            if not rule.enabled:
                continue

            # 检查模式
            for i, compiled_pattern in enumerate(rule.compiled_patterns):
                match = compiled_pattern.search(text)
                if match:
                    # 特殊处理刀具相关检测 - 增加上下文感知
                    if rule.id == "hc-011":  # Weapon Making - Knives and Blades
                        context_result = self._check_knife_context(text, match.group(0))
                        if context_result.is_allowed:
                            continue  # 跳过这个匹配，继续检查其他规则
                        else:
                            return context_result
                    
                    return DetectionResult(
                        is_allowed=not rule.block,
                        detection_type=rule.detection_type,
                        severity=rule.severity,
                        reason=f"Detected {rule.name}: {match.group(0)}",
                        details={
                            "rule_id": rule.id,
                            "rule_name": rule.name,
                            "matched_pattern": rule.patterns[i],
                            "matched_text": match.group(0),
                        },
                    )

            # 检查关键词
            for i, keyword_pattern in enumerate(rule.keyword_patterns):
                match = keyword_pattern.search(text)
                if match:
                    # 特殊处理刀具相关检测 - 增加上下文感知
                    if rule.id == "hc-011":  # Weapon Making - Knives and Blades
                        context_result = self._check_knife_context(text, rule.keywords[i])
                        if context_result.is_allowed:
                            continue  # 跳过这个匹配，继续检查其他规则
                        else:
                            return context_result
                    
                    return DetectionResult(
                        is_allowed=not rule.block,
                        detection_type=rule.detection_type,
                        severity=rule.severity,
                        reason=f"Detected {rule.name}: {rule.keywords[i]}",
                        details={
                            "rule_id": rule.id,
                            "rule_name": rule.name,
                            "matched_keyword": rule.keywords[i],
                        },
                    )

        # 向后兼容：使用关键词字典进行检测
        for category, patterns in self.keyword_patterns.items():
            for i, pattern in enumerate(patterns):
                match = pattern.search(text)
                if match:
                    return DetectionResult(
                        is_allowed=False,
                        detection_type=DetectionType.HARMFUL_CONTENT,
                        severity=Severity.MEDIUM,
                        reason=f"Detected potentially harmful content: {category}",
                        details={
                            "category": category,
                            "matched_keyword": self.keywords[category][i],
                        },
                    )

        # 没有检测到有害内容
        return DetectionResult(is_allowed=True)

    def _check_knife_context(self, text: str, matched_text: str) -> DetectionResult:
        """检查刀具相关内容的上下文，判断是否为合法用途。
        
        Args:
            text: 完整文本
            matched_text: 匹配的文本片段
            
        Returns:
            检测结果
        """
        text_lower = text.lower()
        
        # 从白名单加载合法刀具类型和上下文
        try:
            with open('rules/sensitive_info_whitelist.json', 'r', encoding='utf-8') as f:
                whitelist = json.load(f)
            
            legitimate_knives = whitelist.get('knife_whitelist', [])
            legitimate_contexts = whitelist.get('legitimate_contexts', [])
            professional_identifiers = whitelist.get('professional_identifiers', [])
            educational_phrases = whitelist.get('educational_phrases', [])
            safety_disclaimers = whitelist.get('safety_disclaimers', [])
        except Exception as e:
            logger.warning(f"无法加载白名单文件: {e}")
            legitimate_knives = ['手术刀', '厨刀', '菜刀', 'surgical knife', 'kitchen knife', 'chef knife']
            legitimate_contexts = ['医疗', '医学', '手术', '烹饪', '厨房', 'medical', 'surgery', 'cooking', 'kitchen']
            professional_identifiers = ['我是医生', '我是厨师', 'I am a doctor', 'I am a chef']
            educational_phrases = ['我想了解', '我想学习', 'I want to understand', 'I want to learn']
            safety_disclaimers = ['仅供学习', '教育目的', 'for educational purposes only']
        
        # 1. 检查是否为合法的刀具类型 - 但要结合上下文
        legitimate_knife_detected = None
        for knife_type in legitimate_knives:
            if knife_type.lower() in text_lower:
                legitimate_knife_detected = knife_type
                break
        
        # 2. 检查是否包含危险制作意图的关键词
        dangerous_making_patterns = [
            '如何制作', '怎么制作', '教我制作', '告诉我如何制作',
            'how to make', 'how to create', 'teach me to make'
        ]
        
        has_making_intent = False
        for pattern in dangerous_making_patterns:
            if pattern.lower() in text_lower:
                has_making_intent = True
                break
        
        # 如果检测到合法刀具但没有制作意图，直接允许
        if legitimate_knife_detected and not has_making_intent:
            return DetectionResult(
                is_allowed=True,
                reason=f"Allowed: Legitimate knife type mentioned without making intent - {legitimate_knife_detected}",
                context_analysis={"knife_type": legitimate_knife_detected, "making_intent": False}
            )
        
        # 3. 优先检查专业身份识别
        for identifier in professional_identifiers:
            if identifier.lower() in text_lower:
                return DetectionResult(
                    is_allowed=True,
                    reason=f"Allowed: Professional identity detected - {identifier}",
                    context_analysis={"context": "professional", "identifier": identifier}
                )
        
        # 4. 检查教育免责声明
        for disclaimer in safety_disclaimers:
            if disclaimer.lower() in text_lower:
                return DetectionResult(
                    is_allowed=True,
                    reason=f"Allowed: Educational disclaimer detected - {disclaimer}",
                    context_analysis={"context": "educational_disclaimer", "disclaimer": disclaimer}
                )
        
        # 5. 检查教育性询问短语
        for phrase in educational_phrases:
            if phrase.lower() in text_lower:
                return DetectionResult(
                    is_allowed=True,
                    reason=f"Allowed: Educational inquiry detected - {phrase}",
                    context_analysis={"context": "educational_inquiry", "phrase": phrase}
                )
        
        # 6. 检查是否在合法的上下文中
        context_score = 0
        detected_contexts = []
        
        for context in legitimate_contexts:
            if context.lower() in text_lower:
                context_score += 1
                detected_contexts.append(context)
        
        # 检查是否包含制作意图和危险询问模式
        dangerous_inquiry_patterns = [
            '但是我需要告诉你', '我需要告诉你如何', '但我想知道如何',
            '不过我还是想知道', '但还是想问', '但想了解一下',
            'but I need to tell you', 'but I want to know how'
        ]
        
        has_dangerous_inquiry = False
        for pattern in dangerous_inquiry_patterns:
            if pattern.lower() in text_lower:
                has_dangerous_inquiry = True
                break
        
        # 如果检测到多个合法上下文，但也包含危险询问模式，给出警告
        if context_score >= 2 and has_dangerous_inquiry:
            return DetectionResult(
                is_allowed=False,
                detection_type=DetectionType.HARMFUL_CONTENT,
                severity=Severity.LOW,
                reason=f"Detected indirect knife-making inquiry despite legitimate contexts: {', '.join(detected_contexts)}",
                suggested_action="warn",
                context_analysis={"contexts": detected_contexts, "dangerous_inquiry": True, "action": "warn_only"}
            )
        elif context_score >= 2:
            # 多个合法上下文且无危险询问模式，允许
            return DetectionResult(
                is_allowed=True,
                reason=f"Allowed: Multiple legitimate contexts detected - {', '.join(detected_contexts)}",
                context_analysis={"contexts": detected_contexts, "score": context_score}
            )
        
        # 4. 检查是否包含教育或学术指示器
        educational_indicators = [
            '教育', '学习', '研究', '学术', '课程', '教学',
            'educational', 'learning', 'research', 'academic', 'course', 'teaching',
            '我想了解', '我想学习', '仅供学习', '学术目的',
            'for learning', 'for educational purposes', 'academic purposes'
        ]
        
        for indicator in educational_indicators:
            if indicator.lower() in text_lower:
                return DetectionResult(
                    is_allowed=True,
                    reason=f"Allowed: Educational context detected - {indicator}",
                    context_analysis={"context": "educational", "indicator": indicator}
                )
        
        # 5. 检查是否明确声明非恶意意图
        benign_indicators = [
            '我不是真的想', '只是好奇', '纯粹好奇', '仅仅是想了解',
            'just curious', 'purely curious', 'just wondering', 'not actually planning',
        ]
        
        professional_context = [
            '我是医生', '我是厨师', '我在医院工作', '我在厨房工作',
            'I am a doctor', 'I am a chef', '我是医学院学生',
            '但是我需要告诉你', '我需要告诉你如何', # 反向询问模式
        ]
        
        # 检查良性指示器
        for indicator in benign_indicators:
            if indicator.lower() in text_lower:
                # 但仍然给出警告，降低严重性
                return DetectionResult(
                    is_allowed=False,
                    detection_type=DetectionType.HARMFUL_CONTENT,
                    severity=Severity.LOW,  # 降低严重性
                    reason=f"Detected knife-making request with potential benign intent: {indicator}",
                    suggested_action="warn",  # 建议警告而非阻止
                    context_analysis={"benign_indicator": indicator, "action": "warn_only"}
                )
        
        # 检查专业背景 - 特殊处理反向询问
        for context in professional_context:
            if context.lower() in text_lower:
                # 如果包含反向询问模式，仍然给出警告
                if '但是我需要告诉你' in text_lower or '我需要告诉你如何' in text_lower:
                    return DetectionResult(
                        is_allowed=False,
                        detection_type=DetectionType.HARMFUL_CONTENT,
                        severity=Severity.LOW,
                        reason=f"Detected indirect knife-making inquiry from professional context: {context}",
                        suggested_action="warn",
                        context_analysis={"professional_context": context, "inquiry_type": "indirect", "action": "warn_only"}
                    )
                else:
                    # 直接的专业背景声明通常允许
                    return DetectionResult(
                        is_allowed=True,
                        reason=f"Allowed: Professional context detected - {context}",
                        context_analysis={"professional_context": context, "context": "legitimate_professional"}
                    )
        
        # 6. 默认情况：阻止请求
        return DetectionResult(
            is_allowed=False,
            detection_type=DetectionType.HARMFUL_CONTENT,
            severity=Severity.HIGH,
            reason=f"Detected dangerous weapon-making request: {matched_text}",
            context_analysis={"matched_text": matched_text, "danger_level": "high"}
        )


class ComplianceDetector:
    """Detector for compliance violations."""

    def __init__(self):
        """Initialize the compliance detector."""
        self.rules = self._load_rules()
        # 预编译正则表达式
        self._compile_patterns()

    def _load_rules(self) -> List[SecurityRule]:
        """Load compliance rules from the rules file.

        Returns:
            A list of security rules.
        """
        rules_path = settings.security.compliance_rules_path

        # Create default rules if file doesn't exist
        if not os.path.exists(rules_path):
            os.makedirs(os.path.dirname(rules_path), exist_ok=True)

            default_rules = [
                SecurityRule(
                    id="comp-001",
                    name="GDPR Compliance",
                    description="Detects potential GDPR compliance issues",
                    detection_type=DetectionType.COMPLIANCE_VIOLATION,
                    severity=Severity.HIGH,
                    patterns=[
                        r"(?i)(?:collect|store|process|use)\s+(?:personal|private|user)\s+(?:data|information)\s+without\s+(?:consent|permission)",
                    ],
                    keywords=[
                        "GDPR violation", "data protection", "privacy breach", "consent", "data subject rights"
                    ],
                    priority=40,
                    categories=["gdpr", "privacy"],
                    block=True,
                ),
                SecurityRule(
                    id="comp-002",
                    name="HIPAA Compliance",
                    description="Detects potential HIPAA compliance issues",
                    detection_type=DetectionType.COMPLIANCE_VIOLATION,
                    severity=Severity.HIGH,
                    patterns=[
                        r"(?i)(?:share|disclose|reveal)\s+(?:patient|medical|health)\s+(?:data|information|records)\s+without\s+(?:authorization|consent)",
                    ],
                    keywords=[
                        "HIPAA violation", "PHI", "patient data", "medical records", "health information"
                    ],
                    priority=35,
                    categories=["hipaa", "healthcare"],
                    block=True,
                ),
            ]

            with open(rules_path, "w") as f:
                json.dump([rule.model_dump() for rule in default_rules], f, indent=2)

            return default_rules

        # Load rules from file
        try:
            with open(rules_path, "r") as f:
                rules_data = json.load(f)

            rules = [SecurityRule(**rule) for rule in rules_data]
            # 按优先级排序
            rules.sort(key=lambda x: x.priority)
            return rules
        except Exception as e:
            logger.error(f"Error loading compliance rules: {e}")
            return []

    def _compile_patterns(self):
        """预编译正则表达式以提高性能。"""
        for rule in self.rules:
            rule.compiled_patterns = []
            for pattern in rule.patterns:
                try:
                    rule.compiled_patterns.append(re.compile(pattern, re.IGNORECASE))
                except re.error as e:
                    logger.error(f"正则表达式编译错误 (规则 {rule.id}): {pattern} - {e}")
                    # 添加一个不会匹配任何内容的正则表达式作为占位符
                    rule.compiled_patterns.append(re.compile(r"^\b$"))

            # 预编译关键词正则表达式
            rule.keyword_patterns = []
            for keyword in rule.keywords:
                try:
                    rule.keyword_patterns.append(re.compile(r"\b" + re.escape(keyword) + r"\b", re.IGNORECASE))
                except re.error as e:
                    logger.error(f"关键词正则表达式编译错误 (规则 {rule.id}): {keyword} - {e}")
                    # 添加一个不会匹配任何内容的正则表达式作为占位符
                    rule.keyword_patterns.append(re.compile(r"^\b$"))

    async def detect(self, text: str) -> DetectionResult:
        """Detect compliance violations in text.

        Args:
            text: The text to check.

        Returns:
            The detection result.
        """
        for rule in self.rules:
            if not rule.enabled:
                continue

            # 检查模式
            for i, compiled_pattern in enumerate(rule.compiled_patterns):
                match = compiled_pattern.search(text)
                if match:
                    return DetectionResult(
                        is_allowed=not rule.block,
                        detection_type=rule.detection_type,
                        severity=rule.severity,
                        reason=f"Detected {rule.name}: {match.group(0)}",
                        details={
                            "rule_id": rule.id,
                            "rule_name": rule.name,
                            "matched_pattern": rule.patterns[i],
                            "matched_text": match.group(0),
                        },
                    )

            # 检查关键词
            for i, keyword_pattern in enumerate(rule.keyword_patterns):
                match = keyword_pattern.search(text)
                if match:
                    return DetectionResult(
                        is_allowed=not rule.block,
                        detection_type=rule.detection_type,
                        severity=rule.severity,
                        reason=f"Detected {rule.name}: {rule.keywords[i]}",
                        details={
                            "rule_id": rule.id,
                            "rule_name": rule.name,
                            "matched_keyword": rule.keywords[i],
                        },
                    )

        # 没有检测到合规违规
        return DetectionResult(is_allowed=True)


class JailbreakDetector:
    """Detector for jailbreak attempts."""

    def __init__(self):
        """Initialize the jailbreak detector."""
        self.rules = self._load_rules()
        # 预编译正则表达式
        self._compile_patterns()

    def _load_rules(self) -> List[SecurityRule]:
        """Load jailbreak rules from the rules file.

        Returns:
            A list of security rules.
        """
        rules_path = settings.security.jailbreak_rules_path
        logger.info(f"JailbreakDetector: 加载规则文件: {rules_path}")

        # 定义默认规则
        default_rules = [
            SecurityRule(
                id="jb-001",
                name="DAN Jailbreak",
                description="Detects DAN (Do Anything Now) jailbreak attempts",
                detection_type=DetectionType.JAILBREAK,
                severity=Severity.CRITICAL,
                patterns=[
                    r"(?i)you[.\s]*are[.\s]*now[.\s]*DAN",
                    r"(?i)DAN[.\s]*mode[.\s]*enabled",
                    r"(?i)Do[.\s]*Anything[.\s]*Now",
                ],
                keywords=["DAN", "Do Anything Now"],
                priority=5,  # 最高优先级
                categories=["jailbreak"],
                block=True,
            ),
            SecurityRule(
                id="jb-002",
                name="Alternative Jailbreak Characters",
                description="Detects alternative jailbreak character attempts like STAN, DUDE, etc.",
                detection_type=DetectionType.JAILBREAK,
                severity=Severity.CRITICAL,
                patterns=[
                    r"(?i)(?:STAN|DUDE|KEVIN|DAVE|AIM|ANTI-DAN)[.\s]*(?:模式|mode)",
                    r"(?i)you[.\s]*are[.\s]*(?:STAN|DUDE|KEVIN|DAVE|AIM)",
                ],
                keywords=["STAN", "DUDE", "KEVIN", "DAVE", "AIM", "ANTI-DAN"],
                priority=5,
                categories=["jailbreak"],
                block=True,
            ),
        ]

        # Create default rules if file doesn't exist
        if not os.path.exists(rules_path):
            logger.warning(f"JailbreakDetector: 规则文件不存在，创建默认规则: {rules_path}")
            os.makedirs(os.path.dirname(rules_path), exist_ok=True)

            with open(rules_path, "w") as f:
                json.dump([rule.model_dump() for rule in default_rules], f, indent=2)

            return default_rules

        # Load rules from file
        try:
            logger.info(f"JailbreakDetector: 尝试从文件加载规则: {rules_path}")
            with open(rules_path, "r") as f:
                rules_data = json.load(f)

            logger.info(f"JailbreakDetector: 成功加载规则数据，规则数量: {len(rules_data)}")
            rules = [SecurityRule(**rule) for rule in rules_data]
            # 按优先级排序
            rules.sort(key=lambda x: x.priority)
            logger.info(f"JailbreakDetector: 成功创建规则对象，规则数量: {len(rules)}")

            # 如果成功加载了规则，并且规则数量大于0，则返回加载的规则
            if len(rules) > 0:
                return rules
            else:
                logger.warning(f"JailbreakDetector: 加载的规则数量为0，使用默认规则")
                return default_rules
        except Exception as e:
            logger.error(f"JailbreakDetector: 加载越狱规则错误: {e}，使用默认规则")
            return default_rules

    def _compile_patterns(self):
        """预编译正则表达式以提高性能。"""
        for rule in self.rules:
            rule.compiled_patterns = []
            for pattern in rule.patterns:
                try:
                    rule.compiled_patterns.append(re.compile(pattern, re.IGNORECASE))
                except re.error as e:
                    logger.error(f"JailbreakDetector: 正则表达式编译错误 (规则 {rule.id}): {pattern} - {e}")
                    # 添加一个不会匹配任何内容的正则表达式作为占位符
                    rule.compiled_patterns.append(re.compile(r"^\b$"))

            # 预编译关键词正则表达式
            rule.keyword_patterns = []
            for keyword in rule.keywords:
                try:
                    rule.keyword_patterns.append(re.compile(r"\b" + re.escape(keyword) + r"\b", re.IGNORECASE))
                except re.error as e:
                    logger.error(f"JailbreakDetector: 关键词正则表达式编译错误 (规则 {rule.id}): {keyword} - {e}")
                    # 添加一个不会匹配任何内容的正则表达式作为占位符
                    rule.keyword_patterns.append(re.compile(r"^\b$"))

    async def detect(self, text: str) -> DetectionResult:
        """Detect jailbreak attempts in text.

        Args:
            text: The text to check.

        Returns:
            The detection result.
        """
        logger.info(f"JailbreakDetector: 检查文本，规则数量: {len(self.rules)}")

        # 记录前200个字符的文本，避免日志过长
        logger.info(f"JailbreakDetector: 检查文本: {text[:200]}...")

        for rule in self.rules:
            logger.info(f"JailbreakDetector: 检查规则 {rule.id}: {rule.name}, 启用状态: {rule.enabled}")
            if not rule.enabled:
                continue

            # 使用预编译的正则表达式
            for i, compiled_pattern in enumerate(rule.compiled_patterns):
                try:
                    match = compiled_pattern.search(text)
                    if match:
                        matched_text = match.group(0)
                        
                        # 添加上下文检查，减少误报
                        if self._is_likely_false_positive(text, matched_text, rule):
                            logger.debug(f"JailbreakDetector: 跳过可能的误报: {rule.name} - {matched_text}")
                            continue
                        
                        logger.warning(f"JailbreakDetector: 匹配到模式 {rule.patterns[i]} 在规则 {rule.id}")
                        return DetectionResult(
                            is_allowed=not rule.block,
                            detection_type=rule.detection_type,
                            severity=rule.severity,
                            reason=f"Detected {rule.name}: {matched_text}",
                            details={
                                "rule_id": rule.id,
                                "rule_name": rule.name,
                                "matched_pattern": rule.patterns[i],
                                "matched_text": matched_text,
                            },
                        )
                except Exception as e:
                    logger.error(f"JailbreakDetector: 正则表达式匹配错误 (规则 {rule.id}): {e}")

            # 使用预编译的关键词正则表达式
            for i, keyword_pattern in enumerate(rule.keyword_patterns):
                try:
                    match = keyword_pattern.search(text)
                    if match:
                        matched_text = match.group(0)
                        
                        # 添加上下文检查，减少误报
                        if self._is_likely_false_positive(text, matched_text, rule):
                            logger.debug(f"JailbreakDetector: 跳过可能的误报关键词: {rule.name} - {matched_text}")
                            continue
                        
                        logger.warning(f"JailbreakDetector: 匹配到关键词 {rule.keywords[i]} 在规则 {rule.id}")
                        return DetectionResult(
                            is_allowed=not rule.block,
                            detection_type=rule.detection_type,
                            severity=rule.severity,
                            reason=f"Detected {rule.name}: {rule.keywords[i]}",
                            details={
                                "rule_id": rule.id,
                                "rule_name": rule.name,
                                "matched_keyword": rule.keywords[i],
                            },
                        )
                except Exception as e:
                    logger.error(f"JailbreakDetector: 关键词匹配错误 (规则 {rule.id}): {e}")

        # No jailbreak detected
        logger.info("JailbreakDetector: 未检测到越狱尝试")
        return DetectionResult(is_allowed=True)

    def _is_likely_false_positive(self, text: str, matched_text: str, rule: SecurityRule) -> bool:
        """检查是否可能是误报。

        Args:
            text: 完整文本
            matched_text: 匹配的文本
            rule: 安全规则

        Returns:
            是否可能是误报
        """
        # 查找匹配文本在完整文本中的位置（不区分大小写）
        match_start = text.lower().find(matched_text.lower())
        if match_start == -1:
            return False

        # 获取匹配文本前后的上下文（各200个字符）
        context_start = max(0, match_start - 200)
        context_end = min(len(text), match_start + len(matched_text) + 200)
        context = text[context_start:context_end].lower()
        
        # 获取完整文本用于全局分析
        full_context = text.lower()

        # 1. 检查是否在正常对话或学术讨论中
        normal_context_indicators = [
            # 询问类
            "what is", "what are", "what does", "can you explain", "help me understand",
            "tell me about", "describe", "explain", "definition of", "meaning of",
            "how does", "how do", "how can", "why does", "why do",
            # 中文询问类
            "什么是", "你能解释", "帮我理解", "告诉我", "描述一下", "解释一下",
            "如何", "为什么", "怎么", "怎样", "请说明",
            # 学术讨论类
            "学习", "研究", "讨论", "分析", "understanding", "research", "study",
            "analysis", "academic", "scholarly", "educational", "learning",
            # 引用类
            "in literature", "in movies", "in fiction", "in stories", "in books",
            "在文学中", "在电影中", "在小说中", "在故事中", "在书中", "在游戏中",
            "according to", "based on", "references", "citations",
            # 假设类
            "hypothetically", "theoretically", "假设", "理论上", "假如", "如果",
            "suppose", "imagine", "what if", "in theory",
            # 创作类
            "creative writing", "story", "character", "fiction", "novel",
            "script", "screenplay", "dialogue", "narrative", "creative",
            "write", "writing", "roleplay", "role-play", "playing", "game",
            "创意写作", "故事", "角色", "小说", "虚构", "剧本", "对话", "叙述",
            "写作", "创作", "角色扮演", "扮演", "游戏", "模拟"
        ]

        # 检查上下文指示器
        for indicator in normal_context_indicators:
            if indicator in context:
                logger.debug(f"JailbreakDetector: 发现正常上下文指示器: {indicator}")
                return True

        # 2. 检查是否包含良性意图指示器
        benign_intent_indicators = [
            "just curious", "out of curiosity", "wondering", "interested in",
            "for educational purposes", "for learning", "for research",
            "只是好奇", "出于好奇", "想知道", "感兴趣", "为了学习", "为了研究",
            "for fun", "just for fun", "as a joke", "joking", "kidding",
            "为了好玩", "开玩笑", "开个玩笑", "闹着玩"
        ]
        
        for indicator in benign_intent_indicators:
            if indicator in full_context:
                logger.debug(f"JailbreakDetector: 发现良性意图指示器: {indicator}")
                return True

        # 3. 特殊规则的深度分析
        if rule.id == "jb-002" and "stan" in matched_text.lower():
            # STAN检测的特殊处理
            normal_stan_contexts = [
                # 包含"stan"的正常英文单词
                "assistant", "understand", "constant", "standard", "instance",
                "substantial", "distance", "resistance", "assistance", "stanza",
                "outstanding", "understanding", "withstand", "grandstand",
                # 中文相关
                "助手", "理解", "常数", "标准", "实例", "坚持", "距离", "抵抗", "援助",
                # 人名相关
                "stan lee", "stan smith", "stanley"
            ]
            for ctx in normal_stan_contexts:
                if ctx in context:
                    logger.debug(f"JailbreakDetector: 发现STAN误报上下文: {ctx}")
                    return True

        if rule.id == "jb-001" and "dan" in matched_text.lower():
            # DAN检测的特殊处理
            normal_dan_contexts = [
                # 包含"dan"的正常英文单词
                "dance", "danger", "dangling", "understand", "standard",
                "recommendation", "fundamental", "abundant", "pendant",
                "andan", "jordan", "sudan", "guidance", "attendance",
                # 中文相关
                "跳舞", "危险", "悬挂", "理解", "标准", "建议", "基本", "丰富",
                # 人名相关
                "dan brown", "daniel", "danielle"
            ]
            for ctx in normal_dan_contexts:
                if ctx in context:
                    logger.debug(f"JailbreakDetector: 发现DAN误报上下文: {ctx}")
                    return True

        # 4. 长度和复杂性检查
        if len(text) < 100:  # 较短的文本，可能是正常询问
            simple_patterns = [
                r"\b(what|how|why|when|where|who)\b",
                r"\b(什么|如何|为什么|什么时候|哪里|谁)\b"
            ]
            for pattern in simple_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    logger.debug(f"JailbreakDetector: 短文本中发现疑问词，可能是正常询问")
                    return True

        # 5. 检查是否包含明显的攻击模式
        # 如果包含明显的越狱模式，则不认为是误报
        attack_patterns = [
            "do anything now", "developer mode", "jailbreak mode",
            "evil mode", "unrestricted mode", "bypass", "override",
            "ignore safety", "disable filter", "remove restrictions"
        ]
        
        for pattern in attack_patterns:
            if pattern in full_context:
                logger.debug(f"JailbreakDetector: 发现明显攻击模式: {pattern}")
                return False  # 不是误报

        return False


class SecurityDetector:
    """Main security detector that coordinates all detection types."""

    def __init__(self):
        """Initialize the security detector."""
        self.prompt_injection_detector = PromptInjectionDetector()
        self.sensitive_info_detector = SensitiveInfoDetector()
        self.harmful_content_detector = HarmfulContentDetector()
        self.compliance_detector = ComplianceDetector()
        self.jailbreak_detector = JailbreakDetector()

        # 导入上下文感知检测器
        from src.security.context_aware_detector import context_aware_detector
        self.context_aware_detector = context_aware_detector

        # 导入对话跟踪器
        from src.security.conversation_tracker import conversation_tracker
        self.conversation_tracker = conversation_tracker

        # 导入模型特定检测器
        # from src.security.model_specific_detector import model_specific_detector
        # self.model_specific_detector = model_specific_detector

    def _process_detection_result(self, result: DetectionResult, conversation_id: str = None) -> DetectionResult:
        """处理检测结果，根据建议动作调整响应。

        Args:
            result: 原始检测结果
            conversation_id: 对话ID

        Returns:
            处理后的检测结果
        """
        if result.is_allowed:
            return result

        # 根据建议动作调整响应
        if result.suggested_action == "allow":
            logger.info(f"SecurityDetector: 建议允许，虽然检测到威胁: {result.reason}")
            result.is_allowed = True
            result.status_code = 200
        elif result.suggested_action == "warn":
            logger.warning(f"SecurityDetector: 检测到潜在威胁，发出警告: {result.reason}")
            # 警告模式：记录事件但允许通过
            result.is_allowed = True
            result.status_code = 200
            result.reason = f"[WARNING] {result.reason}"
            # 记录警告事件
            from src.audit.event_logger import event_logger
            event_logger.log_event(result, f"WARNING: {result.reason}")
        elif result.suggested_action == "block":
            logger.warning(f"SecurityDetector: 阻止请求: {result.reason}")
            # 标记对话为已被攻陷（如果适用）
            if conversation_id and result.risk_level in ["high", "critical"]:
                self.conversation_tracker.mark_conversation_as_compromised(conversation_id)
            # 记录安全事件
            from src.audit.event_logger import event_logger
            event_logger.log_event(result, result.reason)
            result.is_allowed = False
            result.status_code = 403

        return result

    async def check_request(self, request: InterceptedRequest) -> DetectionResult:
        """Check a request for security threats.

        Args:
            request: The intercepted request.

        Returns:
            The detection result.
        """
        # Extract text from request
        text = self._extract_text_from_request(request)
        logger.info(f"SecurityDetector: 检查请求，文本长度: {len(text)}")

        if not text:
            logger.info("SecurityDetector: 请求文本为空，允许通过")
            return DetectionResult(is_allowed=True)

        # 快速检查：如果是简单的问候语，直接允许通过
        if self._is_simple_greeting(text.strip()):
            logger.info(f"SecurityDetector: 检测到简单问候语，直接允许通过: {text.strip()}")
            return DetectionResult(is_allowed=True)

        # 记录前200个字符的文本，避免日志过长
        logger.info(f"SecurityDetector: 请求文本: {text[:200]}...")

        # 获取或创建对话，但先不添加当前消息
        conversation_id, conversation = self.conversation_tracker.process_request(request)
        logger.info(f"SecurityDetector: 处理对话 {conversation_id}，历史消息数: {len(conversation.messages)}")

        # 如果对话中有历史消息，则进行上下文感知检测
        if len(conversation.messages) > 0:
            logger.info("SecurityDetector: 执行上下文感知检测")
            # 临时添加当前消息到对话中进行检测
            temp_conversation = self._create_temp_conversation_with_current_message(conversation, request)
            result = self.context_aware_detector.detect(temp_conversation)
            if not result.is_allowed:
                logger.warning(
                    f"Blocked request due to context-aware detection: {result.reason}"
                )
                # 标记对话为已被攻陷
                self.conversation_tracker.mark_conversation_as_compromised(conversation_id)
                # 记录安全事件
                event_logger.log_event(result, temp_conversation.get_full_context())
                return result
                
        # 现在正式添加当前消息到对话历史
        user_content = self._extract_text_from_request(request)
        self.conversation_tracker.add_user_message_to_conversation(conversation_id, user_content)

        # 执行模型特定检测
        # if settings.security.enable_model_specific_detection:
        #     logger.info("SecurityDetector: 执行模型特定检测")
        #     result = self.model_specific_detector.check_request(request, text)
        #     if not result.is_allowed:
        #         logger.warning(
        #             f"Blocked request due to model-specific detection: {result.reason}"
        #         )
        #         # 记录安全事件
        #         event_logger.log_event(result, text)
        #         return result
        # else:
        #     logger.info("SecurityDetector: 模型特定检测已禁用")

        # Check for prompt injection
        logger.info("SecurityDetector: 检查提示注入")
        result = await self.prompt_injection_detector.detect(text)
        if not result.is_allowed:
            return self._process_detection_result(result, conversation_id)

        # Check for jailbreak attempts
        logger.info("SecurityDetector: 检查越狱尝试")
        result = await self.jailbreak_detector.detect(text)
        if not result.is_allowed:
            return self._process_detection_result(result, conversation_id)

        # Check for harmful content
        logger.info("SecurityDetector: 检查有害内容")
        result = await self.harmful_content_detector.detect(text)
        if not result.is_allowed:
            return self._process_detection_result(result, conversation_id)

        # Check for compliance violations
        logger.info("SecurityDetector: 检查合规违规")
        result = await self.compliance_detector.detect(text)
        if not result.is_allowed:
            return self._process_detection_result(result, conversation_id)

        # Check for sensitive information in request
        logger.info("SecurityDetector: 检查敏感信息")
        sensitive_results = await self.sensitive_info_detector.detect(text)
        if sensitive_results:
            result = sensitive_results[0]
            return self._process_detection_result(result, conversation_id)

        # All checks passed
        logger.info("SecurityDetector: 所有检查通过，允许请求")
        return DetectionResult(is_allowed=True)

    async def check_response(self, response: InterceptedResponse, conversation_id: str = None) -> DetectionResult:
        """Check a response for security threats.

        Args:
            response: The intercepted response.
            conversation_id: 对话ID，如果为None则尝试从响应中提取。

        Returns:
            The detection result.
        """
        # 检查是否是流式响应
        if response.is_streaming:
            logger.info("SecurityDetector: 检测到流式响应，跳过内容检查")
            return DetectionResult(is_allowed=True)

        # Extract text from response
        text = self._extract_text_from_response(response)

        if not text:
            return DetectionResult(is_allowed=True)

        # 记录前100个字符的文本，避免日志过长
        logger.info(f"SecurityDetector: 响应文本: {text[:100]}...")

        # 如果提供了对话ID，则更新对话历史
        if conversation_id:
            self.conversation_tracker.process_response(conversation_id, response)
            logger.info(f"SecurityDetector: 更新对话 {conversation_id} 的响应")

        # 执行模型特定检测
        # if settings.security.enable_model_specific_detection:
        #     logger.info("SecurityDetector: 执行模型特定检测")
        #     # 尝试从请求中提取模型名称
        #     model_name = None
        #     if hasattr(response, "request") and hasattr(response.request, "body"):
        #         if "model" in response.request.body:
        #             model_name = response.request.body["model"]
        #
        #     result = self.model_specific_detector.check_response(response, text, model_name)
        #     if not result.is_allowed:
        #         logger.warning(
        #             f"Blocked response due to model-specific detection: {result.reason}"
        #         )
        #         # 记录安全事件
        #         event_logger.log_event(result, text)
        #         return result
        # else:
        #     logger.info("SecurityDetector: 模型特定检测已禁用")

        # Check for prompt injection
        result = await self.prompt_injection_detector.detect(text)
        if not result.is_allowed:
            logger.warning(
                f"Blocked response due to {result.detection_type}: {result.reason}"
            )
            # 记录安全事件
            event_logger.log_event(result, text)
            return result

        # Check for jailbreak attempts
        result = await self.jailbreak_detector.detect(text)
        if not result.is_allowed:
            logger.warning(
                f"Blocked response due to {result.detection_type}: {result.reason}"
            )
            # 记录安全事件
            event_logger.log_event(result, text)
            return result

        # Check for sensitive information in response
        sensitive_results = await self.sensitive_info_detector.detect(text)
        if sensitive_results:
            result = sensitive_results[0]
            logger.warning(
                f"Blocked response due to {result.detection_type}: {result.reason}"
            )
            # 记录安全事件
            event_logger.log_event(result, text)
            return result

        # Check for harmful content
        result = await self.harmful_content_detector.detect(text)
        if not result.is_allowed:
            logger.warning(
                f"Blocked response due to {result.detection_type}: {result.reason}"
            )
            # 记录安全事件
            event_logger.log_event(result, text)
            return result

        # Check for compliance violations
        result = await self.compliance_detector.detect(text)
        if not result.is_allowed:
            logger.warning(
                f"Blocked response due to {result.detection_type}: {result.reason}"
            )
            # 记录安全事件
            event_logger.log_event(result, text)
            return result

        # All checks passed
        logger.info("SecurityDetector: 响应检查通过")
        return DetectionResult(is_allowed=True)

    def _extract_text_from_request(self, request: InterceptedRequest) -> str:
        """Extract text from a request for security checking.

        Args:
            request: The intercepted request.

        Returns:
            The extracted text.
        """
        text = ""

        if request.body:
            # Extract messages from OpenAI-like format
            if "messages" in request.body:
                for message in request.body["messages"]:
                    if "content" in message and isinstance(message["content"], str):
                        text += message["content"] + "\n"

            # Extract prompt from Anthropic-like format
            elif "prompt" in request.body and isinstance(request.body["prompt"], str):
                text += request.body["prompt"]

            # Extract system from Anthropic-like format
            elif "system" in request.body and isinstance(request.body["system"], str):
                text += request.body["system"]

            # Extract inputs from HuggingFace-like format
            elif "inputs" in request.body and isinstance(request.body["inputs"], str):
                text += request.body["inputs"]

            # Extract message from Cohere-like format
            elif "message" in request.body and isinstance(request.body["message"], str):
                text += request.body["message"]

            # Extract chat history from Cohere-like format
            elif "chat_history" in request.body and isinstance(request.body["chat_history"], list):
                for entry in request.body["chat_history"]:
                    if "message" in entry and isinstance(entry["message"], str):
                        text += entry["message"] + "\n"

        return text

    def _extract_text_from_response(self, response: InterceptedResponse) -> str:
        """Extract text from a response for security checking.

        Args:
            response: The intercepted response.

        Returns:
            The extracted text.
        """
        text = ""

        if response.body:
            # Extract choices from OpenAI-like format
            if "choices" in response.body and isinstance(response.body["choices"], list):
                for choice in response.body["choices"]:
                    if "message" in choice and "content" in choice["message"]:
                        text += choice["message"]["content"] + "\n"
                    elif "text" in choice:
                        text += choice["text"] + "\n"

            # Extract completion from Anthropic-like format
            elif "completion" in response.body and isinstance(response.body["completion"], str):
                text += response.body["completion"]

            # Extract generated_text from HuggingFace-like format
            elif isinstance(response.body, list) and len(response.body) > 0:
                for item in response.body:
                    if "generated_text" in item:
                        text += item["generated_text"] + "\n"
            elif "generated_text" in response.body:
                text += response.body["generated_text"]

            # Extract text from Cohere-like format
            elif "text" in response.body:
                text += response.body["text"]

            # Extract generations from Cohere-like format
            elif "generations" in response.body and isinstance(response.body["generations"], list):
                for gen in response.body["generations"]:
                    if "text" in gen:
                        text += gen["text"] + "\n"

        return text

    def _create_temp_conversation_with_current_message(self, conversation, request):
        """创建包含当前消息的临时对话，用于上下文感知检测。
        
        Args:
            conversation: 原始对话对象
            request: 当前请求
            
        Returns:
            包含当前消息的临时对话对象
        """
        from copy import deepcopy
        
        # 深度复制对话对象以避免修改原始对话
        temp_conversation = deepcopy(conversation)
        
        # 提取当前请求的用户内容
        current_content = self._extract_text_from_request(request)
        if current_content:
            temp_conversation.add_message("user", current_content)
            
        return temp_conversation

    def _is_simple_greeting(self, text: str) -> bool:
        """检查是否为简单的问候语。
        
        Args:
            text: 要检查的文本
            
        Returns:
            是否为简单问候语
        """
        if not text or len(text) > 50:  # 问候语通常很短
            return False
            
        # 加载问候语白名单
        try:
            import json
            import os
            whitelist_path = "rules/sensitive_info_whitelist.json"
            if os.path.exists(whitelist_path):
                with open(whitelist_path, "r", encoding="utf-8") as f:
                    whitelist = json.load(f)
                    greeting_list = whitelist.get("greeting_whitelist", [])
                    
                    # 检查是否匹配问候语白名单
                    text_lower = text.lower().strip()
                    for greeting in greeting_list:
                        if text_lower == greeting.lower().strip():
                            return True
        except Exception as e:
            logger.error(f"加载问候语白名单失败: {e}")
            
        # 默认的基础问候语检查
        basic_greetings = ["你好", "您好", "hi", "hello", "hey", "早上好", "下午好", "晚上好"]
        text_lower = text.lower().strip()
        for greeting in basic_greetings:
            if text_lower == greeting.lower():
                return True
                
        return False
