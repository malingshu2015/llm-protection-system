"""集成增强安全检测器 - 将新的ML和自适应算法集成到现有系统"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from src.logger import logger
from src.models_interceptor import DetectionResult, DetectionType, Severity, InterceptedRequest, InterceptedResponse
from src.security.detector import SecurityDetector
from src.security.smart_cache import cache_manager

# 条件导入增强检测器（如果依赖可用）
try:
    from src.security.enhanced_detector import enhanced_detector
    from src.security.adaptive_learning import adaptive_learning_system
    ENHANCED_DETECTION_AVAILABLE = True
    logger.info("增强检测器模块已加载")
except ImportError as e:
    logger.warning(f"增强检测器不可用，使用基础检测: {e}")
    enhanced_detector = None
    adaptive_learning_system = None
    ENHANCED_DETECTION_AVAILABLE = False


@dataclass
class DetectionConfig:
    """检测配置"""
    enable_enhanced_detection: bool = True
    enable_adaptive_learning: bool = True
    enable_ml_detection: bool = True
    enable_behavior_analysis: bool = True
    enhanced_detection_timeout: float = 5.0
    fallback_to_basic: bool = True
    performance_monitoring: bool = True


class IntegratedSecurityDetector(SecurityDetector):
    """集成安全检测器 - 结合基础检测和增强检测"""

    def __init__(self):
        super().__init__()
        self.config = DetectionConfig()
        self.performance_stats = {
            'total_detections': 0,
            'enhanced_detections': 0,
            'basic_detections': 0,
            'enhanced_timeouts': 0,
            'avg_detection_time': 0.0,
            'false_positives': 0,
            'false_negatives': 0
        }
        self.enhanced_available = ENHANCED_DETECTION_AVAILABLE

    async def check_request(self, request: InterceptedRequest) -> DetectionResult:
        """增强版请求检查"""
        start_time = time.time()
        self.performance_stats['total_detections'] += 1

        try:
            # 提取文本和用户信息
            text = self._extract_text_from_request(request)
            user_id = self._extract_user_id(request)

            if not text:
                logger.debug("请求文本为空，允许通过")
                return DetectionResult(is_allowed=True)

            # 先执行基础检测（快速筛选）
            basic_result = await self._run_basic_detection(request, text)

            # 如果基础检测已经阻止，直接返回
            if not basic_result.is_allowed and basic_result.severity in [Severity.HIGH, Severity.CRITICAL]:
                logger.info("基础检测已阻止，跳过增强检测")
                await self._record_detection_performance('basic', time.time() - start_time, basic_result)
                return basic_result

            # 如果启用增强检测且可用
            if self.config.enable_enhanced_detection and self.enhanced_available:
                try:
                    enhanced_result = await self._run_enhanced_detection(text, user_id, request)

                    # 融合基础检测和增强检测结果
                    final_result = self._fuse_detection_results(basic_result, enhanced_result)

                    # 记录学习数据
                    if self.config.enable_adaptive_learning and adaptive_learning_system:
                        await adaptive_learning_system.process_detection_result(text, final_result)

                    await self._record_detection_performance('enhanced', time.time() - start_time, final_result)
                    return final_result

                except asyncio.TimeoutError:
                    logger.warning("增强检测超时，使用基础检测结果")
                    self.performance_stats['enhanced_timeouts'] += 1
                    await self._record_detection_performance('timeout', time.time() - start_time, basic_result)
                    return basic_result
                except Exception as e:
                    logger.error(f"增强检测失败: {e}")
                    if self.config.fallback_to_basic:
                        await self._record_detection_performance('error', time.time() - start_time, basic_result)
                        return basic_result
                    raise

            # 如果增强检测不可用，返回基础检测结果
            await self._record_detection_performance('basic', time.time() - start_time, basic_result)
            return basic_result

        except Exception as e:
            logger.error(f"集成检测失败: {e}")
            # 紧急情况下允许通过，但记录错误
            return DetectionResult(
                is_allowed=True,
                reason=f"检测系统异常，允许通过: {str(e)}"
            )

    async def _run_basic_detection(self, request: InterceptedRequest, text: str) -> DetectionResult:
        """运行基础检测"""
        return await super().check_request(request)

    async def _run_enhanced_detection(self, text: str, user_id: str = None, request: InterceptedRequest = None) -> DetectionResult:
        """运行增强检测"""
        if not self.enhanced_available:
            raise RuntimeError("增强检测不可用")

        # 构建上下文信息
        context = {
            'conversation_length': 0,
            'user_risk_score': 0.0,
            'session_threat_count': 0,
        }

        if request and hasattr(request, 'headers'):
            # 从请求头中提取上下文信息
            context['user_agent'] = request.headers.get('User-Agent', '')
            context['ip_address'] = request.headers.get('X-Real-IP', '')

        # 运行增强检测
        return await asyncio.wait_for(
            enhanced_detector.detect_enhanced_threats(text, user_id, context),
            timeout=self.config.enhanced_detection_timeout
        )

    def _fuse_detection_results(self, basic_result: DetectionResult, enhanced_result: DetectionResult) -> DetectionResult:
        """融合基础检测和增强检测结果"""
        # 如果任一检测器认为是威胁，且置信度足够高，则认为是威胁
        basic_threat_score = 0.0 if basic_result.is_allowed else 0.8
        enhanced_threat_score = enhanced_result.confidence_score if hasattr(enhanced_result, 'confidence_score') else 0.5

        # 加权融合
        basic_weight = 0.4
        enhanced_weight = 0.6
        fused_score = basic_threat_score * basic_weight + enhanced_threat_score * enhanced_weight

        # 确定最终结果
        if fused_score > 0.7:
            # 高威胁 - 选择更严格的结果
            if not basic_result.is_allowed or not enhanced_result.is_allowed:
                final_result = enhanced_result if enhanced_threat_score > basic_threat_score else basic_result
                final_result.reason = f"融合检测: 基础({basic_threat_score:.2f}) + 增强({enhanced_threat_score:.2f}) = {fused_score:.2f}"
                return final_result
        elif fused_score > 0.5:
            # 中等威胁 - 发出警告但允许
            return DetectionResult(
                is_allowed=True,
                detection_type=enhanced_result.detection_type or DetectionType.PROMPT_INJECTION,
                severity=Severity.MEDIUM,
                reason=f"融合检测警告: 检测到潜在威胁 (评分: {fused_score:.2f})",
                details={
                    'basic_result': basic_result.reason,
                    'enhanced_result': enhanced_result.reason,
                    'fused_score': fused_score
                }
            )

        # 低威胁或无威胁 - 允许通过
        return DetectionResult(is_allowed=True)

    def _extract_user_id(self, request: InterceptedRequest) -> Optional[str]:
        """从请求中提取用户ID"""
        if not request or not request.headers:
            return None

        # 尝试从不同地方提取用户标识
        user_id = (
            request.headers.get('X-User-ID') or
            request.headers.get('User-ID') or
            request.headers.get('Authorization', '').split('Bearer ')[-1][:32] if 'Bearer ' in request.headers.get('Authorization', '') else None
        )

        return user_id

    async def _record_detection_performance(self, detection_type: str, duration: float, result: DetectionResult):
        """记录检测性能"""
        if not self.config.performance_monitoring:
            return

        # 更新统计信息
        if detection_type == 'enhanced':
            self.performance_stats['enhanced_detections'] += 1
        else:
            self.performance_stats['basic_detections'] += 1

        # 更新平均检测时间
        total_detections = self.performance_stats['total_detections']
        current_avg = self.performance_stats['avg_detection_time']
        self.performance_stats['avg_detection_time'] = (current_avg * (total_detections - 1) + duration) / total_detections

        # 记录详细性能数据（每100次检测记录一次）
        if total_detections % 100 == 0:
            logger.info(f"检测性能统计: {self.performance_stats}")

    async def report_false_positive(self, text: str, detection_result: DetectionResult):
        """报告误报"""
        self.performance_stats['false_positives'] += 1

        if self.config.enable_adaptive_learning and adaptive_learning_system:
            await adaptive_learning_system.process_detection_result(
                text, detection_result, user_feedback='false_positive', actual_threat=False
            )

        logger.warning(f"误报报告: {text[:100]}... -> {detection_result.reason}")

    async def report_false_negative(self, text: str):
        """报告漏报"""
        self.performance_stats['false_negatives'] += 1

        if self.config.enable_adaptive_learning and adaptive_learning_system:
            # 创建一个表示遗漏的检测结果
            missed_result = DetectionResult(is_allowed=True, reason="系统遗漏的威胁")
            await adaptive_learning_system.process_detection_result(
                text, missed_result, user_feedback='false_negative', actual_threat=True
            )

        logger.error(f"漏报报告: {text[:100]}...")

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        stats = self.performance_stats.copy()

        # 计算额外指标
        total = stats['total_detections']
        if total > 0:
            stats['enhanced_usage_rate'] = stats['enhanced_detections'] / total
            stats['timeout_rate'] = stats['enhanced_timeouts'] / total
            stats['error_rate'] = (stats['false_positives'] + stats['false_negatives']) / total

        return stats

    async def optimize_performance(self):
        """优化性能设置"""
        stats = self.get_performance_stats()

        # 如果超时率过高，调整超时时间
        if stats.get('timeout_rate', 0) > 0.1:  # 超过10%超时
            self.config.enhanced_detection_timeout = min(
                self.config.enhanced_detection_timeout * 1.2,
                10.0  # 最大10秒
            )
            logger.info(f"调整增强检测超时时间至: {self.config.enhanced_detection_timeout}s")

        # 如果增强检测不稳定，暂时禁用
        if stats.get('timeout_rate', 0) > 0.3:  # 超过30%超时
            self.config.enable_enhanced_detection = False
            logger.warning("增强检测超时率过高，暂时禁用")

        # 如果误报率过高，调整策略
        error_rate = stats.get('error_rate', 0)
        if error_rate > 0.1:  # 超过10%错误率
            logger.warning(f"检测错误率过高: {error_rate:.2%}")

            # 如果有自适应学习，触发模型调整
            if self.config.enable_adaptive_learning and adaptive_learning_system:
                logger.info("触发自适应学习调整")


class PerformanceOptimizer:
    """性能优化器"""

    def __init__(self, detector: IntegratedSecurityDetector):
        self.detector = detector
        self.optimization_interval = 300  # 5分钟优化一次
        self.last_optimization = 0

    async def continuous_optimization(self):
        """持续性能优化"""
        while True:
            try:
                current_time = time.time()
                if current_time - self.last_optimization > self.optimization_interval:
                    await self._optimize_detection_pipeline()
                    self.last_optimization = current_time

                await asyncio.sleep(60)  # 每分钟检查一次

            except Exception as e:
                logger.error(f"性能优化失败: {e}")
                await asyncio.sleep(300)  # 出错后等待5分钟

    async def _optimize_detection_pipeline(self):
        """优化检测流水线"""
        logger.info("开始性能优化...")

        # 获取性能统计
        stats = self.detector.get_performance_stats()

        # 优化缓存策略
        await self._optimize_cache_strategy(stats)

        # 优化检测器配置
        await self.detector.optimize_performance()

        # 清理过期数据
        await self._cleanup_expired_data()

        logger.info("性能优化完成")

    async def _optimize_cache_strategy(self, stats: Dict[str, Any]):
        """优化缓存策略"""
        try:
            # 如果检测时间过长，增加缓存使用
            avg_time = stats.get('avg_detection_time', 0)
            if avg_time > 1.0:  # 超过1秒
                # 调整缓存TTL
                cache_manager.default_ttl = min(cache_manager.default_ttl * 1.1, 3600)
                logger.info(f"调整缓存TTL至: {cache_manager.default_ttl}s")

        except Exception as e:
            logger.error(f"缓存优化失败: {e}")

    async def _cleanup_expired_data(self):
        """清理过期数据"""
        try:
            # 清理学习系统的过期数据
            if adaptive_learning_system:
                adaptive_learning_system.save_all_learning_data()

            # 清理缓存
            await cache_manager.cleanup_expired()

        except Exception as e:
            logger.error(f"数据清理失败: {e}")


# 创建全局集成检测器实例
try:
    integrated_detector = IntegratedSecurityDetector()
    performance_optimizer = PerformanceOptimizer(integrated_detector)
    logger.info("集成安全检测器初始化成功")
except Exception as e:
    logger.error(f"集成安全检测器初始化失败: {e}")
    # 降级到基础检测器
    integrated_detector = SecurityDetector()
    performance_optimizer = None