# Release Quality Gate (RQG)

**Version:** 0.1.0 (MVP/Beta)  
**Status:** Beta - Core features complete, improvements in progress

RQG is a system that analyzes test results in CI pipelines, detects flaky tests, and provides a gating mechanism for release decisions.

## Installation

```bash
pip install -e .
```

or

```bash
pipx install .
```

## Quick Start

1. Create `rqg.yml` config file in repo root
2. After tests in your CI pipeline:
   ```bash
   rqg collect
   rqg analyze
   ```
3. Check `rqg/decision.json` and `rqg/summary.md` files
4. Gate pipeline based on exit code (0=PASS, 10=SOFT_BLOCK, 20=HARD_BLOCK)

## CLI Commands

- `rqg collect` - Collects artifacts and creates bundle
- `rqg analyze` - Analyzes with history and produces decision
- `rqg explain <test_id>` - Shows explanation for test or cluster
- `rqg upload` - Uploads bundle to central service (optional)

## Quick Test

```bash
# Install package
pip install -e .

# Run test script
python test_rqg.py
```

## Documentation

- **KULLANIM.md** - Detailed usage and test guide (Turkish)
- **ENTEGRASYON.md** - CI/CD integration guide (Turkish)
- **ROADMAP.md** - Development roadmap
- **docs/quickstart.md** - Quick start guide
- **docs/policy-reference.md** - Policy config reference
- **docs/architecture.md** - Architecture documentation

## Status and Limitations

**Current Version:** 0.1.0 (MVP/Beta)

This version includes core features but some improvements are required for production use:

- CI cache/restore mechanism missing (history resets on each run)
- Limited shard/parallel execution support
- No override permission levels
- No PII redaction and retention policies

## Features

### Core Capabilities

- **Artifact Collection**: Parses JUnit XML files and collects CI logs
- **Failure Fingerprinting**: Creates stable fingerprints for failure clustering
- **Flake Detection**: Analyzes test history to detect flaky tests
- **Policy Engine**: Configurable gating rules via YAML
- **History Tracking**: SQLite database for persistent storage
- **Recommendations**: Targeted rerun plans and quarantine suggestions

### Supported Formats

- pytest JUnit XML
- Maven Surefire/Failsafe
- Gradle JUnit reports
- Jest JUnit output

### Decision Types

- **PASS (0)**: Proceed with release
- **SOFT_BLOCK (10)**: Requires manual override
- **HARD_BLOCK (20)**: Blocks release

## Architecture

RQG follows a modular architecture:

1. **Collection**: Gathers test artifacts and metadata
2. **Storage**: Persists data in SQLite database
3. **Analysis**: Computes flake scores and clusters failures
4. **Policy**: Applies configurable rules to make decisions
5. **Output**: Generates machine-readable and human-readable reports

## Configuration

Configuration is done via `rqg.yml` file:

- History lookback settings
- Input artifact patterns
- Test ID strategy
- Gating rules (hard_block, soft_block)
- Flake detection thresholds
- Recommendation settings

See `docs/policy-reference.md` for complete configuration reference.

## CI/CD Integration

RQG integrates with:

- GitHub Actions
- Jenkins
- GitLab CI

See `ENTEGRASYON.md` for detailed integration examples.

## License

MIT License
