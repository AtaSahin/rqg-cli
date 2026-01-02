# RQG Policy Reference

## Config Schema

### version

Policy schema versiyonu. Şu anda `1`.

### mode

Çalışma modu:

- `pr`: PR gate mode (daha hızlı, SOFT_BLOCK daha sık)
- `release`: Release gate mode (daha güvenli, HARD_BLOCK daha sık)

### history

History ayarları:

- `lookback_runs`: Kaç run'a geriye bakılacak (default: 50)
- `lookback_days`: Kaç güne geriye bakılacak (default: 14)

### inputs

Input artifact pattern'leri:

- `junit_globs`: JUnit XML dosya pattern'leri (glob)
- `log_globs`: Log dosya pattern'leri (glob)

### identity

Test ve environment kimlik ayarları:

- `test_id_strategy`: Test ID oluşturma stratejisi
  - `"classname::name"`: `ClassName::test_name`
  - `"package.class::name"`: `package.ClassName::test_name`
- `env_key_fields`: Environment key için kullanılacak field'lar
  - Örnek: `["os", "browser", "device", "runner_pool"]`

### gating

Gating kuralları:

#### hard_block

- `new_failure_min_repro`: Yeni failure'ın minimum repro sayısı
- `critical_paths`: Critical path test pattern'leri (suite/classname içinde aranır)
- `required_suites`: Mutlaka geçmesi gereken suite'ler
- `max_new_failure_clusters`: Maksimum yeni failure cluster sayısı (0 = hiç izin verme)

#### soft_block

- `max_known_flaky_failures`: Maksimum bilinen flaky failure sayısı
- `max_infra_failures`: Maksimum infrastructure failure sayısı

### flake_detection

Flake detection ayarları:

- `quarantine_candidate`:
  - `min_samples`: Minimum sample sayısı
  - `flake_score_threshold`: Quarantine için minimum flake score (0-1)
  - `confidence_threshold`: Quarantine için minimum confidence (0-1)

### recommendations

Öneri ayarları:

- `targeted_rerun`:
  - `enabled`: Targeted rerun önerisi aktif mi?
  - `max_tests`: Maksimum rerun edilecek test sayısı
  - `rerun_attempts`: Rerun attempt sayısı
  - `prefer_runner_pool`: Tercih edilen runner pool

## Decision Logic

### PASS

- Yeni failure cluster yok veya threshold altında
- Critical path'lerde yeni failure yok
- Required suite'ler geçiyor
- Bilinen flaky ve infra failure'lar threshold altında

### SOFT_BLOCK

- Çok fazla bilinen flaky failure
- Çok fazla infrastructure failure
- Override ile geçilebilir (`RQG_OVERRIDE=true`)

### HARD_BLOCK

- Yeni failure cluster threshold'u aşıyor
- Critical path'te yeni failure
- Required suite failure (ve bilinen flaky değil)
- Override ile geçilemez

## Exit Codes

- `0`: PASS
- `10`: SOFT_BLOCK
- `20`: HARD_BLOCK
- `1`: Error
