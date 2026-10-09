#!/usr/bin/env python3
"""Render the complete target cold-pair batch, including signed paired differences.

Input: this directory's audited qualification.json from
tools/diagnostic/analyze_cold_pair.py. Contract:
docs/design/2026-10-09-cold-pair-qualification.md. Each panel preserves one
mask/epoch/swap identity and all 64 trials for P/S/E. No outlier removal,
empty subtraction, pooling, cycle conversion, fitting, or gate changes.
"""
import json
from pathlib import Path
import statistics

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

DIRECTORY = Path(__file__).resolve().parent
COLORS = {'P': '#0072B2', 'S': '#D55E00', 'E': '#8064A2'}
STATES = ('hot', 'cold', 'delta')
MEMBERS = ('P', 'S', 'E')
ORDER = [(mask, swap) for mask in (0, 4096) for swap in (0, 1)]
matplotlib.rcParams.update({
    'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.titlesize': 10,
    'axes.labelsize': 10, 'svg.hashsalt': 'cold-pair-20261009',
    'svg.fonttype': 'none', 'axes.spines.top': False, 'axes.spines.right': False,
})


def save(fig, name):
    """Stable PNG/SVG metadata; neither output embeds a host path or timestamp."""
    fig.savefig(DIRECTORY / (name + '.png'), dpi=170,
                metadata={'Software': 'cpu-uarch-explorer'})
    svg = DIRECTORY / (name + '.svg')
    fig.savefig(svg, metadata={'Date': None, 'Creator': 'cpu-uarch-explorer'})
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines()) + '\n')
    plt.close(fig)


def panel(ax, candidate, kind):
    """Show every raw value and every same-trial difference; bars are medians/means."""
    labels, extent = [], []
    for group, member in enumerate(MEMBERS):
        values = candidate['members'][member]
        for column, state in enumerate(STATES):
            x = group * 3 + column
            if kind == 'ticks':
                samples = values[state + '_ticks']
                location = statistics.median(samples)
            else:
                samples = values[state + '_counts']['0x3']
                location = statistics.mean(samples)
            if len(samples) != 64:
                raise ValueError('plot requires every trial')
            # Offsets are deterministic trial positions, not random perturbation of y.
            positions = [x + .19 * (2 * trial / 63 - 1) for trial in range(64)]
            color = COLORS[member]
            marker = 's' if state == 'delta' else 'o'
            ax.scatter(positions, samples, s=12, marker=marker, linewidths=.55,
                       edgecolors=color, facecolors='none' if state == 'hot' else color,
                       alpha=.58, zorder=3)
            ax.plot([x - .23, x + .23], [location, location], color='black', lw=1.65,
                    zorder=5)
            if state == 'delta' and member in ('P', 'S'):
                if kind == 'ticks':
                    ax.plot([x - .29, x + .29], [3, 3], color='#555555', lw=1,
                            linestyle=':', zorder=2)
                else:
                    ax.fill_between([x - .29, x + .29], 1.5, 2.5,
                                    color='#ABDDA4', alpha=.32, zorder=1)
            labels.append(member + '\n' + {'hot': 'H', 'cold': 'C', 'delta': 'D'}[state])
            extent.extend(samples)
    ratio = candidate['serial_over_parallel_delta_median']
    if kind == 'ticks':
        text = (f"S D / P D = {ratio:.3f}; P MAD / D = "
                f"{candidate['members']['P']['delta_mad_over_median']:.3f}")
    else:
        text = '; '.join(f"{m} D={candidate['members'][m]['count_delta_means']['0x3']:.3f}"
                         for m in MEMBERS)
    ax.set_title(f"epoch {candidate['epoch']} | mask {candidate['mask']} | swap {candidate['swap']}\n{text}")
    ax.set_xticks(range(9), labels, fontsize=8)
    ax.set_xlim(-.6, 8.6)
    # Each panel gets its own full range. The 178-tick cold outlier and -4-tick
    # empty difference are shown, without trimming or a broken axis.
    low, high = min(0, min(extent)), max(extent)
    padding = max(.5, (high - low) * .1)
    ax.set_ylim(low - padding, high + padding)
    ax.axhline(0, color='#777777', lw=.7, zorder=1)
    ax.grid(axis='y', color='#dddddd', lw=.55, zorder=0)
    ax.set_ylabel('CNTVCT ticks' if kind == 'ticks' else 'Whole PMU window L1 refill count')


def trajectory(candidates):
    """All 64 paired trials in acquisition order; never select a stable suffix."""
    fig, axes = plt.subplots(2, 4, figsize=(17.2, 9.3))
    for epoch in (0, 1):
        for column, (mask, swap) in enumerate(ORDER):
            ax = axes[epoch, column]
            candidate = candidates[epoch, mask, swap]
            for member in MEMBERS:
                samples = candidate['members'][member]['delta_ticks']
                ax.plot(range(64), samples, color=COLORS[member], lw=.8,
                        marker='o', ms=3, label=member, alpha=.8)
            for boundary in (15.5, 31.5, 47.5):
                ax.axvline(boundary, color='#bbbbbb', linestyle=':', lw=.8)
            ax.axhline(0, color='#777777', lw=.7)
            ax.axhline(3, color='#555555', linestyle=':', lw=.8)
            ax.set_title(f'epoch {epoch} | mask {mask} | swap {swap}')
            ax.set_xlim(-1, 64)
            ax.set_xlabel('Trial (0-63, all retained)')
            ax.set_ylabel('Paired cold - hot CNTVCT ticks')
            ax.grid(axis='y', color='#dddddd', lw=.55)
    fig.suptitle('N0 cold-pair: complete paired trajectories within each mapping\n'
                 'No pooling, suffix selection, empty subtraction, or outlier removal',
                 fontsize=15, y=.965)
    fig.legend(*axes[0, 0].get_legend_handles_labels(), loc='lower center',
               ncol=3, frameon=False, bbox_to_anchor=(.5, .05))
    fig.text(.5, .022, 'Every curve contains 64 signed differences. Vertical markers show four descriptive '
             '16-trial blocks, not new qualification cells.\nPanel y ranges differ and retain all tails. '
             'CNTFRQ = 19.2 MHz; no core-cycle conversion.', ha='center', fontsize=9)
    fig.subplots_adjust(left=.055, right=.985, bottom=.15, top=.87, wspace=.38, hspace=.42)
    save(fig, 'trajectory')


def main():
    """Only the fixed N0 device batch can supply these figures."""
    qualification = json.loads((DIRECTORY / 'qualification.json').read_text())
    acceptance = qualification['technical_acceptance']
    if (qualification.get('data_origin') != 'device-raw' or acceptance['passed'] is not True or
            qualification['mode'] != 'rob-cold-pair-qualify' or qualification['windows'] != 3072 or
            acceptance['raw_directory'] != '20261009T160502Z-rob-cold-pair-qualify'):
        raise ValueError('wrong plot input identity')
    candidates = {(c['epoch'], c['mask'], c['swap']): c for c in qualification['candidates']}
    if len(candidates) != 8 or set(candidates) != {(e, m, s) for e in (0, 1) for m, s in ORDER}:
        raise ValueError('incomplete plot matrix')
    for kind, name, subtitle in (
            ('ticks', 'ticks',
             'Internal CNTVCT time: all raw H/C values and signed within-trial D = C - H'),
            ('L1', 'l1-refills',
             'Whole user PMU window L1 refills: hot / cold / signed paired difference')):
        fig, axes = plt.subplots(2, 4, figsize=(17.2, 9.3))
        for epoch in (0, 1):
            for column, (mask, swap) in enumerate(ORDER):
                panel(axes[epoch, column], candidates[epoch, mask, swap], kind)
        fig.suptitle('N0 cold-pair qualification: neither mask qualifies\n' + subtitle,
                     fontsize=15, y=.975)
        handles = [Line2D([], [], marker='o', markerfacecolor='none', color='#555555',
                          linestyle='none', label='H: hot'),
                   Line2D([], [], marker='o', color='#555555', linestyle='none', label='C: cold'),
                   Line2D([], [], marker='s', color='#555555', linestyle='none', label='D: cold - hot')]
        fig.legend(handles=handles, loc='lower center', ncol=3, frameon=False, bbox_to_anchor=(.5, .047))
        statistic = ('Black bars: medians; dotted mark: P/S D median minimum 3 ticks.' if kind == 'ticks'
                     else 'Black bars: arithmetic means; green band: P/S D mean gate [1.5, 2.5].')
        fig.text(.5, .019,
                 '64 trials per group; 3072 raw windows + 1536 paired differences. '
                 'Panel y ranges differ; all tails retained.\n' + statistic +
                 ' E is a sentinel, never subtracted. CNTFRQ = 19.2 MHz; no core-cycle conversion.',
                 ha='center', fontsize=9)
        fig.subplots_adjust(left=.055, right=.985, bottom=.15, top=.87, wspace=.38, hspace=.42)
        save(fig, name)
    trajectory(candidates)


if __name__ == '__main__':
    main()
