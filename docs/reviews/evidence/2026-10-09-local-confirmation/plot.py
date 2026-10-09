"""Export scientific figures from anonymous analysis.json only.

Each thin line/dot is a process epoch median, not a confidence interval.
Two TLB targets were measured in separate batches, not paired epochs.
"""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['svg.hashsalt']='sm8650-local-confirmation-20261009'
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
DATA=json.loads((HERE/'analysis.json').read_text())

def save(fig,name):
    for ext in ('png','svg'):
        fig.savefig(HERE/f'{name}.{ext}',dpi=180,metadata={'Date':None} if ext=='svg' else {})
    plt.close(fig)

a,ax=plt.subplots(figsize=(9,4),layout='constrained')
colors={200:'tab:blue',100:'tab:orange'}
for t in DATA['tlb']:
    target=t['tlb_target']
    for x,s in enumerate(t['summary']):
        xx=x+(-.14 if target==200 else .14)
        ax.scatter([xx+(i-2)*.025 for i in range(5)],s['epoch_values'],color=colors[target],
                   label=f'target {target}' if x==0 else None)
        ax.plot([xx-.09,xx+.09],[s['median']]*2,color=colors[target],lw=2)
ax.axhline(0,color='grey',lw=1);ax.grid(axis='y',alpha=.25)
ax.set_xticks(range(4),['F128 / offset0','F128 / rotate','F512 / offset0','F512 / rotate'])
ax.set_ylabel('DID: DTLB walks / target circle')
ax.set_title('Nested W8/9 contrasts: five mapping epochs per separate target batch')
ax.legend();save(a,'tlb-targets')

curves=DATA['rob']['curves']
def curve(cls,anchor,k,align):
    return next(c for c in curves if (c['class'],c['anchor'],c['chain'],c['loop_mod64'])==(cls,anchor,k,align))

fig,axes=plt.subplots(1,2,figsize=(12,4),layout='constrained')
for align,style in ((0,'-'),(32,'--')):
    for anchor,k,color in (('none',8,'tab:grey'),('fsqrt',8,'tab:blue'),('fsqrt',16,'tab:orange')):
        c=curve('nop',anchor,k,align);pts=c['points'];xx=[p['n'] for p in pts]
        for epoch in (0,1):
            label=f'{anchor}'+(f' k{k}' if anchor=='fsqrt' else '')+f' / align{align}' if epoch==0 else None
            axes[0].plot(xx,[p['epoch_medians'][epoch] for p in pts],style,color=color,marker='.',alpha=.7,label=label)
        if anchor=='fsqrt':
            pts=[p for p in pts if p['n']];xx=[p['n'] for p in pts]
            for epoch in (0,1):
                axes[1].plot(xx,[p['delta_from_n0'][epoch] for p in pts],style,color=color,marker='.',alpha=.65,
                             label=f'k{k} / align{align}' if epoch==0 else None)
axes[0].set_ylabel('PMU cycles / iteration');axes[0].set_title('Raw curves including no-anchor control')
axes[1].axhline(1,color='red',ls=':',label='frozen 1-cycle effect')
axes[1].set_ylabel('cycles / iteration above same-epoch N0');axes[1].set_title('Response curve; no physical entry conversion')
for ax in axes:
    ax.set_xlabel('actual ISA filler instructions per gap N');ax.grid(alpha=.25);ax.legend(fontsize=8)
save(fig,'rob-fine')

fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained')
for ax,cls in zip(axes,('add','fadd')):
    for anchor,k,color in (('none',8,'tab:grey'),('fsqrt',16,'tab:orange')):
        pts=curve(cls,anchor,k,0)['points']
        ax.vlines([p['n'] for p in pts],[p['range_all_rounds'][0] for p in pts],
                  [p['range_all_rounds'][1] for p in pts],color=color,alpha=.4,lw=3)
        for epoch in (0,1):
            ax.scatter([p['n']+(epoch-.5)*7 for p in pts],[p['epoch_medians'][epoch] for p in pts],
                       marker='o' if epoch==0 else 'x',color=color,label=anchor+(' k16' if anchor=='fsqrt' else '') if epoch==0 else None)
    ax.set_title(cls.upper()+' resource sentinels / align0');ax.set_ylabel('PMU cycles / iteration')
    ax.set_xlabel('per-gap N (three sampled points only)');ax.legend();ax.grid(alpha=.25)
save(fig,'resource-sentinels')
for p in HERE.glob('*.svg'):
    p.write_text('\n'.join(s.rstrip() for s in p.read_text().splitlines())+'\n')
