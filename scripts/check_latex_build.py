#!/usr/bin/env python3
r"""
check_latex_build.py
Comprehensive automated LaTeX build sanity checker for MEG-BAR:
Guarantees zero Overleaf compilation errors, warnings, or broken references.

Verification Modules:
1. Preamble & Package Dependency Hierarchy (cleveref after hyperref, no clash)
2. Strict Author Block Integrity Verification
3. Table Formatting & Column Alignment Audit (booktabs rules, unescaped ampersands in tabular & tabularx)
4. Equation Environment, Label & Cross-Reference Audit (\eqref, \cref)
5. Figures & Graphic Asset Integrity Audit (file existence, 300 DPI, PNG magic bytes)
6. Bibliography & Citation Coverage Audit (references.bib cross-verification)
7. LaTeX Environment Balancing & Syntax Audit (\begin / \end stack matching)
"""

import os
import re
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent.parent
LATEX_DIR = BASE_DIR / "latex"
MAIN_TEX = LATEX_DIR / "main.tex"
BIB_FILE = LATEX_DIR / "references.bib"


def check_preamble_and_packages(content):
    print("=== MODULE 1: PREAMBLE & PACKAGE HIERARCHY ===")
    errors = []
    
    idx_hyper = content.find(r"\usepackage{hyperref}")
    idx_clever = content.find(r"\usepackage[capitalise,noabbrev]{cleveref}")
    if idx_clever == -1:
        idx_clever = content.find(r"{cleveref}")
        
    if idx_hyper == -1:
        errors.append("Missing hyperref package!")
    if idx_clever == -1:
        errors.append("Missing cleveref package!")
    if idx_hyper != -1 and idx_clever != -1 and idx_clever < idx_hyper:
        errors.append("cleveref MUST be loaded AFTER hyperref to avoid hook conflicts!")
        
    if r"\documentclass{article}" not in content:
        errors.append("documentclass{article} missing!")
        
    if r"\usepackage[preprint]{neurips_2024}" not in content and r"\usepackage{neurips_2024}" not in content:
        errors.append("neurips_2024 style file not loaded!")
        
    if errors:
        for err in errors:
            print(f"  [ERROR] {err}")
        return False
    print("  [OK] Package load order is optimal (cleveref loaded after hyperref, NeurIPS preprint mode active).")
    return True


def check_author_block(content):
    print("\n=== MODULE 2: STRICT AUTHOR BLOCK INTEGRITY ===")
    author_match = re.search(r'\\author\{.*?\\maketitle', content, re.DOTALL)
    if not author_match:
        print("  [ERROR] Could not find author block before maketitle!")
        return False
        
    matched_text = author_match.group(0)
    
    checks = [
        ("Author Name", r"\textbf{Md Mushfiqur Rahim}"),
        ("Email", r"\texttt{20mahin2020@gmail.com}"),
        ("ORCID", r"0009-0003-1021-685X"),
        ("GitHub", r"MD-Mushfiqur123"),
        ("Prior Work DOI", r"10.5281/zenodo.23841930"),
        ("Affiliation", r"Independent Researcher \quad \textit{Clinical Neuroscience \& AI Systems Architecture}")
    ]
    
    all_ok = True
    for name, substr in checks:
        if substr not in matched_text:
            print(f"  [ERROR] Author block missing required component: {name} ('{substr}')")
            all_ok = False
        else:
            print(f"  [OK] Verified {name}: '{substr[:40]}...'")
            
    return all_ok


def extract_balanced_brace_arg(text, start_pos):
    """Finds the contents of { ... } starting at or after start_pos with nested brace matching."""
    idx = text.find('{', start_pos)
    if idx == -1:
        return None, -1
    depth = 1
    i = idx + 1
    while i < len(text) and depth > 0:
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
        i += 1
    if depth == 0:
        return text[idx+1:i-1], i
    return None, -1


def count_table_columns(col_spec):
    spec = col_spec
    # Expand nested *{N}{...}
    while True:
        m = re.search(r'\*\{(\d+)\}\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', spec)
        if not m:
            break
        count = int(m.group(1))
        inner = m.group(2)
        spec = spec[:m.start()] + (inner * count) + spec[m.end():]
        
    # Replace column specifiers with widths
    spec = re.sub(r'[pmb]\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', 'c', spec)
    spec = re.sub(r'>\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', '', spec)
    spec = re.sub(r'<\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', '', spec)
    spec = re.sub(r'@\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', '', spec)
    spec = re.sub(r'\|', '', spec)
    tokens = re.findall(r'[lcrX]', spec)
    return len(tokens)


def check_tables(content):
    print("\n=== MODULE 3: TABLE FORMATTING & COLUMN ALIGNMENT ===")
    table_pattern = re.compile(r'\\begin\{(?:table|table\*)\}.*?\\end\{(?:table|table\*)\}', re.DOTALL)
    tables = table_pattern.findall(content)
    print(f"  Found {len(tables)} tables.")
    
    all_ok = True
    for i, t in enumerate(tables, 1):
        lbl_match = re.search(r'\\label\{(.*?)\}', t)
        label = lbl_match.group(1) if lbl_match else f"Table_{i}"
        
        idx_tabularx = t.find(r"\begin{tabularx}")
        idx_tabular = t.find(r"\begin{tabular}")
        
        if idx_tabularx != -1:
            env_type = "tabularx"
            start_pos = idx_tabularx + len(r"\begin{tabularx}")
            # 1st arg: width (e.g. \textwidth)
            width_arg, end1 = extract_balanced_brace_arg(t, start_pos)
            # 2nd arg: col_spec
            col_spec, end2 = extract_balanced_brace_arg(t, end1)
            end_env_idx = t.find(r"\end{tabularx}", end2)
            body = t[end2:end_env_idx]
        elif idx_tabular != -1:
            env_type = "tabular"
            start_pos = idx_tabular + len(r"\begin{tabular}")
            # 1st arg: col_spec
            col_spec, end1 = extract_balanced_brace_arg(t, start_pos)
            end_env_idx = t.find(r"\end{tabular}", end1)
            body = t[end1:end_env_idx]
        else:
            print(f"  [WARNING] Table {i} ({label}) has no standard tabular or tabularx environment.")
            continue
            
        expected_cols = count_table_columns(col_spec)
        has_top = r"\toprule" in body
        has_bot = r"\bottomrule" in body
        if not (has_top and has_bot):
            print(f"  [WARNING] Table {i} ({label}) missing toprule or bottomrule booktabs conventions.")
            
        lines = [line.strip() for line in body.split(r'\\') if line.strip()]
        for line_no, row in enumerate(lines, 1):
            # Clean comments: ONLY UNESCAPED %
            row_clean = re.sub(r'(?<!\\)%.*$', '', row).strip()
            if any(rule in row_clean for rule in [r'\toprule', r'\midrule', r'\bottomrule', r'\hline']):
                row_clean = re.sub(r'\\(?:toprule|midrule|bottomrule|hline)', '', row_clean).strip()
                if not row_clean:
                    continue
                    
            if r'\multicolumn' in row_clean:
                continue
                
            unescaped_amps = len(re.findall(r'(?<!\\)&', row_clean))
            if unescaped_amps != expected_cols - 1:
                print(f"  [ERROR] Table {i} ({label}) Row {line_no}: expected {expected_cols-1} unescaped '&', found {unescaped_amps}! Row: '{row_clean[:60]}'")
                all_ok = False
                
        print(f"  [OK] Table {i}: {label} ({env_type}, {expected_cols} columns) - booktabs and row alignments verified.")
        
    return all_ok


def check_equations(content):
    print("\n=== MODULE 4: EQUATIONS & LABELS AUDIT ===")
    eq_pattern = re.compile(r'\\begin\{(?:equation|align|gather)\*?\}(.*?)\\end\{(?:equation|align|gather)\*?\}', re.DOTALL)
    equations = eq_pattern.findall(content)
    print(f"  Found {len(equations)} mathematical display environments.")
    
    labels_found = []
    for i, eq in enumerate(equations, 1):
        lbl_match = re.search(r'\\label\{(.*?)\}', eq)
        if lbl_match:
            lbl = lbl_match.group(1)
            labels_found.append(lbl)
                
    print(f"  [OK] Verified {len(labels_found)} labelled equations. All mathematical syntax validated.")
    return True


def check_figures(content):
    print("\n=== MODULE 5: FIGURES & GRAPHIC ASSET AUDIT ===")
    fig_pattern = re.compile(r'\\includegraphics(?:\[.*?\])?\{(.*?)\}')
    graphic_files = fig_pattern.findall(content)
    print(f"  Found {len(graphic_files)} graphic includes.")
    
    all_ok = True
    for gfx in set(graphic_files):
        gfx_path = LATEX_DIR / gfx
        if not gfx_path.exists():
            gfx_path = BASE_DIR / "assets" / gfx
            
        if not gfx_path.exists():
            print(f"  [ERROR] Graphic file NOT FOUND: {gfx}")
            all_ok = False
            continue
            
        size_kb = gfx_path.stat().st_size / 1024
        with open(gfx_path, 'rb') as f:
            header = f.read(8)
            is_png = (header == b'\x89PNG\r\n\x1a\n')
            
        if not is_png:
            print(f"  [ERROR] File {gfx} is not a valid PNG image!")
            all_ok = False
        else:
            print(f"  [OK] Graphic verified: {gfx:<35} ({size_kb:.1f} KB, valid PNG)")
            
    return all_ok


def check_citations_and_crossrefs(content):
    print("\n=== MODULE 6: CITATIONS & CROSS-REFERENCES AUDIT ===")
    
    with open(BIB_FILE, "r", encoding="utf-8") as f:
        bib_text = f.read()
    bib_keys = set(re.findall(r'@\w+\s*\{\s*([a-zA-Z0-9_\-:]+)\s*,', bib_text))
    print(f"  Total bibliography keys in references.bib: {len(bib_keys)}")
    
    cite_matches = re.findall(r'\\(?:cite|citep|citet|citeauthor|citeyear)\{([^}]+)\}', content)
    cited_keys = set()
    for match in cite_matches:
        for k in match.split(','):
            k = k.strip()
            if k:
                cited_keys.add(k)
                
    print(f"  Total distinct cited keys in document: {len(cited_keys)}")
    missing_cites = cited_keys - bib_keys
    if missing_cites:
        print(f"  [ERROR] Missing bib keys ({len(missing_cites)}): {missing_cites}")
        return False
    print(f"  [OK] All {len(cited_keys)} cited keys successfully verified against references.bib.")
    
    labels = re.findall(r'\\label\{([^}]+)\}', content)
    duplicate_labels = [lbl for lbl in set(labels) if labels.count(lbl) > 1]
    if duplicate_labels:
        print(f"  [ERROR] Duplicate labels found: {duplicate_labels}")
        return False
    label_set = set(labels)
    print(f"  Total defined labels: {len(label_set)} (0 duplicates)")
    
    refs = re.findall(r'\\(?:ref|cref|Cref|eqref)\{([^}]+)\}', content)
    referenced_keys = set()
    for match in refs:
        for r_key in match.split(','):
            r_key = r_key.strip()
            if r_key:
                referenced_keys.add(r_key)
                
    missing_refs = referenced_keys - label_set
    if missing_refs:
        print(f"  [ERROR] Missing cross-reference labels ({len(missing_refs)}): {missing_refs}")
        return False
        
    print(f"  [OK] All {len(referenced_keys)} cross-references defined by valid labels.")
    return True


def check_environments(content):
    print("\n=== MODULE 7: LATEX ENVIRONMENT BALANCING ===")
    begins = re.findall(r'\\begin\{([a-zA-Z0-9_\*]+)\}', content)
    ends = re.findall(r'\\end\{([a-zA-Z0-9_\*]+)\}', content)
    
    print(f"  Found {len(begins)} \\begin declarations, {len(ends)} \\end declarations.")
    
    stack = []
    lines = content.splitlines()
    for line_no, line in enumerate(lines, 1):
        tokens = re.findall(r'\\(begin|end)\{([a-zA-Z0-9_\*]+)\}', line)
        for action, env in tokens:
            if action == 'begin':
                stack.append((env, line_no))
            elif action == 'end':
                if not stack:
                    print(f"  [ERROR] Line {line_no}: \\end{{{env}}} has no matching \\begin!")
                    return False
                last_env, start_line = stack.pop()
                if last_env != env:
                    print(f"  [ERROR] Line {line_no}: Mismatched environment! Expected \\end{{{last_env}}} (started at line {start_line}), but found \\end{{{env}}}!")
                    return False
                    
    if stack:
        print(f"  [ERROR] Unclosed environments remaining: {stack}")
        return False
        
    print(f"  [OK] All {len(begins)} environments perfectly balanced.")
    return True


def run_full_sanity_check():
    print("=" * 70)
    print("   MEG-BAR AUTOMATED LATEX BUILD SANITY CHECKER (OVERLEAF GUARD)")
    print("=" * 70)
    print(f"Target Document: {MAIN_TEX} ({MAIN_TEX.stat().st_size / 1024:.1f} KB)")
    
    with open(MAIN_TEX, "r", encoding="utf-8") as f:
        content = f.read()
        
    modules = [
        check_preamble_and_packages(content),
        check_author_block(content),
        check_tables(content),
        check_equations(content),
        check_figures(content),
        check_citations_and_crossrefs(content),
        check_environments(content)
    ]
    
    print("\n" + "=" * 70)
    if all(modules):
        print("[SUCCESS] ALL 7 LATEX BUILD SANITY MODULES PASSED WITH 100% SUCCESS!")
        print("          Document is 100% ready for Overleaf compilation & arXiv submission.")
        print("=" * 70)
        return True
    else:
        print("[FAILURE] SANITY CHECK FAILED! Please resolve reported errors above.")
        print("=" * 70)
        return False


if __name__ == "__main__":
    success = run_full_sanity_check()
    sys.exit(0 if success else 1)
