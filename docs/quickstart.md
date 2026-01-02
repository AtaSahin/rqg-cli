# RQG Hızlı Başlangıç

## Kurulum

```bash
pip install -e .
```

veya

```bash
pipx install .
```

## Temel Kullanım

### 1. Config Dosyası Oluştur

Repo root'unda `rqg.yml` dosyası oluşturun:

```yaml
version: 1
mode: pr

history:
  lookback_runs: 50
  lookback_days: 14

inputs:
  junit_globs:
    - "**/junit*.xml"
    - "**/TEST-*.xml"
  log_globs:
    - "**/ci.log"

identity:
  test_id_strategy: "classname::name"
  env_key_fields:
    - os
    - browser
    - device
    - runner_pool

gating:
  hard_block:
    new_failure_min_repro: 2
    critical_paths:
      - "payments"
      - "auth"
    required_suites:
      - "smoke"
    max_new_failure_clusters: 0

  soft_block:
    max_known_flaky_failures: 5
    max_infra_failures: 10

flake_detection:
  quarantine_candidate:
    min_samples: 20
    flake_score_threshold: 0.75
    confidence_threshold: 0.6

recommendations:
  targeted_rerun:
    enabled: true
    max_tests: 30
    rerun_attempts: 1
    prefer_runner_pool: "stable"
```

### 2. Testlerden Sonra Collect

```bash
rqg collect
```

Bu komut:

- JUnit XML dosyalarını bulur ve parse eder
- CI log dosyalarını toplar
- Run metadata'sını env var'lardan toplar
- `rqg/bundle.jsonl` dosyası oluşturur

### 3. Analiz ve Decision

```bash
rqg analyze
```

Bu komut:

- Bundle'ı okur
- History ile karşılaştırır
- Flake score'ları hesaplar
- Policy'ye göre decision üretir
- `rqg/decision.json` ve `rqg/summary.md` oluşturur
- Exit code döner:
  - `0` = PASS
  - `10` = SOFT_BLOCK
  - `20` = HARD_BLOCK

### 4. CI Pipeline'da Kullanım

#### GitHub Actions

```yaml
- name: RQG Collect
  run: rqg collect

- name: RQG Analyze
  run: rqg analyze
```

#### Jenkins

```groovy
sh 'rqg collect'
sh 'rqg analyze'
```

Exit code'a göre pipeline'ı gate edin.

## Test Açıklama

Bir test hakkında detaylı bilgi almak için:

```bash
rqg explain tests.test_auth::test_login_failure
```

## Çıktı Dosyaları

- `rqg/bundle.jsonl`: Toplanan artifact'lar (JSON format)
- `rqg/decision.json`: Machine-readable decision record
- `rqg/summary.md`: Human-readable özet
- `.rqg/rqg.db`: SQLite history database
