"""Stage 2 orchestrator - runs Paper 2 3D feature engineering phases in order.

Executes: 11 (distance matrices) -> 12 (contact maps) -> 13 (pocket graphs)
-> 14 (geometric descriptors) -> 15 (feature validation) -> 10 (manifest,
re-run so the frozen manifest covers the new feature artefacts). Checkpoint
state is stored in paper2/results/pipeline_state.json; completed phases are
skipped on rerun unless --force, and rerunning a phase invalidates later ones.

Run:  python3 paper2/scripts/run_stage2.py [--force]
"""

import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, "..", "..")
STATE_PATH = os.path.join(REPO, "paper2", "results", "pipeline_state.json")

PHASES = [
    ("11_distance_matrices", "phase_11_distance_matrices"),
    ("12_contact_maps", "phase_12_contact_maps"),
    ("13_pocket_graphs", "phase_13_pocket_graphs"),
    ("14_geometric_descriptors", "phase_14_geometric_descriptors"),
    ("15_feature_validation", "phase_15_feature_validation"),
    ("10_manifest", "phase_10_manifest"),
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


def main():
    force = "--force" in sys.argv
    state = load_state()
    stages = state.setdefault("stages", {})
    for idx, (name, key) in enumerate(PHASES):
        if stages.get(key, {}).get("status") == "done" and not force:
            print(f"[skip] {key} (done at {stages[key].get('finished_utc')}; "
                  f"use --force to rerun)")
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
    print("\nStage 2 complete. State:", STATE_PATH)


if __name__ == "__main__":
    main()
