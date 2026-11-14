"""Paper 2 artefact tests - no network required, checks committed frozen files."""

import json
import os

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
