"""New measurement boundary; same generated programs and frozen marker gates."""
import contextlib
from tools.diagnostic import rob_fenced_issue_analysis as old
from tools.diagnostic.pmu_own_counter_analysis import direct,MASK
from tools.diagnostic.analyze_cold_pair import _require,_same
MODE='rob-direct-fenced-marker'
EVIDENCE='docs/reviews/evidence/2026-10-13-rob-direct-fenced'
PROTOCOL='docs/design/2026-10-13-rob-direct-fenced-marker.md'
CONSUMER='tools/diagnostic/rob_direct_fenced_analysis.py'
DRIVER='tools/diagnostic/run_sm8650_rob_direct_fenced.py'
def conditions():return old.conditions('qualification')

def expected(k):
 p=old.expected(k);p[0].update(version=2,probe=MODE,routine_warmup_calls=4,count_source='owned-direct-roi',perf_config1=3);p[0].pop('full_window_warmup_calls');return p

def check_roi(z):
 arrays=[z.get(k) for k in ('roi_before','roi_after','kernel_before','kernel_after','counts','fd_counts')];_require(all(type(a)is list and len(a)==6 for a in arrays),'six ROI arrays');pre,post,kb,ka,counts,fd=arrays
 _require(all(type(v)is int and 0<=v<=MASK for a in (kb,ka,counts,fd) for v in a),'six ROI unsigned');a=[direct(v) for v in pre];b=[direct(v) for v in post]
 _require(len({v['index'] for v in pre})==len({v['index'] for v in post})==6,'six unique own counters')
 _require(all(x[k]==y[k] for x,y in zip(pre,post) for k in ('sequence_before','sequence_after','index','offset')),'ROI current metadata changed')
 _require(all(lo<=x<=y<=hi for lo,hi,x,y in zip(kb,ka,a,b)),'ROI absolute FD binding');_require(_same(fd,[y-x for x,y in zip(kb,ka)]) and _same(counts,[(y-x)&MASK for x,y in zip(a,b)]) and all(x<=y for x,y in zip(counts,fd)),'ROI FD delta envelope')

@contextlib.contextmanager
def adapter():
 previous=(old.MODE,old.expected)
 # Capture original function to avoid recursion while reusing pure math.
 original=old.expected
 def actual(k):
  p=original(k);p[0].update(version=2,probe=MODE,routine_warmup_calls=4,count_source='owned-direct-roi',perf_config1=3);p[0].pop('full_window_warmup_calls');return p
 old.MODE=MODE;old.expected=actual
 try:yield
 finally:old.MODE,old.expected=previous

def audit_process(rr,c,plans):
 _require(_same(plans,{str(k):expected(k) for k in (16,32)}),'direct actual producer plans')
 if rr and rr[-1].get('type')!='failure':
  for z in rr[6:-1]:check_roi(z)
 with adapter():return old._audit_records(rr,c)

def analyze(rows):
 with adapter():v=old.analyze(dict(mode=MODE,phase='qualification',processes=6,rows=rows))
 v['status']='DIRECT_FENCED_MARKER_QUALIFIED' if all(p['qualified'] for p in v['processes']) else 'DIRECT_FENCED_MARKER_NOT_QUALIFIED';v['count_source']='owned-direct-roi';return v
