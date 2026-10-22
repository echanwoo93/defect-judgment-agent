import re, json, csv

# ---------- 별표4: 세부공종 -> 담보책임기간 ----------
P = {}
def add(years, names):
    for n in names: P[n] = years
add(2, ['미장공사','수장공사','도장공사','도배공사','타일공사','석공사(건물내부 공사)','석공사(건물내부공사)','옥내가구공사','주방기구공사','가전제품'])
add(3, ['공동구공사','저수조(물탱크)공사','옥외위생(정화조) 관련 공사','옥외 급수 관련 공사','옥외급수 관련 공사',
        '열원기기설비공사','공기조화기기설비공사','닥트설비공사','덕트설비공사','배관설비공사','보온공사','자동제어설비공사',
        '온돌공사','냉방설비공사','급수설비공사','온수공급설비공사','배수·통기설비공사','배수ㆍ통기설비공사','위생기구설비공사',
        '철 및 보온공사','특수설비공사','가스설비공사','가스저장시설공사','구조체 또는 바탕재공사','수장목공사',
        '창문틀 및 문짝공사','창호철물공사','창호유리공사','창호 유리공사','커튼월공사','식재공사','조경시설물공사','조경 시설물 공사',
        '관수 및 배수공사','조경포장공사','조경부대시설공사','잔디심기공사','조형물공사','배관·배선공사','배관ㆍ배선공사','피뢰침공사',
        '동력설비공사','수·변전설비공사','수·배전공사','전기기기공사','발전설비공사','승강기설비공사','인양기설비공사','조명설비공사',
        '태양열설비공사','태양광설비공사','지열설비공사','풍력설비공사','통신·신호설비공사','TV공청설비공사','감시제어설비공사',
        '가정자동화설비공사','정보통신설비공사','홈네트워크망공사','홈네트워크기기공사','단지공용시스템공사','소화설비공사',
        '제연설비공사','방재설비공사','자동화재탐지설비공사','단열공사','옥내설비공사','옥외설비공사','금속공사'])
add(5, ['토공사','석축공사','옹벽공사(토목옹벽)','배수공사','포장공사','일반철근콘크리트공사','특수콘크리트공사',
        '프리캐스트콘크리트공사','옹벽공사(건축옹벽)','콘크리트공사','일반철골공사','철골부대공사','경량철골공사',
        '일반벽돌공사','점토벽돌공사','블록공사','석공사(건물외부공사)','석공사(건물외부 공사)','지붕공사','홈통 및 우수관공사','방수공사'])
add(10, ['기초공사','지정공사'])
def norm(s): return re.sub(r'\s+','',s.replace('ㆍ','·'))
PN = {norm(k): v for k, v in P.items()}
ALIAS = {'옥외위생관련공사':'옥외위생(정화조) 관련 공사','구조용철골공사':'일반철골공사','블럭공사':'블록공사',
         '석공사/건물내부공사':'석공사(건물내부 공사)','벽체,천장및바닥의단열공사':'단열공사','벽체,천장및바닥의공사':'단열공사',
         '창호공사':'창문틀 및 문짝공사'}
def period_one(x):
    if not x: return None
    x = ALIAS.get(norm(x), x)
    if re.search(r'내력구조부|기둥|내력벽|보·바닥', x): return 10
    if norm(x) in PN: return PN[norm(x)]
    nx = re.sub(r'[()/]', '', norm(x))
    for k, v in PN.items():
        kk = re.sub(r'[()/]', '', k)
        if nx and (nx == kk or (len(nx) > 3 and (nx in kk or kk in nx))): return v
    return None
def period_of(major, sub):
    # 복합 공종: 별표1 비고에 따라 가장 긴 기간 적용
    for cand in [sub, major]:
        if not cand: continue
        whole = period_one(cand)
        if whole: return whole
        parts = [p for p in re.split(r',\s*|\s및\s(?=[^()]*$)', cand) if p.strip()]
        vals = [period_one(p.strip()) for p in parts]
        vals = [v for v in vals if v]
        if vals: return max(vals)
    return None
def _old_period_of(major, sub):
    if major and re.search(r'내력|기둥|보·바닥|보ㆍ바닥', major): return 10
    for cand in [sub, major]:
        if cand and norm(cand) in PN: return PN[norm(cand)]
    if sub:
        for k, v in PN.items():
            if norm(sub) and (norm(sub) in k or k in norm(sub)): return v
    return None

NOISE = re.compile(r'(년 하자심사 분·쟁조정 사례집|Ⅱ 하·자심사 사례 공\(종별|Ⅲ 분·쟁조정 사례 유\(형별|Ⅲ 하자심사 사례|하자심사 분쟁조정 사례집|^\||^\d{1,3}$)')
def clean(t):
    out = []
    for l in t.splitlines():
        s = l.strip().replace('\u0007', '').replace('\u200c', '')
        if len(s) <= 2: continue
        if NOISE.search(s): continue
        out.append(s)
    return out

def label(dec):
    if not dec: return None
    d1 = re.sub(r'\s+', '', dec)
    if re.search(r'하자아님으로(판단한종전|판정유지)|하자가아님으로판단한종전', d1): return '비하자'
    if re.search(r'하자로판단한종전|하자판정은유지|하자로판정유지|하자로판단한종전의판정', d1): return '하자'
    if re.search(r'기각|하자\s*아님|하자가 아닌|하자로 보지|인정하기에 부족|하자로 보기 어렵', dec):
        if re.search(r'이의신청을 기각함\(하자로 판정 유지', dec): return '하자'
        return '비하자'
    if re.search(r'하자\s*(로\s*)?판[단정]|하자로 판정 유지', dec): return '하자'
    return None
def dtype(dec):
    if not dec: return None
    for k in ['미시공하자','변경시공하자','시공하자']:
        if k in dec: return k
    return None
GOSI = '공동주택 하자의 조사, 보수비용 산정 및 하자판정기준'
OTHER = []
def _sort(a): return sorted(set(a), key=lambda x: (int(re.match(r'\d+', x).group()), x))
def cite(txt):
    """관련기준 텍스트를 법령별로 분리. 고시 조항만 반환하고, 타 법령은 OTHER 버퍼에 기록."""
    segs = re.split(r'「([^」]+)」', txt)
    ver = None; arts = []; others = []
    for k in range(1, len(segs), 2):
        law, body = segs[k], segs[k+1]
        v = re.search(r'\[시행 (\d{4}\. ?\d+\. ?\d+\.)\]', body)
        heads = re.findall(r'(?m)^제(\d+조(?:의\d+)?)\(', body)
        if not heads:
            first = body.split('\n')[0] if '(' not in body.split('\n')[0] else body[:80]
            heads = re.findall(r'제(\d+조(?:의\d+)?)', re.split(r'\n', body.strip())[0])
        if re.search(r'하자.*판정\s*기준', re.sub(r'\s+', ' ', law)):
            if v and not ver: ver = v.group(1)
            arts += heads
        elif v or heads:
            others.append(dict(law=law, version=v.group(1) if v else None, articles=_sort(heads)))
    OTHER.append(others)
    return ver, _sort(arts)

BARE = {'단열공사','방수공사','내력구조부','기둥·내력벽','보·바닥 및 지붕공사','지붕공사'}
def find_gj(L, i, pat, win=6):
    for q in range(i-1, max(0, i-win), -1):
        mm = pat.match(L[q])
        if mm and ('공사' in mm.group(1) or '구조' in mm.group(1)): return mm.group(1).strip(), mm.group(2).strip()
        if L[q] in BARE: return L[q], L[q]
    return None, None
def sec_bounds(L, names, first_anchor):
    b = []
    for i, l in enumerate(L):
        if i < first_anchor - 40: continue
        for k, v in names.items():
            if l.startswith(k): b.append((i, v))
    return b
def sec_at(b, i, default):
    s = default
    for j, v in b:
        if i > j: s = v
    return s

cases = []

# ---------- 2026 ----------
L = clean(open('r2026.txt', encoding='utf-8').read())
hdr = re.compile(r'^(\d+)년\[([^\]]+)\]\s*:\s*(.+)$')
idx = [i for i, l in enumerate(L) if hdr.match(l)]
# keep only first header of each case (headers can repeat across pages)
starts = []
for i in idx:
    nxt = L[i+1] if i+1 < len(L) else ''
    if re.match(r'^\d{2,3}\s', nxt): starts.append(i)
for n, i in enumerate(starts):
    j = starts[n+1] if n+1 < len(starts) else min(len(L), i+60)
    blk = L[i:j]
    m = hdr.match(blk[0]); yrs, major, sub = m.groups()
    title = re.sub(r'^\d{2,3}\s+', '', blk[1])
    body = '\n'.join(blk[2:])
    body = re.split(r'(분쟁조정 사례|분쟁재정 사례|부록)\n', body)[0]
    claim = re.search(r'신청이유\n(.*?)(?=관련기준)', body, re.S)
    rel = re.search(r'관련기준(.*?)(?=조사내용)', body, re.S)
    inv = re.search(r'조사내용\n(.*?)(?=판정결과)', body, re.S)
    dec = re.search(r'판정결과\n?(.*?)(?:\sl\s*$|\sl\n|$)', body, re.S)
    rel_t = rel.group(1) if rel else ''
    ver, arts = cite(rel_t)
    d = dec.group(1).strip().strip('l').strip() if dec else ''
    _o = OTHER[-1] if OTHER else []
    cases.append(dict(other_citations=_o, edition=2026, section='하자심사', major=major.strip(), sub=sub.strip(), title=title,
        claim=claim.group(1).strip() if claim else '', investigation=inv.group(1).strip() if inv else '',
        decision=d[:600], cited_version=ver, cited_articles=arts,
        period_gold=int(yrs), period_bylaw=period_of(major, sub)))

# ---------- 2024 ----------
L = clean(open('r2024.txt', encoding='utf-8').read())
gj = re.compile(r'^(.+?공사|내력구조부|.+?설비공사)\s*\((.+)\)$')
b24 = sec_bounds(L, {'Ⅲ. 분쟁조정 사례':'분쟁조정','Ⅳ. 재심의 사례':'재심의'}, 150)
anchors = [i for i, l in enumerate(L) if (l == '【당사자 주장】' and sec_at(b24, i, '하자심사') != '재심의') or l == '【원심 사건 개요】']
for n, i in enumerate(anchors):
    j = anchors[n+1] if n+1 < len(anchors) else len(L)
    # title = nearest previous line that is not a header/section line
    k = i-1
    while k > 0 and (gj.match(L[k]) or re.search(r'사례|^\d\.|공사$|^Ⅰ|^Ⅱ|^Ⅲ|^Ⅳ', L[k])): k -= 1
    title = L[k]
    major, sub = find_gj(L, i, gj, 8)
    blkL = L[i:j]
    # cut off trailing header lines that belong to next case
    while blkL and (gj.match(blkL[-1]) or blkL[-1] == title): blkL.pop()
    blk = '\n'.join(blkL)
    section = sec_at(b24, i, '하자심사')
    claim = re.search(r'(?:【당사자 주장】|당사자 주장)\n(.*?)(?=【조사내용】|○ 관계법규|관계법규|○ 설계도서|【)', blk, re.S)
    inv = re.search(r'【조사내용】\n(.*?)(?=【현장사진】|【관련사진】|【판정결과】|【조정결정사항】)', blk, re.S)
    inv_t = inv.group(1) if inv else blk
    ver, arts = cite(inv_t if section != '재심의' else blk)
    # remove 관련기준 statute text from investigation input
    inv_clean = re.sub(r'○\s*관련기준.*?(?=○\s*(시공상태|설계도서|증거자료)|$)', '', inv_t, flags=re.S)
    dec = re.search(r'(?:【판정결과】|【재심의 결과[】\]]|【조정결정사항】)\n(.*)', blk, re.S)
    d = dec.group(1).strip() if dec else ''
    _o = OTHER[-1] if OTHER else []
    cases.append(dict(other_citations=_o, edition=2024, section=section, major=major, sub=sub, title=title,
        claim=claim.group(1).strip() if claim else '', investigation=inv_clean.strip(),
        decision=d[:600], cited_version=ver, cited_articles=arts,
        period_gold=None, period_bylaw=period_of(major, sub)))

# ---------- 2022 ----------
L = clean(open('r2022.txt', encoding='utf-8').read())
gj2 = re.compile(r'^(?:\d+\s+)?(.+?)\s*\((.+)\)$')
anchors = [i for i, l in enumerate(L) if l.startswith('하자내용 |')]
b22 = sec_bounds(L, {'Ⅲ. 분쟁조정 사례':'분쟁조정','Ⅳ. 재심의 사례':'재심의','Ⅴ. 판례':'판례'}, anchors[0])
anchors = [i for i in anchors if sec_at(b22, i, '하자심사') != '판례']
sec_marks = {'Ⅲ. 분쟁조정 사례': '분쟁조정', 'Ⅳ. 재심의 사례': '재심의'}
for n, i in enumerate(anchors):
    j = anchors[n+1] if n+1 < len(anchors) else len(L)
    title = L[i].split('|', 1)[1].strip()
    major, sub = find_gj(L, i, gj2, 4)
    section = sec_at(b22, i, '하자심사')
    blkL = L[i+1:j]
    while blkL and (gj2.match(blkL[-1]) and '공사' in blkL[-1]): blkL.pop()
    blk = '\n'.join(blkL)
    claim = re.search(r'당사자 주장\n(.*?)(?=조사내용)', blk, re.S)
    inv = re.search(r'조사내용[^\n]*\n(.*?)(?=현장사진|판정결과|조정결정사항)', blk, re.S)
    dec = re.search(r'(?:판정결과|조정결정사항)\n(.*)', blk, re.S)
    ver, arts = cite(blk)
    d = dec.group(1).strip() if dec else ''
    d = re.split(r'\n(?:하자보수청구|하자보수청구 및 손해배상청구|하자보수에 갈음하는 손해배상청구(?:청구)?|하자보수보증금 청구|설계법규 위반|설계도서 상이|결로|누수|기능불량|마감재 상이|Ⅳ\..*|Ⅴ\..*|Ⅳ 재·심의 사례 유\(형별)\s*(?:\n|$)', d)[0]
    d = re.sub(r'\n(?:현장사진|시공상태|설계도서|[가-힣·]+공사|내력구조부|기둥·내력벽)\s*$', '', d.strip())
    _o = OTHER[-1] if OTHER else []
    cases.append(dict(other_citations=_o, edition=2022, section=section, major=major, sub=sub, title=title,
        claim=claim.group(1).strip() if claim else '', investigation=(inv.group(1).strip() if inv else ''),
        decision=d[:600], cited_version=ver, cited_articles=arts,
        period_gold=None, period_bylaw=period_of(major, sub)))

for c in cases:
    c['label'] = label(c['decision']) if c['section'] in ('하자심사', '재심의') else None
    c['defect_type'] = dtype(c['decision']) if c['label'] == '하자' else None
    c['investigation'] = re.sub(r'(현장실사 결과|검토 결과)', r'\1', c['investigation'])
    c['has_gold_citation'] = bool(c['cited_articles'])

seq = {}
for c in cases:
    k = (c['edition'], c['section']); seq[k] = seq.get(k, 0) + 1
    c['case_id'] = f"{c['edition']}-{ {'하자심사':'J','재심의':'R','분쟁조정':'M'}[c['section']] }{seq[k]:03d}"

cols = ['case_id','edition','section','major','sub','title','claim','investigation','decision','label','defect_type',
        'cited_version','cited_articles','has_gold_citation','period_gold','period_bylaw']
with open('cases.jsonl', 'w', encoding='utf-8') as f:
    for c in cases: f.write(json.dumps({k: c[k] for k in cols}, ensure_ascii=False) + '\n')
with open('cases.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
    for c in cases:
        r = {k: c[k] for k in cols}; r['cited_articles'] = ';'.join(r['cited_articles']); w.writerow(r)
print(len(cases))

# ---------- post-processing: manual fixes, 공종 extraction & leakage masking ----------
exec(open('fixes.py', encoding='utf-8').read())
LEAK = re.compile(r'((?:신청\s*부위|해당\s*사건)의\s*(?:해당\s*)?공종은\s*)(.+?)(?:\(하자담보책임기간\s*\d+년\))?\s*(?:으로서|로서|으로|로)(?=[\s,])\s*,?\s*')
for c in cases:
    if c['case_id'] in FIX: c.update(FIX[c['case_id']])
    m = LEAK.search(c['investigation'])
    if m:
        stated = m.group(2).strip()
        c['stated_gongjong'] = stated
        if not c['sub']: c['sub'] = stated
        if period_of(c['major'], c['sub']) is None and period_of(None, stated): c['sub'] = stated
        c['investigation'] = LEAK.sub('', c['investigation'])
    else:
        c['stated_gongjong'] = None
    c['investigation'] = re.sub(r'\(하자담보책임기간\s*\d+년\)', '', c['investigation'])
    c['period_bylaw'] = period_of(c['major'], c['sub'])
    c['label'] = label(c['decision']) if c['section'] in ('하자심사', '재심의') else None
    c['defect_type'] = dtype(c['decision']) if c['label'] == '하자' else None
    c['short_form'] = c['case_id'] in SHORT
cols2 = cols + ['other_citations', 'stated_gongjong', 'short_form']
with open('cases.jsonl', 'w', encoding='utf-8') as f:
    for c in cases: f.write(json.dumps({k: c[k] for k in cols2}, ensure_ascii=False) + '\n')
with open('cases.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=cols2); w.writeheader()
    for c in cases:
        r = {k: c[k] for k in cols2}; r['cited_articles'] = ';'.join(r['cited_articles']); r['other_citations'] = '; '.join(f"{o['law']} {','.join(o['articles'])}" for o in r['other_citations']); w.writerow(r)

# ---------- 2차 정리: 판정 누출 제거 ----------
DEC_SENT = re.compile(r'[“"][^”"]{2,80}[”"]\s*(?:건은|건에 대하여)[^。]*?(?:판단함|판정함|기각함)\.?', re.S)
def _title_from_decision(dec):
    m = re.search(r'[“"]([^”"]{2,80})[”"]\s*(?:건은|건에 대하여)', dec or '')
    return m.group(1).strip() if m else None
for c in cases:
    if re.search(r'판단함|판정함', c['title']):
        t = _title_from_decision(c['decision'])
        if t: c['title'] = t
    inv = c['investigation']
    if c['edition'] == 2024 and c['section'] == '재심의':
        inv = re.split(r'【현장사진】|【원심 판정 결과】', inv)[0]
    inv = DEC_SENT.sub('', inv)
    inv = re.sub(r'(?:관계법규|관련법규|관련기준)\s*[:：]?\s*.*?(?=(?:설계도서|시공상태|참고자료|현장실사)\s*[:：]?|$)', '', inv, flags=re.S)
    c['investigation'] = inv.strip()
with open('cases.jsonl', 'w', encoding='utf-8') as f:
    for c in cases: f.write(json.dumps({k: c[k] for k in cols2}, ensure_ascii=False) + '\n')
