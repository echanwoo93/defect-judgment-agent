"""Rebuild data/cases.jsonl (case texts + labels) from the official casebook PDFs.
Requires poppler's `pdftotext` on PATH. Place the PDFs as:
  data/raw/casebook_2022.pdf, data/raw/casebook_2024.pdf, data/raw/casebook_2026.pdf
Run from the repository root:  python build/build_cases.py"""
import os, shutil, subprocess, sys, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ROOT, 'build', 'work'); os.makedirs(WORK, exist_ok=True)
for y in (2022, 2024, 2026):
    pdf = os.path.join(ROOT, 'data', 'raw', f'casebook_{y}.pdf')
    if not os.path.exists(pdf): sys.exit(f'missing {pdf}')
    raw = os.path.join(WORK, f'raw{y}.txt')
    subprocess.run(['pdftotext', pdf, raw], check=True)
    txt = open(raw, encoding='utf-8', errors='ignore').read()
    open(os.path.join(WORK, f'r{y}.txt'), 'w', encoding='utf-8').write(txt)
for f in ['parse.py', 'fixes.py', 'add_pages.py', 'canon.py']:
    shutil.copy(os.path.join(ROOT, 'build', f), WORK)
shutil.copy(os.path.join(ROOT, 'data', 'kb_gongjong.json'), WORK)
os.chdir(WORK)
for f in ['parse.py', 'add_pages.py', 'canon.py']:
    subprocess.run([sys.executable, f], check=True)
shutil.copy('cases.jsonl', os.path.join(ROOT, 'data', 'cases.jsonl'))
ref = {json.loads(l)['case_id']: json.loads(l) for l in open(os.path.join(ROOT, 'data', 'labels.jsonl'), encoding='utf-8')}
new = {json.loads(l)['case_id']: json.loads(l) for l in open('cases.jsonl', encoding='utf-8')}
diff = [k for k in ref if k not in new or new[k]['label'] != ref[k]['label']]
print(f'rebuilt {len(new)} cases; label mismatches vs released labels: {len(diff)}', diff[:10])
