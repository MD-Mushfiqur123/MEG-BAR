# -*- coding: utf-8 -*-
"""Add E4 resume: skip held-out receptors already present in conditioned_results.json."""
import io

P = r'C:\Users\mushfiqur\Desktop\agent\projects\MEG-BAR\scripts\real\07_conditioned_model.py'
s = io.open(P, encoding='utf-8').read()

old = """    for held in genes:
        te = df.index[df.gene == held].values
        pool = df.index[df.gene != held].values
        if len(te) < 40 or len(pool) < 300:"""
new = """    for held in genes:
        if held in res.get('E4_leave_one_receptor_out', {}):
            print('  %-8s [resume] already complete' % held, flush=True)
            continue
        te = df.index[df.gene == held].values
        pool = df.index[df.gene != held].values
        if len(te) < 40 or len(pool) < 300:"""
assert s.count(old) == 1, 'E4 anchor'
s = s.replace(old, new)

io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('added E4 resume')
