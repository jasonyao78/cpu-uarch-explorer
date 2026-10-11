#!/usr/bin/env python3
"""Zero/nonzero MOVZ response; no physical allocation factor.

Contract: docs/design/2026-10-11-rob-zero-value.md. Reuse immutable
instruction encodings from rob_resource_analysis; only the finite request and
counter semantics differ. Raw sources and complete matrix precede naming.
"""
import argparse,hashlib,itertools,json,math,statistics as st,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.diagnostic.analyze_cold_pair import _require,_same,_fields
from tools.diagnostic import rob_resource_analysis as code_model
MODE='rob-zero-value';CLASSES=('nop','movi','mov0','movr');GRID=(0,128,256,704)
EVENTS=(17,8,58,59,33133,35)
PROTOCOL='docs/design/2026-10-11-rob-zero-value.md'
BUILD='docs/reviews/evidence/2026-10-11-rob-zero-value/build.json'
PLAN='docs/reviews/evidence/2026-10-11-rob-zero-value/plan.json'
identity=code_model.identity
def expected_code(condition):
 """Independent legacy A64 words; only MOVZ immediate bit 5 changes for mov0."""
 if identity(condition)[0]!='mov0':return code_model.expected_code(condition)
 import copy,struct
 c=copy.deepcopy(condition);c['args'][c['args'].index('-t')+1]='movi';blob=code_model.expected_code(c)
 words=list(struct.unpack('<'+'I'*(len(blob)//4),blob));changed=0
 for i,w in enumerate(words):
  if w&0xffffffe0==0xd2800020 and 4<=w&31<=11:words[i]=w^32;changed+=1
 _require(changed==2*identity(condition)[2],'zero expected filler count')
 return struct.pack('<'+'I'*len(words),*words)


def expected_config(condition):
 """Same C generation math; exact new six-event order is part of identity."""
 c=code_model.expected_config(condition);c['events']=list(EVENTS);return c

def registered_plan():
 """Interleaved class controls at each anchor/N; entire second epoch reversed."""
 cells=list(itertools.product(('none','fsqrt'),GRID,CLASSES));conditions=[]
 for e in (0,1):
  for a,n,c in (cells if e==0 else reversed(cells)):
   args=['-i','131072','-r','3','--pin','7','--pmu-type','8','-e','0x3a','-e','0x3b','-e','0x816d','-e','0x23','-t',c,'-a',a,'--chain','16','--align','0','-n',str(n)]
   conditions.append(dict(name=f'e{e}-{c}-{a}-k16-a0-n{n}',args=args))
 return dict(mode=MODE,processes=64,windows=192,conditions=conditions,exports={c['name']:dict(config=expected_config(c),sha256=hashlib.sha256(expected_code(c)).hexdigest()) for c in conditions})

def audit_process(records,condition,code):
 """Actual C config/code to exact three raw windows; runtime/PMU kept typed."""
 _require(type(records) is list and len(records)==5,'zero process record coverage')
 c=expected_config(condition);_require(_same(records[0],c),'zero requested/actual config mismatch')
 _require(code==expected_code(condition),'zero exact emitted code mismatch')
 runtime=records[1]
 _fields(runtime,dict(type='runtime',fpcr=0,cpu=7,loop_address_mod64=0,ring_nodes=0,distinct_lines_per_call=0,mapping_4k_verified=None,backing_verified=None,backing_page_bytes=0,backing_info=None),'zero runtime mismatch')
 ids=runtime.get('event_ids');_require(type(ids) is list and len(ids)==6 and all(type(x) is int and 0<x<2**64 for x in ids) and len(set(ids))==6,'zero event ID coverage/type')
 expected_ir=131072*c['loop_instructions']+17
 for i,r in enumerate(records[2:]):
  _fields(r,dict(type='round',round=i,serial=False,pair_step=0,backing_verified=None,backing_before=None,backing_after=None),'zero round order/type')
  _require(all(type(r.get(k)) is int and 0<r[k]<2**64 for k in ('ns','enabled','running')) and r['enabled']==r['running'],'zero empty/mux/timing window')
  counts=r.get('metrics');_require(type(counts) is dict and set(counts)=={hex(e) for e in EVENTS} and all(type(x) is int and 0<=x<2**64 for x in counts.values()) and counts['0x11']>0,'zero event uint64/coverage')
  _require(abs(counts['0x8']-expected_ir)<=max(1000,.01*expected_ir),'zero retired instruction mismatch')
 return dict(condition=condition['name'],class_name=c['class'],anchor=c['anchor'],n=c['n'],epoch=int(condition['name'][1]),cycles=[r['metrics']['0x11']/131072 for r in records[2:]],counts={hex(e):[r['metrics'][hex(e)]/131072 for r in records[2:]] for e in EVENTS})

def analyze(rows):
 """All counter samples and signed control responses, with no capacity fitting."""
 plan=registered_plan();_require(type(rows) is list and len(rows)==64,'zero whole matrix required');cells={}
 for r,c in zip(rows,plan['conditions']):
  cls,a,n=identity(c);e=int(c['name'][1]);_fields(r,dict(condition=c['name'],class_name=cls,anchor=a,n=n,epoch=e),'zero curve identity/order/type mismatch')
  counts=r.get('counts');v=r.get('cycles')
  _require(type(counts) is dict and set(counts)=={hex(x) for x in EVENTS} and all(type(v) is list and len(v)==3 and all(type(x) in (int,float) and math.isfinite(x) and x>=0 for x in v) for v in counts.values()),'zero complete finite counts')
  _require(type(v) is list and len(v)==3 and all(type(x) in (int,float) and math.isfinite(x) and x>0 for x in v) and v==counts['0x11'],'zero cycle/count flow mismatch')
  cells[cls,a,n,e]=r
 points=[]
 for r in rows:
  cls,a,n,e=(r[k] for k in ('class_name','anchor','n','epoch'));events={}
  baseline=cells[cls,a,0,e]
  for event,values in r['counts'].items():
   mid=st.median(values);delta=mid-st.median(baseline['counts'][event])
   events[event]=dict(raw=values,median=mid,range_fraction=(max(values)-min(values))/mid if mid else (None if max(values)>0 else 0),delta_from_n0=delta,per_filler_delta=delta/(2*n) if n else None)
   if event in ('0x816d','0x23'):events[event]['cycle_fraction']=[x/y for x,y in zip(values,r['cycles'])]
  points.append(dict(condition=r['condition'],class_name=cls,anchor=a,n=n,epoch=e,events=events))
 gates=[]
 def spread(v):
  mid=st.median(v);return (max(v)-min(v))/mid if mid else (math.inf if max(v)>0 else 0)
 for e in (0,1):
  for cls in ('movi','mov0'):
   r=cells[cls,'fsqrt',128,e];ratio=st.median([x/y for x,y in zip(r['counts']['0x816d'],r['cycles'])])
   gates.append(dict(class_name=cls,epoch=e,test='rename-response',value=ratio,limit=.5 if cls=='movi' else .1,passed=ratio>=.5 if cls=='movi' else ratio<=.1))
   for event in ('0x11','0x816d'):
    v=spread(r['counts'][event]);gates.append(dict(class_name=cls,epoch=e,event=event,test='three-round-spread',value=v if math.isfinite(v) else None,limit=.1,passed=v<=.1))
 def cycle_status(event):
  ratios=[x/y for r in rows for x,y in zip(r['counts'][event],r['cycles'])]
  if any(v>1 for v in ratios):return 'cycle-semantics-incompatible'
  return 'positive-response-observed-semantics-not-certified' if any(v>0 for v in ratios) else 'positive-response-not-observed'
 ratios=[]
 for e in (0,1):ratios.append(dict(epoch=e,mov0_over_movi=st.median(cells['mov0','none',128,e]['cycles'])/st.median(cells['movi','none',128,e]['cycles'])))
 qualified=all(g['passed'] for g in gates) and cycle_status('0x816d')!='cycle-semantics-incompatible'
 return dict(mode=MODE,processes=64,windows=192,zero_value_status='qualified-limited-response' if qualified else 'not-qualified',primary_gates=gates,none_n128_cycle_ratios=ratios,rename_status=cycle_status('0x816d'),frontend_status=cycle_status('0x23'),points=points,physical_allocation_certified=False,naming_limit='value-associated rename response only; no general elimination or ROB/PRF capacity certification')

def audit_raw(path):
 """Committed launch/source/plan/env audit plus strict real-config/code/raw check."""
 m=json.loads((path/'manifest.json').read_text());plan=registered_plan()
 expected_files={'manifest.json','driver.py','environment-policy.json','initial-environment.json','final-environment.json'}|{c['name']+suffix for c in plan['conditions'] for suffix in ('.stdout.jsonl','.stderr.log','-single.bin','-pre-environment.json','-post-environment.json')}
 _require({p.name for p in path.iterdir()}==expected_files and all(p.is_file() for p in path.iterdir()),'zero complete raw file inventory mismatch')
 _fields(m,dict(mode=MODE,status='complete',target='redmi-k70pro-01',midr='0x410fd821',base_page_bytes=4096,protocol_path=PROTOCOL,build_evidence_path=BUILD,plan_path=PLAN),'zero manifest typed identity mismatch')
 _require(_same(m.get('conditions'),plan['conditions']) and type(m.get('results')) is list and len(m['results'])==64,'zero requested coverage')
 blob=subprocess.check_output(['git','show',m['source_head']+':'+PLAN],cwd=ROOT);_require(_same(json.loads(blob),plan),'zero registered actual plan mismatch')
 build=json.loads(subprocess.check_output(['git','show',m['source_head']+':'+BUILD],cwd=ROOT))
 _require(build.get('plan_path')==PLAN and hashlib.sha256(blob).hexdigest()==m.get('plan_sha256')==build.get('plan_sha256'),'zero plan SHA does not flow through manifest/build')
 rows=[]
 for entry,c in zip(m['results'],plan['conditions']):
  name=c['name'];_fields(entry,dict(name=name,exit_code=0,timed_out=False),'zero result order/status')
  _require((path/(name+'.stderr.log')).read_bytes()==b'','zero unexpected stderr')
  records=[json.loads(l) for l in (path/(name+'.stdout.jsonl')).read_text().splitlines()];code=(path/(name+'-single.bin')).read_bytes()
  _require(_same(entry.get('generated_code'),{'single':plan['exports'][name]}),'zero export config/hash binding')
  rows.append(audit_process(records,c,code))
 from tools.diagnostic.summarize_sm8650_minimal import summarize
 summary=summarize(path)
 return summary,rows,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(path.iterdir()) if p.is_file()}

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('raw',type=Path);p.add_argument('--summary-output',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(argv)
 summary,rows,hashes=audit_raw(a.raw);result=analyze(rows);s=json.dumps(summary,indent=2)+'\n'
 result.update(data_origin='device-raw',input_sha256=hashlib.sha256(s.encode()).hexdigest(),all_raw_sha256=hashes,rows=rows)
 a.summary_output.write_text(s);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ('zero_value_status','rename_status','frontend_status')}))
if __name__=='__main__':main()
