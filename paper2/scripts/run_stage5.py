"""Stage 5 orchestrator - robustness phases in order.

27 (crystal-vs-AF, heavy) -> 28 (radius sweep, heavy) -> 29 (mutation
probe, time-boxed) -> 30 (variance decomposition) -> 31 (hypothesis
verdicts). Heavy phases 27/28 are intended to run in the background via
nohup; the orchestrator resumes cleanly from the pipeline state.

Run:  python3 paper2/scripts/run_stage5.py [--force]
"""

import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, "..", "..")
STATE_PATH = os.path.join(REPO, "paper2", "results", "pipeline_state.json")
ST5 = os.path.join(REPO, "paper2", "results", "stage5")

PHASES = [
    ("27_crystal_vs_af", "phase_27_crystal_vs_af"),
    ("28_radius_sweep", "phase_28_radius_sweep"),
    ("29_mutation_probe", "phase_29_mutation_probe"),
    ("30_variance_decomposition", "phase_30_variance_decomposition"),
    ("31_negative_result_guard", "phase_31_negative_result_guard"),
]

ARTIFACTS = {
    "27_crystal_vs_af": ["af_results.json", "af_comparison.json"],
    "28_radius_sweep": ["radius_sweep.json", "radius_sweep_5.json",
                        "radius_sweep_8.json"],
    "29_mutation_probe": ["mutation_probe.json"],
    "30_variance_decomposition": ["variance_decomposition.json"],
    "31_negative_result_guard": ["hypothesis_verdicts.json",
                                 "hypothesis_verdicts.md"],
}


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return json.load(f)
    return {"stages": {}}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=1)


def phase_complete(name):
    return all(os.path.exists(os.path.join(ST5, a))
               for a in ARTIFACTS[name])


def run_script(name):
    script = os.path.join(HERE, f"{name}.py")
    print(f"\n=== running {name}.py ===", flush=True)
    t0 = time.time()
    proc = subprocess.run([sys.executable, script], cwd=REPO)
    dt = time.time() - t0
    if proc.returncode != 0:
        raise SystemExit(f"{name}.py failed (exit {proc.returncode}) after {dt:.1f}s")
    print(f"=== {name}.py OK ({dt:.1f}s) ===", flush=True)
    return dt


def main():
    force = "--force" in sys.argv
    state = load_state()
    stages = state.setdefault("stages", {})
    for idx, (name, key) in enumerate(PHASES):
        if (not force and stages.get(key, {}).get("status") == "done"
                and phase_complete(name)):
            print(f"[skip] {key} (done at {stages[key].get('finished_utc')})")
            continue
        dt = run_script(name)
        stages[key] = {
            "status": "done",
            "script": f"{name}.py",
            "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "runtime_s": round(dt, 1),
        }
        for _, later_key in PHASES[idx + 1:]:
            if stages.get(later_key, {}).get("status") == "done":
                print(f"[invalidate] {later_key} (upstream {key} reran)")
                stages[later_key]["status"] = "stale"
        save_state(state)
    print("\nStage 5 complete.")


if __name__ == "__main__":
    main()
