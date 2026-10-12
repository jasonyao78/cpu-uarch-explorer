"""Actual producer bytecode, independently interpreted; simulated memory is not device evidence."""
import json,struct,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
MAP=0x20000;TASK=0x30000;MM=0x40000;PGD=0x50000;STACK=0x80000

def interpret(program,syscall_id=172,pid=12345,fail_read=0,task_pid=12345,map_present=True):
    regs=[0]*11;regs[1]=0x10000;regs[10]=STACK;mem={};reads=[]
    def store(addr,value,size):
        for i,b in enumerate(int(value%(1<<(8*size))).to_bytes(size,'little')):mem[addr+i]=b
    def load(addr,size):return int.from_bytes(bytes(mem.get(addr+i,0) for i in range(size)),'little')
    for j in range(64):store(MAP+j,0,1)
    store(regs[1]+8,syscall_id,8);store(TASK+1588,task_pid,4);store(TASK+1440,MM,8);store(MM+56,PGD,8)
    store(PGD+3*8,0xabc003,8);store(PGD+4*8,0xdef003,8)
    pc=0;steps=0
    while pc<len(program):
        steps+=1;assert steps<400
        x=program[pc];code,dst,src,off,imm=[x[k] for k in ('code','dst','src','off','imm')];next_pc=pc+1
        if code==0x18:
            regs[dst]=(program[pc+1]['imm']&0xffffffff)<<32|(imm&0xffffffff);next_pc+=1
        elif code==0xbf:regs[dst]=regs[src]
        elif code==0xb7:regs[dst]=imm&0xffffffffffffffff
        elif code==0x07:regs[dst]=(regs[dst]+imm)&0xffffffffffffffff
        elif code==0x77:regs[dst]>>=imm
        elif code in (0x79,0x61):regs[dst]=load(regs[src]+off,8 if code==0x79 else 4)
        elif code in (0x7b,0x63):store(regs[dst]+off,regs[src],8 if code==0x7b else 4)
        elif code in (0x7a,0x62):store(regs[dst]+off,imm,8 if code==0x7a else 4)
        elif code in (0x55,0x15):
            condition=regs[dst]!=(imm&0xffffffffffffffff)
            if condition==(code==0x55):next_pc+=off
        elif code==0x85:
            if imm==14:regs[0]=(pid<<32)|pid
            elif imm==35:regs[0]=TASK
            elif imm==1:
                assert load(regs[2],4)==0;regs[0]=MAP if map_present else 0
            elif imm==113:
                reads.append((regs[3],regs[2]));nth=len(reads)
                if nth==fail_read:regs[0]=(-14)&0xffffffffffffffff
                else:
                    assert (regs[3],regs[2]) in [(TASK+1588,4),(TASK+1440,8),(MM+56,8),(PGD+24,8),(PGD+32,8)]
                    value=load(regs[3],regs[2]);store(regs[1],value,regs[2]);regs[0]=0
            else:raise AssertionError('unknown helper')
            for j in range(1,6):regs[j]=0
        elif code==0x95:break
        else:raise AssertionError('unknown opcode '+hex(code))
        assert 0<=next_pc<len(program);pc=next_pc
    else:raise AssertionError('missing exit')
    return [load(MAP+j*8,8) for j in range(8)],reads

class TestSelfBytecode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source=ROOT/'probes/diagnostic/translation_self_read.c'
        assert source.exists(),'registered translation_self_read producer is missing'
        cls.temp=tempfile.TemporaryDirectory();cls.binary=Path(cls.temp.name)/'self-read'
        subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror',str(source),'-o',str(cls.binary)],check=True,capture_output=True)
        cls.plan=json.loads(subprocess.check_output([str(cls.binary),'--plan'],text=True));cls.program=cls.plan['instructions']
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_positive_actual_emitter_reads_only_own_root(self):
        out,reads=interpret(self.program);self.assertEqual(out,[6,12345,MM,PGD,0xabc003,0xdef003,0,1]);self.assertEqual(len(reads),5)
        self.assertEqual(self.plan['root_indices'],[3,4]);self.assertEqual(self.plan['task_mm'],1440);self.assertEqual(self.plan['mm_pgd'],56)
    def test_double_filter_dominates_all_kernel_reads(self):
        for kwargs in (dict(pid=12346),dict(syscall_id=178),dict(pid=12346,syscall_id=178)):
            out,reads=interpret(self.program,**kwargs);self.assertEqual(out,[0]*8);self.assertEqual(reads,[])
    def test_each_helper_failure_stops_without_synthetic_success(self):
        for stage in range(1,6):
            out,reads=interpret(self.program,fail_read=stage);self.assertEqual(out[0],stage);self.assertEqual(out[6],(1<<64)-14);self.assertEqual(len(reads),stage);self.assertEqual(out[7],1)
    def test_btf_tgid_sanity_mismatch_stops_before_mm(self):
        out,reads=interpret(self.program,task_pid=54321);self.assertEqual(out[0],1);self.assertEqual(len(reads),1)
    def test_map_missing_no_memory_read(self):
        out,reads=interpret(self.program,map_present=False);self.assertEqual(out,[0]*8);self.assertEqual(reads,[])
    def test_program_jump_bounds_and_host_cannot_claim_android(self):
        for i,x in enumerate(self.program):
            if x['code'] in (0x15,0x55):self.assertTrue(0<=i+1+x['off']<len(self.program));self.assertGreaterEqual(x['off'],0)
        p=subprocess.run([str(self.binary),'--run'],text=True,capture_output=True);self.assertNotEqual(p.returncode,0);d=json.loads(p.stdout);self.assertEqual(d['failure']['reason'],'requires-linux-aarch64');self.assertEqual(d['metrics'],{})
if __name__=='__main__':unittest.main()
