# RQG Architecture

## Genel Bakış

RQG, CI pipeline'larında test sonuçlarını analiz eden, flaky testleri tespit eden ve release kararları için gating mekanizması sağlayan bir sistemdir.

## Bileşenler

### 1. Artifact Collection (`rqg collect`)

- JUnit XML dosyalarını bulur ve parse eder
- CI log dosyalarını toplar
- Run metadata'sını environment variable'lardan toplar
- Bundle (JSON) dosyası oluşturur

### 2. Storage (SQLite)

- Run'ları ve test sonuçlarını saklar
- Failure cluster'ları track eder
- History için query'ler sağlar

### 3. Fingerprinting

- Failure text'lerini sanitize eder (timestamp, UUID, port, duration temizleme)
- Stable fingerprint'ler üretir (SHA256)
- Aynı underlying failure'ı farklı run'larda eşleştirir

### 4. Flake Scoring

- Test bazında flake score hesaplar (0-1)
- Confidence score hesaplar (0-1)
- Evidence toplar:
  - Fail rate
  - Intermittency (consecutive outcome changes)
  - Retry pass rate
  - Same commit inconsistency

### 5. Policy Engine

- Policy config'i okur (`rqg.yml`)
- Current run'ı history ile karşılaştırır
- Decision üretir: PASS, SOFT_BLOCK, HARD_BLOCK
- Decision reason'ları toplar

### 6. Recommendations

- Targeted rerun plan önerir
- Quarantine candidate'ları listeler
- Infrastructure hotspot'ları tespit eder

### 7. Output

- `decision.json`: Machine-readable decision record
- `summary.md`: Human-readable özet
- Exit code: CI pipeline gating için

## Data Flow

```
CI Pipeline
    ↓
Test Execution → JUnit XML + Logs
    ↓
rqg collect → Bundle (JSON)
    ↓
rqg analyze → SQLite Storage
    ↓
History Query → Flake Scoring → Policy Engine
    ↓
Decision Record + Summary
    ↓
Exit Code → CI Gate
```

## Fingerprinting Algorithm

1. Failure text'i sanitize et:

   - Timestamp'leri kaldır
   - UUID/hash'leri kaldır
   - Port numaralarını kaldır
   - Duration'ları kaldır
   - Whitespace'i normalize et

2. Top stack frames'i çıkar (max 10)

3. Exception type'ı çıkar

4. SHA256 hash hesapla: `version|sanitized_text|frames|exception_type`

## Flake Score Calculation

Başlangıç: `0.0`

Artırıcılar:

- Intermittency > 0: `+0.1 * intermittency` (max 0.4)
- Retry pass rate > 0.5: `+0.3` (max)
- Same commit inconsistency: `+0.3`
- Fail rate 0.3-0.9 arası: `+0.2` (max)

Confidence:

- Sample sayısına göre: `min(1.0, samples / 20.0)`
- Pattern consistency'ye göre ayarlanır

## Storage Schema

### runs

- run_id, repo, branch, commit_sha
- CI metadata (provider, workflow, job, build_number, attempt)
- Timestamps, environment (os, browser, device, runner_pool)

### test_results

- run_id, test_id, suite, classname, name
- outcome, duration_ms, failure_text, fingerprint

### failure_clusters

- fingerprint, first_seen_at, last_seen_at
- example_failure_text, infra_hints, test_ids, occurrence_count

## CI Integration

### GitHub Actions

- Environment variables: `GITHUB_SHA`, `GITHUB_REF`, `GITHUB_RUN_ID`, etc.
- Artifact upload: `rqg/` dizini
- Exit code check: `$?` ile gate

### Jenkins

- Environment variables: `GIT_COMMIT`, `BRANCH_NAME`, `BUILD_NUMBER`, etc.
- Archive artifacts: `rqg/**`
- Exit code check: `sh returnStatus: true`
