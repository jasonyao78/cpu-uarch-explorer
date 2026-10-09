#!/usr/bin/env python3
"""Run exactly two single-shot qualification mappings, retaining all private raw.

Purpose: establish cold/hot and independent/serial discriminability at N0;
Singleton diagnosis: docs/design/2026-10-10-cold-load-model.md.
never infer ROB entries. Contract: docs/design/2026-10-09-cold-pair-qualification.md.
Root owns the device exclusively; no frequency/governor/thermal modifications.
"""
import argparse
import copy
from datetime import datetime,timezone
import hashlib
import itertools
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from runner.executor.adb import AdbExecutor
from runner.environment.android_state import collect_android_state
from runner.environment.policy import evaluate_preconditions_full
from runner.environment.journal import default_store
MODE='rob-cold-pair-qualify'
PROTOCOL='docs/design/2026-10-09-cold-pair-qualification.md'
BUILD='docs/reviews/evidence/2026-10-09-cold-pair/build.json'
PLAN='docs/reviews/evidence/2026-10-09-cold-pair/plan.json'
DRIVER='tools/diagnostic/run_sm8650_cold_pair.py'
PROFILE='configs/platforms/redmi-k70pro-01.json'
EVENTS=('0x11','0x8','0x3','0x17','0x34','0x37')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
def same(a,b):
    if type(a) is not type(b):return False
    if type(b) is dict:return set(a)==set(b) and all(same(a[k],v) for k,v in b.items())
    if type(b) is list:return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
    return a==b

def fields(actual,expected):
    if type(actual) is not dict or not all(same(actual.get(k),v) for k,v in expected.items()):
        raise ValueError('requested/actual typed identity mismatch')


def specification(profile='pair'):
    """Two prospective profiles; legacy defaults never silently adopt singletons."""
    if profile not in ('pair','singletons'):raise ValueError('unregistered profile')
    if profile=='pair':return dict(mode=MODE,protocol=PROTOCOL,build=BUILD,plan=PLAN,members=['P','S','E'],cells=24,windows=3072)
    return dict(mode='rob-cold-load-model',protocol='docs/design/2026-10-10-cold-load-model.md',
      build='docs/reviews/evidence/2026-10-10-cold-load-model/build.json',
      plan='docs/reviews/evidence/2026-10-10-cold-load-model/plan.json',members=['P','S','E','A','B'],cells=40,windows=5120)

def plan(profile='pair'):
    """The fixed N0 2-mapping budget; no exploratory runtime parameters."""
    spec=specification(profile)
    return {'mode':spec['mode'],'processes':2,'windows':spec['windows'],'trials':64,'cells_per_trial':spec['cells'],
            'masks':[0,4096],'swaps':[0,1],'members':spec['members'],'states':['hot','cold'],
            'warmup_calls':128,'n':0,'mapping_bytes':8192,
            'conditions':[{'name':'epoch-'+str(e),'args':['--epoch',str(e),'-n','0','--trials','64','--pin','7','--pmu-type','8']+(['--singletons'] if profile=='singletons' else [])} for e in (0,1)]}

def matrix(epoch,profile='pair'):
    """Independent Python expectation for the actual C rotation/reversal producer."""
    if type(epoch) is not int or epoch not in (0,1):raise ValueError('invalid epoch')
    spec=specification(profile)
    base=list(itertools.product((0,4096),(0,1),spec['members'],('hot','cold')))
    rows=[]
    for trial in range(64):
        order=base[trial%len(base):]+base[:trial%len(base)]
        if (trial+epoch)%2:order.reverse()
        rows.extend(dict(epoch=epoch,trial=trial,mask=m,swap=s,member=u,state=c) for m,s,u,c in order)
    return rows

def validate_config(config,epoch,export=None,profile='pair'):
    spec=specification(profile)
    expected={'type':'config','version':2 if profile=='singletons' else 1,'probe':'rob-load-model' if profile=='singletons' else 'rob-cold-pair','n':0,'trials':64,'epoch':epoch,
      'matrix_cells_per_trial':spec['cells'],'windows':spec['windows']//2,'memory_bytes':8192,'mapping_alignment':8192,
      'node_offsets':[0,4096],'masks':[0,4096],'members':spec['members'],'states':['hot','cold'],
      'warmup_calls':128,'internal_clock':'cntvct_el0','code_bytes':116,'kernel_instructions':29,
      'pin':7,'pmu_type':8,'events':[17,8,3,23,52,55],'exclude_kernel':True,'exclude_hv':True,'backing_requested':'4k'}
    if profile=='singletons':expected['singletons_requested']=True
    elif 'singletons_requested' in config:raise ValueError('unexpected singleton identity')
    fields(config,expected)
    if export is None:
        if 'export' in config:raise ValueError('measurement unexpectedly export-only')
    else:fields(config,{'export':export})

def validate(records,epoch,profile='pair'):
    """A complete process only; no fallback, prefix rescue or fake metrics."""
    spec=specification(profile)
    if len(records)!=spec['windows']//2+3:raise ValueError('cold-pair record count mismatch')
    config,runtime,*tail=records;final=tail[-1];rounds=tail[:-1]
    validate_config(config,epoch,profile=profile)
    fields(runtime,{'type':'runtime','cpu':7,'cache_line_bytes':64,'mapping_alignment_verified':True,
      'raw_self_pointer_verified':True,'code_address_mod64':0,'cache_maintenance_completed':True})
    if type(runtime.get('cntfrq_hz')) is not int or not 0<runtime['cntfrq_hz']<=1000000000:raise ValueError('invalid clock frequency')
    ids=runtime.get('event_ids')
    if type(ids) is not list or len(ids)!=6 or any(type(x) is not int or not 0<x<2**64 for x in ids) or len(set(ids))!=6:raise ValueError('PMU event ID coverage')
    fields(final,{'type':'backing-final'})
    backing={'kernel_page_kb':4,'mmu_page_kb':4,'anon_huge_kb':0,'rss_kb':8,'swap_kb':0,'no_huge':True}
    fields(runtime.get('initial_backing'),backing);fields(final.get('backing'),backing)
    for row,expected in zip(rounds,matrix(epoch,profile)):
        fields(row,dict(type='round',**expected))
        if type(row.get('ticks')) is not int or not 0<=row['ticks']<2**64:raise ValueError('invalid internal ticks')
        if any(type(row.get(k)) is not int or not 0<row[k]<2**64 for k in ('enabled','running')) or row['enabled']!=row['running']:raise ValueError('empty or multiplexed PMU window')
        counts=row.get('metrics')
        if type(counts) is not dict or set(counts)!=set(EVENTS) or any(type(v) is not int or not 0<=v<2**64 for v in counts.values()):raise ValueError('invalid raw integer PMU counts')
        if counts['0x11']<=0 or not 29<=counts['0x8']<=1029:raise ValueError('cycles or retired quantity mismatch')
    return records

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary',type=Path,required=True);parser.add_argument('--host-exporter',type=Path,required=True)
    parser.add_argument('--profile',choices=('pair','singletons'),default='pair')
    args=parser.parse_args(argv)
    spec=specification(args.profile);protocol_path=spec['protocol'];build_path=spec['build'];plan_path=spec['plan']
    launch=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    for rel in (protocol_path,build_path,plan_path,DRIVER):
        if hashlib.sha256(subprocess.check_output(['git','show',launch+':'+rel],cwd=ROOT)).hexdigest()!=sha(ROOT/rel):raise RuntimeError('STOP uncommitted launch source '+rel)
    build=json.loads((ROOT/build_path).read_text());actual_plan=json.loads((ROOT/plan_path).read_text())
    if not same(actual_plan,plan(args.profile)) or build['plan_path']!=plan_path or build['plan_sha256']!=sha(ROOT/plan_path):raise RuntimeError('STOP unregistered plan')
    if build['binaries']['rob_cold_pair']!=sha(args.binary):raise RuntimeError('STOP binary digest')
    for rel,digest in build['source_sha256'].items():
        if sha(ROOT/rel)!=digest or hashlib.sha256(subprocess.check_output(['git','show',build['source_commit']+':'+rel],cwd=ROOT)).hexdigest()!=digest:raise RuntimeError('STOP source drift '+rel)
    if default_store().unfinished():raise RuntimeError('STOP unfinished environment journal')
    devices=subprocess.check_output(['adb','devices'],text=True).splitlines()[1:]
    if sum(r.endswith('\tdevice') for r in devices)!=1:raise RuntimeError('STOP exactly one online device required')
    ex=AdbExecutor(timeout_s=120)
    for name in ('ptr_chase','rob_window_probe','tlb_local_pair','tlb_history','tlb_capacity','rob_cold_pair'):
        result=ex.execute(['pidof',name])
        if result.returncode!=1 or result.stdout.strip():raise RuntimeError('STOP active probe or ownership check failed')
    policy=copy.deepcopy(json.loads((ROOT/PROFILE).read_text())['environment_profiles']['charging-thermal']['measurement_environment'])
    policy['preconditions']['cpufreq_governor']='walt'
    out=ROOT/'data/private'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+spec['mode']);out.mkdir(parents=True,exist_ok=False)
    shutil.copy2(__file__,out/'driver.py');write(out/'environment-policy.json',policy)
    manifest={'purpose':__doc__,'mode':spec['mode'],'target':'redmi-k70pro-01','source_branch':subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
      'source_head':launch,'binary_source_head':build['source_commit'],'binary_sha256':sha(args.binary),
      'source_sha256':build['source_sha256'],'driver_sha256':sha(__file__),'build_evidence_path':build_path,'build_evidence_sha256':sha(ROOT/build_path),
      'protocol_path':protocol_path,'protocol_sha256':sha(ROOT/protocol_path),'plan_path':plan_path,'plan_sha256':sha(ROOT/plan_path),
      'conditions':actual_plan['conditions'],'results':[],'status':'started'}
    write(out/'manifest.json',manifest);print('OUT',out,flush=True)
    def inspect(name):
        state=collect_android_state(ex);violations,warnings=evaluate_preconditions_full(state,policy)
        write(out/(name+'-environment.json'),{'snapshot':state,'violations':violations,'warnings':warnings})
        if violations or warnings:raise RuntimeError('STOP environment '+name+': '+str(violations)+' '+str(warnings))
    try:
        inspect('initial');remote='/data/local/tmp/cpu-uarch/rob_cold_pair'
        subprocess.run(['adb','push',str(args.binary),remote],check=True,capture_output=True)
        for command in (['chmod','755',remote],['sha256sum',remote]):
            result=ex.execute(command)
            if result.returncode or (command[0]=='sha256sum' and result.stdout.split()[0]!=manifest['binary_sha256']):raise RuntimeError('STOP deploy check')
        identity=ex.execute(['su','-c','cat /sys/devices/system/cpu/cpu7/regs/identification/midr_el1; getconf PAGESIZE'])
        if identity.returncode or [int(x,0) for x in identity.stdout.split()]!=[0x410fd821,4096]:raise RuntimeError('STOP target identity')
        manifest.update(midr='0x410fd821',base_page_bytes=4096)
        for epoch,c in enumerate(actual_plan['conditions']):
            name=c['name'];time.sleep(15);inspect(name+'-pre');generated={}
            for mask,member in itertools.product((0,4096),spec['members']):
                key='m'+str(mask)+'-'+member;f=out/(name+'-'+key+'.bin')
                r=subprocess.run([str(args.host_exporter),*c['args'],'--mask',str(mask),'--member',member,'--write-asm',str(f)],capture_output=True,text=True,check=True)
                config=json.loads(r.stdout);validate_config(config,epoch,{'mask':mask,'member':member},args.profile);generated[key]={'sha256':sha(f),'config':config}
            start=time.monotonic();result=ex.execute(['su','-c',shlex.join([remote,*c['args']])])
            (out/(name+'.stdout.jsonl')).write_text(result.stdout);(out/(name+'.stderr.log')).write_text(result.stderr)
            entry={'name':name,'exit_code':result.returncode,'timed_out':result.timed_out,'wall_seconds':time.monotonic()-start,
              'stdout_sha256':sha(out/(name+'.stdout.jsonl')),'generated_code':generated};manifest['results'].append(entry);write(out/'manifest.json',manifest)
            if result.returncode or result.timed_out or result.stderr:raise RuntimeError('STOP process failure '+name)
            records=[json.loads(x) for x in result.stdout.splitlines()];validate(records,epoch,args.profile);inspect(name+'-post')
            print('OK',name,str(spec['windows']//2)+' windows',round(entry['wall_seconds'],3),flush=True)
        manifest['status']='complete'
    except Exception as error:
        manifest['status']='stopped';manifest['reason']=str(error);raise
    finally:
        write(out/'manifest.json',manifest)
        try:inspect('final')
        except Exception as error:manifest['status']='stopped';manifest['final_environment_error']=str(error);write(out/'manifest.json',manifest)
    if 'final_environment_error' in manifest:raise RuntimeError(manifest['final_environment_error'])
    return 0
if __name__=='__main__':raise SystemExit(main())
