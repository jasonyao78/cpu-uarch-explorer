#!/usr/bin/env python3
"""Finite instruction-stream hiding response, never a physical ROB count.

Contract: docs/design/2026-10-11-rob-filler-resource.md. Strict raw acceptance
precedes independent class/epoch curves; generated instruction counts do not
calibrate fusion, physical allocation, PRF or scheduler occupancy.
"""
import argparse,hashlib,itertools,json,math,statistics as st,struct,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.diagnostic.analyze_cold_pair import _require,_same,_fields
MODE='rob-resource';CLASSES=('nop','add','movi','movr','fadd');GRID=(0,128,256,384,512,704,768)
EVENTS=(17,8,3,23,52,2)
PROTOCOL='docs/design/2026-10-11-rob-filler-resource.md'
BUILD='docs/reviews/evidence/2026-10-11-rob-resource/build.json'
PLAN='docs/reviews/evidence/2026-10-11-rob-resource/plan.json'

def identity(condition):
 """Parse registered request, never infer identity from count or a default."""
 a=condition['args'];return a[a.index('-t')+1],a[a.index('-a')+1],int(a[a.index('-n')+1])

def expected_config(condition):
 """Independent configuration math for unchanged canonical C producer."""
 c,a,n=identity(condition);anchors=32 if a=='fsqrt' else 0;instructions=2*n+anchors+2
 return dict(type='config',version=2,**{'class':c},anchor=a,n=n,iterations=131072,rounds=3,serial=False,paired=False,asymmetric=False,chain=16,fsqrt_operand_bits='0x3ff0000000000000',loop_offset=64,loop_mod64=0,branch_offset=(16+instructions-1)*4,loop_instructions=instructions,fillers_per_iteration=2*n,anchors_per_iteration=anchors,code_bytes=(16+instructions+1)*4,memory_bytes=0,backing_requested='4k',chase_seed=42,pmu_type=8,exclude_kernel=True,exclude_hv=True,events=list(EVENTS))

def expected_code(condition):
 """Independent A64 instruction words, including exact branch and register sets."""
 c,a,n=identity(condition);words=[0xaa0203ee]
 def imm(r,v):
  words.append(0xd2800000|((v&65535)<<5)|r)
  for shift in (16,32,48):words.append(0xf2800000|(((v>>shift)&65535)<<5)|((shift//16)<<21)|r)
 imm(16,0x1111);imm(17,0x2222)
 if a=='fsqrt' or c=='fadd':
  imm(15,0x3ff0000000000000);words.extend(0x9e670000|(15<<5)|r for r in (0,16,17))
 while len(words)<16:words.append(0xd503201f)
 for side in (0,1):
  if a=='fsqrt':words.extend([0x1e61c000]*16)
  for j in range(n):
   d=4+j%8
   words.append({'nop':0xd503201f,'add':0x8b000000|(17<<16)|(16<<5)|d,'movi':0xd2800000|(1<<5)|d,'movr':0xaa0003e0|(16<<16)|d,'fadd':0x1e602800|(17<<16)|(16<<5)|(4+j%4)}[c])
 words.append(0xf1000463);branch=len(words);words.append(0x54000001|(((16-branch)&0x7ffff)<<5));words.append(0xd65f03c0)
 return struct.pack('<'+'I'*len(words),*words)

def registered_plan():
 """Fixed finite order and independent byte/config expectation for every case."""
 cells=list(itertools.product(CLASSES,('none','fsqrt'),GRID));conditions=[]
 for e in (0,1):
  for c,a,n in (cells if e==0 else reversed(cells)):
   args=['-i','131072','-r','3','--pin','7','--pmu-type','8','-e','0x03','-e','0x17','-e','0x34','-e','0x02','-t',c,'-a',a,'--chain','16','--align','0','-n',str(n)]
   conditions.append(dict(name=f'e{e}-{c}-{a}-k16-a0-n{n}',args=args))
 return dict(mode=MODE,processes=140,windows=420,conditions=conditions,exports={c['name']:dict(config=expected_config(c),sha256=hashlib.sha256(expected_code(c)).hexdigest()) for c in conditions})

def audit_code(config,code):
 """Frozen request-derived bytes, not just a hash matching a mutable exporter."""
 candidates=[c for c in registered_plan()['conditions'] if expected_config(c)==config]
 _require(len(candidates)==2,'resource actual code identity mismatch')
 _require(_same(config,expected_config(candidates[0])) and code==expected_code(candidates[0]),'resource code/config/register/branch mismatch')

def audit_process(records,condition,code):
 """Actual C config/code to exact three raw windows; runtime/PMU kept typed."""
 _require(type(records) is list and len(records)==5,'resource process record coverage')
 c=expected_config(condition);_require(_same(records[0],c),'resource requested/actual config mismatch')
 _require(code==expected_code(condition),'resource exact emitted code mismatch')
 runtime=records[1]
 _fields(runtime,dict(type='runtime',fpcr=0,cpu=7,loop_address_mod64=0,ring_nodes=0,distinct_lines_per_call=0,mapping_4k_verified=None,backing_verified=None,backing_page_bytes=0,backing_info=None),'resource runtime mismatch')
 ids=runtime.get('event_ids');_require(type(ids) is list and len(ids)==6 and all(type(x) is int and 0<x<2**64 for x in ids) and len(set(ids))==6,'resource event ID coverage/type')
 expected_ir=131072*c['loop_instructions']+17
 for i,r in enumerate(records[2:]):
  _fields(r,dict(type='round',round=i,serial=False,pair_step=0,backing_verified=None,backing_before=None,backing_after=None),'resource round order/type')
  _require(all(type(r.get(k)) is int and 0<r[k]<2**64 for k in ('ns','enabled','running')) and r['enabled']==r['running'],'resource empty/mux/timing window')
  counts=r.get('metrics');_require(type(counts) is dict and set(counts)=={hex(e) for e in EVENTS} and all(type(x) is int and 0<=x<2**64 for x in counts.values()) and counts['0x11']>0,'resource event uint64/coverage')
  _require(abs(counts['0x8']-expected_ir)<=max(1000,.01*expected_ir),'resource retired instruction mismatch')
 return dict(condition=condition['name'],class_name=c['class'],anchor=c['anchor'],n=c['n'],epoch=int(condition['name'][1]),cycles=[r['metrics']['0x11']/131072 for r in records[2:]],counts={hex(e):[r['metrics'][hex(e)]/131072 for r in records[2:]] for e in EVENTS})

def analyze(rows):
 """All 140 cases and two epochs before naming; effects are per-iteration cycles."""
 plan=registered_plan();_require(type(rows) is list and len(rows)==140,'resource whole matrix required');cells={}
 for r,c in zip(rows,plan['conditions']):
  cls,a,n=identity(c);e=int(c['name'][1]);_fields(r,dict(condition=c['name'],class_name=cls,anchor=a,n=n,epoch=e),'resource curve identity/order/type mismatch')
  v=r.get('cycles');counts=r.get('counts')
  _require(type(v) is list and len(v)==3 and all(type(x) in (float,int) and math.isfinite(x) and x>0 for x in v),'resource three positive finite cycles')
  _require(type(counts) is dict and set(counts)=={hex(x) for x in EVENTS} and all(type(v) is list and len(v)==3 and all(type(x) in (float,int) and math.isfinite(x) and x>=0 for x in v) for v in counts.values()),'resource count curve shape')
  _require(v==counts['0x11'],'resource cycles/counts do not flow consistently')
  cells[cls,a,n,e]=r
 classes=[]
 for cls in CLASSES:
  points=[];stable=True
  for n in GRID:
   by_epoch=[]
   for e in (0,1):
    a=cells[cls,'fsqrt',n,e]['cycles'];none=cells[cls,'none',n,e]['cycles'];base=st.median(cells[cls,'fsqrt',0,e]['cycles']);mid=st.median(a);spread=(max(a)-min(a))/mid
    stable &= spread<=.1
    by_epoch.append(dict(epoch=e,anchor_cycles=a,none_cycles=none,anchor_median=mid,none_median=st.median(none),baseline=base,difference=mid-base,range_fraction=spread,supply_reference=max(base,st.median(none)),supply_residual=mid-max(base,st.median(none))))
   points.append(dict(n=n,epochs=by_epoch))
  def low(p):return all(abs(e['difference'])<=1 for e in p['epochs'])
  def high(p):return all(e['difference']>1 for e in p['epochs'])
  status='ambiguous';interval=None;reason='epoch-conflict-negative-or-nonmonotonic'
  if not stable:reason='anchor-round-spread-over-10-percent'
  elif all(low(p) for p in points):status='no-onset-through768';reason='all-in-band'
  else:
   for i in range(1,len(points)):
    if all(low(p) for p in points[:i]) and all(high(p) for p in points[i:]):
     if i==len(points)-1:status='right-censored';reason='one-high-point-only'
     elif i==1:status='left-censored';reason='first-nonzero-grid-already-high'
     else:status='interval';interval=[points[i-1]['n'],points[i]['n']];reason='two-epoch-persistent-effect'
     break
  classes.append(dict(class_name=cls,status=status,interval=interval,reason=reason,anchor_stable=stable,points=points))
 return dict(mode=MODE,processes=140,windows=420,classes=classes,physical_rob_entries_certified=False,naming_limit='effective hiding response to instruction streams; allocation/fusion/PRF/RS/frontend not identified')

def audit_raw(path):
 """Committed launch/source/plan/env audit plus strict real-config/code/raw check."""
 m=json.loads((path/'manifest.json').read_text());plan=registered_plan()
 _fields(m,dict(mode=MODE,status='complete',target='redmi-k70pro-01',midr='0x410fd821',base_page_bytes=4096,protocol_path=PROTOCOL,build_evidence_path=BUILD,plan_path=PLAN),'resource manifest typed identity mismatch')
 _require(_same(m.get('conditions'),plan['conditions']) and type(m.get('results')) is list and len(m['results'])==140,'resource requested coverage')
 blob=subprocess.check_output(['git','show',m['source_head']+':'+PLAN],cwd=ROOT);_require(_same(json.loads(blob),plan),'resource registered actual plan mismatch')
 rows=[]
 for entry,c in zip(m['results'],plan['conditions']):
  name=c['name'];_fields(entry,dict(name=name,exit_code=0,timed_out=False),'resource result order/status')
  _require((path/(name+'.stderr.log')).read_bytes()==b'','resource unexpected stderr')
  records=[json.loads(l) for l in (path/(name+'.stdout.jsonl')).read_text().splitlines()];code=(path/(name+'-single.bin')).read_bytes()
  _require(_same(entry.get('generated_code'),{'single':plan['exports'][name]}),'resource export config/hash binding')
  rows.append(audit_process(records,c,code))
 from tools.diagnostic.summarize_sm8650_minimal import summarize
 summary=summarize(path)
 return summary,rows,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(path.iterdir()) if p.is_file()}

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('raw',type=Path);p.add_argument('--summary-output',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(argv)
 summary,rows,hashes=audit_raw(a.raw);result=analyze(rows);s=json.dumps(summary,indent=2)+'\n'
 result.update(data_origin='device-raw',input_sha256=hashlib.sha256(s.encode()).hexdigest(),all_raw_sha256=hashes,rows=rows)
 a.summary_output.write_text(s);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({c['class_name']:c['status'] for c in result['classes']}))
if __name__=='__main__':main()
