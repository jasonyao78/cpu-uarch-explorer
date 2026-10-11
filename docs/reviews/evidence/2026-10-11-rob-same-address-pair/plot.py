#!/usr/bin/env python3
"""All paired and absolute windows, no filtering or capacity fitting."""
import json,os,sys
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/sm8650-matplotlib-config')
import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['svg.hashsalt']='sm8650-2026-10-11';import matplotlib.pyplot as plt
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).parent;a=json.loads((root/'analysis.json').read_text());fig,axes=plt.subplots(2,3,figsize=(14,8));variants=['i0','d0','i128','d128']
for col,(anchor,k) in enumerate([('none',16),('fsqrt',8),('fsqrt',16)]):
 ax=axes[0,col]
 for v in variants:
  pp=[p for p in a['points'] if p['anchor']==anchor and p['chain']==k and p['variant']==v];values=[x for p in pp for x in p['cycles']];ax.plot(range(40),values,'.-',lw=.6,ms=4,label=v)
 ax.set_title(f'{anchor}, chain={k}: all 4 x 40 windows');ax.set_xlabel('epoch / block');ax.set_ylabel('PMU cycles / iteration');ax.set_xticks([0,8,16,24,32],['e0','e1','e2','e3','e4']);ax.legend(fontsize=8);ax.grid(alpha=.2)
ax=axes[1,0]
for anchor,k,color in [('none',16,'gray'),('fsqrt',8,'C0'),('fsqrt',16,'C1')]:
 ps=[b for b in a['blocks'] if b['anchor']==anchor and b['chain']==k];ax.plot(range(40),[b['E'] for b in ps],'.-',lw=.7,label=f'{anchor}/{k}')
ax.axhline(0,c='k',lw=.5);ax.set_title('Byte-identical N0 sentinel E');ax.set_ylabel('C(d0) - C(i0)');ax.legend(fontsize=8);ax.grid(alpha=.2)
ax=axes[1,1]
for anchor,k in [('none',16),('fsqrt',8),('fsqrt',16)]:
 ps=[b for b in a['blocks'] if b['anchor']==anchor and b['chain']==k];ax.plot(range(40),[b['T'] for b in ps],'.-',lw=.7,label=f'{anchor}/{k}')
ax.axhline(0,c='k',lw=.5);ax.set_title('Signed same-block T');ax.set_ylabel('cycles / iteration');ax.legend(fontsize=8);ax.grid(alpha=.2)
ax=axes[1,2]
for k in [8,16]:ax.plot(range(40),[d['D'] for d in a['contrasts'] if d['chain']==k],'.-',lw=.7,label=f'chain={k}')
ax.axhline(5,c='r',ls='--',label='strict D > 5');ax.set_title('Matched D = T(fsqrt) - T(NONE)');ax.set_ylabel('cycles / iteration');ax.legend(fontsize=8);ax.grid(alpha=.2)
for ax in axes[1]:ax.set_xlabel('epoch / block');ax.set_xticks([0,8,16,24,32],['e0','e1','e2','e3','e4'])
fig.suptitle('SM8650 same-code-VA pair: '+a['verdict']+' (no physical entry inference)');fig.tight_layout(rect=[0,0,1,.95]);fig.savefig(root/'response.png',dpi=160);fig.savefig(root/'response.svg',metadata={'Date':None});plt.close(fig)

svg=root/"response.svg"
svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines())+"\n")
