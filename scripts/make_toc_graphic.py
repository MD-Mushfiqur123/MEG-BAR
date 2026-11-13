"""Generate the ACS JCIM Table-of-Contents (TOC) graphic.

ACS specification: 3.25 in wide x 1.75 in tall, >= 300 DPI, PNG or TIFF.
Output: submission/JCIM/TOC_graphic_3.25x1.75in_300dpi.png (975 x 525 px).

Run:  python3 scripts/make_toc_graphic.py
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

W_IN, H_IN, DPI = 3.25, 1.75, 300

GRAY = "#5f6368"
LIGHT = "#f1f3f4"
GREEN = "#1e7d32"
GREEN_BG = "#e6f4ea"
RED = "#b3261e"
RED_BG = "#fcebea"
INK = "#202124"

fig = plt.figure(figsize=(W_IN, H_IN), dpi=DPI)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")


def box(x, y, w, h, fc, ec, lw=0.8):
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.008,rounding_size=0.02",
            facecolor=fc, edgecolor=ec, linewidth=lw,
        )
    )


def arrow(x0, y0, x1, y1, color=GRAY):
    ax.add_patch(
        FancyArrowPatch(
            (x0, y0), (x1, y1),
            arrowstyle="-|>", mutation_scale=6,
            linewidth=0.9, color=color,
        )
    )


def txt(x, y, s, size, weight="normal", color=INK, ha="center", va="center", style="normal"):
    ax.text(x, y, s, fontsize=size, fontweight=weight, color=color,
            ha=ha, va=va, style=style, wrap=True)


L, R = 0.025, 0.545

box(L, 0.70, 0.24, 0.24, LIGHT, GRAY)
txt(L + 0.12, 0.86, "Ligand", 6, "bold")
txt(L + 0.12, 0.77, "Morgan FP (2048-bit)", 5.2, color=GRAY)

box(L + 0.26, 0.70, 0.24, 0.24, LIGHT, GRAY)
txt(L + 0.38, 0.86, "Protein", 6, "bold")
txt(L + 0.38, 0.77, "ESM-2 650M (frozen)", 5.2, color=GRAY)

arrow(L + 0.12, 0.695, L + 0.09, 0.60)
arrow(L + 0.38, 0.695, L + 0.41, 0.60)

box(L, 0.38, 0.155, 0.21, "#fff", GRAY)
txt(L + 0.0775, 0.485, "Expert", 5.4, "bold")
txt(L + 0.0775, 0.425, "routing", 5.4, "bold")

box(L + 0.175, 0.38, 0.155, 0.21, "#fff", GRAY)
txt(L + 0.2525, 0.485, "Pocket", 5.4, "bold")
txt(L + 0.2525, 0.425, "conditioning", 5.4, "bold")

box(L + 0.35, 0.38, 0.155, 0.21, GREEN_BG, GREEN, lw=1.2)
txt(L + 0.4275, 0.485, "Ridge on", 5.4, "bold", color=GREEN)
txt(L + 0.4275, 0.425, "fingerprints", 5.4, "bold", color=GREEN)

txt(L + 0.0775, 0.30, "✗ no significant gain", 5.0, color=RED)
txt(L + 0.0775, 0.245, "(p ≥ 0.0625; wrong-pocket ≈)", 4.4, color=GRAY)

txt(L + 0.2525, 0.30, "✗ matches shared model", 5.0, color=RED)
txt(L + 0.2525, 0.245, "(pocket 3D adds nothing)", 4.4, color=GRAY)

txt(L + 0.4275, 0.30, "✓ competitive, robust", 5.0, color=GREEN)
txt(L + 0.4275, 0.245, "r = 0.39–0.83 (5 seeds)", 4.4, color=GREEN)

ax.plot([R + 0.005, R + 0.005], [0.06, 0.96], color="#dadce0", linewidth=0.8)

txt(R + 0.035, 0.80, "Fingerprints — not expert", 7.6, "bold", ha="left")
txt(R + 0.035, 0.68, "routing or pockets —", 7.6, "bold", ha="left")
txt(R + 0.035, 0.56, "drive cross-family", 7.6, "bold", ha="left")
txt(R + 0.035, 0.44, "affinity prediction", 7.6, "bold", ha="left")

txt(R + 0.035, 0.28, "56,637 measured ChEMBL records", 5.4, color=GRAY, ha="left")
txt(R + 0.035, 0.205, "11 human receptors • ESM-2 650M", 5.4, color=GRAY, ha="left")
txt(R + 0.035, 0.13, "scaffold-disjoint & temporal splits", 5.4, color=GRAY, ha="left")

out_dir = os.path.join(os.path.dirname(__file__), "..", "submission", "JCIM")
os.makedirs(out_dir, exist_ok=True)
out = os.path.join(out_dir, "TOC_graphic_3.25x1.75in_300dpi.png")
fig.savefig(out, dpi=DPI, facecolor="white")
print("wrote", out)
