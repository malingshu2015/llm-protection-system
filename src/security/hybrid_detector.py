"""
混合并行检测机制 (Hybrid Parallel Detection)
阶段 1: M1.1 & M1.2 & M1.3
结合了正则表达式的快速匹配、轻量级AI模型的语义判定与向量相似度拦截。
"""

import asyncio
import time
from typing import Optional

from src.logger import logger
from src.models_interceptor import DetectionResult, DetectionType, Severity


class HybridSemanticDetector:
    """基于轻量级模型 + 向量引擎的混合语义检测器"""

    def __init__(self):
        self._is_model_loaded = False
        self._classifier = None
        self._lock = asyncio.Lock()
        self._loading_task = None
        # M1.3: 向量引擎延迟初始化（依赖可能未安装）
        self._vector_engine = None
        self._vector_init_attempted = False

    async def _ensure_vector_engine(self):
        """确保向量引擎已初始化，失败则忽略。"""
        if self._vector_init_attempted:
            return
        self._vector_init_attempted = True
        try:
            from src.security.vector_engine import vector_engine
            await vector_engine.initialize()
            self._vector_engine = vector_engine
        except Exception as e:
            logger.warning(f"HybridSemanticDetector: 向量引擎初始化失败，降级为无向量模式: {e}")

    async def get_or_load_model(self):
        """异步延迟加载模型，不阻塞主应用启动"""
        async with self._lock:
            if self._is_model_loaded:
                return
            if self._loading_task is not None and not self._loading_task.done():
                return

            self._loading_task = asyncio.create_task(self._do_load_model())

    async def _do_load_model(self):
        try:
            # 尝试导入 transformers，如果未安装，则回退到 mock 模式
            import torch
            from transformers import pipeline

            logger.info("HybridSemanticDetector: 正在从 HuggingFace 初始化轻量级安全分类模型...")

            # unitary/toxic-bert 是经典的有毒文本检测模型
            await asyncio.to_thread(self._init_pipeline, "unitary/toxic-bert")

            self._is_model_loaded = True
            logger.info("HybridSemanticDetector: 轻量级安全分类模型加载完成！")
        except ImportError:
            logger.warning("HybridSemanticDetector: 未检测到 transformers / torch 库。")
            logger.warning("HybridSemanticDetector: 已降级为【规则引擎 + 向量相似度】模式。")
            self._is_model_loaded = False
        except Exception as e:
            logger.error(f"HybridSemanticDetector: 模型加载异常: {e}")
            self._is_model_loaded = False

    def _init_pipeline(self, model_name: str):
        from transformers import pipeline
        # 强制使用 CPU 进行推理，防止 Mac MPS / CUDA 问题
        self._classifier = pipeline("text-classification", model=model_name, top_k=None, device=-1)

    async def detect_async(self, text: str, skip_ai: bool = False) -> DetectionResult:
        """异步执行向量相似度检测 + (可选) 语义模型推理"""

        # --- 1. 向量相似度过滤 (M1.3 — 真实向量引擎) ---
        await self._ensure_vector_engine()
        if self._vector_engine:
            try:
                is_hit, matched_text, similarity = await self._vector_engine.is_malicious(text)
                if is_hit:
                    logger.warning(
                        f"HybridSemanticDetector(Vector): 命中恶意向量库! "
                        f"相似度={similarity:.3f}, 匹配文本=\"{matched_text[:60]}...\""
                    )
                    return DetectionResult(
                        is_allowed=False,
                        detection_type=DetectionType.JAILBREAK,
                        severity=Severity.CRITICAL,
                        reason=f"命中恶意语义向量库 (相似度: {similarity:.2f})",
                        details={
                            "matched_text": matched_text,
                            "similarity_score": similarity,
                            "detection_method": "vector_similarity",
                        },
                        status_code=403
                    )
            except Exception as e:
                logger.error(f"HybridSemanticDetector(Vector): 向量检索异常: {e}")

        # 如果跳过 AI 推理，则直接返回通过
        if skip_ai:
            return DetectionResult(is_allowed=True)

        # --- 2. 深度分类模型检测 (M1.1) ---
        if not self._is_model_loaded:
            if self._classifier is None:
                await self.get_or_load_model()
            logger.debug("HybridSemanticDetector: AI 大模型防护尚未就绪，暂且放行。")
            return DetectionResult(is_allowed=True)

        try:
            start_time = time.time()
            # 在线程池中执行防止阻塞 asyncio event loop
            results = await asyncio.to_thread(self._classifier, text)
            latency = time.time() - start_time

            is_toxic = False
            highest_score = 0.0
            matched_label = ""

            if results and isinstance(results[0], list):
                scores = results[0]
                for score_dict in scores:
                    if score_dict['score'] > 0.85:  # 阈值 0.85
                        is_toxic = True
                        highest_score = score_dict['score']
                        matched_label = score_dict['label']
                        break

            logger.info(f"HybridSemanticDetector: 推理耗时 {latency:.3f}s, [{matched_label}: {highest_score:.2f}]")

            if is_toxic:
                return DetectionResult(
                    is_allowed=False,
                    detection_type=DetectionType.HARMFUL_CONTENT,
                    severity=Severity.HIGH,
                    reason=f"AI Semantic Model Detected: {matched_label} (score: {highest_score:.2f})",
                    status_code=403
                )

            return DetectionResult(is_allowed=True)

        except Exception as e:
            logger.error(f"HybridSemanticDetector 推理时发生异常: {e}")
            return DetectionResult(is_allowed=True)


# 全局单例
hybrid_detector = HybridSemanticDetector()
