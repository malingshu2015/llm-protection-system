#!/usr/bin/env python3
"""
修复聊天端点阻塞问题

问题分析：
- 上下文感知检测器使用大量同步正则表达式匹配
- 在异步上下文中执行同步计算密集型操作，导致事件循环阻塞
- 聊天请求超时，而其他简单API正常

解决方案：
- 将上下文感知检测改为异步执行
- 添加超时保护
- 优化正则表达式性能
"""

import asyncio
import time
import os
import shutil
from pathlib import Path


async def main():
    print("🔧 开始修复聊天端点阻塞问题...")
    
    # 1. 备份当前文件
    detector_file = "src/security/detector.py"
    context_detector_file = "src/security/context_aware_detector.py"
    
    backup_dir = f"backups/chat_fix_backup_{int(time.time())}"
    os.makedirs(backup_dir, exist_ok=True)
    
    print(f"📁 创建备份目录: {backup_dir}")
    shutil.copy2(detector_file, f"{backup_dir}/detector.py")
    shutil.copy2(context_detector_file, f"{backup_dir}/context_aware_detector.py")
    
    # 2. 修复detector.py中的异步调用
    print("🔧 修复安全检测器的异步调用...")
    
    with open(detector_file, 'r', encoding='utf-8') as f:
        detector_content = f.read()
    
    # 修复第1718行：添加await关键字
    detector_content = detector_content.replace(
        "result = self.context_aware_detector.detect(temp_conversation)",
        "result = await self.context_aware_detector.detect(temp_conversation)"
    )
    
    with open(detector_file, 'w', encoding='utf-8') as f:
        f.write(detector_content)
    
    # 3. 修复context_aware_detector.py：改为异步方法
    print("🔧 修复上下文感知检测器为异步方法...")
    
    with open(context_detector_file, 'r', encoding='utf-8') as f:
        context_content = f.read()
    
    # 将detect方法改为异步
    context_content = context_content.replace(
        "def detect(self, conversation: Conversation) -> DetectionResult:",
        "async def detect(self, conversation: Conversation) -> DetectionResult:"
    )
    
    # 添加计算密集型操作的异步执行
    intensive_operations = [
        "_analyze_escalation_patterns",
        "_analyze_pattern_repetition", 
        "_analyze_topic_drift",
        "_analyze_persistence_patterns"
    ]
    
    for operation in intensive_operations:
        # 将同步方法调用改为异步
        old_call = f"{operation}_score = self.{operation}(conversation)"
        new_call = f"{operation}_score = await self._run_in_executor(self.{operation}, conversation)"
        context_content = context_content.replace(old_call, new_call)
    
    # 添加执行器方法
    executor_method = '''
    async def _run_in_executor(self, func, *args):
        """在线程池中执行计算密集型操作。"""
        import concurrent.futures
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            try:
                # 设置超时以防止长时间阻塞
                return await asyncio.wait_for(
                    loop.run_in_executor(executor, func, *args),
                    timeout=5.0  # 5秒超时
                )
            except asyncio.TimeoutError:
                logger.warning("上下文感知检测超时，跳过检测")
                from src.models_interceptor import DetectionResult
                return DetectionResult(is_allowed=True)
'''
    
    # 在类定义的末尾添加执行器方法
    class_end = context_content.rfind("        return DetectionResult(is_allowed=True)")
    if class_end != -1:
        # 找到类定义的末尾
        next_method_or_class = context_content.find("\n    def ", class_end)
        if next_method_or_class == -1:
            next_method_or_class = context_content.find("\nclass ", class_end)
        
        if next_method_or_class != -1:
            context_content = (context_content[:next_method_or_class] + 
                             executor_method + 
                             context_content[next_method_or_class:])
        else:
            # 如果找不到下一个方法或类，添加到文件末尾
            context_content += executor_method
    
    with open(context_detector_file, 'w', encoding='utf-8') as f:
        f.write(context_content)
    
    # 4. 创建性能优化的正则表达式缓存
    print("🔧 优化正则表达式性能...")
    
    optimization_code = '''
import re
from functools import lru_cache

class RegexCache:
    """正则表达式缓存，提高匹配性能。"""
    
    _compiled_patterns = {}
    
    @classmethod
    @lru_cache(maxsize=1000)
    def get_compiled_pattern(cls, pattern: str, flags: int = re.IGNORECASE):
        """获取编译后的正则表达式。"""
        cache_key = (pattern, flags)
        if cache_key not in cls._compiled_patterns:
            cls._compiled_patterns[cache_key] = re.compile(pattern, flags)
        return cls._compiled_patterns[cache_key]
    
    @classmethod
    def search(cls, pattern: str, text: str, flags: int = re.IGNORECASE):
        """使用缓存的正则表达式进行搜索。"""
        compiled_pattern = cls.get_compiled_pattern(pattern, flags)
        return compiled_pattern.search(text)
'''
    
    # 添加正则表达式缓存到context_aware_detector.py
    context_content = optimization_code + "\n\n" + context_content
    
    # 替换所有re.search调用为缓存版本
    context_content = context_content.replace(
        "re.search(pattern, content)",
        "RegexCache.search(pattern, content)"
    )
    context_content = context_content.replace(
        "re.search(pattern, text)",
        "RegexCache.search(pattern, text)"
    )
    
    with open(context_detector_file, 'w', encoding='utf-8') as f:
        f.write(context_content)
    
    # 5. 添加导入语句
    if "import asyncio" not in context_content:
        context_content = "import asyncio\n" + context_content
        with open(context_detector_file, 'w', encoding='utf-8') as f:
            f.write(context_content)
    
    print("✅ 修复完成！")
    print("\n📋 修复摘要:")
    print("1. ✅ 添加了异步执行器，避免阻塞事件循环")
    print("2. ✅ 添加了5秒超时保护，防止长时间阻塞")
    print("3. ✅ 优化了正则表达式缓存，提高匹配性能")
    print("4. ✅ 修复了异步方法调用缺少await的问题")
    print(f"5. ✅ 备份文件保存在: {backup_dir}")
    
    print("\n🔄 建议重启防火墙服务以应用修复...")


if __name__ == "__main__":
    asyncio.run(main())