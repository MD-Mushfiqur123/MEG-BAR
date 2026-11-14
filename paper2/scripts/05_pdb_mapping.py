"""Phase 5 - PDB mapping: find reference structures for the 11 Paper 2 receptors.

Queries the RCSB search API by UniProt accession, then fetches entry metadata
in a single GraphQL call per entry (method, resolution, ligands, organism,
UniProt accessions), ranks candidates, and writes
paper2/data/structures/pdb_selection.json.

Ranking: (1) has a non-solvent co-crystallized ligand, (2) resolution,
(3) Homo sapiens source, (4) preferred method (X-ray / cryo-EM).

Run:  python3 paper2/scripts/05_pdb_mapping.py
"""

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

SOLVENT_AND_COMMON = {
    "HOH", "DOD", "SO4", "PO4", "CL", "NA", "K", "MG", "CA", "ZN", "MN",
    "GOL", "EDO", "PEG", "PGE", "PG4", "1PE", "MES", "ACT", "ACS", "EPE",
    "TRS", "DMS", "MPD", "FLC", "BME", "DTT", "TCE", "IPA", "ETOH", "ACE",
    "NH4", "CD", "CO", "NI", "CU", "BR", "IOD", "SCN", "NO3", "CIT", "FLC",
}

SEARCH_URL = "https://search.rcsb.org/rcsbsearch/v2/query"
GRAPHQL_URL = "https://data.rcsb.org/graphql"
ROWS = 40
MAX_ENTRIES = 10
ENOUGH_LIGAND_BOUND = 5

GQL = """
query($id: String!) {
  entry(entry_id: $id) {
    rcsb_entry_info { experimental_method resolution_combined nonpolymer_entity_count }
    struct { title }
    polymer_entities {
      rcsb_id
      rcsb_entity_source_organism { ncbi_scientific_name }
      rcsb_polymer_entity_container_identifiers {
        reference_sequence_identifiers { database_name database_accession }
      }
    }
    nonpolymer_entities { pdbx_entity_nonpoly { comp_id name } }
  }
}
"""


def post_json(url, payload, tries=2):
    last = None
    for attempt in range(tries):
        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                url, data=data, method="POST",
                headers={"User-Agent": "MEG-BAR-paper2/1.0",
                         "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise last


def search_entries(accession):
    q = {
        "query": {
            "type": "terminal",
            "service": "text",
            "parameters": {
                "attribute": "rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_accession",
                "operator": "exact_match",
                "value": accession,
            },
        },
        "request_options": {
            "paginate": {"start": 0, "rows": ROWS},
            "results_content_type": ["experimental"],
        },
        "return_type": "polymer_entity",
    }
    try:
        res = post_json(SEARCH_URL, q)
    except Exception:
        return []
    return [r["identifier"] for r in res.get("result_set", [])]


def entry_via_graphql(pdb_id):
    d = post_json(GRAPHQL_URL, {"query": GQL, "variables": {"id": pdb_id}})
    e = (d.get("data") or {}).get("entry")
    if not e:
        return None
    info = e.get("rcsb_entry_info") or {}
    res_list = info.get("resolution_combined") or [None]
    ligands = []
    for np_e in e.get("nonpolymer_entities") or []:
        cc = np_e.get("pdbx_entity_nonpoly") or {}
        comp = (cc.get("comp_id") or "?").upper()
        if comp not in SOLVENT_AND_COMMON:
            ligands.append({"comp_id": comp, "name": cc.get("name", "")})
    organisms, accs = [], []
    for pe in e.get("polymer_entities") or []:
        for o in pe.get("rcsb_entity_source_organism") or []:
            organisms.append(o.get("ncbi_scientific_name", ""))
        for ref in (pe.get("rcsb_polymer_entity_container_identifiers") or {}
                    ).get("reference_sequence_identifiers") or []:
            if ref.get("database_name") == "UniProt":
                accs.append(ref.get("database_accession"))
    return {
        "pdb_id": pdb_id,
        "method": (info.get("experimental_method") or "?").lower(),
        "resolution": res_list[0],
        "title": (e.get("struct") or {}).get("title", ""),
        "ligands": ligands,
        "organisms": sorted(set(organisms)),
        "uniprot_accessions": sorted(set(a for a in accs if a)),
    }


def rank(cands):
    def key(c):
        has_lig = 1 if c["ligands"] else 0
        res = c["resolution"] if c["resolution"] is not None else 99.0
        human = 1 if any("Homo sapiens" in o for o in c["organisms"]) else 0
        method_pref = 0 if "x-ray" in c["method"] else (
            1 if "cryo" in c["method"] or "electron" in c["method"] else 2)
        return (-has_lig, res, -human, method_pref)
    return sorted(cands, key=key)


def main():
    out_dir = os.path.join(os.path.dirname(__file__), "..", "data", "structures")
    os.makedirs(out_dir, exist_ok=True)
    result = {
        "purpose": "Paper 2 Phase 5 - reference structure selection for 11 receptors",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ranking": "ligand-bound > resolution > Homo sapiens > X-ray/cryo-EM",
        "receptors": {},
    }
    for sym, acc in RECEPTORS.items():
        ids = search_entries(acc)
        entries = []
        for ident in ids:
            pdb_id = ident.split("_")[0]
            if pdb_id not in entries:
                entries.append(pdb_id)
        cands, lig_bound = [], 0
        for pdb_id in entries:
            if lig_bound >= ENOUGH_LIGAND_BOUND and len(cands) >= ENOUGH_LIGAND_BOUND:
                break
            if len(cands) >= MAX_ENTRIES:
                break
            try:
                c = entry_via_graphql(pdb_id)
            except Exception:
                continue
            if not c:
                continue
            if acc not in c["uniprot_accessions"]:
                continue
            cands.append(c)
            if c["ligands"]:
                lig_bound += 1
            time.sleep(0.1)
        ranked = rank(cands)
        result["receptors"][sym] = {
            "uniprot": acc,
            "n_candidates_found": len(cands),
            "primary": ranked[0] if ranked else None,
            "fallback": ranked[1] if len(ranked) > 1 else None,
            "top5": ranked[:5],
        }
        p = ranked[0] if ranked else {}
        print(f"{sym:8} {acc}  cands={len(cands):3}  "
              f"primary={p.get('pdb_id', '--')}  res={p.get('resolution')}  "
              f"lig={[l['comp_id'] for l in p.get('ligands', [])][:3]}", flush=True)
    out = os.path.join(out_dir, "pdb_selection.json")
    with open(out, "w") as f:
        json.dump(result, f, indent=1)
    print("wrote", out)


if __name__ == "__main__":
    main()
