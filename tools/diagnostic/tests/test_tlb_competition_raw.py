"""Immutable registered C++ plan/selector -> controlled synthetic raw -> CLI.

Only external backing/environment/measurement observations are synthetic.
Git/source/build/plan/driver are real. These temporary files are not device data.
"""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from tools.diagnostic import tlb_competition_analysis as model
from tools.diagnostic.summarize_sm8650_minimal import summarize
ROOT=Path(__file__).resolve().parents[3]

class CompetitionRaw(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder=tempfile.TemporaryDirectory();folder=Path(cls.folder.name)
        cls.launch=subprocess.check_output(['git','rev-parse','7f94dc5'],cwd=ROOT,text=True).strip()
        cls.blob=staticmethod(lambda ref,p:subprocess.check_output(['git','show',ref+':'+p],cwd=ROOT))
        cls.build_path='docs/reviews/evidence/2026-10-10-tlb-competition/build.json'
        cls.build=json.loads(cls.blob(cls.launch,cls.build_path));cls.plan=json.loads(cls.blob(cls.launch,cls.build['plan_path']))
        for p in cls.build['source_sha256']:(folder/Path(p).name).write_bytes(cls.blob(cls.build['source_commit'],p))
        exe=folder/'producer'
        subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(folder),str(folder/'tlb_competition.cpp'),'-o',str(exe)],check=True)
        cls.actual={key:[json.loads(l) for l in subprocess.check_output([str(exe),'--plan',*a],text=True).splitlines()] for key,a in [('forward',[]),('reverse',['--reverse'])]}
        if cls.actual!=cls.plan:raise AssertionError('registered actual C plan drift')
        src=folder/'geom.cpp';geo=folder/'geom'
        src.write_text('#include "tlb_competition_layout.h"\n#include <cstdio>\nvoid arr(const tlb_local::Addresses& a){std::printf("[");for(size_t i=0;i<a.size();++i)std::printf("%s%llu",i?",":"",(unsigned long long)a[i]);std::printf("]");}int main(){auto t=tlb_history::targets((char*)0x40000000ull,65536,100);auto f=tlb_local::fillers((char*)0x80000000ull,2048,t);std::printf("{\\\"type\\\":\\\"geometry\\\",\\\"target\\\":100,\\\"pool_base\\\":1073741824,\\\"pool_pages\\\":65536,\\\"target_pages\\\":[");arr(t[0]);std::printf(",");arr(t[1]);std::printf("],\\\"filler_pages\\\":");arr(f);std::printf("}\\n");}\n'.replace('\\\"','\"').replace('}\\n','}\\n'))
        # Keep actual C string quote escapes; no hand-authored VA arrays.
        text=src.read_text();text=text.replace('std::printf("{"type":"geometry","target":100,"pool_base":1073741824,"pool_pages":65536,"target_pages":[");','std::printf("{\\"type\\":\\"geometry\\",\\"target\\":100,\\"pool_base\\":1073741824,\\"pool_pages\\":65536,\\"target_pages\\":[");').replace('std::printf("],"filler_pages":");','std::printf("],\\"filler_pages\\":");');src.write_text(text)
        subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(folder),str(src),'-o',str(geo)],check=True)
        cls.geometry=json.loads(subprocess.check_output([str(geo)],text=True))
    @classmethod
    def tearDownClass(cls):cls.folder.cleanup()
    @staticmethod
    def sha(blob):return hashlib.sha256(blob).hexdigest()
    def fixture(self,path):
        profile=json.loads(self.blob(self.launch,'configs/platforms/redmi-k70pro-01.json'))
        policy=copy.deepcopy(profile['environment_profiles']['charging-thermal']['measurement_environment']);policy['preconditions']['cpufreq_governor']='walt'
        snapshot={'power':{'wakefulness':'Dozing','screen_on':False},'device_idle':{'force_idle':False},'camera':{'active':False},'services':{'mi_thermald':'running'},'airplane_mode':True,'thermal':{'max_cpu_c':40},'cpufreq':{n:dict(governor='walt',min_khz=672000,max_khz=v) for n,v in policy['preconditions']['cpufreq_max_khz'].items()}}
        conditions=[dict(name=f'epoch-{e}',args=['100',*(['--reverse'] if e%2 else [])]) for e in range(5)]
        manifest=dict(mode='tlb-competition',status='complete',target='redmi-k70pro-01',source_branch='synthetic-test-only',source_head=self.launch,binary_source_head=self.build['source_commit'],binary_sha256=self.build['binaries']['tlb_competition'],driver_sha256=self.sha(self.blob(self.launch,'tools/diagnostic/run_sm8650_minimal.py')),build_evidence_path=self.build_path,build_evidence_sha256=self.sha(self.blob(self.launch,self.build_path)),protocol_path=model.PROTOCOL,protocol_sha256=self.sha(self.blob(self.launch,model.PROTOCOL)),plan_path=self.build['plan_path'],plan_sha256=self.build['plan_sha256'],conditions=conditions,midr='0x410fd821',base_page_bytes=4096,tlb_target=100,results=[])
        (path/'driver.py').write_bytes(self.blob(self.launch,'tools/diagnostic/run_sm8650_minimal.py'));(path/'environment-policy.json').write_text(json.dumps(policy))
        for name in ['initial','final',*[f'epoch-{e}-{side}' for e in range(5) for side in ('pre','post')]]:(path/(name+'-environment.json')).write_text(json.dumps(dict(snapshot=snapshot,violations=[],warnings=[])))
        for e in range(5):
            selected=self.actual['reverse' if e%2 else 'forward'];records=[selected[0],self.geometry]
            for c in selected[1:]:
                records.extend(dict(type='backing',cell=c['cell'],stage=side,base_page_bytes=4096,anon_huge_kb=0) for side in ('before','after'))
                for t in range(16):
                    for p in range(c['passes']+1):
                        victim=p==c['passes'];n=1 if victim else c['k'];walk=int(victim and c['h']==1 and c['k']>=9 and c['passes']>=4)
                        records.append(dict(type='round',**{k:c[k] for k in model.META if k!='rounds'},round=t,role='victim' if victim else 'competition',pass_index=p,enabled=100,running=100,counts=[200,n,walk,n,walk,0]))
            stdout=path/f'epoch-{e}.stdout.jsonl';stdout.write_text('\n'.join(json.dumps(r) for r in records)+'\n');(path/f'epoch-{e}.stderr.log').write_text('')
            manifest['results'].append(dict(name=f'epoch-{e}',exit_code=0,timed_out=False,stdout_sha256=self.sha(stdout.read_bytes()),wall_seconds=.1,generated_code={}))
        (path/'manifest.json').write_text(json.dumps(manifest));return manifest
    def test_real_registered_source_plan_to_complete_synthetic_raw_cli(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d);self.fixture(path);run=summarize(path)
            self.assertEqual(len(run['rows']),480);self.assertEqual(sum(len(c['samples']) for c in run['rows']),36480)
            output,summary=path/'out.json',path/'sum.json';model.main([d,'--output',str(output),'--summary-output',str(summary)])
            result=json.loads(output.read_text());self.assertTrue(result['all_lookup_observable']);self.assertEqual(sum(v['passed'] for v in result['replication']),6)
            self.assertEqual(result['input_sha256'],self.sha(summary.read_bytes()))
    def test_rehashed_raw_binding_config_order_phase_and_environment_reject(self):
        for kind in ('manifest-status','midr','result-order','binary','plan-sha','driver','stderr','missing-env','env-drift','policy','role','missing-round','mux','typed-config','backing'):
            with tempfile.TemporaryDirectory() as d:
                path=Path(d);m=self.fixture(path)
                if kind=='manifest-status':m['status']='stopped'
                elif kind=='midr':m['midr']='0x410fd820'
                elif kind=='result-order':m['results'][:2]=m['results'][:2][::-1]
                elif kind=='binary':m['binary_sha256']='bad'
                elif kind=='plan-sha':m['plan_sha256']='bad'
                elif kind=='driver':(path/'driver.py').write_text('drift')
                elif kind=='stderr':(path/'epoch-0.stderr.log').write_text('warning')
                elif kind=='missing-env':(path/'final-environment.json').unlink()
                elif kind=='env-drift':
                    f=path/'final-environment.json';v=json.loads(f.read_text());v['snapshot']['cpufreq']['policy7']['max_khz']-=1;f.write_text(json.dumps(v))
                elif kind=='policy':
                    f=path/'environment-policy.json';v=json.loads(f.read_text());v['preconditions']['max_cpu_temp_c']=100;f.write_text(json.dumps(v))
                else:
                    f=path/'epoch-0.stdout.jsonl';r=[json.loads(l) for l in f.read_text().splitlines()]
                    if kind=='role':r[4]['role']='victim'
                    elif kind=='missing-round':r.pop()
                    elif kind=='mux':r[4]['running']=99
                    elif kind=='typed-config':r[0]['k_grid'][0]=False
                    else:r[2]['anon_huge_kb']=1
                    f.write_text('\n'.join(json.dumps(x) for x in r)+'\n');m['results'][0]['stdout_sha256']=self.sha(f.read_bytes())
                (path/'manifest.json').write_text(json.dumps(m));out=path/'out.json';summary=path/'sum.json'
                with self.subTest(kind=kind),self.assertRaises((ValueError,AssertionError,FileNotFoundError)):model.main([d,'--output',str(out),'--summary-output',str(summary)])
                self.assertFalse(out.exists());self.assertFalse(summary.exists())
if __name__=='__main__':unittest.main()
