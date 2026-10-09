#!/usr/bin/env python3
"""Plot every accepted singleton trial and signed state residual, including tails.

Input is SHA-linked model.json produced after complete raw audit, not a fit.
Contract: docs/design/2026-10-10-cold-load-model.md. No suffix selection.
"""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
model=json.loads((ROOT/'model.json').read_text())
assert model['technical_acceptance']['passed'] and model['windows']==5120
plt.rcParams.update({'font.size':9,'svg.hashsalt':'cold-load-model-v1'})
colors={'A':'#228833','B':'#66ccee','P':'#4477aa','S':'#cc6677','E':'#999999'}
for kind in ('raw-ticks','model-residuals'):
    fig,axes=plt.subplots(4,2,figsize=(13,13),sharex=True)
    for c in model['candidates']:
        row=c['epoch']*2+int(c['mask']!=0); ax=axes[row,c['swap']]
        if kind=='raw-ticks':
            for member in ('A','B','P','S','E'):
                values=c['members'][member]['cold_ticks']
                ax.plot(range(64),values,'.-',lw=.7,ms=3,color=colors[member],label=member+' cold')
            ax.set_ylabel('Internal CNTVCT ticks')
        else:
            for member in ('P','S'):
                for state in ('hot','cold'):
                    values=c['residuals'][member][state]['values']
                    ax.plot(range(64),values,('.-' if state=='cold' else 'x:'),lw=.7,ms=3,
                            color=colors[member],alpha=1 if state=='cold' else .5,label=member+' '+state)
            ax.axhline(0,color='black',lw=.5)
            ax.axhspan(-2,2,color='grey',alpha=.1,label='Median band only')
            ax.set_ylabel('Signed state residual (ticks)')
        ax.set_title(f"epoch {c['epoch']}, mask {c['mask']}, swap {c['swap']}")
        ax.grid(alpha=.2); ax.legend(ncol=3,fontsize=7)
    for ax in axes[-1]:ax.set_xlabel('All 64 trials (no clipping or suffix selection)')
    title='Raw cold times: 1024 singleton cold windows each LL=1' if kind=='raw-ticks' else 'P - max(A,B); S - (A+B-E): each hot/cold state separately'
    fig.suptitle(title); fig.tight_layout(rect=(0,0,1,.975))
    for ext in ('png','svg'):
        fig.savefig(ROOT/(kind+'.'+ext),dpi=170,metadata={'Software':'cpu-uarch-explorer'} if ext=='png' else {'Date':None,'Creator':'cpu-uarch-explorer'})
        if ext=='svg':
            output=ROOT/(kind+'.'+ext)
            output.write_text('\n'.join(line.rstrip() for line in output.read_text().splitlines())+'\n')
    plt.close(fig)
