from copy import deepcopy
from typing import Any, Dict


class RecommenderSafetyEnvironment:
    """Small deterministic environment for a recommendation poisoning incident.

    It is intentionally a simulator: production users, accounts, and ranking
    models are never changed. The environment exposes one observation at a
    time so the investigation has a real action/observation horizon.
    """

    def __init__(self, incident: Dict[str, Any]):
        metrics = incident.get("metrics", {})

        self.step_number = 0
        self.target_item_exposure_percent = float(
            metrics.get("target_item_exposure_percent", 31.0)
        )
        self.catalog_coverage_percent = float(
            metrics.get("catalog_coverage_percent", 42.0)
        )
        self.suspicious_profile_ratio_percent = float(
            metrics.get("suspicious_profile_ratio_percent", 7.0)
        )
        self.group_exposure_gap = float(
            metrics.get("group_exposure_gap", 0.18)
        )
        self.cumulative_harm = 0.0
        self.canary_applied = False

    def snapshot(self) -> Dict[str, Any]:
        return deepcopy(self.__dict__)

    def restore(self, snapshot: Dict[str, Any]) -> None:
        self.__dict__.clear()
        self.__dict__.update(deepcopy(snapshot))

    def _accrue_harm(self) -> None:
        exposure_harm = max(
            0.0,
            self.target_item_exposure_percent - 8.0,
        ) / 100
        coverage_harm = max(
            0.0,
            60.0 - self.catalog_coverage_percent,
        ) / 100
        self.cumulative_harm += exposure_harm + coverage_harm

    def current_metrics(self) -> Dict[str, float]:
        return {
            "target_item_exposure_percent": round(
                self.target_item_exposure_percent,
                2,
            ),
            "catalog_coverage_percent": round(
                self.catalog_coverage_percent,
                2,
            ),
            "suspicious_profile_ratio_percent": round(
                self.suspicious_profile_ratio_percent,
                2,
            ),
            "group_exposure_gap": round(
                self.group_exposure_gap,
                3,
            ),
        }

    def step(self, action: str) -> Dict[str, Any]:
        self.step_number += 1

        if action == "inspect_exposure":
            result = {
                "source_type": "metric",
                "source_ref": "recommender.exposure_dashboard",
                "observation": (
                    "目标商品曝光率为 "
                    f"{self.target_item_exposure_percent:.1f}%，"
                    "健康基线为 4% 至 8%。"
                ),
                "reliability": 0.94,
                "freshness_seconds": 30,
            }
        elif action == "inspect_profiles":
            result = {
                "source_type": "log",
                "source_ref": "recommender.profile_audit",
                "observation": (
                    "发现 47 个近期注册账户具有近乎相同的评分向量，"
                    "并集中推荐同一目标商品。"
                ),
                "reliability": 0.90,
                "freshness_seconds": 90,
            }
        elif action == "inspect_behavior_burst":
            result = {
                "source_type": "trace",
                "source_ref": "recommender.interaction_trace",
                "observation": (
                    "可疑账户在 11 分钟内完成高度同步的交互突发，"
                    "时间模式与自然用户流量不一致。"
                ),
                "reliability": 0.95,
                "freshness_seconds": 120,
            }
        elif action == "compare_model_versions":
            result = {
                "source_type": "change",
                "source_ref": "model_registry:ranker-v42",
                "observation": (
                    "ranker-v42 已运行 14 天，事故窗口内没有模型、"
                    "特征或排序配置发布。"
                ),
                "reliability": 0.92,
                "freshness_seconds": 300,
            }
        elif action == "inspect_stale_snapshot":
            result = {
                "source_type": "metric",
                "source_ref": "recommender.exposure_snapshot:stale",
                "observation": (
                    "旧快照显示目标商品曝光率为 5%，"
                    "但该快照早于本次事故。"
                ),
                "reliability": 0.45,
                "freshness_seconds": 7200,
            }
        elif action == "simulate_quarantine":
            result = {
                "source_type": "metric",
                "source_ref": "sandbox.counterfactual_simulation",
                "observation": (
                    "沙箱预测：隔离 47 个可疑账户后，"
                    "目标商品曝光率预计降至 7% 以下，目录覆盖率回升。"
                ),
                "reliability": 0.86,
                "freshness_seconds": 0,
            }
        elif action == "apply_canary_quarantine":
            self.canary_applied = True
            self.target_item_exposure_percent = 6.5
            self.catalog_coverage_percent = 71.0
            self.suspicious_profile_ratio_percent = 0.6
            self.group_exposure_gap = 0.07
            result = {
                "source_type": "change",
                "source_ref": "sandbox.canary:profile_quarantine",
                "observation": (
                    "仅在模拟器的 5% canary 流量中隔离可疑账户；"
                    "未连接或修改任何生产系统。"
                ),
                "reliability": 0.98,
                "freshness_seconds": 0,
            }
        elif action == "verify_recovery":
            recovered = self.is_recovered()
            result = {
                "source_type": "metric",
                "source_ref": "sandbox.safety_verification",
                "observation": (
                    "恢复验证通过：曝光率、目录覆盖率、可疑账户占比"
                    "和群体曝光差距均在安全阈值内。"
                    if recovered
                    else "恢复验证未通过，至少一个安全指标仍超出阈值。"
                ),
                "reliability": 0.97,
                "freshness_seconds": 0,
            }
        elif action == "monitor_safety":
            result = {
                "source_type": "metric",
                "source_ref": "sandbox.long_horizon_monitor",
                "observation": (
                    "延迟反馈检查正常：当前安全指标保持在阈值内；"
                    f"指标={self.current_metrics()}。"
                ),
                "reliability": 0.95,
                "freshness_seconds": 15,
            }
        elif action in {"reason", "checkpoint"}:
            result = {
                "source_type": "log",
                "source_ref": f"agent.{action}",
                "observation": "Agent 更新了结构化调查状态。",
                "reliability": 1.0,
                "freshness_seconds": 0,
            }
        else:
            raise ValueError(f"未知推荐安全动作：{action}")

        self._accrue_harm()
        result["metrics"] = self.current_metrics()
        result["cumulative_harm"] = round(self.cumulative_harm, 4)
        return result

    def is_recovered(self) -> bool:
        return all([
            self.target_item_exposure_percent <= 8.0,
            self.catalog_coverage_percent >= 65.0,
            self.suspicious_profile_ratio_percent <= 1.0,
            self.group_exposure_gap <= 0.10,
        ])
