from typing import List, Dict, Any
from collections import defaultdict
from rqg.models import Run, TestCaseResult, FlakeScore
from rqg.config import PolicyConfig


def compute_flake_scores(
    test_id: str,
    env_key: str,
    runs: List[Run],
    config: PolicyConfig
) -> FlakeScore:
    test_outcomes = []
    consecutive_changes = 0
    retry_pass_count = 0
    retry_attempt_count = 0
    same_commit_outcomes = defaultdict(list)
    
    prev_outcome = None
    
    for run in runs:
        for tr in run.test_results:
            if tr.test_id == test_id:
                run_env_key = run.metadata.env_key(config.get_env_key_fields())
                if run_env_key == env_key:
                    outcome = tr.outcome
                    test_outcomes.append({
                        "run_id": run.run_id,
                        "commit": run.metadata.commit_sha,
                        "outcome": outcome,
                        "retry_count": tr.retry_count or 0,
                    })
                    
                    if prev_outcome and prev_outcome != outcome:
                        consecutive_changes += 1
                    
                    prev_outcome = outcome
                    
                    if tr.retry_count and tr.retry_count > 0:
                        retry_attempt_count += 1
                        if outcome == "pass":
                            retry_pass_count += 1
                    
                    same_commit_outcomes[run.metadata.commit_sha].append(outcome)
    
    total = len(test_outcomes)
    if total == 0:
        return FlakeScore(
            test_id=test_id,
            env_key=env_key,
            flake_score=0.0,
            confidence=0.0,
            evidence={},
            fail_rate=0.0,
            intermittency=0,
        )
    
    fails = sum(1 for o in test_outcomes if o["outcome"] == "fail")
    fail_rate = fails / total if total > 0 else 0.0
    
    intermittency = consecutive_changes
    
    retry_pass_rate = retry_pass_count / retry_attempt_count if retry_attempt_count > 0 else None
    
    same_commit_inconsistency = False
    for commit, outcomes in same_commit_outcomes.items():
        if len(set(outcomes)) > 1:
            same_commit_inconsistency = True
            break
    
    flake_score = 0.0
    confidence = 0.0
    
    if total >= 3:
        confidence = min(1.0, total / 20.0)
        
        if intermittency > 0:
            flake_score += min(0.4, intermittency * 0.1)
        
        if retry_pass_rate and retry_pass_rate > 0.5:
            flake_score += min(0.3, retry_pass_rate * 0.4)
        
        if same_commit_inconsistency:
            flake_score += 0.3
        
        if fail_rate > 0.3 and fail_rate < 0.9:
            flake_score += min(0.2, (fail_rate - 0.3) * 0.4)
    
    flake_score = min(1.0, flake_score)
    
    evidence = {
        "total_runs": total,
        "fail_count": fails,
        "fail_rate": fail_rate,
        "intermittency": intermittency,
        "retry_pass_rate": retry_pass_rate,
        "same_commit_inconsistency": same_commit_inconsistency,
    }
    
    return FlakeScore(
        test_id=test_id,
        env_key=env_key,
        flake_score=flake_score,
        confidence=confidence,
        evidence=evidence,
        fail_rate=fail_rate,
        intermittency=intermittency,
        retry_pass_rate=retry_pass_rate,
        same_commit_inconsistency=same_commit_inconsistency,
    )

