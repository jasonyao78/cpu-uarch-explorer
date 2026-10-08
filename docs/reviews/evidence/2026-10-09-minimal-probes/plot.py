"""Scientific figures from anonymous summary.json; no device/raw dependency."""
from pathlib import Path
from collections import defaultdict
import json
import statistics as st
import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['svg.hashsalt']='sm8650-minimal-20261009'
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
runs=json.loads((HERE/'summary.json').read_text())['runs']
tlb=next(r for r in runs if r['mode']=='tlb')
indexed={(r['epoch'],r['seed'],r['f'],r['offset_rotate'],r['h'],r['w']):r['counts_mean'][4] for r in tlb['rows'] if r['w']}
fig,ax=plt.subplots(figsize=(8,4),layout='constrained')
for x,(f,off) in enumerate([(128,False),(128,True),(512,False),(512,True)]):
    epochs=[]
    for e in range(5):
        differences=[]
        for seed in (42,137):
            get=lambda h,w:indexed[(f'epoch-{e}',seed,f,off,h,w)]
            differences.append((get(1,9)-get(1,8))-(get(2,9)-get(2,8)))
        epochs.append(st.mean(differences))
    ax.scatter([x+(e-2)*.055 for e in range(5)],epochs,label=None)
    ax.plot([x-.2,x+.2],[st.median(epochs)]*2,color='black',lw=2)
ax.axhline(0,color='grey',lw=1)
ax.set_xticks(range(4),['F128 / offset0','F128 / rotate','F512 / offset0','F512 / rotate'])
ax.set_ylabel('[(A9-A8) - (C9-C8)] DTLB walks / round')
ax.set_title('Nested TLB contrast: five mapping epochs; seeds averaged within epoch')
ax.grid(axis='y',alpha=.25)
for ext in ('png','svg'): fig.savefig(HERE/f'tlb-paired.{ext}',dpi=180,metadata={'Date':None} if ext=='svg' else {})
plt.close(fig)
rob=next((r for r in runs if r['mode']=='rob-window'),None)
if rob:
    fig,axes=plt.subplots(1,3,figsize=(13,4),layout='constrained')
    for ax,cls in zip(axes[:2],('nop','add')):
        for serial in (False,True):
            g=defaultdict(list)
            for r in rob['rows']:
                if r['anchor']=='miss' and r['class']==cls and r['serial']==serial: g[r['n']]+=r['cycles_per_iteration']
            xs=sorted(g); ys=[st.median(g[x]) for x in xs]
            ax.plot(xs,ys,'o-',label='serial' if serial else 'independent')
            ax.fill_between(xs,[min(g[x]) for x in xs],[max(g[x]) for x in xs],alpha=.15)
        ax.set_title('16 MiB chase / '+cls.upper()); ax.legend(); ax.set_ylabel('PMU cycles / iteration')
    ax=axes[2]
    for chain in (8,16):
        g=defaultdict(list)
        for r in rob['rows']:
            if r['anchor']=='fsqrt' and r['chain']==chain: g[r['n']]+=r['cycles_per_iteration']
        xs=sorted(g); ax.plot(xs,[st.median(g[x]) for x in xs],'o-',label=f'{2*chain} sqrt / iteration')
        ax.fill_between(xs,[min(g[x]) for x in xs],[max(g[x]) for x in xs],alpha=.15)
    ax.set_title('sqrt(1.0) / NOP'); ax.legend(); ax.set_ylabel('PMU cycles / iteration')
    for ax in axes: ax.set_xlabel('actual filler instructions per gap N'); ax.grid(alpha=.25)
    fig.suptitle('Exploratory effective-window responses; no physical ROB entry estimate')
    for ext in ('png','svg'): fig.savefig(HERE/f'rob-curves.{ext}',dpi=180,metadata={'Date':None} if ext=='svg' else {})

for path in HERE.glob('*.svg'):
    path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
