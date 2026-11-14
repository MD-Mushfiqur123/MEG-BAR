# Paper 2 — Preprint Packaging Checklist (Phase 40)

Date: 2026-11-14. All numbers below are measured and frozen; nothing here
requires re-running experiments.

## Files to upload

| File | Where | Notes |
|---|---|---|
| `paper2/manuscript/main.pdf` (9 pp) | Figshare + Zenodo + GitHub release | the preprint itself |
| `paper2/manuscript/main.tex` | Figshare + Zenodo + GitHub release | LaTeX source |
| `paper2/figures/fig_*.png` (4 files) | Figshare + Zenodo | 300 DPI, regenerable |
| `paper2/PREREGISTRATION.md` | Figshare + Zenodo | pre-registration (uploaded before data work) |
| `paper2/DEFECT_REGISTER.md` | Figshare + Zenodo | full defect register |
| `paper2/results/**` frozen JSON stores | Zenodo (zip) | machine-readable per-seed results |
| `paper2/ENVIRONMENT.md` | Figshare + Zenodo | environment lock |

## Figshare (same account as Paper 1, DOI 10.6084/m9.figshare.35002837)

1. New item → upload the files above (PDF + TEX + figures + prereg + defect register).
2. Title: use the exact manuscript title.
3. Authors: Md Mushfiqur Rahim (ORCID 0009-0003-1021-685X).
4. Category: Chemical Information / Computational Biology.
5. Reference the companion preprint DOI 10.6084/m9.figshare.35002837 in the description.
6. Publish → record the new DOI → put it in the manuscript's Data and Software
   Availability section before journal submission (one-line edit + recompile).

## Zenodo deposit

1. Link GitHub repo (MD-Mushfiqur123/MEG-BAR) to Zenodo → create a release; Zenodo
   mints a DOI per release automatically.
2. Or manual upload: zip `paper2/` (well under Zenodo's 50 GB limit).

## GitHub release v3.0.0

- Tag `v3.0.0` on the merge commit of the Paper 2 PR.
- Release notes: see `paper2/RELEASE_NOTES_v3.0.0.md`.
- Attach `main.pdf` and the 4 figures to the release.

## Order of operations

1. Merge PR #13 (Stages 3–8 work).
2. Tag + publish GitHub release v3.0.0.
3. Figshare publish → get DOI.
4. Insert DOI into `main.tex` §Data and Software Availability, recompile, commit.
5. Then journal submission (Phase 41 package).

## Privacy note

No personal details beyond author name, ORCID, city, and email appear in any
uploaded artefact. Nothing else to redact.
