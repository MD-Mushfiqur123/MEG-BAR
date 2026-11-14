"""Phase 6 - AlphaFold DB models for the 11 Paper 2 receptors.

Downloads AF-{ACC}-F1-model_v4.pdb (fallback v3) from AlphaFold DB, extracts
per-residue pLDDT from the B-factor column of CA atoms, and records SHA-256
checksums. Output: paper2/data/structures/afdb/afdb_models.json (+ .pdb files).

Run:  python3 paper2/scripts/06_afdb_models.py
"""

import hashlib
import json
import os
import time
import urllib.request

RECEPTORS = {
    "DRD2":   "P14416",
    "DRD3":   "P35462",
    "HTR1A":  "P08908",
    "HTR2A":  "P28223",
    "CHRM1":  "P11229",
    "ADRA2A": "P08913",
    "ADRB2":  "P07550",
    "HRH1":   "P35367",
    "GABRA1": "P14867",
    "SERT":   "P31645",
    "DAT":    "Q01959",
}

AFDB_API = "https://alphafold.ebi.ac.uk/api/prediction/{acc}"
AFDB_URL = "https://alphafold.ebi.ac.uk/files/AF-{acc}-F1-model_v{v}.pdb"


def fetch(url, tries=3):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MEG-BAR-paper2/1.0"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read()
        except Exception as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise last


def ca_plddt(pdb_bytes):
    """Per-residue pLDDT from CA atoms (B-factor column), 1-based resnum keys."""
    out = {}
    for line in pdb_bytes.decode("utf-8", errors="replace").splitlines():
        if not line.startswith("ATOM"):
            continue
        if line[12:16].strip() != "CA":
            continue
        if line[16] not in (" ", "A"):
            continue
        resnum = int(line[22:26])
        if resnum in out:
            continue
        out[resnum] = float(line[60:66])
    return out


def resolve_pdb_url(acc):
    """Resolve the current AFDB PDB URL via the API; fall back to v4/v3 URLs."""
    try:
        meta = json.loads(fetch(AFDB_API.format(acc=acc)).decode())
        entry = meta[0]
        return entry["pdbUrl"], entry
    except Exception:
        return None, None


def main():
    out_dir = os.path.join(os.path.dirname(__file__), "..", "data", "structures", "afdb")
    os.makedirs(out_dir, exist_ok=True)
    result = {
        "purpose": "Paper 2 Phase 6 - AlphaFold DB models and per-residue pLDDT",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "receptors": {},
    }
    for sym, acc in RECEPTORS.items():
        data, version, api = None, None, None
        url, api = resolve_pdb_url(acc)
        if url:
            try:
                data = fetch(url)
                version = int(url.rsplit("_v", 1)[1].split(".")[0])
            except Exception:
                data = None
        if data is None:
            for v in (4, 3):
                try:
                    data = fetch(AFDB_URL.format(acc=acc, v=v))
                    version = v
                    break
                except Exception:
                    continue
        if data is None:
            raise SystemExit(f"AFDB download failed for {sym} ({acc})")
        fname = f"AF-{acc}-F1-model_v{version}.pdb"
        with open(os.path.join(out_dir, fname), "wb") as f:
            f.write(data)
        plddt = ca_plddt(data)
        vals = sorted(plddt.values())
        mean_plddt = sum(vals) / len(vals)
        low = sum(1 for x in vals if x < 50)
        result["receptors"][sym] = {
            "uniprot": acc,
            "file": f"afdb/{fname}",
            "afdb_version": version,
            "afdb_model_created": api.get("modelCreatedDate") if api else None,
            "afdb_reported_mean_plddt": api.get("globalMetricValue") if api else None,
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
            "n_residues_with_plddt": len(plddt),
            "min_resnum": min(plddt),
            "max_resnum": max(plddt),
            "mean_plddt": round(mean_plddt, 2),
            "pct_plddt_below_50": round(100.0 * low / len(plddt), 2),
            "plddt": {str(k): plddt[k] for k in sorted(plddt)},
        }
        print(f"{sym:8} {acc}  v{version}  n={len(plddt):4}  "
              f"mean_pLDDT={mean_plddt:5.1f}  <50: {100.0*low/len(plddt):4.1f}%", flush=True)
    out = os.path.join(out_dir, "afdb_models.json")
    with open(out, "w") as f:
        json.dump(result, f, indent=1)
    print("wrote", out)


if __name__ == "__main__":
    main()
