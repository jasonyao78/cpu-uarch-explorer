"""Synthetic decision-boundary tests; never hardware measurement evidence."""
import unittest
from tools.diagnostic import analyze_local_confirmation as a

class Departure(unittest.TestCase):
    def test_confirmed_interval_uses_both_epochs(self):
        self.assertEqual(a.first_departure({0:208,512:208.02,544:208.01,576:210,608:215},
                                          {0:208,512:208.03,544:208.02,576:210.1,608:214})['interval'],[544,576])
    def test_epoch_disagreement_not_pooled(self):
        result=a.first_departure({0:208,512:208,544:210,576:214}, {0:208,512:208,544:208,576:214})
        self.assertEqual(result['status'],'ambiguous')
    def test_first_scan_point_left_unresolved(self):
        self.assertEqual(a.first_departure({0:208,512:210,544:211},{0:208,512:210,544:211})['status'],'left-grid-insufficient')
    def test_single_endpoint_right_unconfirmed(self):
        self.assertEqual(a.first_departure({0:208,512:208,544:210},{0:208,512:208,544:210})['status'],'right-edge-unconfirmed')
    def test_return_below_threshold_is_ambiguous(self):
        self.assertEqual(a.first_departure({0:208,512:208,544:210,576:211,608:208},
                                          {0:208,512:208,544:210,576:211,608:208})['status'],'ambiguous')
    def test_negative_departure_is_ambiguous(self):
        self.assertEqual(a.first_departure({0:208,512:206,544:210,576:211},
                                          {0:208,512:208,544:210,576:211})['status'],'ambiguous')
    def test_no_departure_is_reported(self):
        self.assertEqual(a.first_departure({0:208,512:208,544:208},{0:208,512:208,544:208})['status'],'no-departure-observed')
    def test_nonfinite_not_a_platform(self):
        with self.assertRaises(ValueError):
            a.first_departure({0:208,512:float('nan'),544:210,576:212},{0:208,512:208,544:210,576:212})

    def test_grid_mismatch_and_empty_rejected(self):
        for x,y in (({},{}),({0:208,512:208},{0:208,544:208})):
            with self.assertRaises(ValueError): a.first_departure(x,y)


# The matrix and configs come from production conditions and real host export;
# only cycle values below are synthetic (software contract tests).
class WholeConsumer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import json, subprocess, tempfile
        from pathlib import Path
        from tools.diagnostic.run_sm8650_minimal import conditions
        cls.tmp=tempfile.TemporaryDirectory(); tmp=Path(cls.tmp.name)
        root=Path(__file__).resolve().parents[3]; exe=tmp/'exporter'
        subprocess.run(['clang','-O2','-I',str(root/'probes/common'),str(root/'docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c'),'-o',str(exe)],check=True)
        cls.rows=[]
        for name,opts in conditions('rob-fine'):
            c=json.loads(subprocess.check_output([str(exe),*opts,'--write-asm',str(tmp/'code.bin')],text=True))
            r={k:c[k] for k in ('class','anchor','chain','n','loop_mod64','iterations','chase_seed')}
            r.update(epoch=int(name[1]),cycles_per_iteration=[208.0]*3,retired_relative_error=[0.0]*3)
            cls.rows.append(r)
    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()
    def test_whole_matrix_order_and_identity(self):
        import random,copy
        rows=copy.deepcopy(self.rows); expected=a.rob_stats({'rows':rows,'processes':114})
        random.Random(13).shuffle(rows)
        self.assertEqual(a.rob_stats({'rows':rows,'processes':114}),expected)
        self.assertTrue(all(c['iterations']==131072 and c['chase_seed']==42 for c in expected['curves']))
    def test_mixed_source_and_invalid_samples_rejected(self):
        import copy
        for field,value in (('iterations',8),('chase_seed',137),('epoch',2),
                            ('cycles_per_iteration',[208.0]*2),('cycles_per_iteration',[float('nan')]*3)):
            rows=copy.deepcopy(self.rows); rows[0][field]=value
            with self.subTest(field=field,value=value):
                with self.assertRaises(ValueError): a.rob_stats({'rows':rows,'processes':114})


class TlbConsumer(unittest.TestCase):
    def setUp(self):
        import json
        from pathlib import Path
        root=Path(__file__).resolve().parents[3]
        data=json.loads((root/'docs/reviews/evidence/2026-10-09-minimal-probes/summary.json').read_text())
        self.run=next(r for r in data['runs'] if r['mode']=='tlb')
    def test_missing_or_duplicate_epoch_rejected(self):
        import copy
        missing=copy.deepcopy(self.run); missing['rows']=[r for r in missing['rows'] if r['epoch']!='epoch-4']
        duplicate=copy.deepcopy(self.run); duplicate['rows'][-1]=copy.deepcopy(duplicate['rows'][0])
        for run in (missing,duplicate):
            with self.assertRaises(ValueError): a.tlb_stats(run,200)
    def test_target_cannot_be_relabeled(self):
        self.run['tlb_target']=100
        with self.assertRaises(ValueError): a.tlb_stats(self.run,200)
    def test_published_epoch_values_reproduce(self):
        s=a.tlb_stats(self.run,200)
        self.assertEqual(len(s['overall_epoch_values']),5)
        self.assertAlmostEqual(s['overall_epoch_values'][0],2.7960526315789473)

if __name__=='__main__': unittest.main()
