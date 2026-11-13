# -*- coding: utf-8 -*-
"""Fix build(): const context is 1280-d, pocket context is PCA-reduced 128-d."""
import io

P = r'C:\Users\mushfiqur\Desktop\agent\projects\MEG-BAR\scripts\real\07_conditioned_model.py'
s = io.open(P, encoding='utf-8').read()

old = """def build(arch, d_fp, d_res):
    if arch == 'shared':
        return SharedMLP(d_fp)
    if arch == 'const_ctx':
        return ConstCtxMLP(d_fp, d_res)
    return CrossAttentionConditioned(d_fp, d_res)"""
new = """def build(arch, d_fp, d_const, d_pocket):
    if arch == 'shared':
        return SharedMLP(d_fp)
    if arch == 'const_ctx':
        return ConstCtxMLP(d_fp, d_const)
    return CrossAttentionConditioned(d_fp, d_pocket)"""
assert s.count(old) == 1
s = s.replace(old, new)

# call sites
s = s.replace("    d_pocket = POCKET_NP.shape[2]",
              "    d_pocket = POCKET_NP.shape[2]\n    d_const = CONST.shape[1]")

a = "                m = build(arch, FP_BITS, d_pocket)"
assert s.count(a) == 1
s = s.replace(a, "                m = build(arch, FP_BITS, d_const, d_pocket)")

b = "            m = build(arch, FP_BITS, d_pocket)"
assert s.count(b) == 1
s = s.replace(b, "            m = build(arch, FP_BITS, d_const, d_pocket)")

# rng use in train_eval: make deterministic per-epoch without accumulating cost
s = s.replace("        perm = np.random.default_rng(SEED + ep).permutation(n)",
              "        perm = np.random.default_rng(SEED + ep).permutation(n)")

io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('patched build() dims')
