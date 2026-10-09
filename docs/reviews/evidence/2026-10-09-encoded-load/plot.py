#!/usr/bin/env python3
"""Reproduce the registered high-bit encoding observations; no fitted capacity."""
from pathlib import Path
import json
import statistics as stat
import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['svg.hashsalt']='sm8650-encoded-load-20261009'
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent
run=json.loads((HERE/'summary.json').read_text())['runs'][0]
fig,axes=plt.subplots(2,2,figsize=(10,6),layout='constrained')
for epoch in (0,1):
    for mask,color,label in [('0x0000000000000000','#166a97','XOR zero'),('0xffff000000000000','#b65218','XOR high')]:
        for serial,marker,style,member in [(False,'o','-','P'),(True,'s','--','S')]:
            rows=sorted((r for r in run['rows'] if r['epoch']==epoch and r['pointer_xor']==mask and r['serial']==serial and r['memory_bytes']>1048576),key=lambda r:r['memory_bytes'])
            for ax,metric in [(axes[0,epoch],'0x11'),(axes[1,epoch],'0x37')]:
                xs=[r['memory_bytes']//1048576 for r in rows]
                ys=[stat.median(r['counts_per_iteration'][metric]) for r in rows]
                ax.plot(xs,ys,style,marker=marker,color=color,label=label+' / '+member)
                for x,r in zip(xs,rows):
                    ax.scatter([x]*3,r['counts_per_iteration'][metric],color=color,s=10,alpha=.55)
    axes[0,epoch].set_title('Epoch '+str(epoch));axes[0,epoch].set_ylabel('Cycles / iteration')
    axes[1,epoch].axhspan(1.8,2.2,color='#669955',alpha=.16,label='Registered LL gate')
    axes[1,epoch].set_ylabel('LL read-miss proxy / iteration');axes[1,epoch].set_ylim(.8,2.25)
    for ax in axes[:,epoch]:ax.set_xticks([64,128]);ax.set_xlabel('Actual full THP footprint (MiB)');ax.grid(alpha=.2)
axes[0,0].legend(fontsize=8);axes[1,0].legend(fontsize=8)
fig.suptitle('Same decoder shape: all long candidates unqualified')
fig.savefig(HERE/'observations.png',dpi=160,metadata={'Software':'cpu-uarch-explorer'})
fig.savefig(HERE/'observations.svg',metadata={'Date':None,'Creator':'cpu-uarch-explorer'})
svg=HERE/'observations.svg'
svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
