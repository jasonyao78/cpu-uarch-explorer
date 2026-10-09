"""Real C/JIT/map producer tests; host evidence, never target qualification."""
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'probes/diagnostic/rob_cold_pair.c'
COMMON=ROOT/'probes/common'

class ColdProducer(unittest.TestCase):
    def compile(self,folder):
        self.assertTrue(SOURCE.exists(),'single-shot producer not implemented')
        exe=Path(folder)/'exporter'
        subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(COMMON),str(SOURCE),'-o',str(exe)],check=True)
        return exe

    def test_exact_clocks_dependency_and_same_length(self):
        with tempfile.TemporaryDirectory() as folder:
            exe=self.compile(folder)
            for mask in (0,4096):
                for member in ('P','S','E'):
                    for n in (0,1,128,4096):
                        out=Path(folder)/'code.bin'
                        p=subprocess.run([str(exe),'-n',str(n),'--mask',str(mask),'--member',member,'--write-asm',str(out)],capture_output=True,text=True,check=True)
                        c=json.loads(p.stdout);words=struct.unpack('<'+'I'*(len(out.read_bytes())//4),out.read_bytes())
                        prolog=[0xd280000c|(mask<<5),0xf2a0000c,0xf2c0000c,0xf2e0000c]+[0xd503201f]*12
                        clock=[0xd5033f9f,0xd5033fdf,0xd53be04d,0xd5033fdf]
                        a=[0xf9400000,0xca0c0000] if member!='E' else [0xd503201f]*2
                        b=([0xf9400021,0xca0c0021] if member=='P' else [0xf9400000,0xca0c0000]) if member!='E' else [0xd503201f]*2
                        tail=[0xd5033f9f,0xd5033fdf,0xd53be04e,0xcb0d01c0,0xd65f03c0]
                        self.assertEqual(list(words),prolog+clock+a+[0xd503201f]*n+b+[0xd503201f]*n+tail)
                        self.assertEqual(c['code_bytes'],4*(29+2*n));self.assertEqual(c['kernel_instructions'],29+2*n)
                        self.assertEqual(c['export'],{'mask':mask,'member':member})
                        self.assertEqual(c['node_offsets'],[0,4096]);self.assertEqual(c['mapping_alignment'],8192)

    def test_real_mapping_graph_and_self_pointer_arithmetic(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertTrue(SOURCE.exists(),'single-shot producer not implemented')
            src=Path(folder)/'graph.c';exe=Path(folder)/'graph'
            src.write_text('#define main producer_main\n#include "'+str(SOURCE)+'"\n#undef main\nint main(void){struct pair_mapping p={0}; if(!map_pair(&p))return 1; if((uintptr_t)p.data%8192)return 2; for(unsigned m=0;m<=4096;m+=4096){if(!fill_pair(&p,m))return 3; uintptr_t a=(uintptr_t)p.data,b=a+4096; uintptr_t va=*(uintptr_t*)a,vb=*(uintptr_t*)b; if((va^m)!=b||(vb^m)!=a)return 4; if(m&&(va!=a||vb!=b))return 5;} munmap(p.reservation,p.reserved);return 0;}\n')
            subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(COMMON),str(src),'-o',str(exe)],check=True)
            subprocess.run([str(exe)],check=True)

    def test_malformed_and_unregistered_arguments_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            exe=self.compile(folder)
            for args in (['-n','-1'],['-n','4097'],['--mask','1'],['--member','X'],['--epoch','2'],['--trials','63'],['--pin','1024'],['-n','3x'],['extra']):
                p=subprocess.run([str(exe),*args],capture_output=True,text=True)
                self.assertNotEqual(p.returncode,0,args)

    def test_host_does_not_fabricate_measurement(self):
        with tempfile.TemporaryDirectory() as folder:
            exe=self.compile(folder)
            p=subprocess.run([str(exe),'-n','0'],capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0)
            r=[json.loads(x) for x in p.stdout.splitlines()]
            self.assertEqual(r[-1]['metrics'],{});self.assertEqual(r[-1]['failure']['reason'],'measurement-requires-linux-aarch64')
            self.assertFalse(any(x['type']=='round' for x in r))

class SingletonProducer(unittest.TestCase):
    compile=ColdProducer.compile
    def test_explicit_singletons_actual_slots_and_profile(self):
        with tempfile.TemporaryDirectory() as folder:
            exe=self.compile(folder)
            for mask in (0,4096):
                for member in ('A','B'):
                    out=Path(folder)/'code.bin'
                    p=subprocess.run([str(exe),'--singletons','--mask',str(mask),'--member',member,'--write-asm',str(out)],capture_output=True,text=True)
                    self.assertEqual(p.returncode,0,p.stderr)
                    c=json.loads(p.stdout);words=struct.unpack('<29I',out.read_bytes())
                    self.assertEqual(c['version'],2);self.assertIs(c['singletons_requested'],True)
                    self.assertEqual(c['members'],['P','S','E','A','B'])
                    self.assertEqual((c['matrix_cells_per_trial'],c['windows']),(40,2560))
                    self.assertEqual(words[20:24],(0xf9400000,0xca0c0000,0xd503201f,0xd503201f) if member=='A'
                                     else (0xd503201f,0xd503201f,0xf9400021,0xca0c0021))
            for member in ('A','B'):
                p=subprocess.run([str(exe),'--member',member,'--write-asm',str(out)],capture_output=True,text=True)
                self.assertNotEqual(p.returncode,0)

if __name__=='__main__':unittest.main()
