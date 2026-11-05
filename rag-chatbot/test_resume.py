"""Resume only suites 4 and 5 since 1-3 are saved."""
import json
import time
from pathlib import Path

from test_suites import (
    SUITE_4, SUITE_5_CONVERSATIONS,
    run_suite, run_multiturn_suite, summarize, OUT_DIR,
)


def main():
    t0 = time.time()
    all_summaries = []

    # Load existing suite 1/2/3 summaries
    for name in ("suite1_services", "suite2_team", "suite3_projects"):
        path = OUT_DIR / f"{name}.json"
        if path.exists():
            results = json.loads(path.read_text(encoding="utf-8"))
            all_summaries.append(summarize(name, results))

    # Run suite 4
    print(f"\n========== suite4_adversarial ({len(SUITE_4)} queries) ==========", flush=True)
    r4 = run_suite("suite4_adversarial", SUITE_4, reuse_session=False)
    (OUT_DIR / "suite4_adversarial.json").write_text(json.dumps(r4, indent=2), encoding="utf-8")
    s4 = summarize("suite4_adversarial", r4)
    all_summaries.append(s4)
    print(f"[suite4_adversarial] SUMMARY: {s4['passed']}/{s4['total']} passed ({s4['pass_rate']}%), avg {s4['avg_latency_s']}s, max {s4['max_latency_s']}s", flush=True)

    # Run suite 5
    print(f"\n========== suite5_multiturn ({sum(len(c) for c in SUITE_5_CONVERSATIONS)} turns) ==========", flush=True)
    r5 = run_multiturn_suite("suite5_multiturn", SUITE_5_CONVERSATIONS)
    (OUT_DIR / "suite5_multiturn.json").write_text(json.dumps(r5, indent=2), encoding="utf-8")
    s5 = summarize("suite5_multiturn", r5)
    all_summaries.append(s5)
    print(f"[suite5_multiturn] SUMMARY: {s5['passed']}/{s5['total']} passed ({s5['pass_rate']}%), avg {s5['avg_latency_s']}s, max {s5['max_latency_s']}s", flush=True)

    elapsed = round(time.time() - t0, 1)
    master = {"elapsed_seconds": elapsed, "summaries": all_summaries}
    (OUT_DIR / "master_summary.json").write_text(json.dumps(master, indent=2), encoding="utf-8")
    print(f"\n=== DONE in {elapsed}s ===", flush=True)
    for s in all_summaries:
        print(f"{s['suite']}: {s['passed']}/{s['total']} ({s['pass_rate']}%) avg={s['avg_latency_s']}s", flush=True)


if __name__ == "__main__":
    main()
