from typing import List, Dict, Any
from rqg.models import Run
from rqg.config import PolicyConfig


def generate_recommendations(
    current_run: Run,
    new_clusters: List[Dict[str, Any]],
    known_flaky: List[Dict[str, Any]],
    infra_failures: List[Dict[str, Any]],
    config: PolicyConfig,
) -> Dict[str, Any]:
    recommendations = {
        "targeted_rerun": None,
        "quarantine_candidates": [],
        "infra_hotspots": [],
    }
    
    rerun_config = config.recommendations.get("targeted_rerun", {})
    if rerun_config.get("enabled", False):
        rerun_plan = _generate_rerun_plan(
            current_run=current_run,
            new_clusters=new_clusters,
            known_flaky=known_flaky,
            infra_failures=infra_failures,
            config=config,
        )
        if rerun_plan:
            recommendations["targeted_rerun"] = rerun_plan
    
    quarantine_config = config.flake_detection.get("quarantine_candidate", {})
    for flaky in known_flaky:
        if (flaky.get("flake_score", 0) >= quarantine_config.get("flake_score_threshold", 0.75) and
            flaky.get("confidence", 0) >= quarantine_config.get("confidence_threshold", 0.6)):
            recommendations["quarantine_candidates"].append({
                "test_id": flaky["test_id"],
                "flake_score": flaky["flake_score"],
                "confidence": flaky["confidence"],
                "evidence": flaky.get("evidence", {}),
            })
    
    if infra_failures:
        runner_pool = current_run.metadata.runner_pool
        os_type = current_run.metadata.os
        
        if runner_pool:
            recommendations["infra_hotspots"].append({
                "type": "runner_pool",
                "value": runner_pool,
                "failure_count": len(infra_failures),
            })
        
        if os_type:
            recommendations["infra_hotspots"].append({
                "type": "os",
                "value": os_type,
                "failure_count": len(infra_failures),
            })
    
    return recommendations


def _generate_rerun_plan(
    current_run: Run,
    new_clusters: List[Dict[str, Any]],
    known_flaky: List[Dict[str, Any]],
    infra_failures: List[Dict[str, Any]],
    config: PolicyConfig,
) -> Dict[str, Any]:
    rerun_config = config.recommendations.get("targeted_rerun", {})
    max_tests = rerun_config.get("max_tests", 30)
    
    rerun_tests = []
    
    for flaky in known_flaky:
        if flaky["test_id"] not in rerun_tests:
            rerun_tests.append(flaky["test_id"])
    
    for infra in infra_failures:
        if infra["test_id"] not in rerun_tests:
            rerun_tests.append(infra["test_id"])
    
    if len(rerun_tests) > max_tests:
        rerun_tests = rerun_tests[:max_tests]
    
    if not rerun_tests:
        return None
    
    return {
        "tests": rerun_tests,
        "count": len(rerun_tests),
        "runner_pool": rerun_config.get("prefer_runner_pool", "stable"),
        "attempts": rerun_config.get("rerun_attempts", 1),
        "reason": "suspected_flakes_or_infra",
    }

