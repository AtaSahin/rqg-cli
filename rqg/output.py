from pathlib import Path
from rqg.models import DecisionRecord


def write_decision_record(record: DecisionRecord, output_path: Path):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(record.to_json())


def write_summary(record: DecisionRecord, output_path: Path):
    lines = []
    lines.append("# RQG Decision Summary\n")
    lines.append(f"**Decision:** {record.decision}\n")
    lines.append(f"**Timestamp:** {record.timestamp}\n")
    lines.append("\n## Run Context\n")
    
    ctx = record.run_context
    lines.append(f"- Repository: {ctx.get('repo')}")
    lines.append(f"- Commit: {ctx.get('commit')}")
    lines.append(f"- Branch: {ctx.get('branch')}")
    lines.append(f"- Job: {ctx.get('job')}")
    lines.append(f"- Attempt: {ctx.get('attempt')}")
    lines.append(f"- Environment: {ctx.get('env_key')}")
    
    lines.append("\n## Current Run Summary\n")
    summary = record.current_run_summary
    lines.append(f"- Total Tests: {summary.get('total_tests', 0)}")
    lines.append(f"- Passed: {summary.get('passed', 0)}")
    lines.append(f"- Failed: {summary.get('failed', 0)}")
    lines.append(f"- Skipped: {summary.get('skipped', 0)}")
    lines.append(f"- Duration: {summary.get('duration_ms', 0) / 1000:.2f}s")
    
    if record.new_failure_clusters:
        lines.append("\n## New Failure Clusters\n")
        for cluster in record.new_failure_clusters[:10]:
            lines.append(f"- **{cluster.get('test_id')}**")
            lines.append(f"  - Fingerprint: `{cluster.get('fingerprint', '')[:16]}...`")
            if cluster.get('failure_text'):
                lines.append(f"  - Error: {cluster['failure_text'][:200]}")
    
    if record.known_flaky_failures:
        lines.append("\n## Known Flaky Failures\n")
        for flaky in record.known_flaky_failures[:10]:
            lines.append(f"- **{flaky.get('test_id')}**")
            lines.append(f"  - Flake Score: {flaky.get('flake_score', 0):.2f}")
            lines.append(f"  - Confidence: {flaky.get('confidence', 0):.2f}")
    
    if record.infra_failures:
        lines.append("\n## Infrastructure Failures\n")
        for infra in record.infra_failures[:10]:
            lines.append(f"- **{infra.get('test_id')}**")
            lines.append(f"  - Hints: {', '.join(infra.get('hints', []))}")
    
    if record.recommendations:
        lines.append("\n## Recommendations\n")
        
        rerun = record.recommendations.get("targeted_rerun")
        if rerun:
            lines.append("### Targeted Rerun Plan\n")
            lines.append(f"- Rerun {rerun.get('count', 0)} tests")
            lines.append(f"- Runner Pool: {rerun.get('runner_pool')}")
            lines.append(f"- Attempts: {rerun.get('attempts')}")
            if rerun.get('tests'):
                lines.append("- Tests:")
                for test in rerun['tests'][:10]:
                    lines.append(f"  - {test}")
        
        quarantine = record.recommendations.get("quarantine_candidates")
        if quarantine:
            lines.append("\n### Quarantine Candidates\n")
            for q in quarantine[:10]:
                lines.append(f"- {q.get('test_id')} (score: {q.get('flake_score', 0):.2f})")
        
        hotspots = record.recommendations.get("infra_hotspots")
        if hotspots:
            lines.append("\n### Infrastructure Hotspots\n")
            for h in hotspots:
                lines.append(f"- {h.get('type')}: {h.get('value')} ({h.get('failure_count')} failures)")
    
    lines.append("\n## Decision Reasons\n")
    for reason in record.decision_reasons:
        lines.append(f"- **{reason.get('type')}** ({reason.get('severity')})")
        lines.append(f"  - {reason.get('message')}")
    
    if record.analysis_errors:
        lines.append("\n## Analysis Errors\n")
        for error in record.analysis_errors:
            lines.append(f"- {error}")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

