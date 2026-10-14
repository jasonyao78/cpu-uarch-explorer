"""Exact producer ordinals with a bounded, named technical invalid channel.

Contract docs/design/2026-10-14-bounded-owned-roi-packets.md. Never imputes
metrics; hardware metadata validation is performed by each caller afterward.
"""
from tools.diagnostic.analyze_cold_pair import _require

def decode(records,schedule):
 """按注册256/512身份解包；state冲突、漏样、重复或多invalid均拒绝。"""
 # v2.0只扩展已注册512；旧256身份与有限invalid预算不放宽。
 wanted={(s['trial'],s['position']):s for s in schedule};_require(len(schedule) in (256,512) and len(wanted)==len(schedule),'packet native schedule uniqueness');bins={k:{} for k in wanted}
 for z in records:
  _require(type(z)is dict and type(z.get('trial'))is int and type(z.get('position'))is int,'packet identity types');key=z['trial'],z['position'];_require(key in wanted,'packet unknown identity');kind=z.get('type');
  if len(schedule)==512:_require(wanted[key].get('state') in ('hot','cold') and z.get('state')==wanted[key]['state'],'packet state identity')
  _require(kind in ('round','warm-roi','invalid-packet','rejected-window'),'packet unknown record type')
  item=(kind,z.get('ordinal')) if kind=='warm-roi' else (kind,None)
  if kind=='warm-roi':_require(type(z.get('ordinal'))is int and 0<=z['ordinal']<4,'packet warm ordinal')
  _require(item not in bins[key],'packet duplicate');bins[key][item]=z
 valid=[];invalid=[]
 for s in schedule:
  key=s['trial'],s['position'];group=bins[key];inv=group.get(('invalid-packet',None));rej=group.get(('rejected-window',None));warm=[group.get(('warm-roi',j)) for j in range(4)];sample=group.get(('round',None))
  if inv is None:
   _require(rej is None and sample is not None and all(z is not None for z in warm) and len(group)==5,'packet valid complete coverage');valid.append(dict(identity=key,schedule=s,warm=warm,sample=sample))
  else:
   count=inv.get('completed_warm');stage=inv.get('stage');_require(inv.get('metrics')=={} and inv.get('failure')=={'reason':'ROI-metadata-changed'} and type(count)is int and 0<=count<=4 and type(stage)is int and stage==count,'packet invalid named reason/stage');_require(rej is not None and rej.get('reason')=='ROI-metadata-changed' and rej.get('stage')==stage and type(rej.get('stage'))is int and rej.get('metrics')=={} and rej.get('hardware_values_usable')is False,'packet rejection trace');_require(sample is None and all((z is not None)==(j<count) for j,z in enumerate(warm)) and len(group)==count+2,'packet invalid partial coverage');invalid.append(dict(identity=key,schedule=s,warm=warm[:count],invalid=inv,rejected=rej))
 _require(len(invalid)<=1 and len(valid)+len(invalid)==len(schedule),'packet finite metadata budget');return dict(valid=valid,invalid=invalid)

def validate_rejection(z,indices):
 """Only an observed before/after binding change permits a packet rejection."""
 pre=z.get('roi_before_metadata');post=z.get('roi_after_metadata');raw=z.get('captured_register_words');_require(type(pre)is list and type(post)is list and len(pre)==len(post)==6 and type(raw)is list and len(raw)==12 and all(type(v)is int and 0<=v<1<<64 for v in raw),'packet rejected capture')
 for side in (pre,post):
  for v in side:_require(type(v)is dict and v.get('cap')is True and type(v.get('index'))is int and 1<=v['index']<=32 and v.get('width')==64 and type(v.get('sequence_before'))is int and v['sequence_before']==v.get('sequence_after') and not(v['sequence_before']&1) and type(v.get('offset'))is int,'packet rejected live metadata')
 _require([v['index'] for v in pre]==indices,'packet rejection compiled own indices');_require(any(a[k]!=b[k] for a,b in zip(pre,post) for k in ('sequence_before','index','offset')),'packet rejection must observe a change')

def runtime(rr,idx):
 """Own memory, current binding and final attempt coverage remain mandatory."""
 z=rr[5];end=rr[-1];_require(z.get('type')=='runtime' and z.get('cpu')==7 and z.get('fpcr')==0 and z.get('hwcap_sb')is True,'packet runtime target');addrs=[z.get(n+'_base') for n in ('code','near','far','output')];_require(all(type(v)is int and v>0 and v%4096==0 for v in addrs) and len(set(addrs))==4 and z.get('hardware_buffer_base')==addrs[3]+64,'packet own addresses');ids=z.get('event_ids');_require(type(ids)is list and len(ids)==6 and len(set(ids))==6 and all(type(v)is int and 0<v<1<<64 for v in ids),'packet own IDs');binding=z.get('initial_binding');_require(type(binding)is list and len(binding)==6,'packet initial binding')
 for v,i in zip(binding,idx):_require(v.get('cap')is True and type(v.get('index'))is int and v['index']==i and v.get('width')==64 and type(v.get('sequence_before'))is int and v['sequence_before']==v.get('sequence_after') and not(v['sequence_before']&1) and type(v.get('offset'))is int,'packet initial live metadata')
 def pfn(v):_require(type(v)is int and 0<=v<1<<64 and v>>63 and not(v&(1<<62)) and v&((1<<55)-1),'packet PFN');return v&((1<<55)-1)
 a=z.get('pagemap_before');b=end.get('pagemap_after');_require(end.get('type')=='final' and end.get('fds_closed')is True and type(a)is list and type(b)is list and len(a)==len(b)==4 and [pfn(v) for v in a]==[pfn(v) for v in b] and len(set(pfn(v) for v in a))==4,'packet stable final backing');return z

def audit_envelope(group,idx):
 from tools.diagnostic.rob_direct_fenced_analysis import check_roi
 _require(len(group)>0,'packet nonempty envelope')
 for z in group:
  check_roi(z);_require([v['index'] for v in z['roi_before']]==idx,'packet current compiled words');_require(type(z.get('enabled'))is int and type(z.get('running'))is int and z['enabled']>0 and z['running']==z['enabled'],'packet noMUX')
 for field in ('kernel_before','kernel_after','fd_counts','enabled','running'):_require(all(z[field]==group[0][field] for z in group),'packet shared real FD envelope')

def final_counts(final,packets):
 """终态必须逐项等于注册解析所得attempt/valid/invalid，不能补零。"""
 for k,v in dict(attempted_packets=len(packets['valid'])+len(packets['invalid']),valid_packets=len(packets['valid']),invalid_packets=len(packets['invalid'])).items():_require(type(final.get(k))is int and final[k]==v,'packet final accounting '+k)

def paired_trials(cells,*roles):
 """Finite invalids shrink a named intersection; missing samples never become zero."""
 values=[t for t in range(32) if all((t,*role) in cells for role in roles)];_require(len(values)>=31,'packet comparison requires31of32');return values
