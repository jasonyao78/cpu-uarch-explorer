#!/usr/bin/env python3
"""Independent Capstone decode of the actual host-exported A64 bytes.
Run: uv run --no-project --with capstone python tools/diagnostic/audit_rob_disassembly.py EXPORTER OUTPUT
"""
from pathlib import Path
from collections import Counter
import hashlib
import json
import subprocess
import sys
import tempfile
import capstone

md=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_ARM)
results=[]
with tempfile.TemporaryDirectory() as tmp:
    for cls,opcode in [('nop','nop'),('add','add'),('movi','mov'),('movr','mov'),('fadd','fadd'),('ldr','ldr'),('str','str')]:
        path=Path(tmp)/'code.bin'
        p=subprocess.run([sys.argv[1],'-t',cls,'-n','9','-a','fsqrt','--chain','1','--align','32','--write-asm',str(path)],check=True,capture_output=True,text=True)
        config=json.loads(p.stdout); data=path.read_bytes(); insns=list(md.disasm(data,0))
        assert len(insns)*4==len(data)
        loop=[i for i in insns if config['loop_offset']<=i.address<=config['branch_offset']]
        counts=Counter(i.mnemonic for i in loop)
        assert counts['fsqrt']==2 and counts[opcode]==18 and counts['subs']==counts['b.ne']==1
        assert loop[-2].op_str=='x3, x3, #1'
        assert int(loop[-1].op_str[1:],0)==config['loop_offset']
        if cls=='fadd':
            assert {i.op_str.split(',')[0] for i in loop if i.mnemonic=='fadd'}=={'d4','d5','d6','d7'}
        results.append({'class':cls,'config':config,'code_sha256':hashlib.sha256(data).hexdigest(),
                        'body_mnemonics':dict(counts),'loop_disassembly':[f'{i.address:04x}: {i.mnemonic} {i.op_str}' for i in loop]})
Path(sys.argv[2]).write_text(json.dumps({'capstone_version':capstone.__version__,'cases':results},indent=2)+'\n')
print('decoded seven actual generated loops; branch/count/register contracts passed')
