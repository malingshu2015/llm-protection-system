import asyncio
import json
import time
from typing import AsyncGenerator, AsyncIterator, Tuple, Callable

from src.logger import logger
from src.security.detector import SecurityDetector
from src.models_interceptor import DetectionResult, DetectionType, Severity

class StreamSlidingWindowInterceptor:
    """
    滑动窗口拦截器：用于在流式输出期间，一边吐字一边检测。
    降低首字延迟 (TTFT)，实现“发现敏感词当即掐断”的效果。
    """
    
    def __init__(self, detector: SecurityDetector, window_size: int = 150):
        self.detector = detector
        self.window_size = window_size
        self._buffer = ""
        
        # 定义哪些标点符号可能是句子的自然停止点，通常在停止点进行深度检测较准
        self.stop_chars = set(['。', '！', '？', '；', '\n', '.', '!', '?', ';'])
        
    async def process_openai_stream(self, original_generator: AsyncIterator[str], conversation_id: str = None) -> AsyncGenerator[str, None]:
        """
        处理 OpenAI 格式的 SSE 数据流
        """
        async for sse_chunk in original_generator:
            # sse_chunk 形如: "data: {...}\n\n"
            if not sse_chunk.startswith("data: "):
                yield sse_chunk
                continue
                
            data_str = sse_chunk[6:].strip()
            if data_str == "[DONE]":
                yield sse_chunk
                break
                
            try:
                chunk_obj = json.loads(data_str)
                delta = chunk_obj.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                
                if content:
                    self._buffer += content
                    
                    # 取最新的一段窗口
                    window_text = self._buffer[-self.window_size:]
                    
                    # 触发滑动窗口拦截检测
                    # M2.1 性能优化策略：
                    # 1. 平时仅进行正则与向量检测 (skip_ai=True)，首字延迟极低
                    # 2. 遇到句子结束符 (stop_chars) 才进行 AI 模型深度扫描
                    is_sentence_end = any(ch in self.stop_chars for ch in content)
                    is_length_trigger = len(self._buffer) % 50 == 0
                    
                    if is_sentence_end or is_length_trigger:
                        # 调用统一扫描接口
                        result = await self.detector.scan_text(
                            window_text, 
                            conversation_id, 
                            skip_ai=not is_sentence_end
                        )
                        
                        if not result.is_allowed:
                            yield self._build_blocked_chunk(chunk_obj, result)
                            return

            except json.JSONDecodeError:
                pass
                
            # 安全检查通过，送出原始内容
            yield sse_chunk
            
    def _build_blocked_chunk(self, original_chunk_obj: dict, result: DetectionResult) -> str:
        """生成被拦截的流式Chunk块并终止"""
        logger.warning(f"流式响应在半途中被滑动窗口阻断! 原因: {result.reason}")
        
        blocked_chunk = {
            "id": original_chunk_obj.get("id", f"chatcmpl-{int(time.time())}"),
            "object": "chat.completion.chunk",
            "created": original_chunk_obj.get("created", int(time.time())),
            "model": original_chunk_obj.get("model", "unknown"),
            "choices": [
                {
                    "index": original_chunk_obj.get("choices", [{}])[0].get("index", 0),
                    "delta": {"content": f"\n\n[🛡️ 内容已被防火墙掐断: {result.reason}]"},
                    "finish_reason": "stop"
                }
            ]
        }
        return f"data: {json.dumps(blocked_chunk)}\n\ndata: [DONE]\n\n"
