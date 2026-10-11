#!/usr/bin/env python3
"""Reproduce all Q-A curves; tick rotation changes layout only, no data selection."""
import os,sys,json
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/sm8650-matplotlib-config')
import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['svg.hashsalt']='sm8650-2026-10-11'
import matplotlib.pyplot as plt
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).parent
x=json.loads((root/'analysis.json').read_text());fig,axes=plt.subplots(2,3,figsize=(13,7),layout='constrained');colors={'contiguous':'#277c9e','sparse':'#c86432','random-set':'#5b963f'}
for row,offset in enumerate(('constant','rotated')):
 for shape,color in colors.items():
  for order,ls in [('random','-'),('reverse-random','--')]:
   pp=sorted([p for p in x['points'] if p['shape']==shape and p['offset']==offset and p['order']==order],key=lambda p:p['n'])
   for col,(key,label) in enumerate([('refills_per_load','L1D TLB refills / load'),('cycles_per_load','Cycles / load'),('data_refills_per_load','L1D cache refills / load (includes TTW)')]):
    for e in range(5):
     ep=sorted([p for p in x['epoch_points'] if p['shape']==shape and p['offset']==offset and p['order']==order and p['epoch']==e],key=lambda p:p['n']);axes[row,col].plot([p['n'] for p in ep],[p[key] for p in ep],color=color,ls=ls,alpha=.15,lw=.7)
    axes[row,col].plot([p['n'] for p in pp],[p[key] for p in pp],color=color,ls=ls,lw=1.5,marker='.',label=shape+(' reversed' if order!='random' else ''))
 for col,ax in enumerate(axes[row]):
  ax.set_xscale('log',base=2);ax.set_xticks([32,64,96,112,256,512,1024,2048],labels=['32','64','96','112','256','512','1024','2048'],rotation=65,fontsize=8);ax.set_xlabel('Distinct 4K pages N');ax.set_ylabel(['TLB refills / load','Cycles / load','L1D cache refills / load'][col]);ax.set_title(offset+' offset');ax.grid(alpha=.2)
 axes[row,0].axhline(.5,color='#333',lw=.8,ls=':');axes[row,0].legend(fontsize=7,frameon=False)
fig.suptitle('SM8650 X4 Q-A: all 60 operational crossings (96,112]; main sensitivity verdict INCONCLUSIVE\n5 fresh processes x 3 rounds; paired sums; faint lines = individual epochs; physical entries uncalibrated')
fig.savefig(root/'response.png',dpi=160);fig.savefig(root/'response.svg',metadata={'Date':None});plt.close(fig)

svg=root/"response.svg"
svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines())+"\n")
