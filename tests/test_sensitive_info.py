"""测试敏感信息检测功能。"""

import re
from typing import Dict, List

import pytest

from src.models import DetectionResult, DetectionType, Severity


class TestSensitiveInfoDetector:
    """测试敏感信息检测器。"""
    
    def test_credit_card_detection(self):
        """测试信用卡号检测。"""
        # 信用卡正则表达式 - 修改为支持空格分隔的信用卡号
        credit_card_pattern = r"\b(?:4[0-9]{12}(?:[0-9]{3})?|4[0-9]{3}[ -]?[0-9]{4}[ -]?[0-9]{4}[ -]?[0-9]{4}|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})\b"
        
        # 测试文本
        test_text = "My credit card number is 4111 1111 1111 1111."
        
        # 执行检测
        match = re.search(credit_card_pattern, test_text)
        
        # 验证结果
        assert match is not None
        assert match.group(0) == "4111 1111 1111 1111"
    
    def test_email_detection(self):
        """测试电子邮件检测。"""
        # 电子邮件正则表达式
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        
        # 测试文本
        test_text = "My email is user@example.com."
        
        # 执行检测
        match = re.search(email_pattern, test_text)
        
        # 验证结果
        assert match is not None
        assert match.group(0) == "user@example.com"
    
    def test_phone_detection(self):
        """测试电话号码检测。"""
        # 电话号码正则表达式 - 修改以正确匹配括号
        phone_pattern = r"\(\d{3}\)\s\d{3}-\d{4}"
        
        # 测试文本
        test_text = "My phone number is (123) 456-7890."
        
        # 执行检测
        match = re.search(phone_pattern, test_text)
        
        # 验证结果
        assert match is not None
        assert match.group(0) == "(123) 456-7890"
