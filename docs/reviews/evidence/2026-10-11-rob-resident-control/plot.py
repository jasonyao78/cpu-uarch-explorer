#!/usr/bin/env python3
"""Plot every accepted resident-control window; no trimmed/selected data."""
import gzip,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=Path(__file__).resolve().parent
r=json.loads(gzip.decompress((D/'summary.json.gz').read_bytes()))
plt.rcParams['svg.hashsalt']='sm8650-2026-10-11-resident'
fig,ax=plt.subplots(5,3,figsize=(15,12),constrained_layout=True)
for row in r['rows']:
 c=row['config'];epoch=int(row['condition'][1]);i=[('none','independent',0),('none','independent',128),('none','dependent',128),('fsqrt','independent',128),('fsqrt','dependent',128)].index((c['anchor'],c['link'],c['n']));a=ax[i,epoch]
 for prep,color,marker in [('resident','#117a65','o'),('reinstall','#8e44ad','x')]:
  ss=[s for s in row['samples'] if s['preparation']==prep];a.plot([s['position'] for s in ss],[s['counts'][0]/131072 for s in ss],marker=marker,color=color,label=prep)
 a.set_title(f"epoch {epoch}: {c['anchor']} {c['link']} N{c['n']}",fontsize=10);a.set_xlabel('execution position');a.set_ylabel('cycles / iteration');a.set_xticks([0,4,8,12,15]);a.grid(alpha=.25)
ax[0,0].legend(fontsize=8)
fig.savefig(D/'response.png',dpi=180)
fig.savefig(D/'response.svg',metadata={'Date':None})
p=D/'response.svg';p.write_text('\n'.join(l.rstrip() for l in p.read_text().splitlines())+'\n')
