from pathlib import Path
import yaml
from typing import Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class PolicyConfig:
    version: int
    mode: str
    history: Dict[str, Any]
    inputs: Dict[str, List[str]]
    identity: Dict[str, Any]
    gating: Dict[str, Any]
    flake_detection: Dict[str, Any]
    recommendations: Dict[str, Any]

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PolicyConfig":
        return cls(
            version=d.get("version", 1),
            mode=d.get("mode", "pr"),
            history=d.get("history", {}),
            inputs=d.get("inputs", {}),
            identity=d.get("identity", {}),
            gating=d.get("gating", {}),
            recommendations=d.get("recommendations", {}),
            flake_detection=d.get("flake_detection", {}),
        )

    def get_junit_globs(self) -> List[str]:
        return self.inputs.get("junit_globs", ["**/junit*.xml", "**/TEST-*.xml"])

    def get_log_globs(self) -> List[str]:
        return self.inputs.get("log_globs", ["**/ci.log", "**/console.log"])

    def get_test_id_strategy(self) -> str:
        return self.identity.get("test_id_strategy", "classname::name")

    def get_env_key_fields(self) -> List[str]:
        return self.identity.get("env_key_fields", ["os", "browser", "device", "runner_pool"])

    def get_lookback_runs(self) -> int:
        return self.history.get("lookback_runs", 50)

    def get_lookback_days(self) -> int:
        return self.history.get("lookback_days", 14)


def load_config(config_path: str = "rqg.yml") -> PolicyConfig:
    path = Path(config_path)
    if not path.exists():
        return PolicyConfig.from_dict({})
    
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    
    return PolicyConfig.from_dict(data)

