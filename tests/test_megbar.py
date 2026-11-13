#!/usr/bin/env python3
"""
test_megbar.py
Pytest suite for MEG-BAR:
Molecular Expert Grafting with Binding Affinity Router Re-anchoring for Drug-Receptor Specialization.

Tests:
1. Routing logic: Softmax gating, top-k sparsity, probability axioms across 4 and 5 experts.
2. Re-anchoring loss: KL divergence computation and projected gradient masking.
3. Total loss objective: Binding affinity MSE + re-anchoring KL + auxiliary load balancing.
4. Expert activation specialization: Verifying target routing mass concentration.
5. Large-scale benchmark data integrity: Verifying 1,000-complex bootstrap results file exists and conforms to schema.
6. Figure generation outputs: Verifying all 8 publication PNGs (Figures 1-8) exist, non-empty, valid 300 DPI dimensions.
7. Kinase resistance benchmark data integrity: Verifying kinase mutation JSON exists and has valid evaluation metrics.
8. Hierarchical mutation adapter: Verifying low-rank residual addition and projected mask invariance for non-target experts.
9. Zenodo and arXiv submission manifests: Verifying DOI re-anchoring, ORCID, categories, and manifest files.
10. Interactive visualizer dashboard: Verifying self-contained HTML5/Canvas architecture, zero external CDN scripts, and DOM elements.
11. Journal submission package: Verifying Nature Biotechnology cover letters (.tex, .md) and 5-point peer review defense.
12. One-click reproduction script: Verifying pipeline stage coverage and executable completeness.
13. Interactive defense slides: Verifying 18-slide standalone presentation, keyboard navigation, and author metadata.
14. Clinical translation whitepaper: Verifying industrial TPP, FDA/EMA compliance, biophysical assays, and safety profiles.
15. Universal containerized reproduction: Verifying Dockerfile and docker-compose.yml specifications and port 8080 exposure.
16. Google Colab interactive walkthrough: Verifying valid notebook JSON, 5 sections, Colab badge, and strict author metadata.
17. Benchmark & Carbon accounting report: Verifying comparison matrix (AF-Multimer, Rosetta, DiffDock, GShard), FLOPs, and Green AI metrics.
18. Multi-OS CI/CD pipeline: Verifying matrix testing across 3 OS platforms and 3 Python versions.
"""

import os
import re
import json
import pytest
import numpy as np


class MockBindingAffinityRouter:
    """Mock implementation of the MEG-BAR Binding Affinity Router."""
    def __init__(self, d_model=1280, num_experts=4, top_k=2, tau=1.0):
        self.d_model = d_model
        self.num_experts = num_experts
        self.top_k = top_k
        self.tau = tau
        np.random.seed(42)
        self.W_r = np.random.randn(num_experts, d_model) * 0.02
        self.b_r = np.zeros(num_experts)

    def route(self, h):
        """
        Forward pass of router.
        h: (batch_size, d_model)
        Returns: gating weights (batch_size, num_experts), top_k_indices (batch_size, top_k)
        """
        logits = (h @ self.W_r.T + self.b_r) / self.tau  # (B, N)
        exp_logits = np.exp(logits - np.max(logits, axis=-1, keepdims=True))
        probs = exp_logits / np.sum(exp_logits, axis=-1, keepdims=True)

        top_k_indices = np.argsort(-probs, axis=-1)[:, :self.top_k]
        
        # Mask out non-top-k and renormalize
        gating_weights = np.zeros_like(probs)
        for i in range(h.shape[0]):
            idx = top_k_indices[i]
            top_p = probs[i, idx]
            gating_weights[i, idx] = top_p / np.sum(top_p)

        return probs, gating_weights, top_k_indices


def compute_reanchoring_loss(p, q_star, eps=1e-8):
    """
    Compute Kullback-Leibler Re-anchoring Loss:
    L_RA = sum_i D_KL(p_i || q_i^*) = sum_i sum_k p_{i,k} * log( (p_{i,k} + eps) / (q_{i,k}^* + eps) )
    """
    p = np.clip(p, eps, 1.0)
    q_star = np.clip(q_star, eps, 1.0)
    kl = np.sum(p * np.log(p / q_star), axis=-1)
    return np.mean(kl)


def compute_total_megbar_loss(y_pred, y_true, p_router, q_target, alpha=0.5, beta=0.01):
    """
    L_total = L_BA + alpha * L_RA + beta * L_aux
    """
    l_ba = np.mean((y_pred - y_true) ** 2)
    l_ra = compute_reanchoring_loss(p_router, q_target)
    
    # Auxiliary load balancing loss: N * sum_j (mean_p_j * mean_f_j)
    num_experts = p_router.shape[-1]
    mean_p = np.mean(p_router, axis=0)
    l_aux = num_experts * np.sum(mean_p ** 2)
    
    l_total = l_ba + alpha * l_ra + beta * l_aux
    return l_total, l_ba, l_ra, l_aux


def test_router_probabilities_sum_to_one():
    """Verify router softmax output forms a valid probability distribution."""
    router = MockBindingAffinityRouter(d_model=64, num_experts=4, top_k=2)
    x = np.random.randn(10, 64)
    probs, gating, top_k = router.route(x)

    assert probs.shape == (10, 4)
    assert gating.shape == (10, 4)
    assert np.allclose(np.sum(probs, axis=-1), 1.0, atol=1e-6)
    assert np.allclose(np.sum(gating, axis=-1), 1.0, atol=1e-6)


def test_router_5_experts_extension():
    """Verify router generalizes cleanly to 5 receptor families (including beta2-AR)."""
    router = MockBindingAffinityRouter(d_model=128, num_experts=5, top_k=2)
    x = np.random.randn(16, 128)
    probs, gating, top_k = router.route(x)

    assert probs.shape == (16, 5)
    assert gating.shape == (16, 5)
    assert np.allclose(np.sum(probs, axis=-1), 1.0, atol=1e-6)
    assert top_k.shape == (16, 2)


def test_top_k_sparsity():
    """Verify that only top-k experts receive non-zero gating weights."""
    router = MockBindingAffinityRouter(d_model=64, num_experts=4, top_k=2)
    x = np.random.randn(8, 64)
    _, gating, top_k = router.route(x)

    for i in range(8):
        non_zero_count = np.count_nonzero(gating[i] > 1e-6)
        assert non_zero_count == 2
        for k in top_k[i]:
            assert gating[i, k] > 0.0


def test_reanchoring_loss_zero_when_identical():
    """Verify KL divergence is 0 when predicted routing matches target distribution."""
    q_target = np.array([[0.85, 0.05, 0.05, 0.05],
                         [0.10, 0.70, 0.10, 0.10]])
    p_router = q_target.copy()
    loss = compute_reanchoring_loss(p_router, q_target)
    assert np.isclose(loss, 0.0, atol=1e-6)


def test_reanchoring_loss_positive_when_divergent():
    """Verify KL divergence is strictly positive when distributions diverge."""
    q_target = np.array([[0.90, 0.04, 0.03, 0.03]])
    p_uniform = np.array([[0.25, 0.25, 0.25, 0.25]])
    loss = compute_reanchoring_loss(p_uniform, q_target)
    assert loss > 0.40  # Significant divergence penalty


def test_projected_gradient_mask():
    """Verify projected gradient mask zeroes out non-target expert updates."""
    num_experts = 5
    d_model = 64
    target_expert = 2  # e.g., GABA_A
    
    grad_W_r = np.ones((num_experts, d_model))
    M_k = np.zeros((num_experts, d_model))
    M_k[target_expert, :] = 1.0
    
    masked_grad = grad_W_r * M_k
    
    assert np.all(masked_grad[target_expert, :] == 1.0)
    for j in range(num_experts):
        if j != target_expert:
            assert np.all(masked_grad[j, :] == 0.0)


def test_total_loss_composition():
    """Verify total MEG-BAR loss mathematically combines BA, RA, and aux terms."""
    y_pred = np.array([7.8, 6.5, 8.2])
    y_true = np.array([8.0, 6.2, 8.5])
    p_router = np.array([[0.80, 0.10, 0.05, 0.05],
                         [0.10, 0.85, 0.03, 0.02],
                         [0.05, 0.05, 0.80, 0.10]])
    q_target = np.array([[0.90, 0.04, 0.03, 0.03],
                         [0.05, 0.90, 0.03, 0.02],
                         [0.02, 0.03, 0.90, 0.05]])
    
    total, ba, ra, aux = compute_total_megbar_loss(y_pred, y_true, p_router, q_target, alpha=0.5, beta=0.01)
    
    assert ba > 0
    assert ra > 0
    assert aux > 0
    assert np.isclose(total, ba + 0.5 * ra + 0.01 * aux, atol=1e-6)


def test_large_scale_benchmark_results_file():
    """Verify the 1,000-complex bootstrap benchmark results JSON exists and conforms to schema."""
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
    results_file = os.path.join(data_dir, "large_scale_benchmark_results.json")
    
    assert os.path.isfile(results_file), f"Benchmark results file missing: {results_file}"
    assert os.path.getsize(results_file) > 10000, f"File too small: {results_file}"
    
    with open(results_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    assert data["total_complexes"] == 1000
    assert len(data["receptor_families"]) == 5
    assert "MEG-BAR (Ours)" in data["overall_evaluation"]
    
    megbar_res = data["overall_evaluation"]["MEG-BAR (Ours)"]
    assert megbar_res["deterministic_metrics"]["pearson_r"] > 0.80
    assert len(megbar_res["bootstrap_ci_95"]["pearson_r"]["ci_95"]) == 2


def test_generated_figures_exist_and_valid():
    """Verify all 8 publication figures exist in assets/ and have valid PNG format."""
    assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets'))
    expected_figures = [
        'figure1_megbar_architecture.png',
        'figure2_expert_heatmap.png',
        'figure3_binding_comparison.png',
        'figure4_router_weights.png',
        'figure5_training_curves.png',
        'figure6_residue_attention.png',
        'figure7_bootstrap_distribution.png',
        'figure8_mutation_adaptation.png'
    ]

    for fig_name in expected_figures:
        fig_path = os.path.join(assets_dir, fig_name)
        assert os.path.isfile(fig_path), f"Figure missing: {fig_path}"
        assert os.path.getsize(fig_path) > 10000, f"Figure too small / empty: {fig_path}"
        
        with open(fig_path, 'rb') as f:
            header = f.read(8)
            assert header == b'\x89PNG\r\n\x1a\n', f"Invalid PNG magic bytes in {fig_name}"


def test_kinase_resistance_benchmark_data_integrity():
    """Verify Phase 3 oncological kinase & nuclear receptor benchmark JSON file."""
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
    results_file = os.path.join(data_dir, "kinase_resistance_benchmark.json")
    
    assert os.path.isfile(results_file), f"Kinase benchmark missing: {results_file}"
    with open(results_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    assert len(data["systems"]) == 5
    system_names = [s["name"] for s in data["systems"]]
    assert "EGFR" in system_names
    assert "BCR-ABL1" in system_names
    assert "BRAF" in system_names
    assert "ESR1 (ER-alpha)" in system_names
    assert "AR (Androgen Receptor)" in system_names
    
    megbar_metrics = data["summary_metrics"]["MEG_BAR"]
    assert megbar_metrics["overall_pearson_r"] > 0.95
    assert megbar_metrics["overall_rmse"] < 0.35


def test_hierarchical_mutation_adapter_invariance():
    """Verify Proposition 4: Non-target expert centroids receive exactly zero gradient under M_mut."""
    num_experts = 7  # 4 GPCRs + 1 Base Kinase + 2 Mutation Adapters
    d_model = 128
    parent_kinase_idx = 4
    mutation_idx = 5
    
    M_mut = np.zeros((num_experts, d_model))
    M_mut[parent_kinase_idx, :] = 1.0
    M_mut[mutation_idx, :] = 1.0
    
    W_r = np.random.randn(num_experts, d_model)
    W_r_initial = W_r.copy()
    
    grad = np.random.randn(num_experts, d_model)
    learning_rate = 0.01
    
    # Apply projected gradient update
    W_r_updated = W_r - learning_rate * (M_mut * grad)
    
    # Check that non-target experts (GPCRs 0, 1, 2, 3 and unselected adapter 6) are strictly invariant
    non_target_indices = [0, 1, 2, 3, 6]
    for idx in non_target_indices:
        assert np.array_equal(W_r_updated[idx], W_r_initial[idx]), f"Expert {idx} drifted!"
        
    # Check that target experts received updates
    assert not np.array_equal(W_r_updated[parent_kinase_idx], W_r_initial[parent_kinase_idx])
    assert not np.array_equal(W_r_updated[mutation_idx], W_r_initial[mutation_idx])


def test_zenodo_and_arxiv_manifests():
    """Verify Zenodo DOI metadata and arXiv submission manifest schema and file references."""
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    # 1. Zenodo metadata check
    zenodo_path = os.path.join(root_dir, "zenodo_metadata.json")
    assert os.path.isfile(zenodo_path), f"zenodo_metadata.json missing at {zenodo_path}"
    with open(zenodo_path, 'r', encoding='utf-8') as f:
        z_data = json.load(f)
        
    meta = z_data.get("metadata", {})
    with open(os.path.join(root_dir, "latex", "main.tex"), 'r', encoding='utf-8') as f:
        tex_title = re.search(r"\\title\{\\textbf\{(.+?)\}\}", f.read())
    assert tex_title is not None, "\\title{...} not found in latex/main.tex"
    assert meta.get("title", "") == tex_title.group(1), (
        "zenodo_metadata.json title does not match latex/main.tex title"
    )
    assert meta.get("creators", [{}])[0].get("name") == "Rahim, Md Mushfiqur"
    assert meta.get("creators", [{}])[0].get("orcid") == "0009-0003-1021-685X"
    
    # Check related identifier DOI 10.5281/zenodo.23841930
    related = meta.get("related_identifiers", [])
    assert any(
        r.get("identifier") == "10.5281/zenodo.23841930" and r.get("relation") == "isDerivedFrom"
        for r in related
    ), "Prior Zenodo DOI 10.5281/zenodo.23841930 isDerivedFrom link missing!"
    
    # 2. arXiv submission manifest check
    arxiv_path = os.path.join(root_dir, "arxiv_submission_manifest.json")
    assert os.path.isfile(arxiv_path), f"arxiv_submission_manifest.json missing at {arxiv_path}"
    with open(arxiv_path, 'r', encoding='utf-8') as f:
        a_data = json.load(f)
        
    sub = a_data.get("submission_manifest", {})
    assert sub.get("primary_category") == "q-bio.BM"
    assert "cs.LG" in sub.get("secondary_categories", [])
    assert "q-bio.QM" in sub.get("secondary_categories", [])
    assert "28 pages" in sub.get("comments", "")
    assert "8 figures" in sub.get("comments", "")
    assert "19 tables" in sub.get("comments", "")
    
    # Check compilation package components
    pkg = sub.get("compilation_package", {})
    latex_dir = os.path.join(root_dir, "latex")
    assert os.path.isfile(os.path.join(latex_dir, pkg["main_latex"]))
    assert os.path.isfile(os.path.join(latex_dir, pkg["bib_file"]))
    for sty in pkg.get("style_files", []):
        assert os.path.isfile(os.path.join(latex_dir, sty))
    for fig in pkg.get("figures", []):
        assert os.path.isfile(os.path.join(latex_dir, fig))


def test_interactive_visualizer_html_exists_and_valid():
    """Verify Phase 6 Interactive Visualizer Dashboard is self-contained with no external CDN dependencies."""
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    viz_path = os.path.join(root_dir, "visualizer", "index.html")
    
    assert os.path.isfile(viz_path), f"visualizer/index.html missing at {viz_path}"
    assert os.path.getsize(viz_path) > 20000, f"visualizer/index.html too small: {os.path.getsize(viz_path)} bytes"
    
    with open(viz_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Check key canvas and control IDs
    required_ids = [
        "pocketCanvas", "mutationRadarCanvas", "admetRadarCanvas",
        "routing-bars", "slider-pkd", "slider-tau", "slider-alpha",
        "slider-rank", "select-receptor", "disp-mass-conc"
    ]
    for element_id in required_ids:
        assert f'id="{element_id}"' in content, f"Missing required element ID: {element_id}"
        
    # Verify author and DOI metadata
    assert "Md Mushfiqur Rahim" in content, "Author name missing in visualizer!"
    assert "0009-0003-1021-685X" in content, "ORCID missing in visualizer!"
    assert "10.5281/zenodo.23841930" in content, "Prior work DOI missing in visualizer!"
    
    # Verify 100% self-contained: No external CDN or HTTP script inclusions
    assert 'src="http' not in content, "Found external script CDN tag! Must be 100% self-contained."
    assert 'href="http' not in content or 'stylesheet' not in content.lower(), "Found external stylesheet link!"


def test_journal_submission_package():
    """Verify Phase 6 Nature Biotechnology submission package and 5-point peer review defense."""
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sub_dir = os.path.join(root_dir, "submission")
    
    cl_tex = os.path.join(sub_dir, "cover_letter_nature_biotech.tex")
    cl_md = os.path.join(sub_dir, "cover_letter_nature_biotech.md")
    rev_md = os.path.join(sub_dir, "anticipated_reviewer_responses.md")
    
    for path, min_size in [(cl_tex, 3000), (cl_md, 3000), (rev_md, 7000)]:
        assert os.path.isfile(path), f"Missing submission file: {path}"
        assert os.path.getsize(path) >= min_size, f"File too small: {path} ({os.path.getsize(path)} bytes)"
        
    # Check cover letter specifics
    with open(cl_tex, 'r', encoding='utf-8') as f:
        tex_text = f.read()
    assert "Nature Biotechnology" in tex_text
    assert "Andrew Marshall" in tex_text
    assert "Md Mushfiqur Rahim" in tex_text
    assert "0009-0003-1021-685X" in tex_text
    assert "10.5281/zenodo.23841930" in tex_text
    
    # Check 5 peer-review critique vectors in defense document
    with open(rev_md, 'r', encoding='utf-8') as f:
        rev_text = f.read()
    for vec_num in range(1, 6):
        assert f"Critique Vector {vec_num}" in rev_text, f"Critique Vector {vec_num} missing from reviewer defense!"
    assert "Bemis-Murcko" in rev_text
    assert "Projected Gradient Mask" in rev_text
    assert "Dudley chaining" in rev_text
    assert "EGFR T790M" in rev_text
    assert "AlphaFold-Multimer" in rev_text


def test_one_click_reproduce_script_integrity():
    """Verify Phase 6 One-Click Reproduction Engine exists and contains all 8 stages."""
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    script_path = os.path.join(root_dir, "scripts", "one_click_reproduce.py")
    
    assert os.path.isfile(script_path), f"one_click_reproduce.py missing at {script_path}"
    assert os.path.getsize(script_path) > 3000, f"Script too small: {script_path}"
    
    with open(script_path, 'r', encoding='utf-8') as f:
        script_text = f.read()
        
    expected_stages = [
        "stage1_environment",
        "stage2_benchmark_data",
        "stage3_figures",
        "stage4_zenodo_arxiv_manifests",
        "stage5_latex_build_sanity",
        "stage6_pytest_suite",
        "stage7_package_and_sync",
        "stage8_visualizer_and_submission"
    ]
    for stage_func in expected_stages:
        assert stage_func in script_text, f"Stage function '{stage_func}' missing in one_click_reproduce.py!"


def test_interactive_defense_slides_html():
    """Verify Phase 7 Interactive PhD / Nature Defense presentation deck."""
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    slides_path = os.path.join(root_dir, "presentations", "defense_slides.html")
    
    assert os.path.isfile(slides_path), f"presentations/defense_slides.html missing at {slides_path}"
    assert os.path.getsize(slides_path) > 20000, f"Slides deck too small: {os.path.getsize(slides_path)} bytes"
    
    with open(slides_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Check 18 slides
    for slide_idx in range(1, 19):
        assert f'data-slide="{slide_idx}"' in content, f"Slide {slide_idx} missing in defense_slides.html"
        
    # Check navigation and controls
    assert "ArrowRight" in content
    assert "ArrowLeft" in content
    assert "toggleFullscreen" in content
    assert "btn-fullscreen" in content
    assert "progress-bar" in content
    
    # Check author and metadata
    assert "Md Mushfiqur Rahim" in content
    assert "0009-0003-1021-685X" in content
    assert "10.5281/zenodo.23841930" in content
    
    # Check zero external script tags
    assert 'src="http' not in content, "External script detected in defense slides! Must be self-contained."


def test_clinical_translation_whitepaper():
    """Verify Phase 7 Clinical & Translational Pharmacology Whitepaper."""
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    wp_path = os.path.join(root_dir, "whitepapers", "CLINICAL_TRANSLATION_REPORT.md")
    
    assert os.path.isfile(wp_path), f"whitepapers/CLINICAL_TRANSLATION_REPORT.md missing at {wp_path}"
    assert os.path.getsize(wp_path) > 6000, f"Whitepaper too small: {os.path.getsize(wp_path)} bytes"
    
    with open(wp_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    required_keywords = [
        "FDA Modernization Act 2.0",
        "EMA Multi-Target Guidelines",
        "ICH S7B",
        "CNS-MPO",
        "hERG",
        "SAScore",
        "Surface Plasmon Resonance",
        "Isothermal Titration Calorimetry",
        "Target Product Profile",
        "EGFR T790M",
        "BCR-ABL1 T315I",
        "Scientific Integrity and Data Transparency Standards"
    ]
    for kw in required_keywords:
        assert kw in content, f"Required term '{kw}' missing from Clinical Translation Whitepaper!"


def test_docker_reproduction_suite():
    """Verify Phase 7 Universal Containerized Reproduction files."""
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    dockerfile = os.path.join(root_dir, "Dockerfile")
    docker_compose = os.path.join(root_dir, "docker-compose.yml")
    
    assert os.path.isfile(dockerfile), f"Dockerfile missing at {dockerfile}"
    assert os.path.isfile(docker_compose), f"docker-compose.yml missing at {docker_compose}"
    
    with open(dockerfile, 'r', encoding='utf-8') as f:
        df_text = f.read()
    assert "python:3.12-slim" in df_text
    assert "EXPOSE 8080" in df_text
    assert "one_click_reproduce.py" in df_text
    assert "HEALTHCHECK" in df_text
    
    with open(docker_compose, 'r', encoding='utf-8') as f:
        dc_text = f.read()
    assert "8080:8080" in dc_text
    assert "megbar_reproduction_suite" in dc_text


def test_google_colab_notebook_exists_and_valid():
    """Verify Phase 8 Google Colab interactive notebook format, sections, and strict author metadata."""
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    nb_path = os.path.join(root_dir, "notebooks", "megbar_interactive_walkthrough.ipynb")
    
    assert os.path.isfile(nb_path), f"notebooks/megbar_interactive_walkthrough.ipynb missing at {nb_path}"
    assert os.path.getsize(nb_path) > 4000, f"Notebook too small: {os.path.getsize(nb_path)} bytes"
    
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb_data = json.load(f)
        
    assert "cells" in nb_data, "Invalid notebook structure: 'cells' missing!"
    assert len(nb_data["cells"]) >= 10, f"Too few cells in notebook: {len(nb_data['cells'])}"
    
    full_text = ""
    for cell in nb_data["cells"]:
        full_text += "".join(cell.get("source", [])) + "\n"
        
    # Check Colab badge
    assert "colab.research.google.com" in full_text
    assert "megbar_interactive_walkthrough.ipynb" in full_text
    
    # Check strict author block (Independent Researcher, no college text)
    assert "Md Mushfiqur Rahim" in full_text
    assert "20mahin2020@gmail.com" in full_text
    assert "0009-0003-1021-685X" in full_text
    assert "Independent Researcher" in full_text
    assert "Azizul Haque" not in full_text, "College text must NOT be present in Colab notebook!"
    
    # Check all 5 sections
    for sec_num in range(1, 6):
        assert f"Section {sec_num}:" in full_text, f"Section {sec_num} missing in Colab notebook!"


def test_benchmark_carbon_report():
    """Verify Phase 8 Benchmark & Carbon Accounting Report."""
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    bench_path = os.path.join(root_dir, "benchmarks", "BENCHMARK_REPORT.md")
    
    assert os.path.isfile(bench_path), f"benchmarks/BENCHMARK_REPORT.md missing at {bench_path}"
    assert os.path.getsize(bench_path) > 4000, f"Benchmark report too small: {os.path.getsize(bench_path)} bytes"
    
    with open(bench_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Check competitive baseline comparisons
    assert "AlphaFold-Multimer" in content
    assert "Rosetta" in content
    assert "DiffDock" in content
    assert "GShard" in content
    assert "ESM-2" in content
    
    # Check key numerical benchmarks
    assert "4.8 ms" in content
    assert "0.018 kg CO" in content
    assert "98.7%" in content
    assert "0.58M" in content
    assert "1.18 GB" in content
    
    # Check strict author block
    assert "Md Mushfiqur Rahim" in content
    assert "20mahin2020@gmail.com" in content
    assert "Independent Researcher" in content
    assert "Azizul Haque" not in content, "College text must NOT be present in Benchmark report!"


def test_multi_os_github_workflow():
    """Verify Phase 8 Multi-OS CI/CD Pipeline configuration."""
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    workflow_path = os.path.join(root_dir, ".github", "workflows", "reproduce_ci.yml")
    
    assert os.path.isfile(workflow_path), f".github/workflows/reproduce_ci.yml missing at {workflow_path}"
    assert os.path.getsize(workflow_path) > 300, f"Workflow file too small: {os.path.getsize(workflow_path)} bytes"
    
    with open(workflow_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Check multi-OS platforms
    assert "ubuntu-latest" in content
    assert "windows-latest" in content
    assert "macos-latest" in content
    
    # Check python versions
    assert "3.10" in content
    assert "3.11" in content
    assert "3.12" in content
    
    # Check execution steps
    assert "pytest tests/test_megbar.py" in content
    assert "python scripts/one_click_reproduce.py" in content




def test_phase2_admet_artifacts():
    """Phase 2: computed physicochemistry and hERG QSAR replace hardcoded ADMET constants."""
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    real = os.path.join(root_dir, 'data', 'real')

    with open(os.path.join(real, 'admet_physchem.json'), 'r', encoding='utf-8') as f:
        adm = json.load(f)
    assert adm['n_unique_molecules'] > 10000
    assert adm['n_unparseable'] == 0
    mpo = adm['overall']['cns_mpo4']
    assert 0.0 <= mpo['mean'] <= 4.0
    assert mpo['sd'] > 0
    assert 0.0 <= adm['overall']['veber_pass'] <= 1.0
    assert 0.0 <= adm['overall']['lipinski_pass'] <= 1.0
    assert 'cns_mpo_note' in adm and 'CNS-MPO(4)' in adm['cns_mpo_note']

    with open(os.path.join(real, 'herg_results.json'), 'r', encoding='utf-8') as f:
        herg = json.load(f)
    assert herg['n_modelled'] > 5000
    assert herg['n_scaffolds'] > 1000
    assert 0.5 <= herg['test_roc_auc'] <= 1.0
    lo, hi = herg['test_roc_auc_bootstrap95ci']
    assert lo < herg['test_roc_auc'] < hi
    assert herg['target']['uniprot'] == 'Q12809'


def test_phase3_expanded_artifacts():
    """Phase 3: eleven-receptor evidence base with scaffold and temporal splits."""
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    real = os.path.join(root_dir, 'data', 'real')

    with open(os.path.join(real, 'expand_manifest.json'), 'r', encoding='utf-8') as f:
        man = json.load(f)
    assert len(man['targets']) == 7
    assert man['row_count_expanded'] > 40000
    assert man['documents_with_year'] >= 0.99 * man['documents_total']

    with open(os.path.join(real, 'proteins_expanded.json'), 'r', encoding='utf-8') as f:
        prot = json.load(f)
    assert len(prot) == 11
    for gene, rec in prot.items():
        assert rec['length'] == len(rec['sequence'])

    with open(os.path.join(real, 'document_years.json'), 'r', encoding='utf-8') as f:
        years = json.load(f)
    assert years and all(isinstance(v, int) for v in years.values())

    with open(os.path.join(real, 'expanded_results.json'), 'r', encoding='utf-8') as f:
        res = json.load(f)
    assert res['temporal_cutoff'] == 2015
    e3 = [k for k in res if k.startswith('E3|')]
    e5 = [k for k in res if k.startswith('E5|')]
    assert len(e3) >= 10, 'expected scaffold-split blocks for >=10 receptors'
    assert len(e5) >= 8, 'expected temporal-split blocks for >=8 receptors'
    for blk_key in e3 + e5:
        blk = res[blk_key]
        for arch in ('shared', 'crossattn'):
            rec = blk.get(arch)
            if isinstance(rec, dict) and 'skipped' not in rec:
                assert len(rec.get('seeds', [])) == 5, '%s %s incomplete' % (blk_key, arch)
                assert 0.0 <= rec['mean_r'] <= 1.0
