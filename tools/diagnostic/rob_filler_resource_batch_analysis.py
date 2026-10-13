"""A shared absolute FD envelope contains every individually bound live ROI."""
import copy
from tools.diagnostic import rob_filler_resource_hot_analysis as hot
from tools.diagnostic.analyze_cold_pair import _require,_same
MODE='rob-filler-resource-batch';EVIDENCE='docs/reviews/evidence/2026-10-14-rob-filler-resource-batch'
PROTOCOL='docs/design/2026-10-14-rob-filler-resource-batch.md';CONSUMER='tools/diagnostic/rob_filler_resource_batch_analysis.py';DRIVER='tools/diagnostic/run_sm8650_rob_filler_resource_batch.py'
def expected(n,f,idx=hot.base.register.DEFAULT_INDICES):
 p=hot.expected(n,f,idx);p[0].update(probe=MODE,fd_envelope='four-warm-plus-one-formal',warm_protocol='post-RX-no-syscall-owned-ROI');return p
def conditions():return hot.conditions()
def plans():return {f'{n}-{f}':expected(n,f) for n in (32,64) for f in (0,4,8,12)}
def audit_process(rr,c,registered):
 _require(_same(registered,plans()),'batch native plans');n=int(c['args'][2]);f=int(c['args'][4]);_require(type(rr)is list and len(rr)>=2 and _same(rr[0],expected(n,f)[0]),'batch config')
 if rr[-1].get('type')=='failure':return dict(condition=c['name'],args=c['args'],status='TECHNICAL_FAILURE',failure=rr[-1]['failure'])
 _require(len(rr)==1287,'batch complete 4warm+1formal coverage')
 for i in range(256):
  block=rr[6+5*i:6+5*(i+1)]
  for k in ('kernel_before','kernel_after','fd_counts','enabled','running'):_require(all(_same(z.get(k),block[0].get(k)) for z in block),'batch common actual FD envelope')
 clone=list(rr);cfg=copy.deepcopy(rr[0]);cfg.update(probe=hot.MODE,warm_protocol='post-RX-owned-ROI');cfg.pop('fd_envelope');clone[0]=cfg;row=hot.audit_process(clone,c,hot.plans());row['config']=rr[0];return row
def analyze(rows):
 v=hot.analyze(rows);v['mode']=MODE;v['warm_protocol']='post-RX-no-syscall-owned-ROI';v['fd_envelope']='four-warm-plus-one-formal';return v
