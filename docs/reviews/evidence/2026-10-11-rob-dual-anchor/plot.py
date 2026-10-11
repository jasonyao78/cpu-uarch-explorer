#!/usr/bin/env python3
"""Plot every accepted window and all three epoch trajectories, no trimming."""
import argparse,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg');matplotlib.rcParams['svg.hashsalt']='rob-dual-anchor-v1'
import matplotlib.pyplot as plt

def main():
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=('qualification','scan'),required=True);a=p.parse_args();e=Path(__file__).resolve().parent/a.phase;r=json.loads((e/'analysis.json').read_text());fig,ax=plt.subplots(figsize=(10,5.6));colors={'none':'#777777','serial':'#1668b1','independent':'#c63d30'}
 for anchor in colors:
  for epoch in range(3):
   points=sorted((z for z in r['points'] if z['anchor']==anchor and z['epoch']==epoch),key=lambda z:z['n']);ax.plot([z['n'] for z in points],[z['median'] for z in points],color=colors[anchor],alpha=.75,ls=('-','--',':')[epoch],label=anchor+' / epoch '+str(epoch))
   for z in points:ax.scatter([z['n']]*8,z['cycles'],s=8,color=colors[anchor],alpha=.25)
 i0=[v for z in r['points'] if z['anchor']=='independent' and z['n']==0 for v in z['cycles']]
 if a.phase=='scan':
  ax.axhline(.9*min(i0),color='#777777',lw=1,ls='--',label='NONE supply ceiling')
  ax.axhline(1.25*max(i0),color='#c63d30',lw=1,ls='--',label='overlap-loss response floor')
  for z in r.get('curve',[]):
   if z['state']=='supply-or-control-unqualified':ax.axvline(z['n'],color='#e1bc81',lw=5,alpha=.4)
 ax.set(xlabel='NOP instructions per side (N); not physical ROB entries',ylabel='PMU user cycles / iteration',title=a.phase+': '+r['status']+'; all '+str(r['windows'])+' windows');ax.grid(alpha=.2);ax.legend(fontsize=8,ncol=3);fig.tight_layout();fig.savefig(e/'response.png',dpi=180);fig.savefig(e/'response.svg',metadata={'Date':None});plt.close(fig)
 path=e/'response.svg';path.write_text('\n'.join(x.rstrip() for x in path.read_text().splitlines())+'\n')
if __name__=='__main__':main()
