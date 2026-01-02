from typing import List, Dict, Any
from rqg.models import Run, DecisionRecord
from rqg.config import PolicyConfig
from rqg.recommendations import generate_recommendations


def apply_policy(
    current_run: Run,
    new_clusters: List[Dict[str, Any]],
    known_flaky: List[Dict[str, Any]],
    infra_failures: List[Dict[str, Any]],
    config: PolicyConfig,
) -> DecisionRecord:
    decision = "PASS"
    reasons = []
    
    gating = config.gating
    hard_block = gating.get("hard_block", {})
    soft_block = gating.get("soft_block", {})
    
    current_failures = [tr for tr in current_run.test_results if tr.outcome == "fail"]
    
    new_cluster_count = len(new_clusters)
    max_new_clusters = hard_block.get("max_new_failure_clusters", 0)
    
    if new_cluster_count > max_new_clusters:
        decision = "HARD_BLOCK"
        reasons.append({
            "type": "new_failure_clusters",
            "severity": "high",
            "message": f"Found {new_cluster_count} new failure clusters (max allowed: {max_new_clusters})",
            "data": {"count": new_cluster_count, "clusters": new_clusters[:5]},
        })
    
    critical_paths = hard_block.get("critical_paths", [])
    required_suites = hard_block.get("required_suites", [])
    
    for tr in current_failures:
        suite_lower = tr.suite.lower()
        test_id_lower = tr.test_id.lower()
        
        for critical in critical_paths:
            if critical.lower() in suite_lower or critical.lower() in test_id_lower:
                if tr.fingerprint not in [c["fingerprint"] for c in new_clusters]:
                    continue
                
                decision = "HARD_BLOCK"
                reasons.append({
                    "type": "critical_path_failure",
                    "severity": "high",
                    "message": f"New failure in critical path: {critical}",
                    "data": {"test_id": tr.test_id, "suite": tr.suite},
                })
        
        if tr.suite in required_suites:
            is_known_flaky = any(
                f["test_id"] == tr.test_id and f.get("flake_score", 0) >= 0.75
                for f in known_flaky
            )
            
            if not is_known_flaky:
                decision = "HARD_BLOCK"
                reasons.append({
                    "type": "required_suite_failure",
                    "severity": "high",
                    "message": f"Required suite '{tr.suite}' has failure",
                    "data": {"test_id": tr.test_id, "suite": tr.suite},
                })
    
    if decision == "PASS":
        max_known_flaky = soft_block.get("max_known_flaky_failures", 5)
        if len(known_flaky) > max_known_flaky:
            decision = "SOFT_BLOCK"
            reasons.append({
                "type": "too_many_flaky",
                "severity": "medium",
                "message": f"Too many known flaky failures: {len(known_flaky)} (max: {max_known_flaky})",
                "data": {"count": len(known_flaky)},
            })
        
        max_infra = soft_block.get("max_infra_failures", 10)
        if len(infra_failures) > max_infra:
            decision = "SOFT_BLOCK"
            reasons.append({
                "type": "too_many_infra",
                "severity": "medium",
                "message": f"Too many infrastructure failures: {len(infra_failures)} (max: {max_infra})",
                "data": {"count": len(infra_failures)},
            })
    
    recommendations = generate_recommendations(
        current_run=current_run,
        new_clusters=new_clusters,
        known_flaky=known_flaky,
        infra_failures=infra_failures,
        config=config,
    )
    
    run_context = {
        "repo": current_run.metadata.repo,
        "commit": current_run.metadata.commit_sha,
        "branch": current_run.metadata.branch,
        "job": current_run.metadata.job,
        "attempt": current_run.metadata.attempt,
        "env_key": current_run.metadata.env_key(config.get_env_key_fields()),
    }
    
    inputs_present = {
        "junit_count": len(current_run.test_results),
        "logs_present": len(current_run.log_events) > 0,
        "missing_fields": [],
    }
    
    policy_info = {
        "mode": config.mode,
        "version": config.version,
        "hash": str(hash(str(config.__dict__))),
    }
    
    current_run_summary = {
        "total_tests": len(current_run.test_results),
        "passed": sum(1 for tr in current_run.test_results if tr.outcome == "pass"),
        "failed": len(current_failures),
        "skipped": sum(1 for tr in current_run.test_results if tr.outcome == "skip"),
        "duration_ms": sum(tr.duration_ms or 0 for tr in current_run.test_results),
    }
    
    return DecisionRecord(
        run_context=run_context,
        inputs_present=inputs_present,
        policy=policy_info,
        current_run_summary=current_run_summary,
        new_failure_clusters=new_clusters,
        known_flaky_failures=known_flaky,
        infra_failures=infra_failures,
        recommendations=recommendations,
        decision=decision,
        decision_reasons=reasons,
    )

