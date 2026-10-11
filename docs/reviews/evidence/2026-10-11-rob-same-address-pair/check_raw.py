#!/usr/bin/env python3
"""Direct raw arithmetic audit; deliberately imports no production model.

Run check_raw.py RAW SUMMARY ANALYSIS OUTPUT. All 480 counts and signed block
contrasts retained; the same root performs this second computational path.
"""
import hashlib,json,statistics as st,subprocess,sys,struct
from pathlib import Path
raw,summary,analysis,output=map(Path,sys.argv[1:]);run=json.loads(summary.read_text());a=json.loads(analysis.read_text());m=json.loads((raw/'manifest.json').read_text());sha=lambda b:hashlib.sha256(b).hexdigest();files={p.name:sha(p.read_bytes()) for p in sorted(raw.iterdir())};assert files==a['all_raw_sha256'];assert sha(summary.read_bytes())==a['input_sha256'];assert m['status']=='complete' and len(m['results'])==15
root=Path(__file__).resolve().parents[4] if 'evidence' in str(__file__) else Path('/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2');head=m['source_head'];blob=lambda p:subprocess.check_output(['git','show',head+':'+p],cwd=root)
for p,key in [(m['protocol_path'],'protocol_sha256'),(m['plan_path'],'plan_sha256'),(m['build_evidence_path'],'build_evidence_sha256'),('tools/diagnostic/run_sm8650_rob_pair.py','driver_sha256')]:assert sha(blob(p))==m[key]
build=json.loads(blob(m['build_evidence_path']));assert build['binaries']['rob_dependency_pair']==m['binary_sha256'];assert build['source_commit']==m['binary_source_head'];assert sha((raw/'driver.py').read_bytes())==m['driver_sha256']
for p,digest in build['source_sha256'].items():assert sha(blob(p))==digest==sha(subprocess.check_output(['git','show',m['binary_source_head']+':'+p],cwd=root))
program_hashes={};blocks=[];sentinels=[];index={};points=[];windows=[];ir_errors=[];bases=[]
for i,(entry,c,rout) in enumerate(zip(m['results'],m['conditions'],run['rows'])):
 e=i//3;anchor,k=[('none',16),('fsqrt',8),('fsqrt',16)][i%3];assert c['name']==entry['name']==rout['condition']==f'e{e}-{anchor}-k{k}' and entry['exit_code']==0 and entry['timed_out'] is False
 data=(raw/(entry['name']+'.stdout.jsonl')).read_bytes();assert sha(data)==entry['stdout_sha256'];assert (raw/(entry['name']+'.stderr.log')).read_bytes()==b'';rr=[json.loads(l) for l in data.splitlines()];assert len(rr)==38;cfg=rr[0];assert cfg['anchor']==anchor and cfg['chain']==k and cfg['iterations']==131072 and cfg['reverse']==bool(e%2);assert cfg['events']==[17,8,58,59,33133,35];runtime=rr[5];base=runtime['code_base'];bases.append(base);assert type(base) is int and base>0 and base%4096==0 and runtime['cpu']==7 and runtime['fpcr']==0;assert len(set(runtime['event_ids']))==6
 pp={p['variant']:p for p in rr[1:5]};assert pp['i0']['words']==pp['d0']['words'];diff=[(x,y) for x,y in zip(pp['i128']['words'],pp['d128']['words']) if x!=y];assert len(diff)==256 and all((x^y)==((16^12)<<5) for x,y in diff)
 schedule=[(b,s,v) for b in range(8) for s,v in enumerate(['i0','d0','i128','d128'] if b%2==0 else ['d128','i128','d0','i0'])]
 if e%2:schedule.reverse()
 for pos,(r,w) in enumerate(zip(rr[6:],schedule)):
  assert (r['block'],r['slot'],r['variant'])==w and r['position']==pos and r['code_base']==base and r['code_matches_plan'] is True;assert r['enabled']==r['running']>0 and r['ns']>0;v=r['counts'];assert len(v)==6 and all(type(x) is int and 0<=x<2**64 for x in v);p=pp[r['variant']];loop=2*p['n']+(2*k if anchor=='fsqrt' else 0)+4;assert p['loop_instructions']==loop and p['loop_offset']==64 and p['prologue_instructions']==16;expect_ir=131072*loop+17;err=abs(v[1]-expect_ir);assert err<=max(1000,.01*expect_ir);ir_errors.append(err/expect_ir);program_hashes[f'{anchor}-{k}-{r["variant"]}']=sha(struct.pack('<'+'I'*len(p['words']),*p['words']));windows.append(dict(epoch=e,anchor=anchor,chain=k,block=r['block'],variant=r['variant'],cycles_per_iter=v[0]/131072,counts=v,ns=r['ns'],cycles_per_ns=v[0]/r['ns'],**{hex(event):v[j]/v[0] for j,event in enumerate(cfg['events']) if j>=2}))
 by={(r['block'],r['variant']):r['counts'][0]/131072 for r in rr[6:]};E=[]
 for v in ['i0','d0','i128','d128']:
  values=[by[b,v] for b in range(8)];points.append(dict(epoch=e,anchor=anchor,chain=k,variant=v,cycles=values,cycle_median=st.median(values),cycle_range_fraction=(max(values)-min(values))/st.median(values)))
 for b in range(8):
  cv={v:by[b,v] for v in ['i0','d0','i128','d128']};t=(cv['d128']-cv['d0'])-(cv['i128']-cv['i0']);ev=cv['d0']-cv['i0'];E.append(ev);index[e,anchor,k,b]=t;blocks.append(dict(epoch=e,anchor=anchor,chain=k,block=b,cycles=cv,T=t,E=ev))
 med=st.median(E);spread=max(E)-min(E);sentinels.append(dict(condition=c['name'],E=E,median=med,range=spread,passed=abs(med)<=1 and spread<=2))
none=[index[e,'none',16,b] for e in range(5) for b in range(8)];negative=dict(T=none,median=st.median(none),range=max(none)-min(none));negative['passed']=abs(negative['median'])<=5 and negative['range']<=5;contrasts=[dict(epoch=e,chain=k,block=b,D=index[e,'fsqrt',k,b]-index[e,'none',16,b],passed=index[e,'fsqrt',k,b]-index[e,'none',16,b]>5) for e in range(5) for k in (8,16) for b in range(8)];verdict='paired-dependency-associated-response' if all(p['passed'] for p in sentinels) and negative['passed'] and all(p['passed'] for p in contrasts) else 'not-qualified'
windows.sort(key=lambda r:(r['epoch'],0 if r['anchor']=='none' else 1 if r['chain']==8 else 2,r['block'],['i0','d0','i128','d128'].index(r['variant'])))
for key,value in [('blocks',blocks),('points',points),('window_ratios',windows),('sentinel_gates',sentinels),('negative_control',negative),('contrasts',contrasts),('verdict',verdict)]:assert a[key]==value,key
out=dict(windows=480,raw_files=len(files),programs=12,sentinels=sentinels,negative_control=negative,contrasts=contrasts,verdict=verdict,all_arithmetic_exact=True,all_raw_sha256=files,program_sha256=program_hashes,ir_relative_range=[min(ir_errors),max(ir_errors)],same_code_va_per_process=True,unique_code_bases_across_processes=len(set(bases)),method='same root, second arithmetic path; no production model imports')
output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k] for k in ['windows','raw_files','verdict','ir_relative_range','unique_code_bases_across_processes']}))
