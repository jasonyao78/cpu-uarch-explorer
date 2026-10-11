"""All accepted cells/windows, including failed response gates; no capacity fit."""
from pathlib import Path
import sys,json,hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
summary,model,out=map(Path,sys.argv[1:]);s=json.loads(summary.read_text());m=json.loads(model.read_text());assert m['input_sha256']==hashlib.sha256(summary.read_bytes()).hexdigest();out.mkdir(exist_ok=True)
cols=[(w,v,hd) for w in (8,9) for v in (0,w//2,w-1) for hd in (0,1)]
rows=[(f'epoch-{e}',h,d) for e in range(5) for h in (1,2) for d in (0,1)]
points={(p['epoch'],p['w'],p['victim'],p['history_direction'],p['direction']):p for p in m['victim_points']}
a=np.array([[points[ep,w,v,hd,d]['families'][str(h)]['response_rate'] for w,v,hd in cols] for ep,h,d in rows]);fig,ax=plt.subplots(figsize=(12,7));im=ax.imshow(a,cmap='viridis',vmin=0,vmax=1,aspect='auto');ax.set_xticks(range(12),[f'W{w} v{v}\nhist{hd}' for w,v,hd in cols]);ax.set_yticks(range(20),[f'{ep} H{h} dir{d}' for ep,h,d in rows],fontsize=8)
for i in range(20):
 for j in range(12):ax.text(j,i,f'{a[i,j]:.2f}',ha='center',va='center',fontsize=7,color='white' if a[i,j]<.55 else 'black')
ax.set_title('Victim data-walk response rates | 16 windows per cell | all mappings/orders');fig.colorbar(im,ax=ax,label='walk > 0 fraction');fig.tight_layout();fig.savefig(out/'victim-rates.png',dpi=150);fig.savefig(out/'victim-rates.svg');plt.close(fig)
fig,axs=plt.subplots(1,2,figsize=(14,13),sharex=True)
for ax,w in zip(axs,(8,9)):
 key=[(f'epoch-{e}',v,hd,d) for e in range(5) for v in (0,w//2,w-1) for hd in (0,1) for d in (0,1)];a=np.array([sum((points[ep,w,v,hd,d]['families'][str(h)]['walk'] for h in (1,2)),[]) for ep,v,hd,d in key]);im=ax.imshow(a,cmap='viridis',vmin=0,vmax=max(1,a.max()),aspect='auto');ax.axvline(15.5,color='white');ax.set_title(f'W{w}: each raw victim count, A(H1) | C(H2)');ax.set_yticks(range(60),[f'e{ep[-1]} v{v} hist{hd} d{d}' for ep,v,hd,d in key],fontsize=6);ax.set_xticks([0,7,15,16,23,31],['A0','A7','A15','C0','C7','C15'],rotation=90,fontsize=8);fig.colorbar(im,ax=ax,label='DTLB walk count')
fig.suptitle('Complete victim windows, including drift and count > 1');fig.tight_layout();fig.savefig(out/'victim-windows.png',dpi=150);fig.savefig(out/'victim-windows.svg');plt.close(fig)
fig,axs=plt.subplots(2,1,figsize=(13,7),sharex=True,sharey=True)
for ax,index in zip(axs,(1,3)):
 for h,color in ((1,'tab:blue'),(2,'tab:orange')):
  pp=[p for p in m['lookup_points'] if p['h']==h];assert len(pp)==960
  ax.scatter(range(len(pp)),[p['count_mean_differences'][index]/(p['w']-1) for p in pp],s=9,alpha=.5,label=f'H{h}',color=color)
 ax.axhline(.75,color='red',linestyle='--');ax.axhline(1.25,color='red',linestyle='--');ax.set_ylabel(f'{("L1 refill" if index==1 else "L2 lookup")} / K');ax.legend();ax.grid(alpha=.2)
axs[-1].set_xlabel('Each epoch/W/victim/history/competitor direction/pass, all 1,920 points');axs[0].set_title('Matched W1 subtraction, frozen lookup gate [.75,1.25]');fig.tight_layout();fig.savefig(out/'lookup-counts.png',dpi=150);fig.savefig(out/'lookup-counts.svg');plt.close(fig)

# Normalize generated SVG path-line whitespace without changing geometry.
for p in out.glob("*.svg"):
 p.write_text("\n".join(line.rstrip() for line in p.read_text().splitlines())+"\n")
