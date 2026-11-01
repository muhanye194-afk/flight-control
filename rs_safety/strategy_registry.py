import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional
from uuid import uuid4

from rs_safety.strategy_models import (
    ALLOWED_STRATEGY_ACTIONS,
    BASELINE_SYSTEM_PROMPT,
    CandidateProposal,
    StrategyVersion,
)


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_STORE_PATH = BASE_DIR / ".flight_control" / "strategy_registry.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_baseline_strategy() -> StrategyVersion:
    return StrategyVersion(
        version_id="rs_strategy_v1",
        parent_version_id=None,
        created_at=utc_now(),
        system_prompt=BASELINE_SYSTEM_PROMPT,
        evidence_threshold=0.72,
        checkpoint_interval=5,
        allowed_actions=ALLOWED_STRATEGY_ACTIONS.copy(),
        change_summary="Initial evidence-gated recommender safety strategy.",
        status="active",
    )


class StrategyRegistry:
    def __init__(self, store_path: Optional[Path] = None):
        self.store_path = store_path or DEFAULT_STORE_PATH
        self._lock = Lock()
        self._versions: Dict[str, StrategyVersion] = {}
        self._active_version_id = "rs_strategy_v1"
        self._load()

    def _load(self) -> None:
        if self.store_path.exists():
            payload = json.loads(
                self.store_path.read_text(encoding="utf-8")
            )
            self._versions = {
                item["version_id"]: StrategyVersion.model_validate(item)
                for item in payload.get("versions", [])
            }
            self._active_version_id = payload.get(
                "active_version_id",
                "rs_strategy_v1",
            )

        if not self._versions:
            baseline = make_baseline_strategy()
            self._versions[baseline.version_id] = baseline
            self._active_version_id = baseline.version_id

    def _save(self) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "active_version_id": self._active_version_id,
            "versions": [
                version.model_dump()
                for version in self._versions.values()
            ],
        }
        temporary_path = self.store_path.with_suffix(".tmp")
        temporary_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary_path.replace(self.store_path)

    def get_active(self) -> StrategyVersion:
        with self._lock:
            return self._versions[self._active_version_id].model_copy(
                deep=True
            )

    def get(self, version_id: str) -> StrategyVersion:
        with self._lock:
            if version_id not in self._versions:
                raise KeyError(f"未知策略版本：{version_id}")
            return self._versions[version_id].model_copy(deep=True)

    def list_versions(self) -> List[StrategyVersion]:
        with self._lock:
            versions = sorted(
                self._versions.values(),
                key=lambda item: item.created_at,
            )
            return [item.model_copy(deep=True) for item in versions]

    def register_candidate(
        self,
        parent: StrategyVersion,
        proposal: CandidateProposal,
    ) -> StrategyVersion:
        with self._lock:
            version = StrategyVersion(
                version_id=f"rs_strategy_{uuid4().hex[:8]}",
                parent_version_id=parent.version_id,
                created_at=utc_now(),
                system_prompt=proposal.system_prompt,
                evidence_threshold=proposal.evidence_threshold,
                checkpoint_interval=proposal.checkpoint_interval,
                allowed_actions=parent.allowed_actions.copy(),
                change_summary=proposal.change_summary,
                status="candidate",
            )
            self._versions[version.version_id] = version
            self._save()
            return version.model_copy(deep=True)

    def record_evaluation(
        self,
        version_id: str,
        summary: Dict[str, float],
    ) -> None:
        with self._lock:
            version = self._versions[version_id]
            version.evaluation_summary.update(summary)
            self._save()

    def reject(self, version_id: str) -> None:
        with self._lock:
            version = self._versions[version_id]
            if version.status == "candidate":
                version.status = "rejected"
            self._save()

    def promote(self, version_id: str) -> StrategyVersion:
        with self._lock:
            if version_id not in self._versions:
                raise KeyError(f"未知策略版本：{version_id}")

            previous = self._versions[self._active_version_id]
            previous.status = "superseded"

            promoted = self._versions[version_id]
            promoted.status = "active"
            self._active_version_id = version_id
            self._save()
            return promoted.model_copy(deep=True)


STRATEGY_REGISTRY = StrategyRegistry()
