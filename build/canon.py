import json, csv, re
K = json.load(open('kb_gongjong.json', encoding='utf-8'))['taxonomy']
BY = {re.sub(r'\s+', '', k['sub']): k for k in K}
MAP = {'·공기조화기기설비공사': ['공기조화기기설비공사'], '구조용 철골공사': ['일반철골공사'], '기둥·내력벽': ['내력구조부'],
 '보·바닥 및 지붕공사': ['내력구조부'], '내력구조부(보·바닥 및 지붕), 온돌공사, 급수설비공사': ['내력구조부', '온돌공사(세대매립배관 포함)', '급수설비공사'],
 '벽체, 천장 및 바닥의 공사': ['단열공사'], '벽체, 천장 및 바닥의 단열공사': ['단열공사'], '블럭공사': ['블록공사'],
 '석공사/건물내부공사': ['석공사(건물내부 공사)'], '옥외설비공사(담장,울타리,안내시설물 등)': ['옥외설비공사'], '옥외위생관련공사': ['옥외위생(정화조) 관련 공사'],
 '온돌공사': ['온돌공사(세대매립배관 포함)'], '지하저수조(물탱크)공사': ['저수조(물탱크)공사'],
 '창문틀 및 문짝공사, 도배공사 및 방수공사': ['창문틀 및 문짝공사', '도배공사', '방수공사'], '타일공사(방수공사)': ['타일공사'],
 '포장공사 및 배수공사': ['포장공사', '배수공사'], '석공사(건물외부 공사)': ['석공사(건물외부공사)']}
def canon(major, sub):
    if not sub: return []
    if sub in MAP: return MAP[sub]
    if sub == '옹벽공사': return ['옹벽공사(건축옹벽)'] if major and '철근' in major else ['옹벽공사(토목옹벽)']
    if sub == '포장공사' and major and '조경' in major: return ['조경포장공사']
    if sub == '배수공사' and major and '조경' in major: return ['관수 및 배수공사']
    return [sub] if re.sub(r'\s+', '', sub) in BY else []
C = [json.loads(l) for l in open('cases.jsonl', encoding='utf-8')]
miss = []
for c in C:
    g = canon(c['major'], c['sub'])
    c['gongjong_canonical'] = g
    ps = [BY[re.sub(r'\s+', '', x)]['period_years'] for x in g]
    c['period_taxonomy'] = max(ps) if ps else None
    if c['sub'] and not g: miss.append((c['case_id'], c['sub']))
cols = list(C[0].keys())
with open('cases.jsonl', 'w', encoding='utf-8') as f:
    for c in C: f.write(json.dumps(c, ensure_ascii=False) + '\n')
with open('cases.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
    for c in C:
        r = dict(c); r['cited_articles'] = ';'.join(r['cited_articles']); r['gongjong_canonical'] = ';'.join(r['gongjong_canonical'])
        r['other_citations'] = '; '.join(f"{o['law']} {','.join(o['articles'])}" for o in r['other_citations']) if isinstance(r['other_citations'], list) else r['other_citations']
        w.writerow(r)
print('unmapped', miss)
G = [c for c in C if c['period_gold']]
print('gold vs taxonomy', sum(c['period_gold'] == c['period_taxonomy'] for c in G), len(G))
J = [c for c in C if c['section'] != '분쟁조정']
print('judgment cases with canonical gongjong', sum(1 for c in J if c['gongjong_canonical']), len(J))
print('bylaw vs taxonomy disagreements', [(c['case_id'], c['sub'], c['period_bylaw'], c['period_taxonomy']) for c in J if c['period_bylaw'] != c['period_taxonomy']])
