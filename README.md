# Release Quality Gate (RQG)

**Version:** 0.1.0 (MVP/Beta)  
**Status:** Beta - Core features complete, improvements in progress

RQG, CI pipeline'larında test sonuçlarını analiz eden, flaky testleri tespit eden ve release kararları için gating mekanizması sağlayan bir sistemdir.

## Kurulum

```bash
pip install -e .
```

veya

```bash
pipx install .
```

## Hızlı Başlangıç

1. Repo root'unda `rqg.yml` config dosyası oluşturun
2. CI pipeline'ınızda testlerden sonra:
   ```bash
   rqg collect
   rqg analyze
   ```
3. `rqg/decision.json` ve `rqg/summary.md` dosyalarını kontrol edin
4. Exit code'a göre pipeline'ı gate edin (0=PASS, 10=SOFT_BLOCK, 20=HARD_BLOCK)

## CLI Komutları

- `rqg collect` - Artifact'ları toplar ve bundle oluşturur
- `rqg analyze` - History ile analiz yapar ve decision üretir
- `rqg explain <test_id>` - Test veya cluster için açıklama gösterir
- `rqg upload` - Bundle'ı merkezi servise yükler (opsiyonel)

## Hızlı Test

```bash
# Paketi kurun
pip install -e .

# Test scriptini çalıştırın
python test_rqg.py
```

## Dokümantasyon

- **README_EN.md** - English README
- **KULLANIM.md** - Detaylı kullanım ve test kılavuzu
- **ENTEGRASYON.md** - CI/CD entegrasyon rehberi
- **ROADMAP.md** - Geliştirme yol haritası
- **docs/quickstart.md** - Hızlı başlangıç
- **docs/policy-reference.md** - Policy config referansı
- **docs/architecture.md** - Mimari dokümantasyon

## Durum ve Sınırlamalar

**Mevcut Versiyon:** 0.1.0 (MVP/Beta)

Bu versiyon core özellikleri içerir ancak production kullanımı için bazı iyileştirmeler gereklidir:

- CI cache/restore mekanizması eksik (her run'da history sıfırlanıyor)
- Shard/parallel execution desteği sınırlı
- Override yetki seviyeleri yok
- PII redaction ve retention policy'leri yok
