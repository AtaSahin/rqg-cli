# RQG Kullanım Örneği (PowerShell)

Write-Host "=== RQG Kullanım Örneği ===" -ForegroundColor Cyan
Write-Host ""

# 1. Testleri çalıştır (örnek)
Write-Host "1. Testler çalıştırılıyor..." -ForegroundColor Yellow
# pytest --junitxml=junit.xml tests/
# veya
# mvn test
# veya
# npm test

# 2. RQG Collect
Write-Host "2. RQG artifact toplama..." -ForegroundColor Yellow
$branch = git branch --show-current 2>$null
if (-not $branch) { $branch = "main" }

$commit = git rev-parse HEAD 2>$null
if (-not $commit) { $commit = "unknown" }

rqg collect `
  --repo "myorg/myrepo" `
  --branch $branch `
  --commit $commit `
  --workflow "local-test"

# 3. RQG Analyze
Write-Host "3. RQG analiz..." -ForegroundColor Yellow
rqg analyze
$exitCode = $LASTEXITCODE

# 4. Sonuçları göster
Write-Host ""
Write-Host "=== RQG Sonuçları ===" -ForegroundColor Cyan
Get-Content rqg\summary.md

# 5. Decision kontrolü
Write-Host ""
Write-Host "=== Decision Kontrolü ===" -ForegroundColor Cyan
if ($exitCode -eq 0) {
    Write-Host "✓ PASS - Devam edebilirsiniz" -ForegroundColor Green
} elseif ($exitCode -eq 10) {
    Write-Host "⚠ SOFT_BLOCK - Manuel onay gerekli" -ForegroundColor Yellow
    Write-Host "   Override için: `$env:RQG_OVERRIDE='true'" -ForegroundColor Yellow
} elseif ($exitCode -eq 20) {
    Write-Host "✗ HARD_BLOCK - Release engellendi" -ForegroundColor Red
    Write-Host "   Yeni failure'lar tespit edildi" -ForegroundColor Red
}

exit $exitCode

