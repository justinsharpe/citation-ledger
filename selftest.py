#!/usr/bin/env python3
"""Self-test for citation-ledger (stdlib only, cross-platform).

Exercises the four load-bearing behaviours:
  1. ids issued at retrieval time, idempotent + stable for a repeated url
  2. a paraphrased quote is rejected (verbatim gate)
  3. a genuine verbatim quote is accepted
  4. an unsourceable claim is declared with [unverified] and counted as
     provenance
  5. `verify` passes a correct draft
  6. `verify` fails a draft that cites an unknown id
  7. `verify --require-evidence` fails a cited source that carries no quote

Run:  python selftest.py      (exit 0 = all checks passed)
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLI = HERE / "citation_ledger.py"

results: list[tuple[str, bool]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))


def run(ledger: Path, *args: str):
    return subprocess.run(
        [sys.executable, str(CLI), "--ledger", str(ledger), *args],
        capture_output=True, text=True,
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        ledger = work / "ledger.json"

        # -- 1. ids issued at retrieval time, idempotent -------------------
        a = run(ledger, "add", "https://example.org/ice", "--title", "Ice")
        b = run(ledger, "add", "https://example.org/two")
        again = run(ledger, "add", "https://example.org/ice/")  # normalizes to same
        ids_ok = (
            a.returncode == 0
            and a.stdout.strip().startswith("[1]")
            and b.stdout.strip().startswith("[2]")
            and again.stdout.strip().startswith("[1]")  # same url -> same id
        )
        check("issue-ids: url -> [n], repeat url stays [1]", ids_ok,
              f"add={a.stdout.strip()!r} {b.stdout.strip()!r} re-add={again.stdout.strip()!r}")

        # evidence page text (the fetched page)
        page = work / "page.txt"
        page.write_text(
            "Ice is roughly nine percent less dense than liquid water, so it "
            "floats on the surface of a pond.\n",
            encoding="utf-8",
        )

        # -- 2. paraphrased quote is rejected ------------------------------
        para = run(ledger, "note", "1", "--text",
                   "Ice is about 9% less dense than water", "--from", str(page))
        para_ok = para.returncode != 0 and "not found verbatim" in para.stderr
        check("reject-paraphrase: non-verbatim quote refused", para_ok,
              f"rc={para.returncode} stderr={para.stderr.strip()!r}")

        # -- 3. genuine verbatim quote is accepted -------------------------
        good = run(ledger, "note", "1", "--text",
                   "nine percent less dense than liquid water", "--from", str(page))
        good_ok = good.returncode == 0 and "evidence attached" in good.stdout
        check("accept-verbatim: exact quote attached", good_ok,
              f"rc={good.returncode} stdout={good.stdout.strip()!r}")

        # -- 4/5. verify passes; [unverified] is declared provenance -------
        draft = work / "pass.md"
        draft.write_text(
            "Ice floats because it is less dense than liquid water.[1]\n"
            "The refactor likely predates the 2.0 release.[unverified]\n"
            "\n## Sources\n\n"
            "[1] https://example.org/ice\n",
            encoding="utf-8",
        )
        v = run(ledger, "verify", str(draft))
        unsourced_ok = (
            v.returncode == 0
            and "marked [unverified]" in v.stdout
            and "1 with declared provenance" not in v.stdout  # 2/2 coverage, not 1
        )
        # explicit coverage evidence: stats line should read 2/2 (100%)
        cov_ok = "2 with declared provenance (100%)" in v.stdout
        check("flag-unsourceable: [unverified] counted, verify passes",
              unsourced_ok and cov_ok, f"rc={v.returncode} out={v.stdout.strip()!r}")

        # -- 6. verify fails an unknown id ---------------------------------
        bad = work / "bad.md"
        bad.write_text(
            "Water expands when it freezes.[99]\n\n## Sources\n\n[99] https://example.org/nope\n",
            encoding="utf-8",
        )
        vb = run(ledger, "verify", str(bad))
        bad_ok = vb.returncode == 1 and "not in the ledger" in vb.stderr
        check("verify-fail-unknown-id: exit 1", bad_ok,
              f"rc={vb.returncode} stderr={vb.stderr.strip()!r}")

        # -- 7. evidence gate fails an unquoted cited source ---------------
        ev = work / "ev.md"
        ev.write_text(
            "A second claim rests on the second source.[2]\n\n## Sources\n\n[2] https://example.org/two\n",
            encoding="utf-8",
        )
        ve = run(ledger, "verify", str(ev), "--require-evidence")
        ev_ok = ve.returncode == 1 and "no verbatim evidence quote" in ve.stderr
        check("verify-fail-no-evidence: --require-evidence gates delivery", ev_ok,
              f"rc={ve.returncode} stderr={ve.stderr.strip()!r}")

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f"\nSELFTEST: {passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
