# FILE: backend/scripts/run_all_tests.py
"""
Ekzekuton të gjitha testet script-style në scripts/ dhe raporton pass/fail.
ASCII-only output (Windows console compatible).
"""
import subprocess
import sys
from pathlib import Path
from datetime import datetime


TIMEOUT_SEC = 60


def _find_tests(scripts_dir: Path) -> list[Path]:
    return sorted(
        p for p in scripts_dir.glob("test_*.py")
        if p.is_file()
    )


def main():
    backend = Path(__file__).resolve().parent.parent
    scripts = backend / "scripts"

    tests = _find_tests(scripts)
    if not tests:
        print("Nuk u gjet asnje test_*.py ne scripts/")
        sys.exit(1)

    print("=" * 78)
    print(f"RUN ALL TESTS - {len(tests)} files")
    print(f"Started: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 78)

    passed = []
    failed = []
    timed_out = []

    for test_path in tests:
        name = test_path.name
        print(f"\n>> {name} ... ", end="", flush=True)

        try:
            result = subprocess.run(
                [sys.executable, str(test_path)],
                cwd=str(backend),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=TIMEOUT_SEC,
            )
            if result.returncode == 0:
                print("PASS")
                passed.append(name)
            else:
                print(f"FAIL (exit={result.returncode})")
                stderr_tail = (result.stderr or "")[-500:]
                stdout_tail = (result.stdout or "")[-500:]
                failed.append((name, stderr_tail or stdout_tail))
        except subprocess.TimeoutExpired:
            print(f"TIMEOUT (>{TIMEOUT_SEC}s)")
            timed_out.append(name)
        except Exception as e:
            print(f"ERROR: {e}")
            failed.append((name, str(e)))

    print("\n" + "=" * 78)
    print("PERMBLEDHJE")
    print("=" * 78)
    print(f"  Total:     {len(tests)}")
    print(f"  PASS:      {len(passed)}")
    print(f"  FAIL:      {len(failed)}")
    print(f"  TIMEOUT:   {len(timed_out)}")
    print("=" * 78)

    if failed:
        print("\nDESHTIME:")
        for name, err in failed:
            print(f"\n--- {name} ---")
            print(err)

    if timed_out:
        print("\nTIMEOUT:")
        for name in timed_out:
            print(f"  {name}")

    sys.exit(0 if not failed and not timed_out else 1)


if __name__ == "__main__":
    main()