"""Stage 4 orchestrator - runs Paper 2 evaluation phases in order.

22 (scaffold master table) -> 23 (temporal protocol, all arms x 5 seeds -
the long phase) -> 24 (low-resource guard report) -> 25 (pre-registered
statistics) -> 26 (compute budget).

Run:  python3 paper2/scripts/run_stage4.py [--force]
"""

import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, "..", "..")
STATE_PATH = os.path.join(REPO, "paper2", "results", "pipeline_state.json")
TEMPORAL = os.path.join(REPO, "paper2", "results", "stage4", "temporal_results.json")

PHASES = [
    ("22_scaffold_master", "phase_22_scaffold_master"),
    ("23_temporal_protocol", "phase_23_temporal_protocol"),
    ("24_low_resource", "phase_24_low_resource"),
    ("25_statistics", "phase_25_statistics"),
    ("26_compute_budget", "phase_26_compute_budget"),
]


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return json.load(f)
    return {"stages": {}}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=1)


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


def phase_complete(name):
    if name == "23_temporal_protocol":
        if not os.path.exists(TEMPORAL):
            return False
        with open(TEMPORAL, encoding="utf-8") as fh:
            store = json.load(fh)
        blocks = [v for k, v in store.items() if k.startswith("E5|")]
        return len(blocks) >= 8 and all(
            all(("seeds" in (b.get(a) or {})) or "skipped" in (b.get(a) or {})
                for a in ["shared", "ridge", "crossattn_1d", "pocket3d",
                          "dist_bias", "pocket3d_wrongpocket", "pocket3d_shuffled"])
            for b in blocks)
    return os.path.exists(os.path.join(REPO, "paper2", "results", "stage4", {
        "22_scaffold_master": "scaffold_master.json",
        "24_low_resource": "low_resource.json",
        "25_statistics": "statistics.json",
        "26_compute_budget": "compute_budget.json"}[name]))


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
    print("\nStage 4 complete.")


if __name__ == "__main__":
    main()
