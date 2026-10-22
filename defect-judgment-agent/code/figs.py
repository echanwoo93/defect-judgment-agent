import json, re, os
from collections import Counter
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
exec(open('code/analyze.py',encoding='utf-8').read().split('rows = []')[0])
plt.rcParams.update({'font.size':10,'font.family':'DejaVu Sans'})
conds=['direct','rag','agent']; lab={'direct':'Direct','rag':'RAG','agent':'Proposed agent'}
def get(prov,cond,m,con):
    R=load(f'{prov}_{cond}'+('_contrast' if con else '')); R=split(R,con); v,_=metric(R,m); lo,hi=boot_ci(R,m); return v,lo,hi
panels=[('period',False,'(a) Warranty period accuracy\n(2026 test set, n=128)'),('cit',False,'(b) Article citation F1\n(2026 test set)'),
        ('label',True,'(c) Defect judgment accuracy\n(contrast set, n=67)'),('near',True,'(d) Near-threshold accuracy\n(contrast set, n=29)')]
fig,axs=plt.subplots(1,4,figsize=(14,3.6))
cols={'direct':'#bbbbbb','rag':'#7aa6d6','agent':'#1f4e8c'}
for ax,(m,con,t) in zip(axs,panels):
    for i,prov in enumerate(['gpt','claude']):
        for j,c in enumerate(conds):
            v,lo,hi=get(prov,c,m,con); x=i*1.0+(j-1)*0.27
            ax.bar(x,v,0.25,color=cols[c],label=lab[c] if i==0 else None,yerr=[[v-lo],[hi-v]],capsize=2,error_kw={'lw':0.8})
            ax.text(x,min(v+0.04,1.02),f'{v:.2f}',ha='center',fontsize=7)
    ax.set_xticks([0,1]); ax.set_xticklabels(['GPT','Claude']); ax.set_ylim(0,1.1); ax.set_title(t,fontsize=9.5)
    ax.spines[['top','right']].set_visible(False)
axs[0].set_ylabel('Score'); axs[0].legend(fontsize=8,frameon=False,loc='upper left')
plt.tight_layout(); plt.savefig('fig_main.png',dpi=300)

# ablation
fig,ax=plt.subplots(1,2,figsize=(9,3.4))
for k,(m,con,abl,tt) in enumerate([('period',False,'agent_notool','Warranty period accuracy (2026)'),('label',True,'agent_norule','Contrast-set judgment accuracy')]):
    for i,prov in enumerate(['gpt','claude']):
        a=get(prov,'agent',m,con); b=get(prov,abl,m,con)
        for j,(v,nm,cl) in enumerate([(a,'Full agent','#1f4e8c'),(b,'w/o '+('warranty tool' if m=='period' else 'rule engine'),'#e0a040')]):
            x=i+(j-0.5)*0.35; ax[k].bar(x,v[0],0.33,color=cl,label=nm if i==0 else None,yerr=[[v[0]-v[1]],[v[2]-v[0]]],capsize=2,error_kw={'lw':0.8})
            ax[k].text(x,min(v[0]+0.04,1.02),f'{v[0]:.2f}',ha='center',fontsize=8)
    ax[k].set_xticks([0,1]); ax[k].set_xticklabels(['GPT','Claude']); ax[k].set_ylim(0,1.1); ax[k].set_title(tt,fontsize=9.5)
    ax[k].legend(fontsize=8,frameon=False,loc='lower right'); ax[k].spines[['top','right']].set_visible(False)
plt.tight_layout(); plt.savefig('fig_ablation.png',dpi=300)

# 공종 confusion (agent, both models, 2026+2022+2024 real cases)
conf=Counter(); tot=0
for prov in ['gpt','claude']:
    for l in open(f'results/{prov}_agent.jsonl',encoding='utf-8'):
        r=json.loads(l); g=GOLD[r['case_id']]
        gg=g.get('gongjong_canonical') or []
        pg=r['pred'].get('gongjong') or []
        if gg and pg:
            tot+=1
            if ng(pg[0]) not in {ng(x) for x in gg}: conf[(gg[0],pg[0])]+=1
print('total',tot,'errors',sum(conf.values()))
for (a,b),n in conf.most_common(15): print(n,a,'->',b)
