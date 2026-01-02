from typing import Optional
from rqg.config import load_config
from rqg.storage import SQLiteStore
from rqg.scoring import compute_flake_scores


def explain_test(test_id: str, config_path: str = "rqg.yml", history_dir: str = ".rqg"):
    config = load_config(config_path)
    store = SQLiteStore(db_path=f"{history_dir}/rqg.db")
    
    print(f"Explanation for test: {test_id}\n")
    
    recent_runs = store.get_recent_runs(
        repo="unknown",
        lookback_runs=50,
        lookback_days=14,
    )
    
    env_key_fields = config.get_env_key_fields()
    
    for run in recent_runs:
        for tr in run.test_results:
            if tr.test_id == test_id:
                env_key = run.metadata.env_key(env_key_fields)
                flake_score = compute_flake_scores(test_id, env_key, recent_runs, config)
                
                print(f"Environment: {env_key}")
                print(f"Outcome: {tr.outcome}")
                print(f"Flake Score: {flake_score.flake_score:.2f}")
                print(f"Confidence: {flake_score.confidence:.2f}")
                print(f"Fail Rate: {flake_score.fail_rate:.2f}")
                print(f"Intermittency: {flake_score.intermittency}")
                print(f"Evidence: {flake_score.evidence}")
                
                if tr.fingerprint:
                    print(f"Fingerprint: {tr.fingerprint}")
                
                if tr.failure_text:
                    print(f"Failure Text: {tr.failure_text[:500]}")
                
                print("\n" + "="*50 + "\n")
                return
    
    print(f"Test {test_id} not found in recent history")

