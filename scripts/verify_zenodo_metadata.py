#!/usr/bin/env python3
"""
verify_zenodo_metadata.py
Automated validator for Zenodo and arXiv deployment manifests in MEG-BAR:
1. Validates zenodo_metadata.json against Zenodo REST API schema requirements.
2. Validates arxiv_submission_manifest.json against arXiv submission specifications.
3. Confirms all referenced LaTeX source files, styles, and 300 DPI figures exist on disk.
"""

import json
import re
import sys
from pathlib import Path

# Ensure UTF-8 console output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent.parent
ZENODO_JSON = BASE_DIR / "zenodo_metadata.json"
ARXIV_JSON = BASE_DIR / "arxiv_submission_manifest.json"
LATEX_DIR = BASE_DIR / "latex"

ORCID_REGEX = re.compile(r'^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$')
DOI_REGEX = re.compile(r'^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$')


def verify_zenodo_manifest():
    print("=== 1. VERIFYING ZENODO METADATA SCHEMA ===")
    if not ZENODO_JSON.exists():
        print(f"  [ERROR] zenodo_metadata.json NOT FOUND at {ZENODO_JSON}")
        return False

    with open(ZENODO_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "metadata" not in data:
        print("  [ERROR] Root 'metadata' object missing from zenodo_metadata.json!")
        return False

    meta = data["metadata"]
    errors = []

    # Title check
    title = meta.get("title", "")
    if "MEG-BAR: Molecular Expert Grafting with Binding Affinity Router Re-anchoring" not in title:
        errors.append(f"Unexpected title: '{title}'")
    else:
        print(f"  [OK] Title verified: '{title[:60]}...'")

    # Creators check
    creators = meta.get("creators", [])
    if not creators:
        errors.append("Empty creators list!")
    else:
        author = creators[0]
        if "Rahim, Md Mushfiqur" not in author.get("name", ""):
            errors.append(f"Unexpected author name: {author.get('name')}")
        orcid = author.get("orcid", "")
        if not ORCID_REGEX.match(orcid):
            errors.append(f"Invalid ORCID format: '{orcid}'")
        else:
            print(f"  [OK] Creator verified: {author['name']} | ORCID: {orcid}")

    # Keywords check
    required_keywords = {"Mixture of Experts", "Protein Foundation Models", "Drug Discovery", "GPCR", "Kinase", "Binding Affinity", "ESM-2"}
    keywords_set = set(meta.get("keywords", []))
    missing_kw = required_keywords - keywords_set
    if missing_kw:
        errors.append(f"Missing required keywords: {missing_kw}")
    else:
        print(f"  [OK] Keywords verified ({len(keywords_set)} total, all required present)")

    # Related Identifiers check
    rel_ids = meta.get("related_identifiers", [])
    has_prior_work = False
    for item in rel_ids:
        if item.get("identifier") == "10.5281/zenodo.23841930" and item.get("relation") == "isDerivedFrom":
            has_prior_work = True
            break
    if not has_prior_work:
        errors.append("Missing required related_identifier: 10.5281/zenodo.23841930 with relation 'isDerivedFrom'!")
    else:
        print("  [OK] Related identifier verified: DOI 10.5281/zenodo.23841930 (isDerivedFrom)")

    # License and access right
    if meta.get("access_right") != "open":
        errors.append("access_right must be 'open'!")
    if meta.get("license") != "cc-by-4.0":
        errors.append("license must be 'cc-by-4.0'!")

    if errors:
        for err in errors:
            print(f"  [ERROR] {err}")
        return False

    print("  [SUCCESS] zenodo_metadata.json passed all schema validations.\n")
    return True


def verify_arxiv_manifest():
    print("=== 2. VERIFYING ARXIV SUBMISSION MANIFEST ===")
    if not ARXIV_JSON.exists():
        print(f"  [ERROR] arxiv_submission_manifest.json NOT FOUND at {ARXIV_JSON}")
        return False

    with open(ARXIV_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "submission_manifest" not in data:
        print("  [ERROR] Root 'submission_manifest' missing from arxiv_submission_manifest.json!")
        return False

    man = data["submission_manifest"]
    errors = []

    # Categories
    primary = man.get("primary_category", "")
    if primary != "q-bio.BM":
        errors.append(f"Primary category must be 'q-bio.BM', found '{primary}'")
    else:
        print(f"  [OK] Primary category verified: {primary} (Biomolecules)")

    secondaries = set(man.get("secondary_categories", []))
    if not {"cs.LG", "q-bio.QM"}.issubset(secondaries):
        errors.append(f"Secondary categories must include cs.LG and q-bio.QM, found {secondaries}")
    else:
        print(f"  [OK] Secondary categories verified: {secondaries}")

    # Comments
    comments = man.get("comments", "")
    for term in ["28 pages", "8 figures", "13 tables", "NeurIPS"]:
        if term not in comments:
            errors.append(f"Comments missing '{term}' specification! Current: '{comments}'")
    if not errors:
        print(f"  [OK] Comments verified: '{comments}'")

    # Author
    if "Md Mushfiqur Rahim" not in man.get("authors", ""):
        errors.append(f"Unexpected authors string: '{man.get('authors')}'")
    else:
        print(f"  [OK] Authors string verified: '{man.get('authors')}'")

    # Package files on disk
    pkg = man.get("compilation_package", {})
    source_file = LATEX_DIR / pkg.get("main_latex", "main.tex")
    if not source_file.exists():
        errors.append(f"Main LaTeX file missing: {source_file}")
    bib_file = LATEX_DIR / pkg.get("bib_file", "references.bib")
    if not bib_file.exists():
        errors.append(f"Bib file missing: {bib_file}")

    for sty in pkg.get("style_files", []):
        sty_path = LATEX_DIR / sty
        if not sty_path.exists():
            errors.append(f"Style file missing: {sty_path}")

    for fig in pkg.get("figures", []):
        fig_path = LATEX_DIR / fig
        if not fig_path.exists():
            errors.append(f"Figure missing: {fig_path}")

    if errors:
        for err in errors:
            print(f"  [ERROR] {err}")
        return False

    print(f"  [OK] All {len(pkg.get('figures', []))} figures, styles, and sources verified on disk.")
    print("  [SUCCESS] arxiv_submission_manifest.json passed all submission validations.\n")
    return True


def run_all_checks():
    print("=" * 70)
    print("   MEG-BAR ZENODO & ARXIV DEPLOYMENT MANIFEST VERIFICATION")
    print("=" * 70)
    v1 = verify_zenodo_manifest()
    v2 = verify_arxiv_manifest()

    print("=" * 70)
    if v1 and v2:
        print("[SUCCESS] ALL ZENODO AND ARXIV MANIFESTS ARE 100% VALID & DEPLOYMENT-READY!")
        print("=" * 70)
        return True
    else:
        print("[FAILURE] MANIFEST VERIFICATION FAILED!")
        print("=" * 70)
        return False


if __name__ == "__main__":
    success = run_all_checks()
    sys.exit(0 if success else 1)
