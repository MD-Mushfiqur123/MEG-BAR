"""Minimal mmCIF parser and sequence alignment utilities (stdlib only).

Paper 2 Stage 1 helper. Deliberately avoids biopython/prody so the CI matrix
(ubuntu/macos/windows x 3.10/3.11/3.12) stays dependency-light.

Provides:
- parse_atom_site(path) -> (tags, rows) for the _atom_site loop
- polymer_sequence(rows, chain) -> one-letter sequence for a chain (model 1)
- nw_align(s1, s2) -> Needleman-Wunsch alignment as (i, j) index pairs

ANCHOR_RESIDUES holds the conserved orthosteric anchor per receptor in
UniProt numbering, derived from the DRY motif (D3.32 = DRY position - 17)
for the aminergic GPCRs and from SLC6 transporter TM1 for SERT/DAT:
DRD2 D114, DRD3 D110, HTR1A D116, HTR2A D155, CHRM1 D105, ADRA2A D128,
ADRB2 D113, HRH1 D107, SERT D98, DAT D79; GABRA1 has no anchor.
"""

AA3TO1 = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C",
    "GLN": "Q", "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I",
    "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F", "PRO": "P",
    "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
    "MSE": "M", "SEC": "U", "PYL": "O",
}

ANCHOR_RESIDUES = {
    "DRD2": (114, "D"), "DRD3": (110, "D"), "HTR1A": (116, "D"),
    "HTR2A": (155, "D"), "CHRM1": (105, "D"), "ADRA2A": (128, "D"),
    "ADRB2": (113, "D"), "HRH1": (107, "D"), "SERT": (98, "D"),
    "DAT": (79, "D"),
}

ATOM_SITE_TAGS = (
    "group_PDB", "label_atom_id", "label_comp_id", "label_alt_id",
    "label_asym_id", "label_entity_id", "auth_asym_id", "auth_seq_id",
    "Cartn_x", "Cartn_y", "Cartn_z", "type_symbol", "pdbx_PDB_model_num",
)


def _tokenize(line):
    tokens = []
    cur = ""
    quote = None
    for ch in line:
        if quote is not None:
            if ch == quote:
                quote = None
            else:
                cur += ch
        elif ch in "'\"":
            quote = ch
        elif ch.isspace():
            if cur:
                tokens.append(cur)
                cur = ""
        else:
            cur += ch
    if cur:
        tokens.append(cur)
    return tokens


def parse_atom_site(path):
    """Parse the _atom_site loop of an mmCIF file.

    Returns (tags, rows) where tags is the list of column names (without the
    _atom_site. prefix) and rows is a list of token lists. Rows whose token
    count does not match the tag count are skipped (malformed/continuation).
    """
    tags = []
    rows = []
    seen_tags = False
    collecting = False
    malformed = 0
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            s = raw.strip()
            if not s:
                continue
            if s.startswith("#"):
                if seen_tags:
                    break
                continue
            low = s.lower()
            if low.startswith("data_") or low.startswith("loop_"):
                if seen_tags:
                    break
                continue
            if s.startswith("_atom_site."):
                seen_tags = True
                collecting = True
                tags.append(s.split(".", 1)[1].split()[0])
                continue
            if s.startswith("_"):
                if collecting:
                    break
                continue
            if collecting:
                toks = _tokenize(s)
                if len(toks) == len(tags):
                    rows.append(toks)
                else:
                    malformed += 1
    return tags, rows


def _col(tags, name):
    return tags.index(name)


def atom_rows(tags, rows, model="1"):
    """Yield dicts for ATOM records of one model, as needed by Stage 1."""
    ix = {t: _col(tags, t) for t in ATOM_SITE_TAGS if t in tags}
    for r in rows:
        if r[ix["group_PDB"]] != "ATOM":
            continue
        if "pdbx_PDB_model_num" in ix and r[ix["pdbx_PDB_model_num"]] != model:
            continue
        yield {
            "atom": r[ix["label_atom_id"]],
            "comp_id": r[ix["label_comp_id"]],
            "alt_id": r[ix.get("label_alt_id", ix["label_atom_id"])] if "label_alt_id" in ix else ".",
            "label_asym": r[ix["label_asym_id"]],
            "auth_asym": r[ix["auth_asym_id"]] if "auth_asym_id" in ix else r[ix["label_asym_id"]],
            "auth_seq": r[ix["auth_seq_id"]] if "auth_seq_id" in ix else "",
            "x": float(r[ix["Cartn_x"]]),
            "y": float(r[ix["Cartn_y"]]),
            "z": float(r[ix["Cartn_z"]]),
            "element": r[ix["type_symbol"]] if "type_symbol" in ix else "",
        }


def het_rows(tags, rows, model="1"):
    """Yield dicts for HETATM records of one model."""
    ix = {t: _col(tags, t) for t in ATOM_SITE_TAGS if t in tags}
    for r in rows:
        if r[ix["group_PDB"]] != "HETATM":
            continue
        if "pdbx_PDB_model_num" in ix and r[ix["pdbx_PDB_model_num"]] != model:
            continue
        yield {
            "atom": r[ix["label_atom_id"]],
            "comp_id": r[ix["label_comp_id"]],
            "label_asym": r[ix["label_asym_id"]],
            "auth_asym": r[ix["auth_asym_id"]] if "auth_asym_id" in ix else r[ix["label_asym_id"]],
            "x": float(r[ix["Cartn_x"]]),
            "y": float(r[ix["Cartn_y"]]),
            "z": float(r[ix["Cartn_z"]]),
            "element": r[ix["type_symbol"]] if "type_symbol" in ix else "",
        }


def polymer_sequence(rows, chain, tags=None):
    """One-letter polymer sequence for a chain (model 1, first altloc).

    rows may be raw token rows (tags given) or dicts from atom_rows().
    Deduplicates by auth_seq_id, keeping first appearance order.
    """
    if tags is not None:
        rows = list(atom_rows(tags, rows))
    seen = set()
    seq = []
    for a in rows:
        if a["auth_asym"] != chain:
            continue
        aa = AA3TO1.get(a["comp_id"].upper())
        if aa is None:
            continue
        if a.get("alt_id", ".") not in (".", "?", "A"):
            continue
        key = a.get("auth_seq", str(len(seen)))
        if key in seen:
            continue
        seen.add(key)
        seq.append(aa)
    return "".join(seq)


def nw_align(s1, s2, match=1, mismatch=-1, gap=-1):
    """Global Needleman-Wunsch alignment of s1 against s2.

    Returns a list of (i, j) pairs (0-based indices into s1 and s2) for
    aligned residue pairs. Gaps are skipped in the output.
    """
    n, m = len(s1), len(s2)
    if n == 0 or m == 0:
        return []
    prev = [0] * (m + 1)
    ptr = bytearray((n + 1) * (m + 1))
    for j in range(1, m + 1):
        prev[j] = prev[j - 1] + gap
        ptr[j] = 2
    for i in range(1, n + 1):
        cur = [i * gap] + [0] * m
        base = i * (m + 1)
        ptr[base] = 1
        c1 = s1[i - 1]
        for j in range(1, m + 1):
            diag = prev[j - 1] + (match if c1 == s2[j - 1] else mismatch)
            up = prev[j] + gap
            left = cur[j - 1] + gap
            best = diag
            d = 0
            if up > best:
                best, d = up, 1
            if left > best:
                best, d = left, 2
            cur[j] = best
            ptr[base + j] = d
        prev = cur
    pairs = []
    i, j = n, m
    while i > 0 and j > 0:
        d = ptr[i * (m + 1) + j]
        if d == 0:
            pairs.append((i - 1, j - 1))
            i -= 1
            j -= 1
        elif d == 1:
            i -= 1
        else:
            j -= 1
    pairs.reverse()
    return pairs


def alignment_identity(s1, s2):
    """Fraction identity over aligned (non-gap) pairs from nw_align."""
    pairs = nw_align(s1, s2)
    if not pairs:
        return 0.0, 0
    ident = sum(1 for i, j in pairs if s1[i] == s2[j])
    return ident / len(pairs), len(pairs)
