"""Paper 2 artefact tests - no network required, checks committed frozen files."""

import json
import os
import sys

import pytest

PAPER2 = os.path.join(os.path.dirname(__file__), "..", "paper2")


def _load(rel):
    with open(os.path.join(PAPER2, rel)) as f:
        return json.load(f)


def test_phase5_pdb_selection_has_all_11_receptors():
    d = _load(os.path.join("data", "structures", "pdb_selection.json"))
    assert len(d["receptors"]) == 11
    for sym, v in d["receptors"].items():
        assert v["primary"], f"{sym} has no primary structure"
        assert v["primary"]["ligands"], f"{sym} primary structure is not ligand-bound"
        assert v["primary"]["resolution"] <= 3.5, f"{sym} resolution too low"


def test_phase5_anchor_gpcrs_present():
    d = _load(os.path.join("data", "structures", "pdb_selection.json"))
    for sym in ["DRD2", "DRD3", "HTR1A", "HTR2A", "CHRM1", "ADRA2A", "ADRB2", "HRH1"]:
        assert sym in d["receptors"], f"{sym} missing from selection"


def test_phase5_known_classic_structures():
    d = _load(os.path.join("data", "structures", "pdb_selection.json"))
    assert d["receptors"]["ADRB2"]["primary"]["pdb_id"] == "2RH1"
    assert d["receptors"]["SERT"]["primary"]["pdb_id"] == "5I6X"


def test_preregistration_exists_and_frozen():
    src = open(os.path.join(PAPER2, "PREREGISTRATION.md")).read()
    for token in ["H1", "H2", "H3", "H4", "Holm", "Wilcoxon", "P14416", "Q01959"]:
        assert token in src


def test_environment_lock_exists():
    src = open(os.path.join(PAPER2, "ENVIRONMENT.md")).read()
    assert "2.15.0" in src and "5.22.2" in src


def test_mmcif_lite_nw_align_and_tokenize():
    sys.path.insert(0, os.path.join(PAPER2, "scripts"))
    from mmcif_lite import AA3TO1, _tokenize, alignment_identity, nw_align

    assert _tokenize('a "b c" d') == ["a", "b c", "d"]
    assert nw_align("MKTAYIAK", "MKTAYIAK") == [(i, i) for i in range(8)]
    ident, npairs = alignment_identity("ACDEFGHIKLMNPQRSTVWY", "ACDEFGHIKLMNPQRSTVWY")
    assert ident == 1.0 and npairs == 20
    assert AA3TO1["ASP"] == "D" and AA3TO1["MSE"] == "M"


def test_phase6_afdb_models_complete():
    d = _load(os.path.join("data", "structures", "afdb", "afdb_models.json"))
    assert len(d["receptors"]) == 11
    for sym, v in d["receptors"].items():
        assert v["n_residues_with_plddt"] >= 400, f"{sym} pLDDT coverage too low"
        assert len(v["sha256"]) == 64
        assert 0.0 <= v["pct_plddt_below_50"] <= 100.0


def test_phase7_pockets_defined_complete():
    d = _load(os.path.join("data", "structures", "pockets_defined.json"))
    assert len(d["receptors"]) == 11
    for sym, v in d["receptors"].items():
        assert v["receptor_chain"], f"{sym} has no receptor chain"
        assert v["ligand"]["comp_id"], f"{sym} has no chosen ligand"
        assert v["n_pocket_residues"] >= 10, f"{sym} pocket too small"
        assert v["chain_alignment_identity"] >= 0.7, f"{sym} chain alignment weak"


def test_phase8_residue_mapping_exit_criteria():
    d = _load(os.path.join("data", "structures", "residue_mapping.json"))
    assert d["totals"]["total_unmapped"] == 0
    assert len(d["receptors"]) == 11
    anchors = {"DRD2": 114, "DRD3": 110, "HTR1A": 116, "HTR2A": 155,
               "CHRM1": 105, "ADRA2A": 128, "ADRB2": 113, "HRH1": 107,
               "SERT": 98, "DAT": 79}
    for sym, pos in anchors.items():
        a = d["receptors"][sym]["anchor"]
        assert a and a["present"] and a["position"] == pos, f"{sym} anchor check failed"
    assert d["receptors"]["GABRA1"]["anchor"] is None


def test_phase9_pair_mapping_frozen():
    d = _load(os.path.join("data", "structures", "ligand_pair_mapping.json"))
    t = d["totals"]
    assert t["raw_records"] == 56637
    assert t["pairs"] == 41271
    assert t["pairs_with_3d_pocket"] == 41271
    assert t["pairs_without_3d_pocket"] == 0
    for sym, v in d["per_receptor"].items():
        assert v["pocket_grounding_available"], f"{sym} lacks 3D pocket"
        assert v["n_pairs"] > 0
    with open(os.path.join(PAPER2, "data", "structures", "pairs_41271.csv")) as f:
        n_rows = sum(1 for _ in f) - 1
    assert n_rows == 41271


def test_phase10_manifest_covers_artefacts():
    import hashlib

    d = _load(os.path.join("data", "structures", "manifest.json"))
    assert d["n_files"] >= 20
    for rel, e in d["files"].items():
        assert len(e["sha256"]) == 64, f"{rel} bad digest"
        path = os.path.join(PAPER2, "data", "structures", rel)
        with open(path, "rb") as f:
            assert hashlib.sha256(f.read()).hexdigest() == e["sha256"], f"{rel} hash mismatch"
