"""Security detection module for identifying and mitigating security threats."""

import json
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from src.audit.event_logger import event_logger
from src.config import settings
from src.logger import logger
from src.models_interceptor import DetectionResult, DetectionType, InterceptedRequest, InterceptedResponse, SecurityRule, Severity


class PromptInjectionDetector:
    """Detector for prompt injection attacks."""

    def __init__(self):
        """Initialize the prompt injection detector."""
        self.rules = self._load_rules()

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

    def detect(self, text: str) -> DetectionResult:
        """Detect prompt injection in text.

        Args:
            text: The text to check.

        Returns:
            The detection result.
        """
        for rule in self.rules:
            if not rule.enabled:
                continue

            # Check patterns
            for pattern in rule.patterns:
                match = re.search(pattern, text)
                if match:
                    return DetectionResult(
                        is_allowed=not rule.block,
                        detection_type=rule.detection_type,
                        severity=rule.severity,
                        reason=f"Detected {rule.name}: {match.group(0)}",
                        details={
                            "rule_id": rule.id,
                            "rule_name": rule.name,
                            "matched_pattern": pattern,
                            "matched_text": match.group(0),
                        },
                    )

            # Check keywords
            for keyword in rule.keywords:
                if keyword.lower() in text.lower():
                    return DetectionResult(
                        is_allowed=not rule.block,
                        detection_type=rule.detection_type,
                        severity=rule.severity,
                        reason=f"Detected {rule.name}: {keyword}",
                        details={
                            "rule_id": rule.id,
                            "rule_name": rule.name,
                            "matched_keyword": keyword,
                        },
                    )

        # No detection
        return DetectionResult(is_allowed=True)


class SensitiveInfoDetector:
    """Detector for sensitive information."""

    def __init__(self):
        """Initialize the sensitive information detector."""
        self.patterns = self._load_patterns()

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

    def detect(self, text: str) -> List[DetectionResult]:
        """Detect sensitive information in text.

        Args:
            text: The text to check.

        Returns:
            A list of detection results.
        """
        results = []

        for pattern_type, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text)
                for match in matches:
                    results.append(
                        DetectionResult(
                            is_allowed=False,
                            detection_type=DetectionType.SENSITIVE_INFO,
                            severity=Severity.HIGH,
                            reason=f"Detected sensitive information: {pattern_type}",
                            details={
                                "type": pattern_type,
                                "matched_pattern": pattern,
                                "matched_text": match.group(0),
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

    def detect(self, text: str) -> DetectionResult:
        """Detect harmful content in text.

        Args:
            text: The text to check.

        Returns:
            The detection result.
        """
        # 首先使用规则进行检测
        for rule in self.rules:
            if not rule.enabled:
                continue

            # 检查模式
            for pattern in rule.patterns:
                match = re.search(pattern, text)
                if match:
                    return DetectionResult(
                        is_allowed=not rule.block,
                        detection_type=rule.detection_type,
                        severity=rule.severity,
                        reason=f"Detected {rule.name}: {match.group(0)}",
                        details={
                            "rule_id": rule.id,
                            "rule_name": rule.name,
                            "matched_pattern": pattern,
                            "matched_text": match.group(0),
                        },
                    )

            # 检查关键词
            text_lower = text.lower()
            for keyword in rule.keywords:
                if re.search(r"\b" + re.escape(keyword) + r"\b", text_lower):
                    return DetectionResult(
                        is_allowed=not rule.block,
                        detection_type=rule.detection_type,
                        severity=rule.severity,
                        reason=f"Detected {rule.name}: {keyword}",
                        details={
                            "rule_id": rule.id,
                            "rule_name": rule.name,
                            "matched_keyword": keyword,
                        },
                    )

        # 向后兼容：使用关键词字典进行检测
        text_lower = text.lower()
        for category, words in self.keywords.items():
            for word in words:
                if re.search(r"\b" + re.escape(word) + r"\b", text_lower):
                    return DetectionResult(
                        is_allowed=False,
                        detection_type=DetectionType.HARMFUL_CONTENT,
                        severity=Severity.MEDIUM,
                        reason=f"Detected potentially harmful content: {category}",
                        details={
                            "category": category,
                            "matched_keyword": word,
                        },
                    )

        # 没有检测到有害内容
        return DetectionResult(is_allowed=True)


class ComplianceDetector:
    """Detector for compliance violations."""

    def __init__(self):
        """Initialize the compliance detector."""
        self.rules = self._load_rules()

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

    def detect(self, text: str) -> DetectionResult:
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
            for pattern in rule.patterns:
                match = re.search(pattern, text)
                if match:
                    return DetectionResult(
                        is_allowed=not rule.block,
                        detection_type=rule.detection_type,
                        severity=rule.severity,
                        reason=f"Detected {rule.name}: {match.group(0)}",
                        details={
                            "rule_id": rule.id,
                            "rule_name": rule.name,
                            "matched_pattern": pattern,
                            "matched_text": match.group(0),
                        },
                    )

            # 检查关键词
            text_lower = text.lower()
            for keyword in rule.keywords:
                if re.search(r"\b" + re.escape(keyword) + r"\b", text_lower):
                    return DetectionResult(
                        is_allowed=not rule.block,
                        detection_type=rule.detection_type,
                        severity=rule.severity,
                        reason=f"Detected {rule.name}: {keyword}",
                        details={
                            "rule_id": rule.id,
                            "rule_name": rule.name,
                            "matched_keyword": keyword,
                        },
                    )

        # 没有检测到合规违规
        return DetectionResult(is_allowed=True)


class JailbreakDetector:
    """Detector for jailbreak attempts."""

    def __init__(self):
        """Initialize the jailbreak detector."""
        self.rules = self._load_rules()

    def _load_rules(self) -> List[SecurityRule]:
        """Load jailbreak rules from the rules file.

        Returns:
            A list of security rules.
        """
        rules_path = settings.security.jailbreak_rules_path
        logger.info(f"JailbreakDetector: 加载规则文件: {rules_path}")

        # Create default rules if file doesn't exist
        if not os.path.exists(rules_path):
            logger.warning(f"JailbreakDetector: 规则文件不存在，创建默认规则: {rules_path}")
            os.makedirs(os.path.dirname(rules_path), exist_ok=True)

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
            return rules
        except Exception as e:
            logger.error(f"JailbreakDetector: 加载越狱规则错误: {e}")
            return []

    def detect(self, text: str) -> DetectionResult:
        """Detect jailbreak attempts in text.

        Args:
            text: The text to check.

        Returns:
            The detection result.
        """
        logger.info(f"JailbreakDetector: 检查文本，规则数量: {len(self.rules)}")

        # 记录前100个字符的文本，避免日志过长
        logger.info(f"JailbreakDetector: 检查文本: {text[:100]}...")

        for rule in self.rules:
            logger.info(f"JailbreakDetector: 检查规则 {rule.id}: {rule.name}, 启用状态: {rule.enabled}")
            if not rule.enabled:
                continue

            # Check patterns
            for pattern in rule.patterns:
                try:
                    match = re.search(pattern, text)
                    if match:
                        logger.warning(f"JailbreakDetector: 匹配到模式 {pattern} 在规则 {rule.id}")
                        return DetectionResult(
                            is_allowed=not rule.block,
                            detection_type=rule.detection_type,
                            severity=rule.severity,
                            reason=f"Detected {rule.name}: {match.group(0)}",
                            details={
                                "rule_id": rule.id,
                                "rule_name": rule.name,
                                "matched_pattern": pattern,
                                "matched_text": match.group(0),
                            },
                        )
                except Exception as e:
                    logger.error(f"JailbreakDetector: 正则表达式错误 {pattern}: {e}")

            # Check keywords
            text_lower = text.lower()
            for keyword in rule.keywords:
                try:
                    if re.search(r"\b" + re.escape(keyword) + r"\b", text_lower):
                        logger.warning(f"JailbreakDetector: 匹配到关键词 {keyword} 在规则 {rule.id}")
                        return DetectionResult(
                            is_allowed=not rule.block,
                            detection_type=rule.detection_type,
                            severity=rule.severity,
                            reason=f"Detected {rule.name}: {keyword}",
                            details={
                                "rule_id": rule.id,
                                "rule_name": rule.name,
                                "matched_keyword": keyword,
                            },
                        )
                except Exception as e:
                    logger.error(f"JailbreakDetector: 关键词匹配错误 {keyword}: {e}")

        # No jailbreak detected
        logger.info("JailbreakDetector: 未检测到越狱尝试")
        return DetectionResult(is_allowed=True)


class SecurityDetector:
    """Main security detector that coordinates all detection types."""

    def __init__(self):
        """Initialize the security detector."""
        self.prompt_injection_detector = PromptInjectionDetector()
        self.sensitive_info_detector = SensitiveInfoDetector()
        self.harmful_content_detector = HarmfulContentDetector()
        self.compliance_detector = ComplianceDetector()
        self.jailbreak_detector = JailbreakDetector()

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

        # 记录前100个字符的文本，避免日志过长
        logger.info(f"SecurityDetector: 请求文本: {text[:100]}...")

        # Check for prompt injection
        logger.info("SecurityDetector: 检查提示注入")
        result = self.prompt_injection_detector.detect(text)
        if not result.is_allowed:
            logger.warning(
                f"Blocked request due to {result.detection_type}: {result.reason}"
            )
            # 记录安全事件
            event_logger.log_event(result, text)
            return result

        # Check for jailbreak attempts
        logger.info("SecurityDetector: 检查越狱尝试")
        result = self.jailbreak_detector.detect(text)
        if not result.is_allowed:
            logger.warning(
                f"Blocked request due to {result.detection_type}: {result.reason}"
            )
            # 记录安全事件
            event_logger.log_event(result, text)
            return result

        # Check for harmful content
        logger.info("SecurityDetector: 检查有害内容")
        result = self.harmful_content_detector.detect(text)
        if not result.is_allowed:
            logger.warning(
                f"Blocked request due to {result.detection_type}: {result.reason}"
            )
            # 记录安全事件
            event_logger.log_event(result, text)
            return result

        # Check for compliance violations
        logger.info("SecurityDetector: 检查合规违规")
        result = self.compliance_detector.detect(text)
        if not result.is_allowed:
            logger.warning(
                f"Blocked request due to {result.detection_type}: {result.reason}"
            )
            # 记录安全事件
            event_logger.log_event(result, text)
            return result

        # Check for sensitive information in request
        logger.info("SecurityDetector: 检查敏感信息")
        sensitive_results = self.sensitive_info_detector.detect(text)
        if sensitive_results:
            result = sensitive_results[0]
            logger.warning(
                f"Blocked request due to {result.detection_type}: {result.reason}"
            )
            # 记录安全事件
            event_logger.log_event(result, text)
            return result

        # All checks passed
        logger.info("SecurityDetector: 所有检查通过，允许请求")
        return DetectionResult(is_allowed=True)

    async def check_response(self, response: InterceptedResponse) -> DetectionResult:
        """Check a response for security threats.

        Args:
            response: The intercepted response.

        Returns:
            The detection result.
        """
        # Extract text from response
        text = self._extract_text_from_response(response)

        if not text:
            return DetectionResult(is_allowed=True)

        # Check for prompt injection
        result = self.prompt_injection_detector.detect(text)
        if not result.is_allowed:
            logger.warning(
                f"Blocked response due to {result.detection_type}: {result.reason}"
            )
            # 记录安全事件
            event_logger.log_event(result, text)
            return result

        # Check for jailbreak attempts
        result = self.jailbreak_detector.detect(text)
        if not result.is_allowed:
            logger.warning(
                f"Blocked response due to {result.detection_type}: {result.reason}"
            )
            # 记录安全事件
            event_logger.log_event(result, text)
            return result

        # Check for sensitive information in response
        sensitive_results = self.sensitive_info_detector.detect(text)
        if sensitive_results:
            result = sensitive_results[0]
            logger.warning(
                f"Blocked response due to {result.detection_type}: {result.reason}"
            )
            # 记录安全事件
            event_logger.log_event(result, text)
            return result

        # Check for harmful content
        result = self.harmful_content_detector.detect(text)
        if not result.is_allowed:
            logger.warning(
                f"Blocked response due to {result.detection_type}: {result.reason}"
            )
            # 记录安全事件
            event_logger.log_event(result, text)
            return result

        # Check for compliance violations
        result = self.compliance_detector.detect(text)
        if not result.is_allowed:
            logger.warning(
                f"Blocked response due to {result.detection_type}: {result.reason}"
            )
            # 记录安全事件
            event_logger.log_event(result, text)
            return result

        # All checks passed
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
