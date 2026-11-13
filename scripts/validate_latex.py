#!/usr/bin/env python3
"""
validate_latex.py
Validates main.tex and references.bib for:
- Matching environments (\begin / \end)
- Valid citations against references.bib
- Valid cross-references (\ref, \cref against \label)
- Image file existence
"""

import os
import re

TEX_PATH = r"C:\Users\mushfiqur\Desktop\agent\projects\MEG-BAR\latex\main.tex"
BIB_PATH = r"C:\Users\mushfiqur\Desktop\agent\projects\MEG-BAR\latex\references.bib"
LATEX_DIR = r"C:\Users\mushfiqur\Desktop\agent\projects\MEG-BAR\latex"

with open(TEX_PATH, "r", encoding="utf-8") as f:
    tex = f.read()

with open(BIB_PATH, "r", encoding="utf-8") as f:
    bib = f.read()

print("=== 1. CHECKING CITATIONS ===")
bib_keys = set(re.findall(r'@\w+\{([^,]+),', bib))
print(f"Found {len(bib_keys)} bib entries.")

# Extract citations: \cite{...}, \citep{...}, \citet{...}
cite_matches = re.findall(r'\\cite[pt]?\{([^}]+)\}', tex)
used_keys = set()
for match in cite_matches:
    for k in match.split(','):
        used_keys.add(k.strip())

missing_keys = used_keys - bib_keys
if missing_keys:
    print(f"ERROR: Missing bib keys in references.bib: {missing_keys}")
else:
    print(f"SUCCESS: All {len(used_keys)} cited keys found in references.bib!")

print("\n=== 2. CHECKING CROSS-REFERENCES ===")
labels = set(re.findall(r'\\label\{([^}]+)\}', tex))
refs = set()
for r in re.findall(r'\\(?:ref|cref|Cref)\{([^}]+)\}', tex):
    for k in r.split(','):
        refs.add(k.strip())

missing_labels = refs - labels
if missing_labels:
    print(f"WARNING: Referenced labels not explicitly defined by \\label: {missing_labels}")
else:
    print(f"SUCCESS: All {len(refs)} cross-references defined by \\label!")

print(f"Total labels defined: {len(labels)}")

print("\n=== 3. CHECKING GRAPHICS FILES ===")
graphics = re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', tex)
all_found = True
for g in graphics:
    full_p = os.path.join(LATEX_DIR, g)
    if not os.path.exists(full_p):
        print(f"ERROR: Image not found: {g}")
        all_found = False
    else:
        sz = os.path.getsize(full_p) / 1024
        print(f"  Found image: {g} ({sz:.1f} KB)")

if all_found:
    print("SUCCESS: All graphics files exist!")

print("\n=== 4. CHECKING ENVIRONMENT BALANCING ===")
begins = re.findall(r'\\begin\{([^}]+)\}', tex)
ends = re.findall(r'\\end\{([^}]+)\}', tex)

from collections import Counter
b_count = Counter(begins)
e_count = Counter(ends)

imbalanced = False
for env in set(begins) | set(ends):
    if b_count[env] != e_count[env]:
        print(f"ERROR: Environment '{env}' imbalanced: \\begin={b_count[env]}, \\end={e_count[env]}")
        imbalanced = True

if not imbalanced:
    print(f"SUCCESS: All {len(b_count)} environments properly balanced!")
