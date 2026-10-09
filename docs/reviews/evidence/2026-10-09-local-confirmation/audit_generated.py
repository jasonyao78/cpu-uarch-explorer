"""Decode each ACTUAL saved fine-grid loop; write anonymous audit evidence.

Usage: uv run --no-project --with capstone python <this-file> PRIVATE_RUN OUTPUT
No device access. Host bytes do not replace target INST_RETIRED validation.
"""
import hashlib
import json
from pathlib import Path
import sys
from collections import Counter
import capstone

raw=Path(sys.argv[1]); m=json.loads((raw/'manifest.json').read_text())
assert m['status']=='complete' and m['mode']=='rob-fine'
md=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_ARM)
results=[]
for entry in m['results']:
    generated=entry['generated_code']['single'];c=generated['config']
    data=(raw/(entry['name']+'-single.bin')).read_bytes()
    assert hashlib.sha256(data).hexdigest()==generated['sha256']
    insns=list(md.disasm(data,0));assert len(insns)*4==len(data)
    loop=[i for i in insns if c['loop_offset']<=i.address<=c['branch_offset']]
    counts=Counter(i.mnemonic for i in loop)
    assert len(loop)==c['loop_instructions'] and c['loop_offset']%64==c['loop_mod64']
    assert counts[c['class']]==2*c['n'] if c['n'] else counts[c['class']]==0
    assert counts['fsqrt']==(2*c['chain'] if c['anchor']=='fsqrt' else 0)
    assert counts['subs']==counts['b.ne']==1 and loop[-2].op_str=='x3, x3, #1'
    assert int(loop[-1].op_str[1:],0)==c['loop_offset']
    if c['class']=='fadd':
        assert not ({i.op_str.split(',')[0] for i in loop if i.mnemonic=='fadd'}&{'d0',*(f'd{i}' for i in range(8,16))})
    observed=[json.loads(s) for s in (raw/(entry['name']+'.stdout.jsonl')).read_text().splitlines()]
    assert [r for r in observed if r['type']=='config']==[c]
    results.append({'condition':entry['name'],'code_sha256':generated['sha256'],
                    'loop_mod64':c['loop_mod64'],'loop_instructions':len(loop),'body_mnemonics':dict(counts)})
Path(sys.argv[2]).write_text(json.dumps({'capstone_version':capstone.__version__,'cases':results},indent=2)+'\n')
print('decoded',len(results),'actual saved loops; config/branch/count/register checks passed')
