#!/usr/bin/env python3
"""All competition count contrasts, all victim rates/trials; no filtering.

Protocol frozen 2026-10-10; target execution 2026-10-11. Rates are whole-window
responses, not certified page miss probabilities or physical TLB occupancy.
"""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parent
m=json.loads((ROOT/'analysis.json').read_text())
assert m['windows']==36480 and len(m['lookup_points'])==1500
plt.rcParams.update({'font.size':8,'svg.hashsalt':'tlb-competition-v1'})
colors={1:'#4477aa',2:'#ee7733',4:'#228833',8:'#cc6677'}

def save(fig,name):
 fig.tight_layout(rect=(0,0,1,.97))
 for ext in ('png','svg'):
  out=ROOT/(name+'.'+ext)
  fig.savefig(out,dpi=160,metadata={'Software':'cpu-uarch-explorer'} if ext=='png' else {'Date':None,'Creator':'cpu-uarch-explorer'})
  if ext=='svg':out.write_text('\n'.join(l.rstrip() for l in out.read_text().splitlines())+'\n')
 plt.close(fig)

fig,axes=plt.subplots(5,2,figsize=(12,13),sharex=True,sharey=True)
for e in range(5):
 for col,event in enumerate((1,3)):
  ax=axes[e,col]
  for h in (1,2):
   pts=[p for p in m['lookup_points'] if p['epoch']==f'epoch-{e}' and p['h']==h]
   ax.scatter([p['k']+(.025 if h==1 else -.025)+.002*(p['pass_index']-3) for p in pts],[p['count_mean_differences'][event]/p['k'] for p in pts],s=6,alpha=.4,label=f'H{h}')
  ax.axhspan(.75,1.25,color='gray',alpha=.12,label='Frozen band');ax.axhline(1,color='black',lw=.5)
  ax.set_title(f"epoch {e}, {'0x05' if col==0 else '0x2f'} / K");ax.set_ylabel('(mean count - matched K0) / K');ax.set_ylim(.70,1.30);ax.grid(alpha=.2);ax.legend(fontsize=6)
for ax in axes[-1]:ax.set_xlabel('K (jitter separates overlapping markers only)')
fig.suptitle('All 1,500 competitor observations: per pass, both orders and H families')
save(fig,'lookup-counts')

fig,axes=plt.subplots(5,2,figsize=(12,13),sharex=True,sharey=True)
for e in range(5):
 for d in (0,1):
  ax=axes[e,d]
  for p in (1,2,4,8):
   pts=sorted([v for v in m['victim_points'] if (v['epoch'],v['direction'],v['passes'])==(f'epoch-{e}',d,p)],key=lambda v:v['k'])
   for h in ('1','2'):
    ax.plot([v['k'] for v in pts],[v['families'][h]['response_rate'] for v in pts],'.-' if h=='1' else 'x--',lw=.8,ms=4,color=colors[p],label=f'H{h}, {p} pass')
   bad=[v for v in pts if v['issues']]
   ax.scatter([v['k'] for v in bad],[v['families']['1']['response_rate'] for v in bad],marker='x',s=65,color='red')
  ax.set_title(f'epoch {e}, order {d}');ax.set_ylabel('Whole-window walk > 0 rate');ax.set_ylim(-.05,1.05);ax.grid(alpha=.2);ax.legend(fontsize=5,ncol=2)
for ax in axes[-1]:ax.set_xlabel('K (sparse grid; line is a visual guide)')
fig.suptitle('All 240 victim contrasts; red X = frozen preparation-drift block')
save(fig,'victim-rates')

fig,axes=plt.subplots(5,2,figsize=(12,17),sharex=True)
labels=[f'p{p}/H{h}/K{k}' for p in (1,2,4,8) for h in ('1','2') for k in (0,7,8,9,10,11)]
for e in range(5):
 for d in (0,1):
  ax=axes[e,d];rows=[]
  for p in (1,2,4,8):
   for h in ('1','2'):
    for k in (0,7,8,9,10,11):
     v=next(v for v in m['victim_points'] if (v['epoch'],v['direction'],v['passes'],v['k'])==(f'epoch-{e}',d,p,k));rows.append(v['families'][h]['walk'])
  ax.imshow(np.array(rows),aspect='auto',interpolation='nearest',vmin=0,vmax=1,cmap='Greys');ax.set_title(f'epoch {e}, order {d} (black = one walk)');ax.set_yticks(range(48));ax.set_yticklabels(labels,fontsize=4);ax.set_xticks(range(0,16,2))
for ax in axes[-1]:ax.set_xlabel('All 16 trials, starting at 0')
fig.suptitle('All 7,680 victim windows, including the isolated K7 response and drift blocks')
save(fig,'victim-windows')
