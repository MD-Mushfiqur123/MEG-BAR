# MEG-BAR - top-level task runner
# Paper 2 (3D structural pocket grounding) workflow automation.

PYTHON ?= python3

.PHONY: help paper2-stage1 paper2-stage1-force paper2-phase5 paper2-manifest \
        paper2-mapping paper2-test test

help:
	@echo "MEG-BAR targets:"
	@echo "  paper2-stage1        - run Paper 2 Stage 1 (AFDB -> pockets -> mapping -> manifest)"
	@echo "  paper2-stage1-force  - rerun all Stage 1 phases ignoring checkpoints"
	@echo "  paper2-phase5        - rerun PDB structure selection (RCSB search + GraphQL)"
	@echo "  paper2-mapping       - rerun residue mapping only (phase 08)"
	@echo "  paper2-manifest      - regenerate SHA-256 manifest only (phase 10)"
	@echo "  paper2-test          - run the Paper 2 artefact tests"
	@echo "  test                 - run the full test suite"

paper2-stage1:
	$(PYTHON) paper2/scripts/run_stage1.py

paper2-stage1-force:
	$(PYTHON) paper2/scripts/run_stage1.py --force

paper2-phase5:
	$(PYTHON) paper2/scripts/05_pdb_mapping.py

paper2-mapping:
	$(PYTHON) paper2/scripts/08_residue_mapping.py

paper2-manifest:
	$(PYTHON) paper2/scripts/10_manifest.py

paper2-test:
	$(PYTHON) -m pytest tests/test_paper2.py -v

test:
	$(PYTHON) -m pytest tests/ -v
