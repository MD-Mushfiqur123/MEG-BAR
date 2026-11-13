"""One-off maintenance: remove seed records measured at D_MODEL=64.

Why this exists
---------------
During a mid-run configuration change the evaluator was launched with D_MODEL=64
to reduce CPU memory pressure. The 64-wide cross-attention arms are *not*
comparable with the 128-wide arms in the same reported table: a reviewer would
correctly object that the losing architecture was silently narrowed before being
compared against the winner, and the artefact would then contain a mean_r
averaged across two different models.

Rather than relabelling those records (which would hide the change) or averaging
across widths (which would be wrong), the 64-wide records are deleted by
(block, arch, seed) - every removal below was confirmed against the run log of
the session that produced it, `data/real/robust_run2.log`. The evaluator is then
re-run at the single width D_MODEL=128 that every other arm uses, and each seed
record now carries its own `config` field so this can never happen silently
again.

Removed:
    E4|DRD2   crossattn             seeds 3, 4        (seeds 0-2 are 128-wide, kept)
    E4|DRD2   crossattn_wrongpocket seeds 0-4        (all 64-wide, deleted)
    E4|GABRA1 crossattn             seed  0          (64-wide, deleted)

Kept, because the shared MLP does not depend on D_MODEL at all:
    E4|GABRA1 shared                seeds 0-4

Usage:  python scripts/real/_drop_mixed_width_seeds.py
Backup: data/real/robust_results.json.pred64.bak
"""
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.abspath(os.path.join(HERE, '..', '..', 'data', 'real', 'robust_results.json'))

BAD = {
    "E4|DRD2": [("crossattn", [3, 4]), ("crossattn_wrongpocket", [0, 1, 2, 3, 4])],
    "E4|GABRA1": [("crossattn", [0])],
}
AGGREGATES = ("mean_r", "sd_r", "bootstrap_ci")


def main():
    with open(P, encoding="utf-8") as fh:
        d = json.load(fh)

    report = []
    for blk, entries in BAD.items():
        if blk not in d:
            report.append("%-12s ABSENT (nothing to do)" % blk)
            continue
        for arch, seeds in entries:
            rec = d[blk].get(arch)
            if not isinstance(rec, dict) or "seeds" not in rec:
                report.append("%-12s %-24s no seed list" % (blk, arch))
                continue
            before = [s["seed"] for s in rec["seeds"]]
            rec["seeds"] = [s for s in rec["seeds"] if s["seed"] not in seeds]
            after = [s["seed"] for s in rec["seeds"]]
            report.append("%-12s %-24s %s -> %s" % (blk, arch, before, after))
            # Aggregates computed over a width-mixed seed set are void; the next
            # run recomputes them from a uniform set and rewrites the artefact.
            for k in AGGREGATES:
                rec.pop(k, None)
            if not rec["seeds"]:
                d[blk].pop(arch, None)
                report.append("%-12s %-24s removed entirely (no uniform seeds left)"
                              % (blk, arch))
        d[blk].pop("wilcoxon_crossattn_vs_shared", None)

    backup = P + ".pred64.bak"
    shutil.copy2(P, backup)
    with open(P, "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=2)

    print("original preserved as:", os.path.basename(backup))
    print()
    print("\n".join(report))
    print("\nseed coverage now in the artefact:")
    for k in sorted(x for x in d if "|" in x):
        parts = []
        for a in ("ridge", "shared", "crossattn", "crossattn_wrongpocket"):
            r = d[k].get(a)
            if not r:
                parts.append("%s=-" % a)
            elif "skipped" in r:
                parts.append("%s=skip" % a)
            elif "seeds" in r:
                parts.append("%s=%d" % (a, len(r["seeds"])))
            else:
                parts.append("%s=1fit" % a)
        print("  %-12s %s" % (k, "  ".join(parts)))


if __name__ == "__main__":
    main()
