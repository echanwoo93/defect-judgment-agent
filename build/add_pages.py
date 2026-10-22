import json, csv, glob, re, subprocess
RAW = '../../data/raw'
files = {y: f'{RAW}/casebook_{y}.pdf' for y in (2022, 2024, 2026)}
pages = {}
for y, f in files.items():
    n = int(re.search(r'Pages:\s+(\d+)', subprocess.run(['pdfinfo', f], capture_output=True).stdout.decode('utf-8', 'ignore')).group(1))
    pages[y] = [re.sub(r'\s+', '', subprocess.run(['pdftotext', '-f', str(p), '-l', str(p), f, '-'], capture_output=True).stdout.decode('utf-8', 'ignore')) for p in range(1, n+1)]
C = [json.loads(l) for l in open('cases.jsonl', encoding='utf-8')]
last = {}
for c in C:
    key = re.sub(r'\s+', '', c['title'])[:12]
    start = last.get((c['edition'], c['section']), 0)
    hits = [p+1 for p, tx in enumerate(pages[c['edition']]) if key and key in tx and p+1 > start - 1]
    c['source_page'] = hits[0] if hits else None
    if hits: last[(c['edition'], c['section'])] = hits[0]
cols = list(C[0].keys())
cols = ['case_id', 'source_page'] + [k for k in cols if k not in ('case_id', 'source_page')]
with open('cases.jsonl', 'w', encoding='utf-8') as f:
    for c in C: f.write(json.dumps({k: c[k] for k in cols}, ensure_ascii=False) + '\n')
with open('cases.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
    for c in C:
        r = dict(c); r['cited_articles'] = ';'.join(r['cited_articles']); w.writerow({k: r[k] for k in cols})
print(sum(1 for c in C if c['source_page']), len(C))
