#!/usr/bin/env python3
"""Render every measured TLB-history trajectory and victim sample.

Inputs are the audited, address-free summary.json and analysis.json beside this
script. Requires matplotlib. Regenerate with ``python plot.py``; no raw/private
files, hardware access, interpolation, window rejection or confidence interval.
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
from tools.diagnostic.tlb_history_analysis import analyze


def save(figure, directory, name):
    """PNG preview and SVG export share the exact same plotted observations."""
    figure.savefig(directory/(name+'.png'),dpi=180,metadata={'Software':'TLB history evidence plot'})
    svg = directory/(name+'.svg')
    figure.savefig(svg,metadata={'Date':None,'Creator':'TLB history evidence plot'})
    # Matplotlib emits spaces before path-data newlines; normalize Git hygiene.
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    plt.close(figure)


def trajectories(analysis, directory):
    rows = analysis['trajectory']
    specs = [(128,8,0),(128,8,1),(128,9,0),(128,9,1),
             (512,8,0),(512,8,1),(512,9,0),(512,9,1),(0,8,0),(0,12,0)]
    fig, axes = plt.subplots(10,5,figsize=(18,24),sharex=True,sharey=True)
    maximum = max(v for cell in rows for v in cell['datawalk']['values'])
    styles = {(1,6):('#0072B2','--'),(1,12):('#0072B2','-'),
              (2,6):('#D55E00','--'),(2,12):('#D55E00','-')}
    plotted = 0
    for ri,(f,w,direction) in enumerate(specs):
        for epoch in range(5):
            ax = axes[ri,epoch]
            selected = [c for c in rows if (c['epoch'],c['f'],c['w'],c['direction'])==
                        (f'epoch-{epoch}',f,w,direction)]
            for cell in selected:
                color, style = styles[cell['h'],cell['history']]
                ax.plot(range(1,17),cell['datawalk']['values'],color=color,linestyle=style,
                        marker='o' if cell['h']==1 else 's',markersize=2.5,linewidth=1.25)
                # ITLB activity is preserved and marked; it is never subtracted.
                for step,count in enumerate(cell['counts'],1):
                    if count[5]:
                        ax.scatter(step,count[4],marker='x',color='#222222',s=30,zorder=5)
                plotted += 1
            ax.axvspan(12.5,16.5,color='#eeeeee',zorder=-2)
            ax.axhline(0,color='#999999',linewidth=.5,zorder=-1)
            ax.grid(axis='y',color='#dddddd',linewidth=.5)
            ax.set_xlim(.5,16.5); ax.set_ylim(-.4,maximum+.6)
            ax.set_xticks([1,8,16]); ax.tick_params(labelsize=8)
            if ri==0:
                ax.set_title(f'Epoch {epoch}'+(' · reversed cells' if epoch%2 else ''),fontsize=10)
            if epoch==0:
                ax.set_ylabel(f'F{f} · W{w} · '+('reverse' if direction else 'forward')+'\n0x34 / window',fontsize=9)
            if ri==len(specs)-1:
                ax.set_xlabel('Measured step (all 16 kept)',fontsize=9)
    assert plotted==140
    legend = [Line2D([0],[0],color=color,linestyle=style,marker='o' if h==1 else 's',
                     markersize=4,label=f'{"A / H1" if h==1 else "C / H2"}, history {hist}')
              for (h,hist),(color,style) in styles.items()]
    legend.append(Line2D([0],[0],color='#222222',marker='x',linestyle='none',label='ITLB walk > 0 in this window'))
    fig.suptitle('TLB history: all 140 measured trajectories',fontsize=17,y=.994)
    fig.text(.5,.975,'Each column is one mapping process; no cross-epoch averaging. Grey band = last four steps. F0/F512 use history 12.',
             ha='center',fontsize=10)
    fig.legend(handles=legend,loc='upper center',bbox_to_anchor=(.5,.964),ncol=5,frameon=False,fontsize=9)
    fig.subplots_adjust(left=.075,right=.99,bottom=.035,top=.935,hspace=.28,wspace=.13)
    save(fig,directory,'trajectory')


def victims(analysis, directory):
    bundles = analysis['victim']
    lookup = {(c['epoch'],c['h'],c['history']):c for c in bundles}
    fig, axes = plt.subplots(5,5,figsize=(18,17),gridspec_kw={'height_ratios':[1,1,1,1,1.05]})
    specs = [(1,6),(1,12),(2,6),(2,12)]
    maximum = max(s['datawalk'] for c in bundles for v in c['victims'] for s in v['samples'])
    samples = 0
    for row,(h,history) in enumerate(specs):
        for epoch in range(5):
            cell = lookup[f'epoch-{epoch}',h,history]
            matrix = [[None]*8 for _ in range(8)]
            for victim in cell['victims']:
                for sample in victim['samples']:
                    matrix[sample['trial']][victim['victim']] = sample['datawalk']
                    samples += 1
            assert all(v is not None for trial in matrix for v in trial)
            ax = axes[row,epoch]
            image = ax.imshow(matrix,vmin=0,vmax=max(1,maximum),cmap='Blues',aspect='auto',interpolation='none')
            ax.set_xticks(range(8)); ax.set_yticks(range(8)); ax.tick_params(labelsize=8)
            ax.set_title(f'Σ window rates={cell["walk_rate_sum"]:g}; trace step1={cell["trajectory_step1_datawalk"]}',fontsize=9)
            if epoch==0:
                ax.set_ylabel(f'{"A / H1" if h==1 else "C / H2"} · history {history}\nPreparation trial',fontsize=10)
            if row==3:
                ax.set_xlabel('Victim index',fontsize=9)
            if epoch==4 and h==1 and history==12:
                for spine in ax.spines.values():
                    spine.set_edgecolor('#CC3311'); spine.set_linewidth(2)
    assert samples==1280
    for epoch in range(5):
        ax = axes[4,epoch]
        selected = [lookup[f'epoch-{epoch}',h,hist] for h,hist in specs]
        ax.bar(range(4),[c['walk_rate_sum'] for c in selected],width=.5,color='#56B4E9',label='Σ single-page window rates')
        ax.scatter(range(4),[c['trajectory_step1_datawalk'] for c in selected],color='#222222',marker='D',s=30,
                   label='Whole-circle trace step1',zorder=4)
        ax.set_xticks(range(4),['A6','A12','C6','C12']); ax.set_ylim(-.15,8.7)
        ax.tick_params(labelsize=9); ax.grid(axis='y',color='#dddddd',linewidth=.5)
        ax.set_title(f'Epoch {epoch}: separate prepared windows',fontsize=10)
        if epoch==0:
            ax.set_ylabel('Rates sum / walk count\n(different estimands)',fontsize=9)
    fig.suptitle('Single-page probes: every one of 1280 windows retained',fontsize=17,y=.995)
    fig.text(.5,.975,'Columns: epochs 0–4. Heatmaps: raw 0x34 counts by trial and victim; position=(victim−trial) mod 8.',ha='center',fontsize=10)
    fig.text(.5,.96,'Repeated preparation is not a reset. Window walk rates are not certified residency probabilities. All single-page counts here are 0 or 1.',
             ha='center',fontsize=10)
    for epoch in range(5):
        axes[0,epoch].text(.5,1.22,f'Epoch {epoch}',ha='center',transform=axes[0,epoch].transAxes,fontsize=11,fontweight='bold')
    fig.subplots_adjust(left=.065,right=.93,bottom=.065,top=.915,hspace=.44,wspace=.25)
    color_ax = fig.add_axes([.947,.38,.014,.4])
    fig.colorbar(image,cax=color_ax,ticks=range(max(1,maximum)+1),label='0x34 count / window')
    handles,labels = axes[4,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.5,.017),ncol=2,frameon=False,fontsize=10)
    save(fig,directory,'victim')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary',type=Path,default=Path(__file__).with_name('summary.json'))
    parser.add_argument('--analysis',type=Path,default=Path(__file__).with_name('analysis.json'))
    parser.add_argument('--outdir',type=Path,default=Path(__file__).parent)
    args = parser.parse_args()
    source = args.summary.read_bytes()
    summary = json.loads(source); result = json.loads(args.analysis.read_text())
    assert result['input_sha256']==hashlib.sha256(source).hexdigest(), 'analysis input SHA mismatch'
    expected = analyze(summary['runs'][0]); expected['input_sha256']=result['input_sha256']
    # JSON histogram keys are strings after loading, unlike in-memory int keys.
    assert json.loads(json.dumps(expected))==result, 'analysis differs from the current audited consumer'
    matplotlib.rcParams.update({'font.family':'DejaVu Sans','svg.fonttype':'none','svg.hashsalt':'tlb-history-v1'})
    trajectories(result,args.outdir); victims(result,args.outdir)
    print(json.dumps({'trajectory_series':140,'victim_windows':1280,'output':str(args.outdir)}))


if __name__=='__main__':
    main()
