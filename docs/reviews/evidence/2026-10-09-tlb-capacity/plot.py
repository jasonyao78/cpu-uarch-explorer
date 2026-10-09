#!/usr/bin/env python3
"""Render audited local TLB response intervals and retained window diagnostics.

Inputs are the address-free summary.json and analysis.json beside this script.
Requires matplotlib. Regeneration never reads private data or selects windows.
Protocol: docs/design/2026-10-09-tlb-local-capacity.md. Mapping processes remain
separate; no confidence interval, interpolation or certified miss probability.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from tools.diagnostic.tlb_capacity_analysis import analyze_capacity

A, C = '#0072B2', '#D55E00'


def save(figure,directory,name):
    """PNG preview and editable SVG contain the same measured observations."""
    figure.savefig(directory/(name+'.png'),dpi=170,metadata={'Software':'TLB capacity evidence plot'})
    svg=directory/(name+'.svg')
    figure.savefig(svg,metadata={'Date':None,'Creator':'TLB capacity evidence plot'})
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    plt.close(figure)


def style(ax,xmin,xmax,xticks,ymax):
    ax.set_xlim(xmin,xmax);ax.set_xticks(xticks);ax.set_ylim(-.15,ymax)
    ax.tick_params(labelsize=8);ax.grid(axis='y',color='#dddddd',linewidth=.5)


def families_legend(extra=None):
    handles=[Line2D([0],[0],color=A,marker='o',label='A / H1'),
             Line2D([0],[0],color=C,marker='s',label='C / H2')]
    return handles+(extra or [])


def interval_label(curve):
    """Grid's preceding low point is open; only confirmed responses are bounded."""
    if not curve['bounded_confirmed']:
        return 'No bounded interval'
    low,high=curve['interval']
    return f'({low},{high}]'


def working_set(data,directory):
    """All fifteen epoch/F/order curves; every W point and decrease survives."""
    fig,axes=plt.subplots(3,5,figsize=(18,9),sharey=True)
    lookup={(c['epoch'],c['f'],c['direction']):c for c in data['working_set']}
    ymax=max(max(p['a_last8'],p['c_last8'],p['difference']) for c in lookup.values() for p in c['points'])+.7
    plotted=0
    for row,(f,direction) in enumerate(((128,0),(128,1),(512,0))):
        for epoch in range(5):
            ax=axes[row,epoch];curve=lookup[f'epoch-{epoch}',f,direction];points=curve['points'];x=[p['x'] for p in points]
            ax.plot(x,[p['difference'] for p in points],':',color='#222222',marker='x',markersize=4,label='A − C',zorder=4)
            for family,color,marker in (('a',A,'o'),('c',C,'s')):
                ax.plot(x,[p[family+'_last8'] for p in points],color=color,marker=marker,markersize=4)
                ax.plot(x,[p[family+'_preceding8'] for p in points],color=color,linestyle='--',alpha=.45,linewidth=.8)
            ax.axhline(1,color='#CC3311',linewidth=.7,linestyle='--')
            if curve['bounded_confirmed']:
                ax.axvspan(*curve['interval'],color='#e2f2df',zorder=-3)
            style(ax,min(x)-.3,max(x)+.3,x,ymax)
            ax.set_title(f'E{epoch}: {curve["status"]}\n'+interval_label(curve),fontsize=9)
            if epoch==0:
                ax.set_ylabel(f'F{f} · '+('reverse' if direction else 'forward')+'\n0x34 / circle',fontsize=10)
            if row==2:ax.set_xlabel('Working set W (fixed nested pages)',fontsize=9)
            plotted+=1
    assert plotted==15
    fig.suptitle('Local working-set response: separate mapping processes and target orders',fontsize=16,y=.993)
    fig.text(.5,.945,'Solid = steps 25–32; dashed = steps 17–24. D=A−C threshold 1. Green band = accepted adjacent response interval.',ha='center',fontsize=10)
    fig.legend(handles=families_legend([Line2D([0],[0],color='#222222',linestyle=':',marker='x',label='A − C')]),
               loc='upper center',bbox_to_anchor=(.5,.927),ncol=3,frameon=False,fontsize=10)
    fig.subplots_adjust(left=.06,right=.99,bottom=.07,top=.84,hspace=.45,wspace=.17)
    save(fig,directory,'working-set')


def victims(data,directory):
    """Both competitor orders in every epoch, with censoring kept explicit."""
    fig,axes=plt.subplots(2,5,figsize=(18,7),sharex=True,sharey=True)
    lookup={(c['epoch'],c['direction']):c for c in data['victim_response']}
    for direction in (0,1):
        for epoch in range(5):
            ax=axes[direction,epoch];curve=lookup[f'epoch-{epoch}',direction];points=curve['points'];x=[p['x'] for p in points]
            for family,color,marker in (('a',A,'o'),('c',C,'s')):
                ax.plot(x,[p[family+'_rate'] for p in points],color=color,marker=marker,markersize=4)
            ax.plot(x,[p['difference'] for p in points],':',color='#222222',marker='x',markersize=4,zorder=4)
            ax.axhline(.5,color='#CC3311',linestyle='--',linewidth=.7)
            ax.set_title(f'E{epoch}: {curve["status"]}\n'+interval_label(curve),fontsize=9)
            style(ax,-.3,11.3,[0,4,8,11],1.1)
            if epoch==0:
                ax.set_ylabel(('Reverse' if direction else 'Forward')+' competitors\nWindow walk rate',fontsize=10)
            if direction==1:ax.set_xlabel('Competitor pages K',fontsize=9)
    fig.suptitle('Victim response: one fixed victim after repeated preparation',fontsize=16,y=.995)
    fig.text(.5,.952,'Rate = windows with 0x34>0 / 16; it is not a certified miss probability. K11 alone has no next-point confirmation.',ha='center',fontsize=10)
    fig.legend(handles=families_legend([Line2D([0],[0],color='#222222',linestyle=':',marker='x',label='A − C')]),
               loc='upper center',bbox_to_anchor=(.5,.935),ncol=3,frameon=False,fontsize=10)
    fig.subplots_adjust(left=.065,right=.99,bottom=.09,top=.83,hspace=.55,wspace=.2)
    save(fig,directory,'victim')


def trajectories(data,directory):
    """Prespecified representative W8/W9/W12 traces retain all thirty-two steps."""
    fig,axes=plt.subplots(6,5,figsize=(18,16),sharex=True,sharey=True)
    lookup={(c['epoch'],c['h'],c['f'],c['direction'],c['w']):c for c in data['trajectory']}
    ymax=max(max(c['datawalk']['values']) for c in lookup.values())+.6
    plotted=0
    for row,(w,direction) in enumerate((w,d) for w in (8,9,12) for d in (0,1)):
        for epoch in range(5):
            ax=axes[row,epoch]
            for h,color,marker in ((1,A,'o'),(2,C,'s')):
                cell=lookup[f'epoch-{epoch}',h,128,direction,w]
                ax.plot(range(1,33),cell['datawalk']['values'],color=color,marker=marker,markersize=2.5,linewidth=1.1)
                for step,count in enumerate(cell['counts'],1):
                    if count[5]:ax.scatter(step,count[4],marker='x',color='#222222',s=25,zorder=5)
                plotted+=1
            ax.axvspan(16.5,24.5,color='#e5eff8',zorder=-3);ax.axvspan(24.5,32.5,color='#eeeeee',zorder=-3)
            style(ax,.5,32.5,[1,8,16,24,32],ymax)
            if row==0:ax.set_title(f'Epoch {epoch}'+(' · reversed cells' if epoch%2 else ''),fontsize=10)
            if epoch==0:ax.set_ylabel(f'W{w} · '+('reverse' if direction else 'forward')+'\n0x34 / window',fontsize=10)
            if row==5:ax.set_xlabel('Measured step (all 32 retained)',fontsize=9)
    assert plotted==60
    fig.suptitle('Representative full trajectories: W8, W9 and W12, F128',fontsize=16,y=.995)
    fig.text(.5,.975,'All mappings/orders/families retained. Blue band = preceding eight (17–24); grey band = final eight (25–32).',ha='center',fontsize=10)
    fig.legend(handles=families_legend([Line2D([0],[0],color='#222222',marker='x',linestyle='none',label='ITLB walk > 0')]),
               loc='upper center',bbox_to_anchor=(.5,.964),ncol=3,frameon=False,fontsize=10)
    fig.subplots_adjust(left=.06,right=.99,bottom=.045,top=.924,hspace=.23,wspace=.15)
    save(fig,directory,'trajectory')


def victim_windows(data,directory):
    """Every one of 3840 victim windows is visible, including ITLB activity."""
    lookup={(c['epoch'],c['h'],c['direction'],c['k']):c for c in data['victim_cells']}
    fig,axes=plt.subplots(4,5,figsize=(18,13),sharex=True,sharey=True)
    maximum=max(v for c in lookup.values() for v in c['datawalk']);plotted=0
    for row,(direction,h) in enumerate((d,h) for d in (0,1) for h in (1,2)):
        for epoch in range(5):
            ax=axes[row,epoch];cells=[lookup[f'epoch-{epoch}',h,direction,k] for k in range(12)]
            matrix=[[c['datawalk'][r] for c in cells] for r in range(16)]
            image=ax.imshow(matrix,cmap='Blues',vmin=0,vmax=max(1,maximum),aspect='auto',interpolation='none')
            for k,cell in enumerate(cells):
                for r,count in enumerate(cell['counts']):
                    if count[5]:ax.scatter(k,r,color='#222222',marker='x',s=24)
            plotted+=16*12
            ax.set_xticks([0,4,8,11]);ax.set_yticks([0,7,15]);ax.tick_params(labelsize=8)
            ax.set_title(f'E{epoch}: {sum(v>0 for r in matrix for v in r)}/192 walk windows',fontsize=10)
            if epoch==0:
                ax.set_ylabel(('A / H1' if h==1 else 'C / H2')+' · '+('reverse' if direction else 'forward')+'\nPreparation trial (from 0)',fontsize=10)
            if row==3:ax.set_xlabel('Competitor pages K',fontsize=9)
    assert plotted==3840
    fig.suptitle('Victim windows: every trial, K, family, competitor order and mapping',fontsize=16,y=.995)
    fig.text(.5,.971,'Raw 0x34 counts; black × marks ITLB activity without subtraction. Repeated preparation is not an architectural reset.',ha='center',fontsize=10)
    fig.subplots_adjust(left=.07,right=.93,bottom=.055,top=.937,hspace=.27,wspace=.2)
    color_ax=fig.add_axes([.95,.34,.012,.36]);fig.colorbar(image,cax=color_ax,ticks=range(max(1,maximum)+1),label='0x34 / window')
    save(fig,directory,'victim-windows')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary',type=Path,default=Path(__file__).with_name('summary.json'))
    parser.add_argument('--analysis',type=Path,default=Path(__file__).with_name('analysis.json'))
    parser.add_argument('--outdir',type=Path,default=Path(__file__).parent)
    parser.add_argument('--refresh-analysis',action='store_true',help='Recompute the analysis from the audited public summary before plotting')
    args=parser.parse_args();source=args.summary.read_bytes();summary=json.loads(source)
    expected=analyze_capacity(summary['runs'][0]);expected['input_sha256']=hashlib.sha256(source).hexdigest()
    if args.refresh_analysis:args.analysis.write_text(json.dumps(expected,indent=2)+'\n')
    result=json.loads(args.analysis.read_text());assert result==json.loads(json.dumps(expected)), 'analysis or exact input SHA differs'
    matplotlib.rcParams.update({'font.family':'DejaVu Sans','svg.fonttype':'none','svg.hashsalt':'tlb-capacity-v1'})
    working_set(result,args.outdir);victims(result,args.outdir);trajectories(result,args.outdir);victim_windows(result,args.outdir)
    print(json.dumps({'working_set_curves':15,'victim_curves':10,'representative_trajectory_series':60,'victim_windows':3840}))


if __name__=='__main__':main()
