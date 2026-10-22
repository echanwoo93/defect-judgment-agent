import json, glob, os, re, random, csv
from collections import defaultdict, Counter
from scipy.stats import binomtest

AG = 'data'
GOLD = {}
for f in ['labels.jsonl', 'contrast.jsonl']:
    for l in open(os.path.join(AG, f), encoding='utf-8'):
        c = json.loads(l); GOLD[c['case_id']] = c
GENERAL = {"1", "2", "3", "4", "5", "6", "6의2", "127", "128"}

def akey(x):
    m = re.search(r"(\d+)\s*조(?:\s*의\s*(\d+))?", str(x))
    return None if not m else (m.group(1) + (f"의{m.group(2)}" if m.group(2) else ""))
def ng(x): return re.sub(r"\s+", "", str(x))

def score(r):
    g = GOLD[r['case_id']]; p = r['pred']; s = {}
    ok = not (p.get('_error') or p.get('_parse_error'))
    s['label'] = int(ok and p.get('label') == g['label'])
    gp = g.get('period_gold') or g.get('period_taxonomy')
    if gp:
        try: s['period'] = int(ok and int(p.get('warranty_years')) == gp)
        except Exception: s['period'] = 0
    gg = {ng(x) for x in g.get('gongjong_canonical') or []}
    if gg:
        pg = [ng(x) for x in (p.get('gongjong') or [])] if ok else []
        s['gj_top1'] = int(bool(pg) and pg[0] in gg); s['gj_any'] = int(bool(gg & set(pg)))
    if g.get('has_gold_citation') and not g.get('short_form'):
        gs = {akey(x) for x in g['cited_articles']} - GENERAL
        if gs:
            ps = ({akey(x) for x in p.get('cited_articles') or []} - {None} - GENERAL) if ok else set()
            tp = len(gs & ps); fp = len(ps - gs); fn = len(gs - ps)
            s['cit'] = (tp, fp, fn)
    if g.get('near_threshold'): s['near'] = s['label']
    return s

def load(name):
    p = f'results/{name}.jsonl'
    if not os.path.exists(p): return None
    R = {}
    for l in open(p, encoding='utf-8'):
        r = json.loads(l)
        g = GOLD[r['case_id']]
        if g['edition'] in (2026, 0): R[r['case_id']] = score(r)
    return R

def f1(items):
    tp = sum(i[0] for i in items); fp = sum(i[1] for i in items); fn = sum(i[2] for i in items)
    P = tp / (tp + fp) if tp + fp else 0; Rr = tp / (tp + fn) if tp + fn else 0
    return 2 * P * Rr / (P + Rr) if P + Rr else 0

def metric(R, m, ids=None):
    ids = ids or [k for k in R if m in R[k]]
    vals = [R[k][m] for k in ids if m in R[k]]
    if not vals: return None, ids
    return (f1(vals) if m == 'cit' else sum(vals) / len(vals)), ids

def boot_ci(R, m, B=2000, seed=0):
    rnd = random.Random(seed); ids = [k for k in R if m in R[k]]
    vals = []
    for _ in range(B):
        s = [rnd.choice(ids) for _ in ids]
        vals.append(f1([R[k][m] for k in s]) if m == 'cit' else sum(R[k][m] for k in s) / len(s))
    vals.sort(); return vals[int(.025 * B)], vals[int(.975 * B)]

def mcnemar(A, Bm, m):
    ids = [k for k in A if m in A[k] and k in Bm and m in Bm[k]]
    b = sum(1 for k in ids if A[k][m] == 1 and Bm[k][m] == 0)
    c = sum(1 for k in ids if A[k][m] == 0 and Bm[k][m] == 1)
    p = binomtest(b, b + c, 0.5).pvalue if b + c else 1.0
    return b, c, p

def paired_boot_f1(A, Bm, B=2000, seed=0):
    rnd = random.Random(seed); ids = [k for k in A if 'cit' in A[k] and k in Bm]
    d0 = f1([A[k]['cit'] for k in ids]) - f1([Bm[k]['cit'] for k in ids]); cnt = 0
    for _ in range(B):
        s = [rnd.choice(ids) for _ in ids]
        if f1([A[k]['cit'] for k in s]) - f1([Bm[k]['cit'] for k in s]) <= 0: cnt += 1
    return d0, cnt / B

def is_contrast(k): return GOLD[k]['edition'] == 0
def split(R, contrast):
    return {k: v for k, v in R.items() if is_contrast(k) == contrast} if R else None

rows = []
for prov in ['gpt', 'claude']:
    for cond in ['direct', 'rag', 'agent', 'agent_notool', 'agent_norule', 'agent_noversion', 'rag_noversion', 'agent_noguard']:
        Rt = load(f'{prov}_{cond}'); Rc = load(f'{prov}_{cond}_contrast')
        T = split(Rt, False) if Rt else None; Cc = split(Rc, True) if Rc else None
        row = dict(model=prov, condition=cond)
        for nm, R, m in [('period', T, 'period'), ('cit_F1', T, 'cit'), ('label_real', T, 'label'), ('gj_top1', T, 'gj_top1'),
                         ('label_contrast', Cc, 'label'), ('near_contrast', Cc, 'near')]:
            if R:
                v, _ = metric(R, m)
                lo, hi = boot_ci(R, m)
                row[nm] = f"{v:.3f} [{lo:.2f}, {hi:.2f}]"
        rows.append(row)
with open('table_main.csv', 'w', encoding='utf-8-sig', newline='') as f:
    keys = ['model', 'condition', 'period', 'cit_F1', 'label_real', 'gj_top1', 'label_contrast', 'near_contrast']
    w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
    for r in rows: w.writerow({k: r.get(k, '') for k in keys})

tests = []
for prov in ['gpt', 'claude']:
    def L(c, con=False):
        R = load(f'{prov}_{c}' + ('_contrast' if con else '')); return split(R, con) if R else None
    ag, agc = L('agent'), L('agent', True)
    for other in ['direct', 'rag', 'agent_notool']:
        o = L(other)
        if o: b, c, p = mcnemar(ag, o, 'period'); tests.append((prov, 'period (2026)', f'agent vs {other}', b, c, p))
    for other in ['direct', 'rag', 'agent_norule']:
        o = L(other, True)
        if o:
            for m in ['label', 'near']:
                b, c, p = mcnemar(agc, o, m); tests.append((prov, f'{m} (contrast)', f'agent vs {other}', b, c, p))
    for other in ['direct', 'rag']:
        o = L(other)
        d, p = paired_boot_f1(ag, o); tests.append((prov, 'citation F1 (2026)', f'agent vs {other}', f'ΔF1={d:+.3f}', '', p))
with open('tests.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f); w.writerow(['model', 'metric', 'comparison', 'agent_only_correct(b)', 'other_only_correct(c)', 'p_value'])
    for t in tests: w.writerow(t)
for r in rows: print(r)
print()
for t in tests: print(t[0], t[1], t[2], t[3], t[4], f"p={t[5]:.4f}" if isinstance(t[5], float) else t[5])
