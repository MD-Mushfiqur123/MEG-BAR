# Mentorship Outreach Email — Draft

**Purpose:** ask a computational-chemistry or ML-in-drug-discovery researcher to
read the MEG-BAR manuscript and give feedback. For an independent young
researcher this is the single highest-leverage action in the publication plan.

**Who to send to:** authors of recent papers on (a) evaluation pitfalls in
ML for drug discovery, (b) molecular benchmark design / scaffold splits,
(c) foundation models for proteins. One email at a time, personalised to each
recipient's own work — see the customisation slot below.

---

**Subject:** Feedback request: controlled negative result on expert routing for cross-family affinity prediction (56,637 measured ChEMBL records)

Dear Professor [Name],

I am an independent researcher working on machine learning for drug
discovery. I am writing to ask whether you would be willing to read a draft
manuscript and share your critique — I have no formal advisor, and an expert
review at this stage would meaningfully improve the work.

The manuscript, **MEG-BAR**, is a controlled measurement study of a proposal
that circulates in the protein-foundation-model literature: grafting sparse
mixture-of-experts onto ESM-2 with contrastive router re-anchoring to obtain
modular drug–receptor affinity prediction. Earlier preprints in this line
reported large accuracy margins from simulation. I rebuilt the entire pipeline
on measured data:

- 56,637 measured Ki/IC50/Kd records (ChEMBL) for eleven human
  neurotransmitter receptors, reduced to 41,271 unique receptor–ligand pairs;
- Bemis–Murcko scaffold-disjoint and temporal (pre-2015 train / 2015+ test)
  splits, five seeds, paired statistics;
- three controls: gate-entropy analysis, a wrong-pocket control, and a Ridge
  regression baseline on Morgan fingerprints alone.

The result is negative and, I believe, useful: the trained router stays
near-uniform, cross-attention receptor conditioning never significantly
outperforms a shared model, the wrong-pocket control matches it, and the
fingerprint baseline is competitive throughout (r = 0.39–0.83) — including on
a low-resource receptor where the deep models collapse to r ≈ 0.01. The
manuscript retains the earlier simulation-only material as a clearly labelled
design study and catalogues every withdrawn claim in a defect register. All
scripts, frozen artefacts, and raw ChEMBL fetches are public:
https://github.com/MD-Mushfiqur123/MEG-BAR

I would be grateful for 15–30 minutes of your time: a short reading of the
methods and a frank assessment of (1) whether the evaluation design is sound,
(2) which venue you would consider appropriate for a result of this shape, and
(3) what a referee would attack first. I am of course happy to share the full
PDF, the artefacts, or anything else that makes the review easier.

Thank you for your consideration.

Sincerely,
Md Mushfiqur Rahim
Independent Researcher, Bogura, Bangladesh
ORCID: 0009-0003-1021-685X
GitHub: https://github.com/MD-Mushfiqur123
Email: 20mahin2020@gmail.com

---

## Customisation slot (fill in per recipient)

- **[Name]**
- **Connection to their work:** one or two sentences citing a specific paper
  of theirs and how it relates (e.g. their benchmark/split methodology, their
  work on molecular representations, or their critique papers).
- **Why them, specifically:** e.g. "your group's work on scaffold-disjoint
  evaluation directly motivates the split design in §6".

## Sending rules

1. One recipient per email; never mass-send.
2. Send the PDF only on request, or attach a link to the public repo.
3. If no reply in 10–14 days, send exactly one polite follow-up.
4. Keep the tone factual; do not oversell — the paper's own discipline is
   "no sentence a measurement does not support".
