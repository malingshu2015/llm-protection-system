"""
规则模式管理器 (M2.2)
全局单例，管理所有规则的 Dry-Run / Blocking 模式状态。
由于 SecurityDetector 在多处被独立实例化，规则模式状态需要集中管理。
"""

import json
import os
from typing import Dict, Optional
from src.logger import logger

# 规则模式持久化文件路径
RULE_MODES_FILE = "data/security/rule_modes.json"


class RuleModeManager:
    """集中管理所有规则的执行模式。

    规则模式独立于 SecurityDetector 实例存储，确保跨多个实例的一致性。
    模式状态可持久化到磁盘，服务重启后自动恢复。
    """

    def __init__(self):
        # rule_id -> mode ("blocking" | "dry_run")
        self._modes: Dict[str, str] = {}
        # rule_id -> dry_run 命中计数
        self._dry_run_hits: Dict[str, int] = {}
        self._load_from_disk()

    def _load_from_disk(self):
        """从磁盘加载规则模式配置。"""
        try:
            if os.path.exists(RULE_MODES_FILE):
                with open(RULE_MODES_FILE, "r") as f:
                    data = json.load(f)
                    self._modes = data.get("modes", {})
                    self._dry_run_hits = data.get("hits", {})
                    logger.info(f"[RuleModeManager] 已加载 {len(self._modes)} 条规则模式配置")
        except Exception as e:
            logger.warning(f"[RuleModeManager] 加载规则模式配置失败，使用默认值: {e}")

    def _save_to_disk(self):
        """将规则模式配置持久化到磁盘。"""
        try:
            os.makedirs(os.path.dirname(RULE_MODES_FILE), exist_ok=True)
            with open(RULE_MODES_FILE, "w") as f:
                json.dump({
                    "modes": self._modes,
                    "hits": self._dry_run_hits,
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[RuleModeManager] 保存规则模式配置失败: {e}")

    def get_mode(self, rule_id: str) -> str:
        """获取规则的执行模式，默认为 blocking。"""
        return self._modes.get(rule_id, "blocking")

    def is_dry_run(self, rule_id: str) -> bool:
        """判断规则是否处于 Dry-Run 模式。"""
        return self.get_mode(rule_id) == "dry_run"

    def set_mode(self, rule_id: str, mode: str) -> str:
        """设置规则的执行模式。

        Args:
            rule_id: 规则ID
            mode: "blocking" 或 "dry_run"

        Returns:
            之前的模式
        """
        old_mode = self._modes.get(rule_id, "blocking")
        self._modes[rule_id] = mode

        # 切换回 blocking 时重置命中计数
        if mode == "blocking":
            self._dry_run_hits[rule_id] = 0

        self._save_to_disk()
        logger.info(f"[RuleModeManager] 规则 {rule_id} 模式: {old_mode} → {mode}")
        return old_mode

    def record_hit(self, rule_id: str):
        """记录 Dry-Run 命中。"""
        self._dry_run_hits[rule_id] = self._dry_run_hits.get(rule_id, 0) + 1
        # 不每次写盘，在获取统计或切换模式时再写
        logger.debug(f"[RuleModeManager] 规则 {rule_id} dry-run 命中: {self._dry_run_hits[rule_id]}")

    def get_hits(self, rule_id: str) -> int:
        """获取 Dry-Run 命中计数。"""
        return self._dry_run_hits.get(rule_id, 0)

    def get_all_stats(self) -> Dict:
        """获取所有规则的模式和命中统计。"""
        # 持久化最新的命中数据
        self._save_to_disk()
        return {
            "modes": dict(self._modes),
            "hits": dict(self._dry_run_hits),
        }


# 全局单例
rule_mode_manager = RuleModeManager()
