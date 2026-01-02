import os
import json
import uuid
from pathlib import Path
from datetime import datetime
from glob import glob
from typing import Optional
from rqg.models import Run, RunMetadata, TestCaseResult
from rqg.parsers import parse_junit_xml
from rqg.fingerprint import compute_fingerprint, detect_infra_hints
from rqg.config import load_config


def collect_artifacts(
    config_path: str = "rqg.yml",
    output_path: str = "rqg/bundle.jsonl",
    repo: Optional[str] = None,
    branch: Optional[str] = None,
    commit: Optional[str] = None,
    workflow: Optional[str] = None,
    build_number: Optional[str] = None,
    attempt: Optional[int] = None,
) -> str:
    config = load_config(config_path)
    
    run_id = str(uuid.uuid4())
    
    metadata = _collect_metadata(
        repo=repo,
        branch=branch,
        commit=commit,
        workflow=workflow,
        build_number=build_number,
        attempt=attempt,
    )
    
    test_results = []
    
    for junit_glob in config.get_junit_globs():
        for xml_path in glob(junit_glob, recursive=True):
            path = Path(xml_path)
            if path.exists():
                try:
                    results = parse_junit_xml(path, config)
                    test_results.extend(results)
                except Exception as e:
                    print(f"Warning: Failed to parse {xml_path}: {e}")
    
    log_text = _collect_logs(config)
    
    for tr in test_results:
        if tr.failure_text:
            tr.fingerprint = compute_fingerprint(tr.failure_text)
    
    run = Run(
        run_id=run_id,
        metadata=metadata,
        test_results=test_results,
        log_events=[],
    )
    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(run.to_dict(), f, indent=2)
    
    return str(output_file)


def _collect_metadata(
    repo: Optional[str] = None,
    branch: Optional[str] = None,
    commit: Optional[str] = None,
    workflow: Optional[str] = None,
    build_number: Optional[str] = None,
    attempt: Optional[int] = None,
) -> RunMetadata:
    repo = repo or os.getenv("GITHUB_REPOSITORY") or os.getenv("GIT_REPO") or "unknown"
    branch = branch or os.getenv("GITHUB_REF_NAME") or os.getenv("BRANCH_NAME") or os.getenv("GIT_BRANCH") or "unknown"
    commit = commit or os.getenv("GITHUB_SHA") or os.getenv("GIT_COMMIT") or "unknown"
    
    ci_provider = None
    if os.getenv("GITHUB_ACTIONS"):
        ci_provider = "github_actions"
        workflow = workflow or os.getenv("GITHUB_WORKFLOW")
        build_number = build_number or os.getenv("GITHUB_RUN_ID")
        attempt = attempt or int(os.getenv("GITHUB_RUN_ATTEMPT", "1"))
    elif os.getenv("JENKINS_URL"):
        ci_provider = "jenkins"
        workflow = workflow or os.getenv("JOB_NAME")
        build_number = build_number or os.getenv("BUILD_NUMBER")
    
    return RunMetadata(
        repo=repo,
        branch=branch,
        commit_sha=commit,
        ci_provider=ci_provider,
        workflow=workflow,
        job=workflow,
        build_number=build_number,
        attempt=attempt,
        started_at=datetime.utcnow(),
        ended_at=datetime.utcnow(),
        os=os.getenv("RUNNER_OS") or os.getenv("OS"),
        browser=os.getenv("BROWSER"),
        device=os.getenv("DEVICE"),
        runner_pool=os.getenv("RUNNER_POOL"),
        shard_id=os.getenv("SHARD_ID"),
    )


def _collect_logs(config) -> Optional[str]:
    log_texts = []
    
    for log_glob in config.get_log_globs():
        for log_path in glob(log_glob, recursive=True):
            path = Path(log_path)
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        log_texts.append(f.read())
                except Exception as e:
                    print(f"Warning: Failed to read log {log_path}: {e}")
    
    return "\n".join(log_texts) if log_texts else None

