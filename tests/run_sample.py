"""Evaluate a subset of cases in order, with a pause between them.

The free Mistral tier allows 2 chat requests a minute, so a full 24-case run
cannot finish. This runs the same evaluator on a sampled set and reports the
count, so a resubmission after the key is raised is a one-command change.

    python -m tests.run_sample --cases 1,2,3 --delay 35
"""

from __future__ import annotations

import sys
import time

from tests.run_eval import CASES, evaluate


def main() -> int:
    wanted = [int(part) for part in sys.argv[1].split(",")] if len(sys.argv) > 1 else None
    delay = float(sys.argv[3]) if len(sys.argv) > 3 else 35.0
    chosen = [c for c in CASES if wanted is None or c.number in wanted]
    passed = 0
    for case in chosen:
        result = evaluate(case)
        ok = result["passed"]
        passed += ok
        print(f"[{case.number:2d}] {'PASS' if ok else 'FAIL ' + str(result['failures'])[:120]}", flush=True)
        time.sleep(delay)
    print(f"{passed}/{len(chosen)} passed")
    return 0 if passed == len(chosen) else 1


if __name__ == "__main__":
    raise SystemExit(main())
