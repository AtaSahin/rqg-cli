from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
import json


@dataclass
class RunMetadata:
    repo: str
    branch: str
    commit_sha: str
    ci_provider: Optional[str] = None
    workflow: Optional[str] = None
    job: Optional[str] = None
    build_number: Optional[str] = None
    attempt: Optional[int] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    os: Optional[str] = None
    browser: Optional[str] = None
    device: Optional[str] = None
    runner_pool: Optional[str] = None
    shard_id: Optional[str] = None

    def to_dict(self):
        d = asdict(self)
        for k, v in d.items():
            if isinstance(v, datetime):
                d[k] = v.isoformat()
        return d

    @classmethod
    def from_dict(cls, d):
        for k in ["started_at", "ended_at"]:
            if k in d and d[k]:
                d[k] = datetime.fromisoformat(d[k])
        return cls(**d)

    def env_key(self, fields: List[str]) -> str:
        parts = []
        for field in fields:
            value = getattr(self, field, None)
            if value:
                parts.append(f"{field}={value}")
        return "|".join(parts) if parts else "default"


@dataclass
class TestCaseResult:
    test_id: str
    suite: str
    classname: Optional[str] = None
    name: Optional[str] = None
    duration_ms: Optional[float] = None
    outcome: str = "pass"
    failure_text: Optional[str] = None
    fingerprint: Optional[str] = None
    retry_count: Optional[int] = None
    system_out: Optional[str] = None
    system_err: Optional[str] = None

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


@dataclass
class Run:
    run_id: str
    metadata: RunMetadata
    test_results: List[TestCaseResult] = field(default_factory=list)
    log_events: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self):
        return {
            "run_id": self.run_id,
            "metadata": self.metadata.to_dict(),
            "test_results": [tr.to_dict() for tr in self.test_results],
            "log_events": self.log_events,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            run_id=d["run_id"],
            metadata=RunMetadata.from_dict(d["metadata"]),
            test_results=[TestCaseResult.from_dict(tr) for tr in d.get("test_results", [])],
            log_events=d.get("log_events", []),
        )


@dataclass
class FailureCluster:
    fingerprint: str
    first_seen_at: datetime
    last_seen_at: datetime
    example_failure_text: str
    infra_hints: List[str] = field(default_factory=list)
    test_ids: List[str] = field(default_factory=list)
    occurrence_count: int = 0

    def to_dict(self):
        d = asdict(self)
        for k, v in d.items():
            if isinstance(v, datetime):
                d[k] = v.isoformat()
        return d


@dataclass
class FlakeScore:
    test_id: str
    env_key: str
    flake_score: float
    confidence: float
    evidence: Dict[str, Any]
    fail_rate: float
    intermittency: int
    retry_pass_rate: Optional[float] = None
    same_commit_inconsistency: bool = False

    def to_dict(self):
        return asdict(self)


@dataclass
class DecisionRecord:
    run_context: Dict[str, Any]
    inputs_present: Dict[str, Any]
    policy: Dict[str, Any]
    current_run_summary: Dict[str, Any]
    new_failure_clusters: List[Dict[str, Any]]
    known_flaky_failures: List[Dict[str, Any]]
    infra_failures: List[Dict[str, Any]]
    recommendations: Dict[str, Any]
    decision: str
    decision_reasons: List[Dict[str, Any]]
    analysis_errors: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self):
        return asdict(self)

    def to_json(self, indent=2):
        return json.dumps(self.to_dict(), indent=indent)

