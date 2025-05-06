"""内容脱敏模块。"""

import json
import os
import re
from typing import Dict, List, Optional, Tuple

from src.config import settings
from src.logger import logger
from src.models_interceptor import InterceptedResponse


class ContentMasker:
    """内容脱敏器。"""

    def __init__(self):
        """初始化内容脱敏器。"""
        self.sensitive_patterns_file = settings.security.sensitive_info_patterns_path
        self.patterns = self._load_patterns()
        self.default_mask = "****"

    def _load_patterns(self) -> Dict[str, List[str]]:
        """从文件加载敏感信息模式。

        Returns:
            敏感信息模式字典，键为类型，值为正则表达式模式列表。
        """
        if not os.path.exists(self.sensitive_patterns_file):
            logger.warning(f"敏感信息模式文件不存在: {self.sensitive_patterns_file}")
            return {}

        try:
            with open(self.sensitive_patterns_file, "r") as f:
                patterns = json.load(f)
            logger.info(f"成功加载敏感信息模式，类型数量: {len(patterns)}")
            return patterns
        except Exception as e:
            logger.error(f"加载敏感信息模式失败: {e}")
            return {}

    def mask_sensitive_info(self, text: str) -> Tuple[str, List[Dict]]:
        """对文本中的敏感信息进行脱敏处理。

        Args:
            text: 要处理的文本。

        Returns:
            (脱敏后的文本, 脱敏信息列表)
        """
        if not settings.security.enable_content_masking:
            return text, []

        masked_text = text
        mask_info = []

        for pattern_type, patterns in self.patterns.items():
            for pattern in patterns:
                try:
                    # 查找所有匹配
                    matches = list(re.finditer(pattern, masked_text))
                    
                    # 从后向前替换，避免替换位置偏移
                    for match in reversed(matches):
                        start, end = match.span()
                        matched_text = match.group(0)
                        
                        # 根据类型选择不同的脱敏方式
                        if pattern_type == "phone_number":
                            # 保留前3位和后4位
                            if len(matched_text) >= 7:
                                masked_value = matched_text[:3] + "*" * (len(matched_text) - 7) + matched_text[-4:]
                            else:
                                masked_value = self.default_mask
                        elif pattern_type == "email":
                            # 保留用户名首字符和域名
                            parts = matched_text.split("@")
                            if len(parts) == 2 and len(parts[0]) > 0:
                                username = parts[0][0] + "*" * (len(parts[0]) - 1)
                                masked_value = f"{username}@{parts[1]}"
                            else:
                                masked_value = self.default_mask
                        elif pattern_type == "id_card":
                            # 保留前3位和后4位
                            if len(matched_text) >= 7:
                                masked_value = matched_text[:3] + "*" * (len(matched_text) - 7) + matched_text[-4:]
                            else:
                                masked_value = self.default_mask
                        elif pattern_type == "credit_card":
                            # 仅保留后4位
                            if len(matched_text) >= 4:
                                masked_value = "*" * (len(matched_text) - 4) + matched_text[-4:]
                            else:
                                masked_value = self.default_mask
                        else:
                            # 默认完全脱敏
                            masked_value = self.default_mask
                        
                        # 替换文本
                        masked_text = masked_text[:start] + masked_value + masked_text[end:]
                        
                        # 记录脱敏信息
                        mask_info.append({
                            "type": pattern_type,
                            "start": start,
                            "end": end,
                            "original_length": len(matched_text),
                            "masked_length": len(masked_value)
                        })
                except Exception as e:
                    logger.error(f"脱敏处理失败，模式: {pattern}, 错误: {e}")

        return masked_text, mask_info

    def process_response(self, response: InterceptedResponse) -> InterceptedResponse:
        """处理响应，对敏感信息进行脱敏。

        Args:
            response: 拦截的响应。

        Returns:
            处理后的响应。
        """
        if not settings.security.enable_content_masking:
            return response

        # 提取响应文本
        text = self._extract_text_from_response(response)
        if not text:
            return response

        # 脱敏处理
        masked_text, mask_info = self.mask_sensitive_info(text)
        
        # 如果没有进行脱敏，直接返回原响应
        if not mask_info:
            return response
            
        # 更新响应内容
        updated_response = self._update_response_text(response, masked_text)
        
        # 添加脱敏信息到响应头部
        if "headers" not in updated_response.model_fields:
            updated_response.headers = {}
        updated_response.headers["X-Content-Masked"] = "true"
        updated_response.headers["X-Content-Mask-Count"] = str(len(mask_info))
        
        return updated_response

    def _extract_text_from_response(self, response: InterceptedResponse) -> str:
        """从响应中提取文本。

        Args:
            response: 拦截的响应。

        Returns:
            提取的文本。
        """
        if not response.body:
            return ""

        # 尝试从不同的响应格式中提取文本
        try:
            # OpenAI格式
            if "choices" in response.body:
                choices = response.body["choices"]
                if choices and isinstance(choices, list):
                    if "message" in choices[0]:
                        return choices[0]["message"].get("content", "")
                    elif "text" in choices[0]:
                        return choices[0]["text"]
            
            # Anthropic格式
            if "content" in response.body:
                return response.body["content"]
                
            # Ollama格式
            if "response" in response.body:
                return response.body["response"]
                
            # 通用JSON响应
            if "text" in response.body:
                return response.body["text"]
            if "output" in response.body:
                return response.body["output"]
                
            # 如果无法识别格式，尝试将整个响应体转换为字符串
            return str(response.body)
        except Exception as e:
            logger.error(f"从响应中提取文本失败: {e}")
            return ""

    def _update_response_text(self, response: InterceptedResponse, new_text: str) -> InterceptedResponse:
        """更新响应中的文本。

        Args:
            response: 拦截的响应。
            new_text: 新文本。

        Returns:
            更新后的响应。
        """
        if not response.body:
            return response

        # 创建响应的副本
        updated_body = dict(response.body)
        
        # 尝试更新不同格式的响应
        try:
            # OpenAI格式
            if "choices" in updated_body and updated_body["choices"] and isinstance(updated_body["choices"], list):
                if "message" in updated_body["choices"][0]:
                    updated_body["choices"][0]["message"]["content"] = new_text
                elif "text" in updated_body["choices"][0]:
                    updated_body["choices"][0]["text"] = new_text
            
            # Anthropic格式
            elif "content" in updated_body:
                updated_body["content"] = new_text
                
            # Ollama格式
            elif "response" in updated_body:
                updated_body["response"] = new_text
                
            # 通用JSON响应
            elif "text" in updated_body:
                updated_body["text"] = new_text
            elif "output" in updated_body:
                updated_body["output"] = new_text
            else:
                # 如果无法识别格式，不进行更新
                logger.warning("无法识别响应格式，无法更新文本")
                return response
        except Exception as e:
            logger.error(f"更新响应文本失败: {e}")
            return response
            
        # 创建新的响应对象
        return InterceptedResponse(
            status_code=response.status_code,
            headers=response.headers,
            body=updated_body,
            timestamp=response.timestamp,
            latency=response.latency
        )


# 创建全局内容脱敏器实例
content_masker = ContentMasker()
