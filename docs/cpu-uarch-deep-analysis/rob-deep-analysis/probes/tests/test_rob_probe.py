"""核验真实A64生成码及backing契约，防止THP请求被误报为实际大页。"""
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

    def test_backing_export_preserves_generated_code(self):
        """内存backing不改变JIT码；host导出不能冒称验证过目标映射。"""
        default_words, default_stdout = self.dump('-t', 'nop', '-n', '64')
        self.assertEqual(json.loads(default_stdout).get('backing_requested'), '4k')
        for kind in ('4k', 'thp2m'):
            with self.subTest(backing=kind):
                words, stdout = self.dump('-t', 'nop', '-n', '64', '--backing', kind)
                self.assertEqual(words, default_words)
                self.assertEqual(json.loads(stdout)['backing_requested'], kind)
                self.assertNotIn('backing_verified', json.loads(stdout))

    def test_explicit_collapse_preserves_code_and_requires_thp(self):
        default,stdout=self.dump('-t','nop','-n','0','--backing','thp2m','-m','256')
        self.assertNotIn('collapse_requested',json.loads(stdout))
        words,stdout=self.dump('-t','nop','-n','0','--backing','thp2m','-m','256','--collapse')
        self.assertEqual(words,default)
        self.assertIs(json.loads(stdout)['collapse_requested'],True)
        p=subprocess.run([str(self.exe),'-t','nop','-n','0','--collapse'],capture_output=True,text=True)
        self.assertNotEqual(p.returncode,0)
        row=json.loads(p.stdout)
        self.assertEqual(row['metrics'],{})
        self.assertEqual(row['failure']['reason'],'collapse-requires-thp2m-miss')

    def test_invalid_backing_is_structured_failure(self):
        """禁止未知backing、非miss THP及不完整2MiB映射静默降级。"""
        for opts, reason in [
            (('--backing', 'bogus'), 'backing-unknown'),
            (('--backing', 'thp2m', '-a', 'fsqrt'), 'backing-thp2m-requires-miss'),
            (('--backing', 'thp2m', '-m', '3'), 'backing-thp2m-requires-2m-multiple'),
        ]:
            with self.subTest(opts=opts):
                p = subprocess.run([str(self.exe), '-t', 'nop', '-n', '0', *opts],
                                   capture_output=True, text=True)
                self.assertNotEqual(p.returncode, 0)
                self.assertTrue(p.stdout.strip(), '缺少结构化backing失败记录')
                failure = json.loads(p.stdout)
                self.assertEqual(failure['type'], 'failure')
                self.assertEqual(failure['metrics'], {})
                self.assertEqual(failure['failure']['reason'], reason)

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

    def test_failed_backing_keeps_observation_without_metrics(self):
        """部分THP保留实际值；解析失败输出null，不能把零结构当实测。"""
        header = ROOT / 'probes/common/rob_backing.h'
        self.assertIn('rob_backing_inspect', header.read_text(),
                      '失败验收缺少可区分parse与coverage的生产观测')
        harness = pathlib.Path(self.tmp.name) / 'backing_failure.c'
        harness.write_text(r'''#include "rob_backing.h"
#include <assert.h>
static void sample(const char *text) {
    FILE *f=tmpfile(); assert(f); fputs(text,f); rewind(f);
    struct rob_backing_info info={0};
    enum rob_backing_status status=rob_backing_inspect(f,0x200000,0x400000,true,ROB_PMD_BYTES,&info);
    fclose(f);
    assert(status!=ROB_BACKING_VERIFIED);
    rob_backing_failure_json(stdout,"chase-backing-not-thp2m",0x400000,true,ROB_PMD_BYTES,status,&info);
}
int main(void) {
    sample("200000-600000 rw-p 0 00:00 0\nKernelPageSize: 4 kB\nMMUPageSize: 4 kB\nAnonHugePages: 2048 kB\nRss: 4096 kB\nSwap: 0 kB\nVmFlags: rd wr hg\n");
    sample("200000-600000 rw-p 0 00:00 0\nAnonHugePages: 2048 kB\n");
    return 0;
}
''')
        exe = pathlib.Path(self.tmp.name) / 'backing_failure'
        result = subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',
                    str(ROOT / 'probes/common'),str(harness),'-o',str(exe)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        result = subprocess.run([str(exe)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        mismatch, unparsed = map(json.loads,result.stdout.splitlines())
        for row in (mismatch,unparsed):
            self.assertEqual(row['type'],'failure')
            self.assertEqual(row['metrics'],{})
            self.assertEqual(row['failure']['reason'],'chase-backing-not-thp2m')
            self.assertEqual(row['failure']['backing_requested'],'thp2m')
            self.assertEqual(row['failure']['memory_bytes'],4194304)
        self.assertEqual(mismatch['failure']['backing_status'],'coverage-mismatch')
        self.assertEqual(mismatch['failure']['backing_info']['anon_huge_kb'],2048)
        self.assertEqual(mismatch['failure']['backing_info']['rss_kb'],4096)
        self.assertEqual(unparsed['failure']['backing_status'],'smaps-parse-failed')
        self.assertIsNone(unparsed['failure']['backing_info'])

    def test_production_smaps_and_aligned_mapping(self):
        """执行生产解析器/真实mmap，拒绝只看THP hint、混合覆盖及伪造完整VMA。"""
        header = ROOT / 'probes/common/rob_backing.h'
        self.assertTrue(header.exists(), '缺少实际smaps/backing验收helper')
        harness = pathlib.Path(self.tmp.name) / 'backing.c'
        harness.write_text(r'''#include "rob_backing.h"
#include <assert.h>
static bool parse(const char *text, struct rob_backing_info *out) {
    FILE *f=tmpfile(); assert(f); assert(fputs(text,f)>=0); rewind(f);
    bool ok=rob_backing_parse(f,0x200000,0x400000,out); assert(!fclose(f)); return ok;
}
static bool sample(size_t huge,size_t rss,size_t swap,const char *flags,bool thp) {
    char text[1024]; struct rob_backing_info out;
    snprintf(text,sizeof(text),
        "100000-180000 rw-p 00000000 00:00 0\nAnonHugePages: 512 kB\n"
        "200000-600000 rw-p 00000000 00:00 0\n"
        "KernelPageSize: 4 kB\nMMUPageSize: 4 kB\nAnonHugePages: %zu kB\n"
        "Rss: %zu kB\nSwap: %zu kB\nVmFlags: %s\n"
        "700000-800000 rw-p 00000000 00:00 0\nAnonHugePages: 0 kB\n",
        huge,rss,swap,flags);
    assert(parse(text,&out));
    assert(out.kernel_kb==4 && out.mmu_kb==4 && out.huge_kb==huge);
    return rob_backing_matches(&out,0x400000,thp,ROB_PMD_BYTES);
}
int main(void) {
    assert(sample(4096,4096,0,"rd wr mr mw me ac hg",true));
    assert(sample(0,4096,0,"rd wr mr mw me ac nh",false));
    assert(!sample(2048,4096,0,"rd wr mr mw me ac hg",true));
    assert(!sample(4096,2048,0,"rd wr mr mw me ac hg",true));
    assert(!sample(4096,4096,4,"rd wr mr mw me ac hg",true));
    assert(!sample(4096,4096,0,"rd wr mr mw me ac nh",true));
    assert(!sample(0,4096,0,"rd wr mr mw me ac nhx",false));
    assert(!sample(0,4096,0,"rd wr mr mw me ac hg",true));
    assert(!sample(4096,4096,0,"rd wr mr mw me ac hg",false));
    struct rob_backing_info out;
    const char *fields="KernelPageSize: 4 kB\nMMUPageSize: 4 kB\n"
        "AnonHugePages: 4096 kB\nRss: 4096 kB\nSwap: 0 kB\nVmFlags: rd wr hg\n";
    char text[1024];
    snprintf(text,sizeof(text),"100000-600000 rw-p 0 00:00 0\n%s",fields);
    assert(!parse(text,&out)); // 仅覆盖目标范围的大VMA不能冒充精确mapping。
    snprintf(text,sizeof(text),"200000-600000 rw-p 0 00:00 0\n%s",fields);
    assert(parse(text,&out));
    assert(!rob_backing_matches(&out,0x400000,true,0x100000));
    assert(!rob_backing_matches(&out,0x300000,true,ROB_PMD_BYTES));
    assert(!parse("200000-600000 rw-p 0 00:00 0\nAnonHugePages: 4096 kB\n",&out));
    snprintf(text,sizeof(text),"200000-600000 rw-p 0 00:00 0\n%sRss: 4096 kB\n",fields);
    assert(!parse(text,&out));
    snprintf(text,sizeof(text),"200000-600000 rw-p 0 00:00 0\n%sSwap: 0 MB\n",fields);
    assert(!parse(text,&out));
    FILE *pmd=tmpfile(); assert(pmd); fputs("2097152\n",pmd); rewind(pmd);
    size_t pmd_bytes=0; assert(rob_backing_read_pmd(pmd,&pmd_bytes) && pmd_bytes==ROB_PMD_BYTES); fclose(pmd);
    pmd=tmpfile(); assert(pmd); fputs("1048576\n",pmd); rewind(pmd);
    assert(!rob_backing_read_pmd(pmd,&pmd_bytes)); fclose(pmd);
    pmd=tmpfile(); assert(pmd); fputs("2097152 junk\n",pmd); rewind(pmd);
    assert(!rob_backing_read_pmd(pmd,&pmd_bytes)); fclose(pmd);
    for(unsigned i=1;i<=3;++i) {
        size_t bytes=i*ROB_PMD_BYTES; char *mem=rob_backing_map_2m(bytes);
        assert(mem!=MAP_FAILED && (uintptr_t)mem%ROB_PMD_BYTES==0);
        mem[0]=1; mem[bytes-1]=2; assert(mem[0]==1 && mem[bytes-1]==2);
        assert(!munmap(mem,bytes));
    }
    assert(rob_backing_map_2m(0)==MAP_FAILED);
    assert(rob_backing_map_2m(ROB_PMD_BYTES+4096)==MAP_FAILED);
    out=(struct rob_backing_info){.kernel_kb=4,.mmu_kb=4,.huge_kb=4096,.rss_kb=4096};
    rob_backing_json(stdout,&out); putchar('\n'); rob_backing_json(stdout,NULL); putchar('\n');
    return 0;
}
''')
        exe = pathlib.Path(self.tmp.name) / 'backing'
        compiled = subprocess.run(['clang', '-O2', '-Wall', '-Wextra', '-Werror', '-I',
                        str(ROOT / 'probes/common'), str(harness), '-o', str(exe)],
                        capture_output=True, text=True)
        self.assertEqual(compiled.returncode, 0, compiled.stderr)
        executed = subprocess.run([str(exe)], capture_output=True, text=True)
        self.assertEqual(executed.returncode, 0, executed.stderr)
        observation, absent = [json.loads(line) for line in executed.stdout.splitlines()]
        self.assertEqual(observation, {
            'kernel_page_kb': 4, 'mmu_page_kb': 4, 'anon_huge_kb': 4096,
            'rss_kb': 4096, 'swap_kb': 0, 'no_huge': False,
        })
        self.assertIsNone(absent)

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
