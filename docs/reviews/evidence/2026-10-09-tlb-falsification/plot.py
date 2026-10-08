# SPDX-License-Identifier: Apache-2.0
"""Render all five process observations at each main-grid point; no outlier removal.

W12 end controls are retained in summary.json and the report, outside this grid.
Target200 W9 was collected in the later followup epoch, as the preregistered branch.
"""
import json, statistics
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
matplotlib.rcParams['svg.hashsalt']='sm8650-tlb-falsification-20261009'
HERE=Path(__file__).resolve().parent
summary=json.loads((HERE/'summary.json').read_text())
grid={100:{},200:{}}
for epoch in summary['epochs']:
    if epoch['directory'].endswith('controls'):
        continue
    for c in epoch['conditions']:
        if 'end' in c['label'] or 'floor' in c['label']:
            continue
        p=c['params'];target=p['set_target'];w=p['set_window'];h=p['set_hypothesis']
        assert (h,w) not in grid[target]
        grid[target][h,w]=c['metrics']['pmu.dtlb_walk.count']
fig,axes=plt.subplots(1,2,figsize=(10.4,4.3),sharey=True)
for ax,target in zip(axes,(200,100)):
    for h,color,label in ((1,'#1f63a7','A: low VPN concentrated'),(2,'#2a8b69','C: low VPN dispersed')):
        ws=sorted(w for hh,w in grid[target] if hh==h)
        med=[]
        for w in ws:
            values=grid[target][h,w];med.append(statistics.median(values))
            jitter=[-.12,-.06,0,.06,.12]
            marker='D' if target==200 and w==9 else 'o'
            ax.scatter([w+j for j in jitter],values,c=color,alpha=.6,s=25,marker=marker,zorder=3)
        ax.plot(ws,med,color=color,linewidth=1.7,label=label,zorder=2)
    ax.axhline(2,color='#777777',linestyle='--',linewidth=1,label='Exploratory median threshold = 2')
    ax.set_title(f'Target {target}')
    ax.set_xticks([6,8,9,10,12]);ax.set_xlim(5.5,12.5);ax.set_ylim(-.5,13)
    ax.set_xlabel('Target pages W');ax.grid(axis='y',alpha=.18)
axes[0].set_ylabel('Data translation walks / valid round (0x34)')
axes[1].legend(loc='upper left',fontsize=8)
fig.suptitle('TLB local transition: process spread matters',fontsize=14)
fig.text(.5,.015,'Dots: five fresh processes (horizontal jitter only); lines: medians. Target200 W9: later epoch (diamonds).',ha='center',fontsize=8)
fig.tight_layout(rect=[0,.05,1,.94])
fig.savefig(HERE/'local-transition.png',dpi=180)
fig.savefig(HERE/'local-transition.svg', metadata={'Date':None})
svg=HERE/'local-transition.svg'
# Matplotlib path formatting leaves trailing spaces; normalize without changing geometry.
svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
