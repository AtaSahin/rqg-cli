import json
from pathlib import Path
from typing import Dict, Any, List
from rqg.models import Run, DecisionRecord, FailureCluster
from rqg.config import load_config
from rqg.storage import SQLiteStore
from rqg.fingerprint import compute_fingerprint, detect_infra_hints
from rqg.scoring import compute_flake_scores
from rqg.policy import apply_policy
from rqg.output import write_decision_record, write_summary


def analyze_run(
    config_path: str = "rqg.yml",
    bundle_path: str = "rqg/bundle.jsonl",
    output_dir: str = "rqg",
) -> Dict[str, Any]:
    config = load_config(config_path)
    
    bundle_file = Path(bundle_path)
    if not bundle_file.exists():
        raise FileNotFoundError(f"Bundle not found: {bundle_path}")
    
    with open(bundle_file, "r", encoding="utf-8") as f:
        current_run = Run.from_dict(json.load(f))
    
    store = SQLiteStore()
    
    for tr in current_run.test_results:
        if tr.failure_text and not tr.fingerprint:
            tr.fingerprint = compute_fingerprint(tr.failure_text)
    
    store.save_run(current_run)
    
    history_runs = store.get_recent_runs(
        repo=current_run.metadata.repo,
        branch=current_run.metadata.branch,
        lookback_runs=config.get_lookback_runs(),
        lookback_days=config.get_lookback_days(),
    )
    
    failure_clusters = store.get_failure_clusters(
        lookback_days=config.get_lookback_days()
    )
    
    current_failures = [tr for tr in current_run.test_results if tr.outcome == "fail"]
    
    new_clusters = []
    known_clusters = {}
    
    for cluster in failure_clusters:
        known_clusters[cluster.fingerprint] = cluster
    
    for tr in current_failures:
        if tr.fingerprint:
            if tr.fingerprint not in known_clusters:
                new_clusters.append({
                    "fingerprint": tr.fingerprint,
                    "test_id": tr.test_id,
                    "failure_text": tr.failure_text[:500] if tr.failure_text else "",
                })
            else:
                cluster = known_clusters[tr.fingerprint]
                cluster.last_seen_at = current_run.metadata.started_at or current_run.metadata.ended_at
                cluster.occurrence_count += 1
                if tr.test_id not in cluster.test_ids:
                    cluster.test_ids.append(tr.test_id)
                store.update_failure_cluster(cluster)
    
    flake_scores = {}
    env_key_fields = config.get_env_key_fields()
    
    for tr in current_run.test_results:
        env_key = current_run.metadata.env_key(env_key_fields)
        key = f"{tr.test_id}::{env_key}"
        if key not in flake_scores:
            flake_scores[key] = compute_flake_scores(
                tr.test_id,
                env_key,
                history_runs + [current_run],
                config,
            )
    
    known_flaky = []
    infra_failures = []
    
    for tr in current_failures:
        if tr.fingerprint and tr.fingerprint in known_clusters:
            cluster = known_clusters[tr.fingerprint]
            key = f"{tr.test_id}::{current_run.metadata.env_key(env_key_fields)}"
            flake_score = flake_scores.get(key)
            
            if flake_score and flake_score.flake_score >= 0.5:
                known_flaky.append({
                    "test_id": tr.test_id,
                    "fingerprint": tr.fingerprint,
                    "flake_score": flake_score.flake_score,
                    "confidence": flake_score.confidence,
                    "evidence": flake_score.evidence,
                })
        
        hints = detect_infra_hints(tr.failure_text)
        if hints:
            infra_failures.append({
                "test_id": tr.test_id,
                "fingerprint": tr.fingerprint,
                "hints": hints,
            })
    
    decision_record = apply_policy(
        current_run=current_run,
        new_clusters=new_clusters,
        known_flaky=known_flaky,
        infra_failures=infra_failures,
        config=config,
    )
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    write_decision_record(decision_record, output_path / "decision.json")
    write_summary(decision_record, output_path / "summary.md")
    
    return decision_record.to_dict()

