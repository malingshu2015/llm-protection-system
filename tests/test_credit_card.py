"""测试信用卡检测功能。"""

import re
import pytest

def test_credit_card_regex():
    """测试信用卡正则表达式。"""
    # 信用卡正则表达式
    credit_card_pattern = r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})\b"
    
    # 测试文本
    test_text = "My credit card number is 4111111111111111."
    
    # 执行检测
    match = re.search(credit_card_pattern, test_text)
    
    # 验证结果
    assert match is not None
    assert match.group(0) == "4111111111111111"
    
    # 测试带空格的信用卡号
    test_text_with_spaces = "My credit card number is 4111 1111 1111 1111."
    
    # 使用修改后的正则表达式
    credit_card_pattern_with_spaces = r"\b(?:4[0-9]{3}[ -]?[0-9]{4}[ -]?[0-9]{4}[ -]?[0-9]{4}|4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})\b"
    
    # 执行检测
    match_with_spaces = re.search(credit_card_pattern_with_spaces, test_text_with_spaces)
    
    # 验证结果
    assert match_with_spaces is not None
    assert match_with_spaces.group(0) == "4111 1111 1111 1111"
