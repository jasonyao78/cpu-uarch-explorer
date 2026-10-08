"""Validate exported A64 instructions, not emitter source strings."""
import json
import pathlib
import struct
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[5]
SRC = pathlib.Path(__file__).resolve().parents[1] / 'rob_window_probe.c'

class RobCode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.exe = pathlib.Path(cls.tmp.name) / 'probe'
        subprocess.run(['clang', '-O2', '-Wall', '-Wextra', '-Werror',
                        '-I', str(ROOT / 'probes/common'), str(SRC), '-o', str(cls.exe)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def dump(self, *args):
        path = pathlib.Path(self.tmp.name) / 'code.bin'
        p = subprocess.run([str(self.exe), *args, '--write-asm', str(path)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        data = path.read_bytes()
        return list(struct.unpack('<' + 'I' * (len(data)//4), data)), p.stdout

    def test_branch_returns_to_first_anchor(self):
        words, _ = self.dump('-t', 'nop', '-n', '64', '-i', '8', '-r', '1', '-m', '1')
        first = words.index(0xF9400000)
        at = next(i for i,w in enumerate(words) if w & 0xFF00001F == 0x54000001)
        delta = (words[at] >> 5) & 0x7FFFF
        if delta & 0x40000: delta -= 0x80000
        self.assertEqual(at + delta, first)

    def test_zero_filler_is_real_anchor_control(self):
        self.dump('-t', 'nop', '-n', '0', '-i', '8', '-r', '1', '-m', '1')

    def test_fp_fillers_do_not_clobber_anchor_or_abi(self):
        words, _ = self.dump('-t', 'fadd', '-n', '64', '-a', 'fsqrt', '-i', '8', '-r', '1')
        # Both single and double precision FADD encodings.
        dests = {w & 31 for w in words if w & 0xFFA0FC00 == 0x1E202800}
        self.assertTrue(dests)
        self.assertFalse(dests & ({0} | set(range(8,16))))

    def test_invalid_numeric_and_unknown_anchor_rejected(self):
        for opts in [('-i','0'),('-r','0'),('-n','-1'),('-a','bogus'),('-i','12x')]:
            p = subprocess.run([str(self.exe), '-t','nop','-n','64',*opts,
                                '--write-asm',str(pathlib.Path(self.tmp.name)/'bad')], capture_output=True)
            self.assertNotEqual(p.returncode, 0, opts)

    def test_all_modes_counts_alignment_and_branch(self):
        for cls in ('nop','add','movi','movr','fadd','ldr','str'):
            for anchor in ('miss','fsqrt','none'):
                for n in (0,1,9,384,1024,4096):
                    for align in (0,16,32,48):
                        words, stdout = self.dump('-t',cls,'-a',anchor,'-n',str(n),
                                                   '--align',str(align),'-i','1')
                        meta=json.loads(stdout)
                        first=meta['loop_offset']//4; at=meta['branch_offset']//4
                        delta=(words[at]>>5)&0x7ffff
                        if delta & 0x40000: delta-=0x80000
                        self.assertEqual(at+delta,first)
                        self.assertEqual(first*4%64,align)
                        self.assertEqual(meta['fillers_per_iteration'],2*n)
                        self.assertEqual(meta['anchors_per_iteration'],2 if anchor=='miss' else 16 if anchor=='fsqrt' else 0)
                        self.assertEqual(at-first+1,2*n+meta['anchors_per_iteration']+2)
                        self.assertEqual(words[-1],0xd65f03c0)
                        self.assertEqual(words[at-1],0xf1000463)  # subs x3,x3,#1
                        if anchor=='fsqrt': self.assertEqual(words[first: first+8],[0x1e61c000]*8)
                        if anchor=='miss':
                            self.assertEqual(words[first],0xf9400000)
                            self.assertEqual(words[first+n+1],0xf9400021)

    def test_fsqrt_chain_boundaries(self):
        for chain in (1,256):
            words, stdout=self.dump('-t','fadd','-n','9','-a','fsqrt','--chain',str(chain))
            meta=json.loads(stdout)
            self.assertEqual(words.count(0x1e61c000),2*chain)
            self.assertEqual(meta['anchors_per_iteration'],2*chain)
            self.assertEqual(meta['fsqrt_operand_bits'],'0x3ff0000000000000')

    def test_serial_dependency_and_asymmetric_counts(self):
        for flag in ('--serial','--asymmetric'):
            words, stdout=self.dump('-t','add','-n','9',flag)
            m=json.loads(stdout); first=m['loop_offset']//4
            self.assertEqual(words[first+10],0xf9400000 if flag=='--serial' else 0xf9400021)
            self.assertEqual(m['fillers_per_iteration'],18 if flag=='--serial' else 9)

    def test_production_decoder_and_chase_graphs(self):
        # Include the actual production C implementation in a host-only harness.
        harness=pathlib.Path(self.tmp.name)/'contracts.c'
        harness.write_text(r'''#define main rob_probe_main
#include "''' + str(SRC) + r'''"
#undef main
int main(void) {
    uint64_t ids[]={101,202}; struct pg_sample s,a,b,d;
    uint64_t good[]={2,100,100,22,202,11,101};
    assert(!pg_decode(good,7,ids,2,&s) && s.values[0]==11 && s.values[1]==22);
    assert(pg_decode(good,6,ids,2,&s)); assert(pg_decode(good,8,ids,2,&s));
    good[4]=101; assert(pg_decode(good,7,ids,2,&s));
    good[4]=999; assert(pg_decode(good,7,ids,2,&s));
    good[4]=202; good[0]=1; assert(pg_decode(good,7,ids,2,&s));
    a=(struct pg_sample){.enabled=100,.running=90,.values={10,20}};
    b=(struct pg_sample){.enabled=120,.running=110,.values={15,29}};
    assert(!pg_delta(&a,&b,2,&d) && d.enabled==20 && d.values[1]==9);
    b.running=109; assert(pg_delta(&a,&b,2,&d));
    b.running=89; assert(pg_delta(&a,&b,2,&d));
    b.running=110; b.values[0]=9; assert(pg_delta(&a,&b,2,&d));
    b=a; assert(pg_delta(&a,&b,2,&d));
    enum{N=256}; _Alignas(64) char mem[N*64]; uintptr_t addresses[N];
    assert(init_chase(mem,sizeof(mem),false,42));
    uintptr_t x=chase_heads[0],y=chase_heads[1]; unsigned char seen[N]={0};
    for(unsigned i=0;i<N/2;++i) {
        addresses[2*i]=x; addresses[2*i+1]=y;
        size_t ix=(x-(uintptr_t)mem)/64,iy=(y-(uintptr_t)mem)/64;
        assert(ix<N && iy<N && !seen[ix] && !seen[iy]); seen[ix]=seen[iy]=1;
        x=*(uintptr_t *)x; y=*(uintptr_t *)y;
    }
    assert(x==chase_heads[0] && y==chase_heads[1]);
    assert(init_chase(mem,sizeof(mem),true,42)); x=chase_heads[0];
    for(unsigned i=0;i<N;++i) { assert(x==addresses[i]); x=*(uintptr_t *)x; }
    assert(x==chase_heads[0]);
    return 0;
}
''')
        exe=pathlib.Path(self.tmp.name)/'contracts'
        subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),str(harness),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True)

if __name__ == '__main__': unittest.main()
