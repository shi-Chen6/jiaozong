# -*- coding: utf-8 -*-
import io, sys, json
sys.path.insert(0, 'tools')
from parse import build

md = sys.argv[1]
for c in build(md):
    print(f"\n### {c['title']}  ({len(c['qs'])}题)")
    for q in c['qs']:
        o = ' '.join(f"{k}.{v}" for k, v in q['o'].items())
        print(f"{q['n']:>2} [{q['t'][:2]}] {q['s']}")
        if o: print(f"     {o}")
        print(f"     答案={q['a']}  tag={q.get('tag','')}")
