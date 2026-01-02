import os
import sys
import shutil
from pathlib import Path
from rqg.collect import collect_artifacts
from rqg.analyze import analyze_run

if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def setup_test_environment():
    print("Test ortamı hazırlanıyor...")
    
    os.environ["GITHUB_REPOSITORY"] = "test/repo"
    os.environ["GITHUB_REF_NAME"] = "main"
    os.environ["GITHUB_SHA"] = "test123abc"
    os.environ["GITHUB_WORKFLOW"] = "test-workflow"
    os.environ["GITHUB_RUN_ID"] = "1"
    os.environ["GITHUB_RUN_ATTEMPT"] = "1"
    
    if Path(".rqg").exists():
        shutil.rmtree(".rqg")
    if Path("rqg").exists():
        shutil.rmtree("rqg")
    
    print("[OK] Test ortami hazir\n")

def test_collect():
    print("=" * 50)
    print("TEST 1: Artifact Collection")
    print("=" * 50)
    
    try:
        bundle_path = collect_artifacts(
            config_path="rqg.yml",
            output_path="rqg/bundle.jsonl",
        )
        
        if Path(bundle_path).exists():
            print(f"[OK] Bundle olusturuldu: {bundle_path}")
            print(f"  Dosya boyutu: {Path(bundle_path).stat().st_size} bytes")
            return True
        else:
            print(f"[HATA] Bundle dosyasi bulunamadi: {bundle_path}")
            return False
    except Exception as e:
        print(f"[HATA] Hata: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_analyze():
    print("\n" + "=" * 50)
    print("TEST 2: Analysis ve Decision")
    print("=" * 50)
    
    try:
        decision = analyze_run(
            config_path="rqg.yml",
            bundle_path="rqg/bundle.jsonl",
            output_dir="rqg",
        )
        
        decision_type = decision.get("decision", "UNKNOWN")
        print(f"[OK] Analiz tamamlandi")
        print(f"  Decision: {decision_type}")
        print(f"  Test sayisi: {decision.get('current_run_summary', {}).get('total_tests', 0)}")
        print(f"  Basarisiz: {decision.get('current_run_summary', {}).get('failed', 0)}")
        
        decision_file = Path("rqg/decision.json")
        summary_file = Path("rqg/summary.md")
        
        if decision_file.exists():
            print(f"[OK] Decision record: {decision_file}")
        if summary_file.exists():
            print(f"[OK] Summary: {summary_file}")
            print("\nÖzet içeriği:")
            print("-" * 50)
            with open(summary_file, "r", encoding="utf-8") as f:
                print(f.read()[:500])
            print("-" * 50)
        
        return True
    except Exception as e:
        print(f"✗ Hata: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_with_fixtures():
    print("\n" + "=" * 50)
    print("TEST 3: Fixture Dosyaları ile Test")
    print("=" * 50)
    
    fixtures_dir = Path("fixtures")
    if not fixtures_dir.exists():
        print("[HATA] Fixtures dizini bulunamadi")
        return False
    
    junit_file = fixtures_dir / "sample-junit.xml"
    if not junit_file.exists():
        print("[HATA] JUnit fixture dosyasi bulunamadi")
        return False
    
    shutil.copy(junit_file, "junit.xml")
    print(f"[OK] JUnit dosyasi kopyalandi: {junit_file} -> junit.xml")
    
    log_file = fixtures_dir / "sample-ci.log"
    if log_file.exists():
        shutil.copy(log_file, "ci.log")
        print(f"[OK] Log dosyasi kopyalandi: {log_file} -> ci.log")
    
    try:
        bundle_path = collect_artifacts(
            config_path="rqg.yml",
            output_path="rqg/bundle.jsonl",
        )
        print(f"[OK] Bundle olusturuldu: {bundle_path}")
        
        decision = analyze_run(
            config_path="rqg.yml",
            bundle_path=bundle_path,
            output_dir="rqg",
        )
        
        print(f"[OK] Analiz tamamlandi")
        print(f"  Decision: {decision.get('decision')}")
        
        if Path("rqg/summary.md").exists():
            print("\nDecision Summary:")
            with open("rqg/summary.md", "r", encoding="utf-8") as f:
                print(f.read())
        
        return True
    except Exception as e:
        print(f"✗ Hata: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        for f in ["junit.xml", "ci.log"]:
            if Path(f).exists():
                Path(f).unlink()

def main():
    print("\n" + "=" * 50)
    print("RQG Test Senaryosu")
    print("=" * 50 + "\n")
    
    setup_test_environment()
    
    results = []
    
    results.append(("Collect", test_collect()))
    results.append(("Analyze", test_analyze()))
    results.append(("Fixtures", test_with_fixtures()))
    
    print("\n" + "=" * 50)
    print("Test Sonuçları")
    print("=" * 50)
    
    for name, result in results:
        status = "[OK] BASARILI" if result else "[HATA] BASARISIZ"
        print(f"{name}: {status}")
    
    all_passed = all(r for _, r in results)
    
    if all_passed:
        print("\n[OK] Tum testler basarili!")
        print("\nCikti dosyalarini kontrol edin:")
        print("  - rqg/decision.json")
        print("  - rqg/summary.md")
        print("  - rqg/bundle.jsonl")
        print("  - .rqg/rqg.db")
    else:
        print("\n[HATA] Bazi testler basarisiz oldu")
        sys.exit(1)

if __name__ == "__main__":
    main()

