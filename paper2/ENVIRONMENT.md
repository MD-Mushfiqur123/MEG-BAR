# Paper 2 — Environment Lock (Phase 3)

Recorded: 2026-11-13. Everything below was verified by running
`importlib.metadata.version` in the working environment.

## Installed and verified

| Package | Version | Role in Paper 2 |
|---|---|---|
| numpy | 2.5.4 | arrays, distance matrices |
| pandas | 3.1.1 | record tables |
| scipy | 1.18.1 | statistics (Wilcoxon, bootstrap) |
| scikit-learn | 1.9.1 | Ridge baseline, splits (identical to Paper 1) |
| torch | 2.15.0+cpu | models (CPU-only, same as Paper 1) |
| transformers | 5.22.2 | ESM-2 650M (frozen, same checkpoint as Paper 1) |
| requests | 2.34.2 | RCSB / AFDB / UniProt / ChEMBL API access |
| rdkit | 2026.9.2 | Morgan fingerprints (baseline parity with Paper 1) |
| matplotlib | 3.11.2 | figures (300 DPI) |

## To be installed in Stage 1 (structure work)

| Package | Planned version bound | Role |
|---|---|---|
| biopython | >= 7.8 | PDB/mmCIF parsing, SIFTS alignment |
| prody | >= 2.4 | contact maps, pocket extraction, GNM |
| MDAnalysis | >= 2.7 (fallback) | alternative structure parsing |

These will be added to `requirements.txt` (bounded ranges) and
`requirements_colab.txt` (exact pins) in the same commit as the first
structure script (Phase 5), so CI always tests the real dependency set.

## Frozen inputs inherited from Paper 1 (SHA-256 under data/real/)

- `protein_embeddings.npz` / `protein_embeddings_expanded.npz` — ESM-2 650M embeddings (frozen backbone, never re-run)
- `ligand_fp_cache.npz` / `ligand_fp_cache_expanded.npz` — 2048-bit Morgan fingerprints
- `pockets.json` / `pockets_expanded.json` — UniProt binding-site annotations (11 receptors)
- `proteins_expanded.json` — sequences + UniProt accessions (11 receptors)
- `expanded_results.json`, `document_years.json` — split definitions and temporal metadata

Paper 2 must consume these artefacts as-is. Any re-derivation is a protocol
deviation and must be documented.

## Compute

CPU-only machine (same as Paper 1). If any Stage 3 arm proves infeasible on
CPU within the documented budget, that is reported honestly in the
manuscript's compute section — no silent hardware switch.
