"""Actual own binding generates a branch-free, memory-free observer ROI."""
from tools.diagnostic import rob_fenced_issue_analysis as old
NOP=0xd503201f
SAVED_EXPECTED=old.expected
MODE='rob-register-fenced-marker'
EVIDENCE='docs/reviews/evidence/2026-10-13-rob-register-fenced'
PROTOCOL='docs/design/2026-10-13-rob-register-fenced-marker.md'
CONSUMER='tools/diagnostic/rob_register_fenced_analysis.py'
DRIVER='tools/diagnostic/run_sm8650_rob_register_fenced.py'
DEFAULT_INDICES=[32,3,4,5,6,7]
def program_words(k,mode,indices):
 def read(index,register):return [NOP if index==32 else 0xd280000b|((index-1)<<5),NOP if index==32 else 0xd51b9cab,0xd5033fdf,(0xd53b9d00 if index==32 else 0xd53b9d40)|register]
 w=[0xa9bc53f3,0xa9015bf5,0xa90263f7,0xa9036bf9,0xd5033b9f]
 for j,i in enumerate(indices):w+=read(i,20+j)
 w+=[0xd50330ff]+SAVED_EXPECTED(k)[1+mode]['words'][:-1]
 for j,i in enumerate(indices):w+=read(i,[13,14,15,16,17,19][j])
 return w+[0xd50330ff,0xa90054b4,0xa9015cb6,0xa90264b8,0xa90338ad,0xa90440af,0xa9054cb1,0xa9436bf9,0xa94263f7,0xa9415bf5,0xa8c453f3,0xd65f03c0]
def warm_words(k,w):
 out=list(w);out[5:29]=[NOP]*24;suffix=len(w)-36;out[suffix:suffix+24]=[NOP]*24;out[suffix+25:suffix+31]=[NOP]*6;return out

import contextlib
from tools.diagnostic.analyze_cold_pair import _require,_same
from tools.diagnostic.rob_direct_fenced_analysis import check_roi

def indices(v):
 _require(type(v)is list and len(v)==6 and len(set(v))==6 and all(type(x)is int and 1<=x<=32 for x in v),'own six indices');return v

def expected(k,idx=DEFAULT_INDICES):
 idx=indices(idx);p=SAVED_EXPECTED(k);p[0].update(version=3,probe=MODE,routine_warmup_calls=4,count_source='owned-register-only-roi',perf_config1=3);p[0].pop('full_window_warmup_calls')
 for mode,z in enumerate(p[1:5]):
  w=program_words(k,mode,idx);z.update(words=w,code_bytes=4*len(w),counter_indices=idx,warm_words=warm_words(k,w))
 return p

def conditions():return old.conditions('qualification')

@contextlib.contextmanager
def adapter(idx):
 prior=(old.MODE,old.expected);old.MODE=MODE;old.expected=lambda k:expected(k,idx)
 try:yield
 finally:old.MODE,old.expected=prior

def audit_process(rr,c,plans):
 _require(_same(plans,{str(k):expected(k) for k in (16,32)}),'register symbolic actual plans');k=int(c['args'][2]);_require(type(rr)is list and len(rr)>=2 and _same(rr[0],expected(k)[0]),'register config')
 if rr[-1].get('type')=='failure':
  _require(rr[-1].get('metrics')=={} and type(rr[-1].get('failure'))is dict,'register failure');return dict(condition=c['name'],args=c['args'],status='TECHNICAL_FAILURE',failure=rr[-1]['failure'])
 _require(len(rr)==263,'register full coverage');runtime=rr[5];idx=indices(runtime.get('counter_indices'));binding=runtime.get('initial_binding');_require(type(binding)is list and len(binding)==6,'initial own binding')
 for v,index in zip(binding,idx):
  _require(type(v)is dict and v.get('cap')is True and type(v.get('index'))is int and v['index']==index and v.get('width')==64 and type(v.get('sequence_before'))is int and v['sequence_before']==v.get('sequence_after') and not(v['sequence_before']&1) and type(v.get('offset'))is int,'initial current metadata')
 _require(runtime.get('hardware_buffer_base')==runtime.get('output_base',0)+64,'own timestamp buffer')
 for z in rr[6:-1]:
  check_roi(z);_require([v['index'] for v in z['roi_before']]==idx,'actual words versus current binding')
 with adapter(idx):return old._audit_records(rr,c)

def analyze(rows):
 original_audit=old._audit_records;previous_mode=old.MODE
 def current(rr,c):
  with adapter(indices(rr[5]['counter_indices'])):return original_audit(rr,c)
 old.MODE=MODE;old._audit_records=current
 try:v=old.analyze(dict(mode=MODE,phase='qualification',processes=6,rows=rows))
 finally:old._audit_records=original_audit;old.MODE=previous_mode
 v['status']='REGISTER_FENCED_MARKER_QUALIFIED' if all(x['qualified'] for x in v['processes']) else 'REGISTER_FENCED_MARKER_NOT_QUALIFIED';v['count_source']='owned-register-only-roi';return v
