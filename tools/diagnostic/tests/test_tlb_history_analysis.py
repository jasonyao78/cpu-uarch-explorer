"""Production-plan contract tests with synthetic counts, not device evidence.

The matrix and virtual geometry come from the current production C++ code.
Only fabricated counter/backing records below exercise software acceptance and
decision boundaries; they must never be promoted as hardware measurements.
"""
import copy
import hashlib
import importlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
try:
    analysis = importlib.import_module('tools.diagnostic.tlb_history_analysis')
except ModuleNotFoundError:
    analysis = None


class ProductionPlan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        tmp = Path(cls.tmp.name)
        compiler = shutil.which('clang++') or shutil.which('g++')
        if not compiler:
            raise RuntimeError('C++ compiler required for the production --plan contract')
        common = [compiler, '-std=c++17', '-O2', '-I', str(ROOT/'probes/common'),
                  '-I', str(ROOT/'probes/diagnostic')]
        exe = tmp/'tlb-history-host'
        subprocess.run([*common, str(ROOT/'probes/diagnostic/tlb_history.cpp'), '-o', str(exe)], check=True)
        cls.plan = {}
        for reverse, key in ((False, 'forward'), (True, 'reverse')):
            output = subprocess.check_output([str(exe), '--plan', *(['--reverse'] if reverse else [])], text=True)
            cls.plan[key] = [json.loads(line) for line in output.splitlines()]
        # Pure integer selection calls the real collector and append policy.
        helper = tmp/'geometry.cpp'
        helper.write_text(r'''
#include "tlb_history_layout.h"
#include <cstdio>
#include <random>
static void array(const tlb_local::Addresses& a) {
    std::printf("[");
    for(size_t i=0;i<a.size();++i) std::printf("%s%llu",i?",":"",static_cast<unsigned long long>(a[i]));
    std::printf("]");
}
int main() {
    auto ts=tlb_history::targets(reinterpret_cast<char*>(0x100000000ull),65536,100);
    auto fs=tlb_local::fillers(reinterpret_cast<char*>(0x200000000ull),2048,ts);
    std::mt19937_64 rng(137);std::shuffle(fs.begin(),fs.end(),rng);
    std::printf("{\"type\":\"geometry\",\"target\":100,\"pool_base\":4294967296,\"pool_pages\":65536,\"target_pages\":[");
    array(ts[0]);std::printf(",");array(ts[1]);std::printf("],\"filler_pages\":");array(fs);std::puts("}");
}
''')
        geometry = tmp/'geometry'
        subprocess.run([*common, str(helper), '-o', str(geometry)], check=True)
        cls.geometry = json.loads(subprocess.check_output([str(geometry)], text=True))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def api(self):
        self.assertIsNotNone(analysis, 'TLB history audit and analysis are not implemented')
        return analysis

    def raw(self, reverse=False, count=None):
        plan = self.plan['reverse' if reverse else 'forward']
        rows = [copy.deepcopy(plan[0]), copy.deepcopy(self.geometry)]
        for cell in plan[1:]:
            for stage in ('before', 'after'):
                rows.append({'type':'backing', 'cell':cell['cell'], 'stage':stage,
                             'base_page_bytes':4096, 'anon_huge_kb':0})
            for index in range(cell['rounds']):
                row = {k:v for k,v in cell.items() if k not in ('rounds', 'type')}
                row.update(type='round', round=index//8 if cell['kind']==2 else index,
                           trial_position=index%8 if cell['kind']==2 else 0,
                           victim=(index//8+index%8)%8 if cell['kind']==2 else -1,
                           enabled=1000, running=1000)
                walk = count(cell, index) if count else 0
                row['counts'] = [100, walk, walk, walk, walk, 0]
                rows.append(row)
        return rows

    def audited_run(self, effects=None, fading=False):
        cells = []
        for epoch in range(5):
            effect = effects[epoch] if effects is not None else 2
            def count(cell, index):
                if cell['kind']==0:
                    return 0
                if cell['kind']==2:
                    return int(cell['h']==1 and (index//8+index%8)%8==0)
                if cell['f']==0:
                    return 0
                if cell['h']==2:
                    return 2 if cell['history']==12 else 1
                value = 20 - 2*cell['direction']
                if cell['history']==12:
                    value += 1 + (0 if fading and index>=12 else effect)
                return value
            exported = self.api().audit_history(self.raw(bool(epoch%2), count), bool(epoch%2), self.plan)
            cells.extend(dict(cell, epoch=f'epoch-{epoch}') for cell in exported)
        return {'mode':'tlb-history', 'tlb_target':100, 'rows':cells}

    def test_real_forward_and_reverse_plans_are_audited_without_addresses(self):
        frozen = json.loads((ROOT/'docs/reviews/evidence/2026-10-09-tlb-history/plan.json').read_text())
        self.assertEqual(self.plan,frozen,'production plan changed without updating the frozen artifact')
        for reverse in (False, True):
            with self.subTest(reverse=reverse):
                result = self.api().audit_history(self.raw(reverse), reverse, self.plan)
                self.assertEqual(len(result), 38)
                self.assertEqual(sum(len(c['samples']) for c in result), 800)
                self.assertEqual([c['cell'] for c in result], [c['cell'] for c in self.plan['reverse' if reverse else 'forward'][1:]])
                text = json.dumps(result)
                for private in ('pool_base', 'target_pages', 'filler_pages', str(self.geometry['pool_base'])):
                    self.assertNotIn(private, text)

    def test_raw_missing_duplicate_unknown_and_failure_records_are_rejected(self):
        original = self.raw()
        mutations = [original[:-1], original+[copy.deepcopy(original[-1])],
                     original+[{'type':'failure', 'metrics':{}, 'failure':{'reason':'synthetic'}}],
                     original+[{'type':'unknown'}], original+[copy.deepcopy(original[0])],
                     original+[copy.deepcopy(original[1])]]
        for rows in mutations:
            with self.subTest(size=len(rows)):
                with self.assertRaises(ValueError): self.api().audit_history(rows, False, self.plan)

    def test_round_metadata_counts_and_multiplexing_are_checked(self):
        mutations = [('h',2), ('w',8), ('f',128), ('history',6), ('direction',1),
                     ('position',1), ('cell','not-a-cell'), ('kind',1), ('block',1),
                     ('round',1), ('victim',0), ('trial_position',1),
                     ('enabled',0), ('running',999), ('counts',[1]*5),
                     ('counts',[1,0,0,0,-1,0]), ('counts',[True,0,0,0,0,0]),
                     ('counts',[1,0,0,0,0.5,0])]
        for field, value in mutations:
            rows = self.raw()
            next(r for r in rows if r['type']=='round')[field] = value
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError): self.api().audit_history(rows, False, self.plan)

    def test_physical_order_and_victim_trial_coverage_are_checked(self):
        rows = self.raw()
        indices = [i for i,r in enumerate(rows) if r['type']=='round' and r['kind']==2]
        rows[indices[0]], rows[indices[1]] = rows[indices[1]], rows[indices[0]]
        with self.assertRaises(ValueError): self.api().audit_history(rows, False, self.plan)
        rows = self.raw()
        victim = next(r for r in rows if r['type']=='round' and r['kind']==2)
        victim['victim'] = (victim['victim']+1)%8
        with self.assertRaises(ValueError): self.api().audit_history(rows, False, self.plan)
        rows = self.raw()
        indices = [i for i,r in enumerate(rows) if r['type']=='round']
        rows[indices[0]], rows[indices[16]] = rows[indices[16]], rows[indices[0]]
        with self.assertRaises(ValueError): self.api().audit_history(rows, False, self.plan)

    def test_backing_endpoints_are_bound_to_each_cell(self):
        for field, value in (('cell','wrong'), ('stage','after'), ('base_page_bytes',16384), ('anon_huge_kb',2048)):
            rows = self.raw()
            next(r for r in rows if r['type']=='backing')[field] = value
            with self.subTest(field=field):
                with self.assertRaises(ValueError): self.api().audit_history(rows, False, self.plan)

    def test_geometry_target_prefix_filler_and_pool_bounds_are_checked(self):
        for mutation in ('target', 'pool', 'unaligned', 'duplicate', 'old-prefix', 'filler-overlap', 'filler-duplicate'):
            rows = self.raw(); geometry = rows[1]
            if mutation=='target': geometry['target']=200
            if mutation=='pool': geometry['pool_pages']=1024
            if mutation=='unaligned': geometry['target_pages'][0][0]+=8
            if mutation=='duplicate': geometry['target_pages'][0][1]=geometry['target_pages'][0][0]
            if mutation=='old-prefix':
                geometry['target_pages'][0][0],geometry['target_pages'][0][1]=geometry['target_pages'][0][1],geometry['target_pages'][0][0]
            if mutation=='filler-overlap': geometry['filler_pages'][0]=geometry['target_pages'][0][0]
            if mutation=='filler-duplicate': geometry['filler_pages'][0]=geometry['filler_pages'][1]
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError): self.api().audit_history(rows, False, self.plan)

    def test_config_and_plan_identity_are_not_inferred_from_row_count(self):
        for field,value in (('seed',42), ('target',200), ('reverse',True), ('old_prefix',12), ('version',2), ('cells',37)):
            rows = self.raw(); rows[0][field]=value
            with self.subTest(field=field):
                with self.assertRaises(ValueError): self.api().audit_history(rows, False, self.plan)
        plan = copy.deepcopy(self.plan); plan['forward'][2]=copy.deepcopy(plan['forward'][1])
        with self.assertRaises(ValueError): self.api().audit_history(self.raw(), False, plan)

    def test_history_and_direction_did_keep_epoch_and_full_trajectories(self):
        result = self.api().analyze(self.audited_run())
        self.assertEqual(len(result['history_did']),4)
        self.assertEqual(len(result['direction_did']),6)
        for contrast in result['history_did']:
            self.assertEqual([e['step1'] for e in contrast['epochs']],[2]*5)
            self.assertTrue(contrast['persistent']['passed'])
            self.assertEqual(contrast['persistent']['sign'],1)
            self.assertFalse(contrast['fading']['passed'])
            self.assertTrue(all(e['values']==[2]*16 for e in contrast['epochs']))
        self.assertTrue(all(e['step1']==2 for c in result['direction_did'] for e in c['epochs']))
        self.assertEqual(len(result['trajectory']),140)

    def test_persistent_gate_counts_individual_epoch_magnitude_and_sign(self):
        result = self.api().analyze(self.audited_run([1,1,1,1,-10]))
        self.assertTrue(all(c['persistent']['passed'] and c['persistent']['sign']==1 for c in result['history_did']))
        result = self.api().analyze(self.audited_run([10,0,0,0,0]))
        self.assertTrue(all(not c['persistent']['passed'] for c in result['history_did']))

    def test_fading_requires_initial_effect_and_same_epoch_joint_condition(self):
        result = self.api().analyze(self.audited_run(fading=True))
        self.assertTrue(all(c['fading']['passed'] for c in result['history_did']))
        result = self.api().analyze(self.audited_run([0]*5, fading=True))
        self.assertTrue(all(not c['fading']['passed'] for c in result['history_did']))
        run = self.audited_run(fading=True)
        # Four initial effects and four small tails overlap in only three epochs.
        for cell in run['rows']:
            if cell['kind']==1 and cell['f']==128 and cell['h']==1 and cell['history']==12:
                if cell['epoch']=='epoch-0': cell['samples'][0]['counts'][4]-=2
                if cell['epoch']=='epoch-4':
                    for sample in cell['samples'][-4:]: sample['counts'][4]+=2
        result = self.api().analyze(run)
        self.assertTrue(all(not c['fading']['passed'] for c in result['history_did']))

    def test_victim_preserves_latin_positions_drift_and_multiple_walks(self):
        run = self.audited_run()
        bundle = next(c for c in run['rows'] if c['kind']==2)
        bundle['samples'][0]['counts'][4]=2
        result = self.api().analyze(run)
        self.assertEqual(len(result['victim']),20)
        first = next(c for c in result['victim'] if c['epoch']==bundle['epoch'] and c['h']==bundle['h'] and c['history']==bundle['history'])
        self.assertEqual(first['count_gt1'],1)
        self.assertEqual(first['walk_rate_sum'],1)
        self.assertEqual(first['mean_datawalk_sum'],1.125)
        self.assertEqual(len(first['trial_means']),8)
        self.assertEqual(len(first['position_means']),8)
        for victim in first['victims']:
            self.assertEqual({s['trial_position'] for s in victim['samples']},set(range(8)))
        self.assertEqual(first['trajectory_step1_datawalk'],20)
        self.assertIn('single-load window',result['victim_interpretation'])

    def test_analysis_rejects_missing_duplicate_epochs_and_relabeling(self):
        original = self.audited_run()
        for mutation in ('missing-epoch','duplicate','target','mode','metadata','sample-missing'):
            run = copy.deepcopy(original)
            if mutation=='missing-epoch': run['rows']=[c for c in run['rows'] if c['epoch']!='epoch-4']
            if mutation=='duplicate': run['rows'][-1]=copy.deepcopy(run['rows'][0])
            if mutation=='target': run['tlb_target']=200
            if mutation=='mode': run['mode']='tlb-confirm100'
            if mutation=='metadata': run['rows'][0]['f']=128
            if mutation=='sample-missing': run['rows'][0]['samples'].pop()
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError): self.api().analyze(run)

    def test_public_cell_order_does_not_change_the_analysis(self):
        run = self.audited_run()
        expected = self.api().analyze(run)
        run['rows'].reverse()
        self.assertEqual(self.api().analyze(run),expected)

    def test_cli_binds_exact_input_and_does_not_publish_a_rejected_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'synthetic-software-evidence.json'
            output = Path(tmp)/'analysis.json'
            run = self.audited_run()
            source.write_text(json.dumps({'runs':[run]}))
            command = [sys.executable,'-B',str(ROOT/'tools/diagnostic/tlb_history_analysis.py'),
                       str(source),'--output',str(output)]
            subprocess.run(command,check=True,capture_output=True,text=True)
            result = json.loads(output.read_text())
            self.assertEqual(result.get('input_sha256'),hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(result['windows'],4000)
            output.unlink()
            run['rows'].pop()
            source.write_text(json.dumps({'runs':[run]}))
            failed = subprocess.run(command,capture_output=True,text=True)
            self.assertNotEqual(failed.returncode,0)
            self.assertFalse(output.exists())


if __name__=='__main__':
    unittest.main()
