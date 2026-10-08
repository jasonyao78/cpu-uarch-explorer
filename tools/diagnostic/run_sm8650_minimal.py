#!/usr/bin/env python3
"""Bounded standalone probe experiments; raw output stays in data/private.

Purpose: test nested TLB contrasts and effective-window controls, NOT formal A1
or a ROB entry estimate. Single device/operator; no environment mutation.
Protocol: docs/design/2026-10-09-minimal-tlb-rob-probes.md.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from runner.executor.adb import AdbExecutor
from runner.environment.android_state import collect_android_state
from runner.environment.policy import evaluate_preconditions_full
from runner.environment.journal import default_store


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def conditions(mode):
    if mode.startswith('tlb'):
        # One excluded smoke epoch, then five mapping epochs (target200 primary).
        return [(f'epoch-{i}', (['200','--reverse'] if i%2 else ['200'])) for i in range(1 if mode == 'tlb-smoke' else 5)]
    base = ['-i', '131072', '-r', '3', '--pin', '7', '--pmu-type', '8',
            '-e', '0x03', '-e', '0x17', '-e', '0x34', '-e', '0x02']
    if mode == 'rob-qualify':
        rows = [(f'miss-m{mb}-n0', ['-t','nop','-n','0','-a','miss','-m',str(mb),'--paired']) for mb in (1,16)]
        rows += [(f'fsqrt-chain{k}-n0', ['-t','nop','-n','0','-a','fsqrt','--chain',str(k)]) for k in (1,8,16)]
        rows += [(f'none-n{n}', ['-t','nop','-n',str(n),'-a','none']) for n in (0,512)]
        return [(name, base + args) for name,args in rows]
    rows = []
    for epoch in range(2):
        for cls in ('nop','add'):
            for n in (0,64,128,192,256,384,512,768,1024):
                rows.append((f'e{epoch}-miss-{cls}-n{n}', base + ['-t',cls,'-n',str(n),'-a','miss','-m','16','--paired']))
        for chain in (8,16):
            for n in (0,64,128,256,512,768,1024):
                rows.append((f'e{epoch}-fsqrt-k{chain}-n{n}', base + ['-t','nop','-n',str(n),'-a','fsqrt','--chain',str(chain)]))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['tlb-smoke','tlb','rob-qualify','rob-window'])
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--host-exporter', type=Path)
    args = parser.parse_args()
    if default_store().unfinished():
        raise SystemExit('STOP unfinished environment journal')
    # Never print or persist serial identifiers.
    devices = subprocess.check_output(['adb','devices'], text=True).splitlines()[1:]
    if sum(line.endswith('\tdevice') for line in devices) != 1:
        raise SystemExit('STOP exactly one online target required')
    ex = AdbExecutor(timeout_s=120)
    for name in ('ptr_chase','rob_window_probe','tlb_local_pair'):
        active = ex.execute(['pidof',name])
        if active.returncode != 1 or active.stdout.strip():
            raise SystemExit('STOP active probe or failed process check')
    profile = json.loads((ROOT/'configs/platforms/redmi-k70pro-01.json').read_text())
    policy = copy.deepcopy(profile['environment_profiles']['charging-thermal']['measurement_environment'])
    policy['preconditions']['cpufreq_governor'] = 'walt'
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = ROOT/'data/private'/f'{stamp}-{args.mode}'
    out.mkdir(parents=True, exist_ok=False)
    shutil.copy2(__file__, out/'driver.py')
    rows = conditions(args.mode)
    manifest = {'purpose':__doc__, 'mode':args.mode, 'target':'redmi-k70pro-01',
                'source_branch':subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
                'source_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                'binary_sha256':sha(args.binary),'driver_sha256':sha(__file__),
                'protocol_sha256':sha(ROOT/'docs/design/2026-10-09-minimal-tlb-rob-probes.md'),
                'conditions':[{'name':name,'args':opts} for name,opts in rows], 'results':[], 'status':'started'}
    write(out/'manifest.json',manifest)
    write(out/'environment-policy.json',policy)
    print('OUT',out,flush=True)

    def inspect(name):
        state=collect_android_state(ex)
        violations,warnings=evaluate_preconditions_full(state,policy)
        write(out/f'{name}-environment.json',{'snapshot':state,'violations':violations,'warnings':warnings})
        if violations or warnings: raise RuntimeError(f'STOP environment {name}: {violations} {warnings}')

    try:
        inspect('initial')
        remote='/data/local/tmp/cpu-uarch/'+('tlb_local_pair' if args.mode.startswith('tlb') else 'rob_window_probe')
        subprocess.run(['adb','push',str(args.binary),remote],check=True,capture_output=True)
        result=ex.execute(['chmod','755',remote])
        if result.returncode: raise RuntimeError('deploy-chmod')
        result=ex.execute(['sha256sum',remote])
        if result.returncode or result.stdout.split()[0]!=manifest['binary_sha256']: raise RuntimeError('deploy-sha256')
        identity=ex.execute(['su','-c','cat /sys/devices/system/cpu/cpu7/regs/identification/midr_el1; getconf PAGESIZE'])
        if identity.returncode or [int(v,0) for v in identity.stdout.split()]!=[0x410fd821,4096]: raise RuntimeError('target-identity')
        manifest['midr']='0x410fd821'; manifest['base_page_bytes']=4096
        for name,opts in rows:
            inspect(name+'-pre')
            result_code={}
            if args.host_exporter:
                # Save exact generated bytes for both members of same-VA paired control.
                export_opts=[v for v in opts if v!='--paired']
                for member in (['parallel','serial'] if '--paired' in opts else ['single']):
                    path=out/f'{name}-{member}.bin'
                    command=[str(args.host_exporter),*export_opts]
                    if member=='serial': command+=['--serial']
                    p=subprocess.run(command+['--write-asm',str(path)],capture_output=True,text=True,check=True)
                    result_code[member]={'sha256':sha(path),'config':json.loads(p.stdout)}
            t=time.monotonic()
            result=ex.execute(['su','-c',shlex.join([remote,*opts])])
            (out/f'{name}.stdout.jsonl').write_text(result.stdout)
            (out/f'{name}.stderr.log').write_text(result.stderr)
            entry={'name':name,'exit_code':result.returncode,'timed_out':result.timed_out,
                   'wall_seconds':time.monotonic()-t,'stdout_sha256':sha(out/f'{name}.stdout.jsonl'),
                   'generated_code':result_code}
            manifest['results'].append(entry); write(out/'manifest.json',manifest)
            if result.returncode != 0: raise RuntimeError('STOP probe failure '+name)
            parsed=[json.loads(line) for line in result.stdout.splitlines()]
            if any(row['type']=='failure' for row in parsed): raise RuntimeError('STOP structured failure')
            rounds=[row for row in parsed if row['type']=='round']
            expected=800 if args.mode.startswith('tlb') else 6 if '--paired' in opts else 3
            if len(rounds)!=expected: raise RuntimeError('STOP wrong round count')
            if any(row['enabled']<=0 or row['enabled']!=row['running'] for row in rounds): raise RuntimeError('STOP mux/empty window')
            if args.mode.startswith('rob'):
                config=next(row for row in parsed if row['type']=='config')
                expected_retired=config['iterations']*config['loop_instructions']+config['loop_offset']//4+1
                for row in rounds:
                    retired=row['metrics']['0x8']
                    if abs(retired-expected_retired)>max(1000,expected_retired*0.01):
                        raise RuntimeError('STOP generated instructions vs INST_RETIRED mismatch')
            inspect(name+'-post')
            print('OK',name,round(len(rounds) and entry['wall_seconds'],3),flush=True)
        manifest['status']='complete'
    except Exception as error:
        manifest['status']='stopped'; manifest['reason']=str(error)
        raise
    finally:
        write(out/'manifest.json',manifest)
        # Always keep final observed state; no restore needed because no settings changed.
        try: inspect('final')
        except Exception as error:
            manifest['final_environment_error']=str(error); write(out/'manifest.json',manifest)
    return 0

if __name__=='__main__':
    raise SystemExit(main())
