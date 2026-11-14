"""Paper 2 Stage 4/5 artefact tests - committed frozen files only.

Skips (never fails) when a stage's artefacts are not yet committed, so
CI stays green while long-running stages are in flight.
"""

import json
import os

import pytest

PAPER2 = os.path.join(os.path.dirname(__file__), "..", "paper2")
ST4 = os.path.join(PAPER2, "results", "stage4")
ST5 = os.path.join(PAPER2, "results", "stage5")

ALL_ARMS = ["shared", "ridge", "crossattn_1d", "pocket3d", "dist_bias",
            "pocket3d_wrongpocket", "pocket3d_shuffled"]


def _load(path):
    with open(path) as f:
        return json.load(f)


def _exists(*parts):
    return os.path.exists(os.path.join(*parts))


# ---------- Stage 4 ----------

def test_stage4_scaffold_master_complete():
    if not _exists(ST4, "scaffold_master.json"):
        pytest.skip("stage4 scaffold_master not yet committed")
    d = _load(os.path.join(ST4, "scaffold_master.json"))
    assert len(d.get("receptors", d)) >= 1


def test_stage4_temporal_store_complete():
    if not _exists(ST4, "temporal_results.json"):
        pytest.skip("stage4 temporal store not yet committed")
    d = _load(os.path.join(ST4, "temporal_results.json"))
    blocks = [k for k in d if k.startswith("E5|")]
    assert len(blocks) >= 8, "temporal protocol expected >= 8 receptor blocks"
    for key in blocks:
        blk = d[key]
        for arm in ALL_ARMS:
            rec = blk.get(arm, {})
            ok = "seeds" in rec or "skipped" in rec or "pearson_r" in rec
            assert ok, f"{key}/{arm} incomplete"
            if "seeds" in rec:
                assert len(rec["seeds"]) == 5, f"{key}/{arm} needs 5 seeds"


def test_stage4_statistics_h2_recorded():
    if not _exists(ST4, "statistics.json"):
        pytest.skip("stage4 statistics not yet committed")
    d = _load(os.path.join(ST4, "statistics.json"))
    assert d["h2_verdict"] in ("SUPPORTED",
                               "NOT SUPPORTED - decisive negative result per "
                               "PREREGISTRATION.md decision rule 1")
    prim = d["primary_endpoint"]["result"]["pooled"]
    assert "wilcoxon_p" in prim and "mean_diff" in prim
    assert "bootstrap_ci95" in prim


def test_stage4_low_resource_guard_honest():
    if not _exists(ST4, "low_resource.json"):
        pytest.skip("stage4 low_resource not yet committed")
    d = _load(os.path.join(ST4, "low_resource.json"))
    assert d["rule"]
    for proto in ("scaffold_guard_skips", "temporal_guard_skips"):
        assert proto in d
        for g, arms in d[proto].items():
            assert arms, f"{proto}/{g} empty"
            for arm, why in arms.items():
                assert "MIN_TRAIN" in why or "n_train" in why, f"{proto}/{g}/{arm}"


def test_stage4_compute_budget_measured():
    if not _exists(ST4, "compute_budget.json"):
        pytest.skip("stage4 compute budget not yet committed")
    d = _load(os.path.join(ST4, "compute_budget.json"))
    assert d["total_measured_training_seconds"] > 0
    assert d["total_measured_training_hours"] > 0
    assert d["hardware"]


# ---------- Stage 5 ----------

def test_stage5_af_store_matches_crystal_protocol():
    if not _exists(ST5, "af_results.json"):
        pytest.skip("stage5 AF store not yet committed")
    d = _load(os.path.join(ST5, "af_results.json"))
    blocks = [k for k in d if k.startswith("E3|")]
    assert len(blocks) >= 1
    for key in blocks:
        for arm in ("pocket3d", "pocket3d_wrongpocket"):
            rec = d[key].get(arm, {})
            assert "seeds" in rec or "skipped" in rec, f"{key}/{arm} incomplete"
            if "seeds" in rec:
                assert len(rec["seeds"]) == 5


def test_stage5_af_comparison_has_pocket_meta():
    if not _exists(ST5, "af_comparison.json"):
        pytest.skip("stage5 AF comparison not yet committed")
    d = _load(os.path.join(ST5, "af_comparison.json"))
    assert d["afdb_context_meta"]
    for sym, m in d["afdb_context_meta"].items():
        assert "missing_in_afdb" in m
        assert m["n_pocket_residues"] >= 15, f"{sym} AF pocket too small"


def test_stage5_radius_sweep_both_radii():
    if not _exists(ST5, "radius_sweep.json"):
        pytest.skip("stage5 radius sweep not yet committed")
    d = _load(os.path.join(ST5, "radius_sweep.json"))
    assert set(d["radii"]) == {"5", "8"}
    for radius, block in d["radii"].items():
        keys = [k for k in block["results"] if k.startswith("R%s|" % radius.replace(".", "p"))]
        assert keys, f"radius {radius} has no results"
        for key in keys:
            for arm in ("pocket3d", "pocket3d_wrongpocket"):
                rec = block["results"][key].get(arm, {})
                assert "seeds" in rec or "skipped" in rec, f"{key}/{arm} incomplete"


def test_stage5_mutation_probe_honest():
    if not _exists(ST5, "mutation_probe.json"):
        pytest.skip("stage5 mutation probe not yet committed")
    d = _load(os.path.join(ST5, "mutation_probe.json"))
    assert d["status"] in ("not-run", "run")
    if d["status"] == "not-run":
        assert d["reason"], "not-run needs an explicit reason"
    else:
        assert d["evidence"].get("n_mutation_keyword_rows", 0) > 0


def test_stage5_variance_decomposition():
    if not _exists(ST5, "variance_decomposition.json"):
        pytest.skip("stage5 variance decomposition not yet committed")
    d = _load(os.path.join(ST5, "variance_decomposition.json"))
    e3 = d["e3_scaffold"]
    assert e3["n_cells"] > 0
    shares = [e3["receptor_var_share"], e3["arm_var_share"],
              e3["residual_var_share"]]
    assert all(s is not None for s in shares)
    assert abs(sum(shares) - 1.0) < 0.02, "variance shares must sum to ~1"


def test_stage5_hypothesis_verdicts_formal():
    if not _exists(ST5, "hypothesis_verdicts.json"):
        pytest.skip("stage5 hypothesis verdicts not yet committed")
    d = _load(os.path.join(ST5, "hypothesis_verdicts.json"))
    assert set(d["hypotheses"]) == {"H1", "H2", "H3", "H4"}
    for h, v in d["hypotheses"].items():
        assert isinstance(v["supported"], bool), f"{h} verdict must be boolean"
        assert v["statement"]
    assert d["decision"]
