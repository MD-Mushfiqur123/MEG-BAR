# -*- coding: utf-8 -*-
"""Fix: POCKET/PMASK are per-gene arrays; index them via PIDX."""
import io

P = r'C:\Users\mushfiqur\Desktop\agent\projects\MEG-BAR\scripts\real\07_conditioned_model.py'
s = io.open(P, encoding='utf-8').read()

old_sig = "def train_eval(model, tr, va, te, FP, CONST, POCKET, PMASK, y, verbose=False):"
new_sig = "def train_eval(model, tr, va, te, FP, CONST, POCKET, PMASK, y, PIDX, verbose=False):"
assert s.count(old_sig) == 1
s = s.replace(old_sig, new_sig)

old_pack = """    def pack(idx):
        return (torch.tensor(FP[idx]), torch.tensor(CONST[idx]),
                torch.tensor(POCKET[idx]), torch.tensor(PMASK[idx]),
                torch.tensor(y[idx], dtype=torch.float32))"""
new_pack = """    def pack(idx):
        g = PIDX[idx]
        return (torch.tensor(FP[idx]), torch.tensor(CONST[idx]),
                torch.tensor(POCKET[g]), torch.tensor(PMASK[g]),
                torch.tensor(y[idx], dtype=torch.float32))"""
assert s.count(old_pack) == 1
s = s.replace(old_pack, new_pack)

a = "train_eval(m, tr_g, va_g, te_g, FP, CONST, POCKET, PMASK, y)"
assert s.count(a) == 1
s = s.replace(a, "train_eval(m, tr_g, va_g, te_g, FP, CONST, POCKET, PMASK, y, PIDX)")

b = "train_eval(m, tr, va, te, FP, CONST, POCKET, PMASK, y)"
assert s.count(b) == 1
s = s.replace(b, "train_eval(m, tr, va, te, FP, CONST, POCKET, PMASK, y, PIDX)")

io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('patched PIDX indexing')
