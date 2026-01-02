# RQG Entegrasyon Kılavuzu

## 1. Kendi Test Sonuçlarınızı Kullanma

### Adım 1: JUnit XML Formatında Test Sonuçları Üretin

RQG, JUnit XML formatını kullanır. Test framework'ünüze göre:

#### Python (pytest)

```bash
pytest --junitxml=junit.xml tests/
```

#### Java (Maven)

```bash
mvn test
# Sonuçlar: target/surefire-reports/TEST-*.xml
```

#### Java (Gradle)

```bash
./gradlew test
# Sonuçlar: build/test-results/test/TEST-*.xml
```

#### JavaScript/TypeScript (Jest)

```bash
npm install --save-dev jest-junit
# jest.config.js içine:
# reporters: [['jest-junit', { outputFile: 'junit.xml' }]]
npm test
```

### Adım 2: RQG Config Dosyasını Düzenleyin

`rqg.yml` dosyasını kendi projenize göre ayarlayın:

```yaml
version: 1
mode: pr # veya "release"

inputs:
  junit_globs:
    - "**/junit.xml" # pytest için
    - "**/TEST-*.xml" # Maven için
    - "**/test-results/**/*.xml" # Gradle için
    - "junit.xml" # Jest için
  log_globs:
    - "**/ci.log"
    - "**/test-output.log"

identity:
  test_id_strategy: "classname::name" # Python için
  # veya "package.class::name"         # Java için

gating:
  hard_block:
    new_failure_min_repro: 2
    critical_paths:
      - "payments" # Kendi kritik path'leriniz
      - "auth"
      - "checkout"
    required_suites:
      - "smoke" # Mutlaka geçmesi gereken suite'ler
    max_new_failure_clusters: 0

  soft_block:
    max_known_flaky_failures: 5
    max_infra_failures: 10
```

### Adım 3: RQG'yi Çalıştırın

```bash
# 1. Artifact toplama
rqg collect

# 2. Analiz
rqg analyze

# 3. Sonuçları kontrol et
cat rqg/summary.md
```

## 2. CI/CD Pipeline Entegrasyonu

### GitHub Actions

`.github/workflows/test.yml` dosyası oluşturun:

```yaml
name: Test with RQG

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.8"

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest

      - name: Run tests
        run: |
          pytest --junitxml=junit.xml tests/ || true

      - name: Save test logs
        if: always()
        run: |
          echo "Test execution completed" > ci.log
          pytest --junitxml=junit.xml tests/ --tb=short >> ci.log 2>&1 || true

      - name: Install RQG
        run: |
          pip install -e .

      - name: RQG Collect
        run: |
          rqg collect \
            --repo ${{ github.repository }} \
            --branch ${{ github.ref_name }} \
            --commit ${{ github.sha }} \
            --workflow ${{ github.workflow }} \
            --build-number ${{ github.run_number }} \
            --attempt ${{ github.run_attempt }}

      - name: RQG Analyze
        id: rqg
        continue-on-error: true
        run: |
          rqg analyze

      - name: Upload RQG artifacts
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: rqg-artifacts
          path: |
            rqg/decision.json
            rqg/summary.md
            rqg/bundle.jsonl

      - name: Check RQG decision
        if: steps.rqg.outcome == 'failure'
        run: |
          if [ -f rqg/decision.json ]; then
            cat rqg/summary.md
            exit 1
          fi

      - name: Gate deployment
        if: steps.rqg.outcome == 'failure'
        run: |
          DECISION=$(python -c "import json; print(json.load(open('rqg/decision.json'))['decision'])")
          if [ "$DECISION" = "HARD_BLOCK" ]; then
            echo "::error::RQG HARD_BLOCK: Release blocked"
            exit 1
          elif [ "$DECISION" = "SOFT_BLOCK" ]; then
            if [ "${{ env.RQG_OVERRIDE }}" != "true" ]; then
              echo "::warning::RQG SOFT_BLOCK: Override required"
              exit 1
            fi
          fi
```

### Jenkins

`Jenkinsfile` dosyanıza ekleyin:

```groovy
pipeline {
    agent any

    environment {
        RQG_DB_PATH = "${WORKSPACE}/.rqg/rqg.db"
    }

    stages {
        stage('Test') {
            steps {
                sh '''
                    pip install -r requirements.txt
                    pytest --junitxml=junit.xml tests/ || true
                '''
            }
        }

        stage('RQG Collect') {
            steps {
                sh '''
                    pip install -e .
                    rqg collect \
                        --repo ${GIT_REPO:-unknown} \
                        --branch ${BRANCH_NAME} \
                        --commit ${GIT_COMMIT} \
                        --workflow ${JOB_NAME} \
                        --build-number ${BUILD_NUMBER}
                '''
            }
        }

        stage('RQG Analyze') {
            steps {
                script {
                    def rqgExitCode = sh(
                        script: 'rqg analyze',
                        returnStatus: true
                    )

                    if (rqgExitCode == 20) {
                        error("RQG HARD_BLOCK: Release blocked")
                    } else if (rqgExitCode == 10) {
                        if (env.RQG_OVERRIDE != "true") {
                            error("RQG SOFT_BLOCK: Override required")
                        }
                    }
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'rqg/**', fingerprint: true
        }
    }
}
```

### GitLab CI

`.gitlab-ci.yml` dosyasına ekleyin:

```yaml
test:
  stage: test
  script:
    - pip install -r requirements.txt
    - pytest --junitxml=junit.xml tests/ || true
    - pip install -e .
    - rqg collect --repo $CI_PROJECT_PATH --branch $CI_COMMIT_REF_NAME --commit $CI_COMMIT_SHA
    - rqg analyze
  artifacts:
    paths:
      - rqg/
    reports:
      junit: junit.xml
  allow_failure: false
```

## 3. Gerçek Kullanım Senaryoları

### Senaryo 1: Yeni Bir Test Ekleme

1. Test yazın ve çalıştırın:

```bash
pytest tests/test_new_feature.py --junitxml=junit.xml
```

2. RQG ile analiz edin:

```bash
rqg collect
rqg analyze
```

3. Sonuçları kontrol edin:

```bash
cat rqg/summary.md
```

### Senaryo 2: Flaky Test Tespiti

1. Birkaç kez test çalıştırın:

```bash
for i in {1..5}; do
  pytest --junitxml=junit-$i.xml tests/
  rqg collect --output rqg/bundle-$i.jsonl
  rqg analyze --bundle rqg/bundle-$i.jsonl
done
```

2. Flaky testleri görün:

```bash
cat rqg/summary.md | grep -A 5 "Known Flaky"
```

### Senaryo 3: Release Öncesi Kontrol

1. Release branch'inde test çalıştırın:

```bash
pytest --junitxml=junit.xml tests/
rqg collect --branch release/v1.0
rqg analyze
```

2. Decision'ı kontrol edin:

```bash
DECISION=$(python -c "import json; print(json.load(open('rqg/decision.json'))['decision'])")
echo "Decision: $DECISION"

if [ "$DECISION" = "HARD_BLOCK" ]; then
  echo "Release blocked!"
  exit 1
fi
```

## 4. Custom Policy Ayarları

### Kritik Path'leri Tanımlama

`rqg.yml` dosyasında:

```yaml
gating:
  hard_block:
    critical_paths:
      - "payments" # Test classname veya suite adında "payments" geçenler
      - "auth"
      - "checkout"
      - "database" # Database testleri
```

### Flake Threshold'ları Ayarlama

```yaml
flake_detection:
  quarantine_candidate:
    min_samples: 20 # Minimum 20 run gerekli
    flake_score_threshold: 0.75 # %75 flake score
    confidence_threshold: 0.6 # %60 confidence
```

### Targeted Rerun Ayarları

```yaml
recommendations:
  targeted_rerun:
    enabled: true
    max_tests: 30 # Maksimum 30 test rerun
    rerun_attempts: 1
    prefer_runner_pool: "stable" # Stable runner pool kullan
```

## 5. Sonuçları Okuma ve Kullanma

### Decision JSON'dan Bilgi Çıkarma

```python
import json

with open('rqg/decision.json') as f:
    decision = json.load(f)

print(f"Decision: {decision['decision']}")
print(f"Total Tests: {decision['current_run_summary']['total_tests']}")
print(f"Failed: {decision['current_run_summary']['failed']}")

for cluster in decision['new_failure_clusters']:
    print(f"New failure: {cluster['test_id']}")
```

### Summary Markdown'u Görüntüleme

```bash
# Terminal'de görüntüle
cat rqg/summary.md

# Veya GitHub'da PR comment olarak ekle
gh pr comment --body-file rqg/summary.md
```

## 6. Troubleshooting

### Problem: JUnit XML bulunamıyor

**Çözüm:** `rqg.yml` dosyasındaki `junit_globs` pattern'lerini kontrol edin:

```yaml
inputs:
  junit_globs:
    - "**/junit*.xml" # Tüm alt dizinlerde
    - "junit.xml" # Root dizinde
```

### Problem: Test ID'ler yanlış formatlanmış

**Çözüm:** `test_id_strategy` ayarını değiştirin:

```yaml
identity:
  test_id_strategy: "classname::name"  # Python için
  # veya
  test_id_strategy: "package.class::name"  # Java için
```

### Problem: History database boş

**Çözüm:** İlk birkaç run'da history olmayacak. Birkaç kez çalıştırın:

```bash
# 5 kez çalıştır
for i in {1..5}; do
  pytest --junitxml=junit.xml
  rqg collect
  rqg analyze
done
```

## 7. İleri Seviye Kullanım

### Custom Environment Key

Environment variable'ları kullanarak test ortamını ayırt edin:

```bash
export RUNNER_POOL="stable"
export BROWSER="chrome"
export DEVICE="desktop"

rqg collect
rqg analyze
```

### Multiple Test Suites

Farklı suite'ler için farklı policy'ler:

```yaml
gating:
  hard_block:
    required_suites:
      - "smoke" # Smoke testleri mutlaka geçmeli
      - "integration" # Integration testleri mutlaka geçmeli
```

### Custom Recommendations

RQG'nin önerilerini kullanarak otomatik rerun:

```python
import json

with open('rqg/decision.json') as f:
    decision = json.load(f)

rerun_plan = decision['recommendations'].get('targeted_rerun')
if rerun_plan:
    tests = rerun_plan['tests']
    # Bu testleri tekrar çalıştır
    pytest tests/ --select-tests " ".join(tests)
```

## 8. Örnek Workflow

Tam bir örnek workflow:

```bash
#!/bin/bash

# 1. Testleri çalıştır
echo "Running tests..."
pytest --junitxml=junit.xml tests/

# 2. Log'ları kaydet
pytest --junitxml=junit.xml tests/ --tb=short > ci.log 2>&1

# 3. RQG collect
echo "Collecting artifacts..."
rqg collect \
  --repo "myorg/myrepo" \
  --branch "$(git branch --show-current)" \
  --commit "$(git rev-parse HEAD)"

# 4. RQG analyze
echo "Analyzing..."
rqg analyze
EXIT_CODE=$?

# 5. Sonuçları göster
cat rqg/summary.md

# 6. Decision'a göre işlem yap
if [ $EXIT_CODE -eq 20 ]; then
  echo "HARD_BLOCK: Release blocked!"
  exit 1
elif [ $EXIT_CODE -eq 10 ]; then
  echo "SOFT_BLOCK: Manual review required"
  if [ "$OVERRIDE" != "true" ]; then
    exit 1
  fi
fi

echo "Tests passed!"
```

Bu kılavuzu kullanarak RQG'yi kendi projenize entegre edebilirsiniz!
