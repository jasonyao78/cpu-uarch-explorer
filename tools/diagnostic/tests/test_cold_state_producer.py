"""Actual C four-state production; host evidence, never phone timing."""
import itertools
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from tools.diagnostic.analyze_cold_pair import generated_code
ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'probes/diagnostic/rob_cold_pair.c'

class ColdStateProducer(unittest.TestCase):
    def compile(self,folder,source=SOURCE):
        exe=Path(folder)/'producer'
        subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),str(source),'-o',str(exe)],check=True,capture_output=True)
        return exe

    def test_explicit_shape_and_identical_all_twelve_exported_codes(self):
        with tempfile.TemporaryDirectory() as folder:
            exe=self.compile(folder);out=Path(folder)/'code.bin'
            for epoch,mask,member in itertools.product((0,1),(0,4096),('P','S','E')):
                p=subprocess.run([str(exe),'--single-cold','--epoch',str(epoch),'-n','0','--pin','7','--pmu-type','8','--mask',str(mask),'--member',member,'--write-asm',str(out)],capture_output=True,text=True)
                self.assertEqual(p.returncode,0,p.stderr)
                c=json.loads(p.stdout)
                self.assertEqual((c['version'],c['probe'],c['matrix_cells_per_trial'],c['windows']),(3,'rob-cold-state',48,3072))
                self.assertIs(c['single_cold_requested'],True)
                self.assertEqual(c['state_cold_slot_masks'],[0,1,2,3])
                self.assertEqual(c['states'],['hot','first-cold','second-cold','cold'])
                self.assertNotIn('singletons_requested',c)
                self.assertEqual(out.read_bytes(),generated_code(mask,member))

    def test_real_full_matrix_and_selected_actual_heads(self):
        with tempfile.TemporaryDirectory() as folder:
            src=Path(folder)/'matrix.c'
            src.write_text('#define main producer_main\n#include "'+str(SOURCE)+'"\n#undef main\nint main(void){for(unsigned e=0;e<2;++e)for(unsigned t=0;t<64;++t)for(unsigned p=0;p<48;++p){struct cell c=cell_at_single_cold(e,t,p);uintptr_t a=0x10000,b=0x11000; struct cold_addresses x=select_cold_heads(c.swap?b:a,c.swap?a:b,c.cooling); printf("%u %u %u %u %s %u %u %llu %llu\\n",e,t,c.mask,c.swap,names[c.member],c.cooling,x.count,(unsigned long long)(x.count?x.address[0]:0),(unsigned long long)(x.count>1?x.address[1]:0));}return 0;}\n')
            try:exe=self.compile(folder,src)
            except subprocess.CalledProcessError as ex:self.fail('four-state production functions missing: '+ex.stderr.decode()[:500])
            rows=[line.split() for line in subprocess.check_output([str(exe)],text=True).splitlines()]
            expected=[]
            for e in (0,1):
                for t in range(64):
                    base=list(itertools.product((0,4096),(0,1),('P','S','E'),(0,1,2,3)))
                    base=base[t%48:]+base[:t%48]
                    if (t+e)%2:base.reverse()
                    for m,s,u,c in base:
                        heads=(0x11000,0x10000) if s else (0x10000,0x11000)
                        chosen=[head for i,head in enumerate(heads) if c&(1<<i)]
                        expected.append([str(v) for v in (e,t,m,s,u,c,len(chosen),chosen[0] if chosen else 0,chosen[1] if len(chosen)>1 else 0)])
            self.assertEqual(rows,expected);self.assertEqual(len(rows),6144)

    def test_conflicting_flags_and_singleton_members_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            exe=self.compile(folder);out=Path(folder)/'code.bin'
            for flags in (['--single-cold','--singletons'],['--singletons','--single-cold'],['--single-cold','--member','A'],['--single-cold','--member','B'],['--single-cold','--unknown']):
                p=subprocess.run([str(exe),*flags,'--write-asm',str(out)],capture_output=True,text=True)
                self.assertNotEqual(p.returncode,0)

if __name__=='__main__':unittest.main()
