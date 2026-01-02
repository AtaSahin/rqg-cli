#!/bin/bash

echo "=== RQG Kullanım Örneği ==="
echo ""

# 1. Testleri çalıştır (örnek)
echo "1. Testler çalıştırılıyor..."
# pytest --junitxml=junit.xml tests/ || true
# veya
# mvn test
# veya
# npm test

# 2. RQG Collect
echo "2. RQG artifact toplama..."
rqg collect \
  --repo "myorg/myrepo" \
  --branch "$(git branch --show-current 2>/dev/null || echo 'main')" \
  --commit "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')" \
  --workflow "local-test"

# 3. RQG Analyze
echo "3. RQG analiz..."
rqg analyze
EXIT_CODE=$?

# 4. Sonuçları göster
echo ""
echo "=== RQG Sonuçları ==="
cat rqg/summary.md

# 5. Decision kontrolü
echo ""
echo "=== Decision Kontrolü ==="
if [ $EXIT_CODE -eq 0 ]; then
  echo "✓ PASS - Devam edebilirsiniz"
elif [ $EXIT_CODE -eq 10 ]; then
  echo "⚠ SOFT_BLOCK - Manuel onay gerekli"
  echo "   Override için: export RQG_OVERRIDE=true"
elif [ $EXIT_CODE -eq 20 ]; then
  echo "✗ HARD_BLOCK - Release engellendi"
  echo "   Yeni failure'lar tespit edildi"
fi

exit $EXIT_CODE

