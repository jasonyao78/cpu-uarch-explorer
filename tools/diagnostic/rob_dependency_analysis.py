#!/usr/bin/env python3
"""Matched ADD anchor dependency; no physical allocation factor.

Contract: docs/design/2026-10-11-rob-anchor-dependency.md. Reuse immutable
instruction encodings from rob_resource_analysis; only the finite request and
counter semantics differ. Raw sources and complete matrix precede naming.
"""
import argparse,hashlib,itertools,json,math,statistics as st,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.diagnostic.analyze_cold_pair import _require,_same,_fields
MODE='rob-dependency';GRID=(0,64,128,256)
EVENTS=(17,8,58,59,33133,35)
PROTOCOL='docs/design/2026-10-11-rob-anchor-dependency.md'
BUILD='docs/reviews/evidence/2026-10-11-rob-dependency/build.json'
PLAN='docs/reviews/evidence/2026-10-11-rob-dependency/plan.json'
def identity(c):
 a=c['args'];return a[a.index('--anchor-link')+1],a[a.index('-a')+1],int(a[a.index('--chain')+1]),int(a[a.index('-n')+1])
def expected_config(c):
 """Independent finite config: bridge and actual chain lengths are identity."""
 link,a,k,n=identity(c);anchors=2*k if a=='fsqrt' else 0;ins=2*n+anchors+4
 return dict(type='config',version=2,**{'class':'add'},anchor=a,n=n,iterations=131072,rounds=3,serial=False,paired=False,asymmetric=False,chain=k,fsqrt_operand_bits='0x3ff0000000000000',loop_offset=64,loop_mod64=0,branch_offset=(16+ins-1)*4,loop_instructions=ins,fillers_per_iteration=2*n,anchors_per_iteration=anchors,code_bytes=(16+ins+1)*4,memory_bytes=0,backing_requested='4k',chase_seed=42,pmu_type=8,exclude_kernel=True,exclude_hv=True,events=list(EVENTS),anchor_link=link,bridges_per_iteration=2)
def expected_code(c):
 """Independent A64 words; pair differs only in ADD Rn, with identical values."""
 import struct
 link,a,k,n=identity(c);words=[0xaa0203ee]
 def imm(r,v):
  words.append(0xd2800000|((v&65535)<<5)|r)
  for sh in (16,32,48):words.append(0xf2800000|(((v>>sh)&65535)<<5)|((sh//16)<<21)|r)
 imm(16,0x3ff0000000000000);imm(17,0x2222);imm(15,0x3ff0000000000000);words.extend(0x9e670000|(15<<5)|r for r in (0,16,17))
 for side in (0,1):
  if a=='fsqrt':words.extend([0x1e61c000]*k)
  words.append(0x9e66000c)
  for j in range(n):words.append(0x8b000000|(17<<16)|((12 if link=='dependent' else 16)<<5)|(4+j%8))
 words.append(0xf1000463);branch=len(words);words.extend([0x54000001|(((16-branch)&0x7ffff)<<5),0xd65f03c0]);return struct.pack('<'+'I'*len(words),*words)
def registered_plan():
 cells=[(a,k,n,link) for a,k in (('none',16),('fsqrt',8),('fsqrt',16)) for n in GRID for link in ('independent','dependent')];conditions=[]
 for e in (0,1):
  for a,k,n,link in (cells if e==0 else reversed(cells)):
   args=['-i','131072','-r','3','--pin','7','--pmu-type','8','-e','0x3a','-e','0x3b','-e','0x816d','-e','0x23','-t','add','-a',a,'--chain',str(k),'--align','0','-n',str(n),'--anchor-link',link]
   conditions.append(dict(name=f'e{e}-{link}-{a}-k{k}-a0-n{n}',args=args))
 return dict(mode=MODE,processes=48,windows=144,conditions=conditions,exports={c['name']:dict(config=expected_config(c),sha256=hashlib.sha256(expected_code(c)).hexdigest()) for c in conditions})

def audit_process(records,condition,code):
 """Actual C config/code to exact three raw windows; runtime/PMU kept typed."""
 _require(type(records) is list and len(records)==5,'dependency process record coverage')
 c=expected_config(condition);_require(_same(records[0],c),'dependency requested/actual config mismatch')
 _require(code==expected_code(condition),'dependency exact emitted code mismatch')
 runtime=records[1]
 _fields(runtime,dict(type='runtime',fpcr=0,cpu=7,loop_address_mod64=0,ring_nodes=0,distinct_lines_per_call=0,mapping_4k_verified=None,backing_verified=None,backing_page_bytes=0,backing_info=None),'dependency runtime mismatch')
 ids=runtime.get('event_ids');_require(type(ids) is list and len(ids)==6 and all(type(x) is int and 0<x<2**64 for x in ids) and len(set(ids))==6,'dependency event ID coverage/type')
 expected_ir=131072*c['loop_instructions']+17
 for i,r in enumerate(records[2:]):
  _fields(r,dict(type='round',round=i,serial=False,pair_step=0,backing_verified=None,backing_before=None,backing_after=None),'dependency round order/type')
  _require(all(type(r.get(k)) is int and 0<r[k]<2**64 for k in ('ns','enabled','running')) and r['enabled']==r['running'],'dependency empty/mux/timing window')
  counts=r.get('metrics');_require(type(counts) is dict and set(counts)=={hex(e) for e in EVENTS} and all(type(x) is int and 0<=x<2**64 for x in counts.values()) and counts['0x11']>0,'dependency event uint64/coverage')
  _require(abs(counts['0x8']-expected_ir)<=max(1000,.01*expected_ir),'dependency retired instruction mismatch')
 return dict(condition=condition['name'],class_name=c['class'],anchor=c['anchor'],chain=c['chain'],link=c['anchor_link'],n=c['n'],epoch=int(condition['name'][1]),cycles=[r['metrics']['0x11']/131072 for r in records[2:]],counts={hex(e):[r['metrics'][hex(e)]/131072 for r in records[2:]] for e in EVENTS})

def analyze(rows):
 """Complete data-flow identity and four pre-registered signed contrasts."""
 p=registered_plan();_require(type(rows) is list and len(rows)==48,'dependency whole matrix');cells={};points=[]
 for r,c in zip(rows,p['conditions']):
  link,a,k,n=identity(c);e=int(c['name'][1]);_fields(r,dict(condition=c['name'],class_name='add',anchor=a,chain=k,link=link,n=n,epoch=e),'dependency curve identity/order/type')
  v=r.get('cycles');counts=r.get('counts')
  _require(type(counts) is dict and set(counts)=={hex(x) for x in EVENTS} and all(type(v) is list and len(v)==3 and all(type(x) in (int,float) and math.isfinite(x) and x>=0 for x in v) for v in counts.values()),'dependency finite full count shape')
  _require(type(v) is list and len(v)==3 and all(type(x) in (int,float) and math.isfinite(x) and x>0 for x in v) and v==counts['0x11'],'dependency cycle/count value flow')
  mid=st.median(v);spread=(max(v)-min(v))/mid;cells[link,a,k,n,e]=r
  points.append(dict(r,cycle_median=mid,cycle_range_fraction=spread,stable=spread<=.1,cycle_fractions={event:[x/y for x,y in zip(counts[event],v)] for event in ('0x816d','0x23')}))
 def median(link,a,k,n,e):return st.median(cells[link,a,k,n,e]['cycles'])
 def delta(a,k,n,e):return (median('dependent',a,k,n,e)-median('dependent',a,k,0,e))-(median('independent',a,k,n,e)-median('independent',a,k,0,e))
 contrasts=[]
 for e in (0,1):
  for k in (8,16):
   for n in GRID:
    value=delta('fsqrt',k,n,e)-delta('none',16,n,e);contrasts.append(dict(epoch=e,chain=k,n=n,difference_in_differences=value))
 gates=[]
 for e in (0,1):
  for k in (8,16):
   required=[(link,a,ck,n,e) for link in ('independent','dependent') for a,ck in (('fsqrt',k),('none',16)) for n in (0,128)]
   spreads=[(max(cells[key]['cycles'])-min(cells[key]['cycles']))/st.median(cells[key]['cycles']) for key in required]
   value=delta('fsqrt',k,128,e)-delta('none',16,128,e);gates.append(dict(epoch=e,chain=k,n=128,value=value,strict_lower=5,range_fractions=spreads,passed=value>5 and all(x<=.1 for x in spreads)))
 semantics={event:'cycle-semantics-incompatible' if any(x>y for r in rows for x,y in zip(r['counts'][event],r['cycles'])) else 'observed-response-not-full-structure-semantics-certification' for event in ('0x816d','0x23')}
 return dict(mode=MODE,processes=48,windows=144,dependency_status='dependency-associated-hiding-response' if all(g['passed'] for g in gates) else 'not-qualified',primary_gates=gates,points=points,contrasts=contrasts,cycle_semantics=semantics,physical_allocation_certified=False,naming_limit='finite equal-value source dependency response, not ROB/PRF/RS capacity')

def audit_raw(path):
 """Committed launch/source/plan/env audit plus strict real-config/code/raw check."""
 m=json.loads((path/'manifest.json').read_text());plan=registered_plan()
 expected_files={'manifest.json','driver.py','environment-policy.json','initial-environment.json','final-environment.json'}|{c['name']+suffix for c in plan['conditions'] for suffix in ('.stdout.jsonl','.stderr.log','-single.bin','-pre-environment.json','-post-environment.json')}
 _require({p.name for p in path.iterdir()}==expected_files and all(p.is_file() for p in path.iterdir()),'dependency complete raw file inventory mismatch')
 _fields(m,dict(mode=MODE,status='complete',target='redmi-k70pro-01',midr='0x410fd821',base_page_bytes=4096,protocol_path=PROTOCOL,build_evidence_path=BUILD,plan_path=PLAN),'dependency manifest typed identity mismatch')
 _require(_same(m.get('conditions'),plan['conditions']) and type(m.get('results')) is list and len(m['results'])==48,'dependency requested coverage')
 blob=subprocess.check_output(['git','show',m['source_head']+':'+PLAN],cwd=ROOT);_require(_same(json.loads(blob),plan),'dependency registered actual plan mismatch')
 build=json.loads(subprocess.check_output(['git','show',m['source_head']+':'+BUILD],cwd=ROOT))
 _require(build.get('plan_path')==PLAN and hashlib.sha256(blob).hexdigest()==m.get('plan_sha256')==build.get('plan_sha256'),'dependency plan SHA does not flow through manifest/build')
 rows=[]
 for entry,c in zip(m['results'],plan['conditions']):
  name=c['name'];_fields(entry,dict(name=name,exit_code=0,timed_out=False),'dependency result order/status')
  _require((path/(name+'.stderr.log')).read_bytes()==b'','dependency unexpected stderr')
  records=[json.loads(l) for l in (path/(name+'.stdout.jsonl')).read_text().splitlines()];code=(path/(name+'-single.bin')).read_bytes()
  _require(_same(entry.get('generated_code'),{'single':plan['exports'][name]}),'dependency export config/hash binding')
  rows.append(audit_process(records,c,code))
 from tools.diagnostic.summarize_sm8650_minimal import summarize
 summary=summarize(path)
 return summary,rows,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(path.iterdir()) if p.is_file()}

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('raw',type=Path);p.add_argument('--summary-output',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(argv)
 summary,rows,hashes=audit_raw(a.raw);result=analyze(rows);s=json.dumps(summary,indent=2)+'\n'
 result.update(data_origin='device-raw',input_sha256=hashlib.sha256(s.encode()).hexdigest(),all_raw_sha256=hashes,rows=rows)
 a.summary_output.write_text(s);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ('dependency_status','cycle_semantics')}))
if __name__=='__main__':main()
