# -*- coding: utf-8 -*-
"""Wire the wrong-pocket ablation into run_block (it was built but never selected)."""
import io

P = r'C:\Users\mushfiqur\Desktop\agent\projects\MEG-BAR\scripts\real\08_robust_eval.py'
s = io.open(P, encoding='utf-8').read()

old = """def run_block(label, tr, va, te, FP, POCKET_T, PMASK_T, PIDX, y, store):
    \"\"\"Run every architecture x seed for one split; flush after each seed.\"\"\"
    cache = store.setdefault(label, {})
    for arch in ARCHS:"""
new = """def run_block(label, tr, va, te, FP, POCKET_T, PMASK_T, PIDX, y, store,
              WRONG_T=None, WRONG_M=None):
    \"\"\"Run every architecture x seed for one split; flush after each seed.\"\"\"
    cache = store.setdefault(label, {})
    for arch in ARCHS:
        # the wrong-pocket ablation uses identical parameters but a mismatched receptor pocket
        if arch == 'crossattn_wrongpocket' and WRONG_T is not None:
            use_pk, use_pm = WRONG_T, WRONG_M
        else:
            use_pk, use_pm = POCKET_T, PMASK_T"""
assert s.count(old) == 1
s = s.replace(old, new)

old2 = "            pred, eps = train_eval(arch, tr, va, te, FP, POCKET_T, PMASK_T, PIDX, y, sd)"
new2 = "            pred, eps = train_eval(arch, tr, va, te, FP, use_pk, use_pm, PIDX, y, sd)"
assert s.count(old2) == 1
s = s.replace(old2, new2)

old3 = "        run_block('E3|' + g, tr, va, te, FP, PK_T, PM_T, PIDX, y, store)"
new3 = "        run_block('E3|' + g, tr, va, te, FP, PK_T, PM_T, PIDX, y, store, WK_T, WM_T)"
assert s.count(old3) == 1
s = s.replace(old3, new3)

old4 = "        run_block('E4|' + held, tr, va, te, FP, PK_T, PM_T, PIDX, y, store)"
new4 = "        run_block('E4|' + held, tr, va, te, FP, PK_T, PM_T, PIDX, y, store, WK_T, WM_T)"
assert s.count(old4) == 1
s = s.replace(old4, new4)

io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('wrong-pocket ablation wired')
