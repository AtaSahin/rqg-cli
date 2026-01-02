import os
import sys
from pathlib import Path
from rqg.collect import collect_artifacts
from rqg.analyze import analyze_run

if __name__ == "__main__":
    print("RQG Example Usage\n")
    
    os.environ["GITHUB_REPOSITORY"] = "example/repo"
    os.environ["GITHUB_REF_NAME"] = "main"
    os.environ["GITHUB_SHA"] = "abc123def456"
    os.environ["GITHUB_WORKFLOW"] = "test"
    os.environ["GITHUB_RUN_ID"] = "123"
    
    print("1. Collecting artifacts...")
    bundle_path = collect_artifacts(
        config_path="rqg.yml",
        output_path="rqg/bundle.jsonl",
    )
    print(f"   Bundle created: {bundle_path}\n")
    
    print("2. Analyzing run...")
    try:
        decision = analyze_run(
            config_path="rqg.yml",
            bundle_path=bundle_path,
            output_dir="rqg",
        )
        print(f"   Decision: {decision.get('decision')}")
        print(f"   Check rqg/decision.json and rqg/summary.md for details")
    except Exception as e:
        print(f"   Error: {e}")
        sys.exit(1)

