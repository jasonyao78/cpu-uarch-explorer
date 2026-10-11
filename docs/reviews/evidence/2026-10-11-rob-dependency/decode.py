import capstone,collections,hashlib,json,subprocess,tempfile,sys
from pathlib import Path
root=Path(__file__).resolve().parents[4];sys.path.insert(0,str(root));from tools.diagnostic.rob_dependency_analysis import registered_plan,expected_code
md=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_ARM);rows=[]
with tempfile.TemporaryDirectory() as d:
 f=Path(d)/'code'
 for p in registered_plan()['conditions']:
  cfg=json.loads(subprocess.check_output([sys.argv[1],*p['args'],'--write-asm',str(f)],text=True));b=f.read_bytes();ins=list(md.disasm(b,0));loop=[i for i in ins if cfg['loop_offset']<=i.address<=cfg['branch_offset']]
  assert len(ins)*4==len(b) and len(loop)==cfg['loop_instructions'];assert loop[-2].op_str=='x3, x3, #1' and loop[-1].mnemonic=='b.ne' and loop[-1].op_str=='#0x40' and ins[-1].mnemonic=='ret'
  anchors=[i for i in loop if i.mnemonic=='fsqrt'];assert len(anchors)==cfg['anchors_per_iteration'] and all(i.op_str=='d0, d0' for i in anchors)
  bridges=[i for i in loop if i.mnemonic=='fmov'];assert len(bridges)==2 and all(i.op_str=='x12, d0' for i in bridges)
  add=[i for i in loop if i.mnemonic=='add'];assert len(add)==2*cfg['n'];source='x12' if cfg['anchor_link']=='dependent' else 'x16'
  assert all(i.op_str==f'x{4+j%8}, {source}, x17' for j,i in enumerate(add))
  # Gap sequence, not just aggregate mnemonic counts, is audited independently.
  expected=[]
  for side in (0,1):
   expected.extend([('fsqrt','d0, d0')]*(cfg['chain'] if cfg['anchor']=='fsqrt' else 0));expected.append(('fmov','x12, d0'));expected.extend([('add',f'x{4+j%8}, {source}, x17') for j in range(cfg['n'])])
  assert [(i.mnemonic,i.op_str) for i in loop[:-2]]==expected and b==expected_code(p)
  rows.append(dict(condition=p['name'],config=cfg,code_sha256=hashlib.sha256(b).hexdigest(),body_mnemonics=dict(collections.Counter(i.mnemonic for i in loop)),bridge='x12,d0',ADD_Rn=source,branch=f'{loop[-1].address:#x}->0x40'))
(Path(__file__).resolve().parent/'code-audit.json').write_text(json.dumps(dict(capstone_version=capstone.__version__,actual_exported_cases=48,cases=rows),indent=2)+'\n');print('48 actual bodies independent Capstone: each bridge/source, gap sequence, branch and RET exact')
