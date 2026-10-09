#!/usr/bin/env python3
"""Every accepted four-state trial, signed residual and tail; no clipping/fitting.

Contract: docs/design/2026-10-10-cold-state-injection.md. Independent panel
y scales; grey band is only the frozen median-resolution band, not a CI.
"""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
model=json.loads((ROOT/'model.json').read_text())
assert model['technical_acceptance']['passed'] and model['windows']==6144
plt.rcParams.update({'font.size':9,'svg.hashsalt':'cold-state-v1'})
colors={'hot':'#999999','first-cold':'#228833','second-cold':'#4477aa','cold':'#cc6677','P':'#4477aa','S':'#cc6677'}
for kind in ('raw-ticks','model-residuals'):
    fig,axes=plt.subplots(4,2,figsize=(13,13),sharex=True)
    for c in model['candidates']:
        ax=axes[c['epoch']*2+int(c['mask']!=0),c['swap']]
        if kind=='raw-ticks':
            for u in ('P','S'):
                for state in ('hot','first-cold','second-cold','cold'):
                    ax.plot(range(64),c['members'][u][state]['ticks']['values'],'.-' if u=='P' else 'x:',lw=.7,ms=3,color=colors[state],label=u+' '+state)
            ax.set_ylabel('Internal CNTVCT ticks')
        else:
            for u in ('P','S'):
                ax.plot(range(64),c['residuals'][u]['values'],'.-',lw=.7,ms=3,color=colors[u],label=u)
            ax.axhline(0,color='black',lw=.5);ax.axhspan(-2,2,color='grey',alpha=.1,label='Median band only')
            ax.set_ylabel('Signed four-state residual (ticks)')
        ax.set_title(f"epoch {c['epoch']}, mask {c['mask']}, swap {c['swap']}")
        ax.grid(alpha=.2);ax.legend(ncol=2,fontsize=6)
    for ax in axes[-1]:ax.set_xlabel('All 64 trials (no clipping or suffix selection)')
    fig.suptitle('Same P/S code: hot, first cold, second cold, both cold' if kind=='raw-ticks' else 'P: T11-max(T10,T01); S: T11-T10-T01+T00')
    fig.tight_layout(rect=(0,0,1,.975))
    for ext in ('png','svg'):
        out=ROOT/(kind+'.'+ext)
        fig.savefig(out,dpi=170,metadata={'Software':'cpu-uarch-explorer'} if ext=='png' else {'Date':None,'Creator':'cpu-uarch-explorer'})
        if ext=='svg':out.write_text('\n'.join(line.rstrip() for line in out.read_text().splitlines())+'\n')
    plt.close(fig)
