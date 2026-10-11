#!/usr/bin/env python3
"""All 420 accepted windows, both epochs and controls; no clipping or fitting.

Frozen protocol: docs/design/2026-10-11-rob-filler-resource.md. N counts
architectural filler instructions per gap, not physical allocation units.
"""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
m=json.loads((ROOT/'analysis.json').read_text());assert len(m['rows'])==140 and m['windows']==420
plt.rcParams.update({'font.size':8,'svg.hashsalt':'rob-resource-v1'})
colors={'fsqrt':'#4477aa','none':'#cc6677'}
def save(fig,name):
 fig.tight_layout(rect=(0,0,1,.97))
 for ext in ('png','svg'):
  out=ROOT/(name+'.'+ext)
  fig.savefig(out,dpi=165,metadata={'Software':'cpu-uarch-explorer'} if ext=='png' else {'Date':None,'Creator':'cpu-uarch-explorer'})
  if ext=='svg':out.write_text('\n'.join(l.rstrip() for l in out.read_text().splitlines())+'\n')
 plt.close(fig)
for kind in ('cycles','signed-effects'):
 fig,axes=plt.subplots(5,2,figsize=(12,14),sharex=True)
 for i,c in enumerate(m['classes']):
  for e in (0,1):
   ax=axes[i,e];pts=[dict(n=p['n'],**p['epochs'][e]) for p in c['points']]
   if kind=='cycles':
    for a in ('anchor','none'):
     color=colors['fsqrt' if a=='anchor' else 'none']
     ax.plot([p['n'] for p in pts],[p[a+'_median'] for p in pts],'-',lw=.8,color=color,label='fsqrt k16' if a=='anchor' else 'none')
     ax.scatter([p['n']+j*3-3 for p in pts for j in range(3)],[v for p in pts for v in p[a+'_cycles']],s=13,color=color,alpha=.7)
    ax.plot([p['n'] for p in pts],[p['supply_reference'] for p in pts],'--',color='grey',lw=.7,label='simple max reference');ax.set_ylabel('PMU cycles / iteration')
   else:
    ax.plot([p['n'] for p in pts],[p['difference'] for p in pts],'-',color=colors['fsqrt'],lw=.8,label='median effect')
    ax.scatter([p['n']+j*3-3 for p in pts for j in range(3)],[v-p['baseline'] for p in pts for v in p['anchor_cycles']],s=13,color=colors['fsqrt'])
    ax.plot([p['n'] for p in pts],[p['supply_residual'] for p in pts],'x--',color='grey',lw=.7,label='median - max reference');ax.axhspan(-1,1,color='grey',alpha=.12,label='frozen effect band');ax.axhline(0,color='black',lw=.5);ax.set_ylabel('Signed cycles / iteration')
   ax.set_title(f"{c['class_name']}, epoch {e}: {c['status']}");ax.grid(alpha=.2);ax.legend(fontsize=6)
 for ax in axes[-1]:ax.set_xlabel('N per gap (jitter separates three raw rounds only)')
 fig.suptitle('All 420 windows: independent instruction streams and anchor controls' if kind=='cycles' else 'All anchor rounds and signed effects; no baseline subtraction for physical entries')
 save(fig,kind)
