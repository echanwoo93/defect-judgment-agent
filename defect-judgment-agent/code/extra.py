import json, re
from collections import Counter, defaultdict
exec(open('code/analyze.py',encoding='utf-8').read().split('rows = []')[0])
def recs(name): return [json.loads(l) for l in open(f'results/{name}.jsonl',encoding='utf-8')]
print('=== 1. 실제 사례에서 규칙 엔진 작동 ===')
for prov in ['gpt','claude']:
    R=[r for r in recs(f'{prov}_agent') if GOLD[r['case_id']]['edition']!=0]
    fired=[r for r in R if r.get('rule_findings')]
    pos=[r for r in fired if any(f['verdict']=='하자' for f in r['rule_findings'])]
    neg=[r for r in fired if not any(f['verdict']=='하자' for f in r['rule_findings'])]
    pos_ok=sum(GOLD[r['case_id']]['label']=='하자' for r in pos)
    neg_gold_nd=sum(GOLD[r['case_id']]['label']=='비하자' for r in neg)
    flips=[r for r in R if r['pred'].get('_llm_label') and r['pred'].get('_llm_label')!=r['pred'].get('label')]
    flip_ok=sum(r['pred']['label']==GOLD[r['case_id']]['label'] for r in flips)
    rules=Counter(f['rule'] for r in fired for f in r['rule_findings'])
    print(prov,'real',len(R),'fired',len(fired),'| 위반(하자)판정',len(pos),'정답일치',pos_ok,'| 위반없음',len(neg),'(그중 정답 비하자',neg_gold_nd,') | LLM판단 뒤집음',len(flips),'뒤집어서 정답',flip_ok)
    print('   rule types',dict(rules))
    for r in pos:
        if GOLD[r['case_id']]['label']!='하자': print('   FP',r['case_id'],[f['detail'] for f in r['rule_findings']])
print('\n=== 2. 판본별 성능 (오염 점검: direct 조건) ===')
for prov in ['gpt','claude']:
    for cond in ['direct','rag','agent']:
        R=recs(f'{prov}_{cond}'); by=defaultdict(list)
        for r in R:
            g=GOLD[r['case_id']]
            if g['edition']==0: continue
            s=score(r); by[g['edition']].append(s)
        out=[]
        for e in [2022,2024,2026]:
            S=by[e]; per=[x['period'] for x in S if 'period' in x]; gj=[x['gj_top1'] for x in S if 'gj_top1' in x]
            out.append(f"{e}: 기간 {sum(per)/len(per):.2f} 공종 {sum(gj)/len(gj):.2f} (n={len(S)})")
        print(prov,cond,' | '.join(out))
print('\n=== 3. 대조 사례 규칙 유형별 정확도 ===')
for prov in ['gpt','claude']:
    for cond in ['direct','rag','agent_norule','agent']:
        R=recs(f'{prov}_{cond}_contrast'); by=defaultdict(list)
        for r in R:
            g=GOLD[r['case_id']]; by[g['contrast_rule'].split('-')[0]].append(r['pred'].get('label')==g['label'])
        print(prov,cond,{k:f"{sum(v)}/{len(v)}" for k,v in sorted(by.items())})
print('\n=== 4. 2026 담보기간 오류 분해 (agent) ===')
for prov in ['gpt','claude']:
    R=[r for r in recs(f'{prov}_agent') if GOLD[r['case_id']]['edition']==2026]
    err=[r for r in R if 'period' in score(r) and not score(r)['period']]
    gj_wrong=sum(1 for r in err if not score(r).get('gj_top1',1))
    print(prov,'기간 오류',len(err),'그중 공종 오판으로 인한 것',gj_wrong)
print('\n=== 5. 대공종별 담보기간 정확도 (2026, agent vs rag) ===')
K=json.load(open('data/kb_gongjong.json',encoding='utf-8'))['taxonomy']
MJ={ng(t['sub']):t['major'] for t in K}
for prov in ['gpt','claude']:
    for cond in ['rag','agent']:
        by=defaultdict(list)
        for r in recs(f'{prov}_{cond}'):
            g=GOLD[r['case_id']]
            if g['edition']!=2026 or not g.get('gongjong_canonical'): continue
            p=g['period_gold']; by[p].append(score(r).get('period',0))
        print(prov,cond,{f'{k}년':f"{sum(v)/len(v):.2f}(n={len(v)})" for k,v in sorted(by.items())})
