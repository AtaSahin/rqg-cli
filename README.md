# Release Quality Gate (RQG)

Policy-based CI quality gate that analyzes JUnit/pytest results and CI logs to classify flaky vs deterministic failures and output an auditable release decision (`PASS`, `SOFT_BLOCK`, `HARD_BLOCK`).

## Why this exists
CI failures are often not product regressions (flaky tests, infra noise, retries, parallel shards). Teams lose trust and start “rerun until green”. RQG turns noisy signals into a decision with evidence and next actions.

## What it does
### Inputs
- JUnit XML (pytest, Maven/Gradle, Jest JUnit output)
- CI logs (one or more files)
- Run metadata (commit, branch, job, attempt, environment key)

### Processing
- Normalizes results into a common model
- Fingerprints failures by sanitizing timestamps/UUIDs/ports/durations to form stable clusters
- Computes explainable flake score + confidence from history
- Applies `rqg.yml` policy to decide: `PASS` / `SOFT_BLOCK` / `HARD_BLOCK`
- Generates recommendations: targeted rerun, quarantine candidates, infra hotspots

### Outputs
- `rqg/decision.json` decision record (policy hash, evidence, reasons, missing inputs)
- `rqg/summary.md` short human-readable summary
- Exit codes for CI gating: `0` PASS, `10` SOFT_BLOCK, `20` HARD_BLOCK

## Quick start
```bash
pip install -e .
pytest --junitxml=report/junit.xml | tee ci.log
rqg collect --junit-glob "report/junit.xml" --log-glob "ci.log"
rqg analyze
```
## CLI

- `rqg collect` discovers artifacts, parses JUnit, collects logs/metadata, produces a run bundle  
- `rqg analyze` loads bundle + history (SQLite), scores, decides, writes outputs, returns gate exit code  
- `rqg explain <test_id|fingerprint>` prints evidence behind a classification  
- `rqg upload` optional bundle upload (MVP works locally)

## Policy (`rqg.yml`) minimal example

```yaml
version: 1
mode: pr
history: { lookback_runs: 50, lookback_days: 14 }

inputs:
  junit_globs: ["**/junit*.xml", "**/TEST-*.xml"]
  log_globs: ["**/ci.log", "**/console.log"]

identity:
  test_id_strategy: "classname::name"
  env_key_fields: ["os", "browser", "device", "runner_pool"]

gating:
  hard_block:
    new_failure_min_repro: 2
    critical_paths: ["payments", "auth", "checkout"]
    required_suites: ["smoke"]
    max_new_failure_clusters: 0
  soft_block:
    max_known_flaky_failures: 5
    max_infra_failures: 10
```
## CI integration (shape)

Run after tests:

1. tests produce JUnit + logs  
2. `rqg collect`  
3. `rqg analyze` gates the deploy stage via exit code  
4. archive `rqg/` artifacts  

