"""All raw windows and count response densities; no allocation conversion."""
import json,statistics as st
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parent;m=json.loads((root/'analysis.json').read_text());rows=m['rows'];points=m['points'];classes=('nop','add','movi','movr');colors=('#0072b2','#d55e00','#009e73','#cc79a7')
plt.rcParams.update({'font.size':9,'svg.hashsalt':'sm8650-rob-event-v1'})
def save(fig,name):
 fig.tight_layout(rect=(0,0,1,.975));fig.savefig(root/(name+'.png'),dpi=180);fig.savefig(root/(name+'.svg'),metadata={'Date':None});p=root/(name+'.svg');p.write_text('\n'.join(l.rstrip() for l in p.read_text().splitlines())+'\n');plt.close(fig)
fig,axes=plt.subplots(4,2,figsize=(11,11));fig.suptitle('All 192 raw windows: operation-event control streams')
for i,c in enumerate(classes):
 for j,anchor in enumerate(('none','fsqrt')):
  ax=axes[i,j]
  for e in (0,1):
   rr=sorted([r for r in rows if r['class_name']==c and r['anchor']==anchor and r['epoch']==e],key=lambda x:x['n']);ax.plot([r['n'] for r in rr],[st.median(r['cycles']) for r in rr],color=colors[e],label=f'epoch {e}')
   for r in rr:ax.scatter([r['n']+x for x in (-2,0,2)],r['cycles'],s=13,color=colors[e],alpha=.65)
  ax.set_title(c+' / '+anchor);ax.set_xlabel('N per gap; jitter separates rounds');ax.set_ylabel('PMU cycles / iteration');ax.grid(alpha=.2);ax.legend(fontsize=7)
save(fig,'cycles')
for kind,evs,ylabel in [('operation-density',('0x3a','0x3b'),'Reported operations / added filler'),('stall-fractions',('0x816d','0x23'),'Counts / PMU cycles')]:
 fig,axes=plt.subplots(4,2,figsize=(11,11));fig.suptitle('Reported counts, not physical allocation or occupancy: '+kind)
 for i,c in enumerate(classes):
  for j,event in enumerate(evs):
   ax=axes[i,j];color=0
   for anchor in ('none','fsqrt'):
    for e in (0,1):
     rr=sorted([p for p in points if p['class_name']==c and p['anchor']==anchor and p['epoch']==e and (p['n']>0 or kind=='stall-fractions')],key=lambda x:x['n']);v=[p['events'][event]['per_filler_delta'] if kind=='operation-density' else st.median(p['events'][event]['cycle_fraction']) for p in rr]
     ax.plot([p['n'] for p in rr],v,color=colors[color],linestyle='-' if anchor=='none' else '--',label=anchor+f' epoch {e}')
     base=next(p for p in points if p['class_name']==c and p['anchor']==anchor and p['epoch']==e and p['n']==0)['events'][event]['median']
     for p in rr:
      values=[(x-base)/(2*p['n']) for x in p['events'][event]['raw']] if kind=='operation-density' else p['events'][event]['cycle_fraction'];ax.scatter([p['n']+x for x in (-2,0,2)],values,s=13,color=colors[color],alpha=.65)
     color+=1
   
   if kind=='operation-density':
    assert all(.95<=(x-base)/(2*p['n'])<=1.05 for anchor in ('none','fsqrt') for e in (0,1) for p in [p for p in points if p['class_name']==c and p['anchor']==anchor and p['epoch']==e and p['n']>0] for base in [next(b for b in points if b['class_name']==c and b['anchor']==anchor and b['epoch']==e and b['n']==0)['events'][event]['median']] for x in p['events'][event]['raw'])
    ax.set_ylim(.95,1.05);ax.ticklabel_format(axis='y',style='plain',useOffset=False)
   ax.set_title(c+' / '+event);ax.set_xlabel('N per gap');ax.set_ylabel(ylabel);ax.grid(alpha=.2);ax.legend(fontsize=6)
 save(fig,kind)
