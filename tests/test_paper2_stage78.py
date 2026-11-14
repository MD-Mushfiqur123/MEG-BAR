"""Paper 2 Stage 7-8 tests: manuscript artefacts (Phases 39).

Skip-safe: every test skips with a clear reason when the artefact it
checks does not exist in the working tree (e.g. CI checkout without
compiled PDFs).
"""
import os
import re

import pytest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TEX = os.path.join(REPO, 'paper2', 'manuscript', 'main.tex')
PDF = os.path.join(REPO, 'paper2', 'manuscript', 'main.pdf')
FIG_DIR = os.path.join(REPO, 'paper2', 'figures')

FIGURES = [
    'fig_per_receptor_delta.png',
    'fig_temporal_decay.png',
    'fig_crystal_vs_af.png',
    'fig_radius_sweep.png',
]

REQUIRED_TEX = [
    '41{,}271',
    'Data and Software Availability',
    'wrong-pocket',
    'PREREGISTRATION',
    'DEFECT\\_REGISTER.md',
]


@pytest.mark.skipif(not os.path.exists(TEX), reason='manuscript main.tex not present')
class TestManuscriptSource:
    def test_tex_exists_nonempty(self):
        assert os.path.getsize(TEX) > 10000

    def test_required_sections_and_numbers(self):
        with open(TEX) as fh:
            tex = fh.read()
        for needle in REQUIRED_TEX:
            assert needle in tex, 'missing from main.tex: %r' % needle

    def test_no_fabricated_keywords(self):
        with open(TEX) as fh:
            tex = fh.read().lower()
        for bad in ['simulated result', 'we simulate', 'placeholder',
                    'todo', 'xxx', 'lorem ipsum']:
            assert bad not in tex, 'forbidden marker in main.tex: %r' % bad

    def test_mutation_probe_reported_not_run(self):
        with open(TEX) as fh:
            tex = fh.read()
        assert 'not run' in tex or 'not-run' in tex


@pytest.mark.skipif(not os.path.exists(PDF), reason='compiled main.pdf not present')
class TestManuscriptPdf:
    def test_pdf_page_count(self):
        from pypdf import PdfReader
        n = len(PdfReader(PDF).pages)
        assert 5 <= n <= 20

    def test_pdf_no_dangling_refs(self):
        from pypdf import PdfReader
        txt = ''.join(p.extract_text() or '' for p in PdfReader(PDF).pages)
        assert '??' not in txt


@pytest.mark.skipif(not os.path.isdir(FIG_DIR), reason='figures dir not present')
class TestFigures:
    @pytest.mark.parametrize('name', FIGURES)
    def test_figure_exists(self, name):
        assert os.path.exists(os.path.join(FIG_DIR, name))

    @pytest.mark.parametrize('name', FIGURES)
    def test_figure_referenced_in_tex(self, name):
        if not os.path.exists(TEX):
            pytest.skip('manuscript main.tex not present')
        with open(TEX) as fh:
            assert name in fh.read()
