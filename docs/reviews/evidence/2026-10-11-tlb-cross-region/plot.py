#!/usr/bin/env python3
"""All finite victim points and censored residuals, no selected averages."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=Path(__file__).resolve().parent;a=json.loads((D/'analysis.json').read_text());plt.rcParams['svg.hashsalt']='sm8650-2026-10-11-cross-region'
fig,axes=plt.subplots(2,3,figsize=(13,6),constrained_layout=True)
for ti,t in enumerate((7,100)):
 for g,label in enumerate(('I: isolated','G1: low constant','G3: folded constant')):
  ax=axes[ti,g]
  for epoch in range(5):
   for direction in range(2):
    p=[p for p in a['victim_points'] if (p['epoch'],p['target'],p['group'],p['direction'])==(epoch,t,g,direction)];p.sort(key=lambda x:x['w']);offset=(epoch*2+direction-4.5)*.025;ax.plot([x['w']+offset for x in p],[x['response_rate'] for x in p],marker='o',markersize=3,alpha=.7)
    for x in p:
     if x['issues']:ax.scatter(x['w']+offset,x['response_rate'],marker='x',s=90,color='red',zorder=4)
  ax.axhline(.5,color='black',ls='--',lw=.8);ax.set(title=f'target {t}, {label}',xlabel='W (victim included)',ylabel='nonzero victim walk rate',xticks=[8,9,12],ylim=(-.05,1.08));ax.grid(alpha=.2)
fig.savefig(D/'response.png',dpi=180);fig.savefig(D/'response.svg',metadata={'Date':None});p=D/'response.svg';p.write_text('\n'.join(l.rstrip() for l in p.read_text().splitlines())+'\n')
