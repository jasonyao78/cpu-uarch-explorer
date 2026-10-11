import capstone,collections,hashlib,json,subprocess,tempfile,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from tools.diagnostic.rob_zero_analysis import registered_plan,expected_code
md=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_ARM);rows=[]
with tempfile.TemporaryDirectory() as d:
 f=Path(d)/'code'
 for p in registered_plan()['conditions']:
  cfg=json.loads(subprocess.check_output([sys.argv[1],*p['args'],'--write-asm',str(f)],text=True));code=f.read_bytes();ins=list(md.disasm(code,0));loop=[i for i in ins if cfg['loop_offset']<=i.address<=cfg['branch_offset']]
  assert len(ins)*4==len(code) and len(loop)==cfg['loop_instructions']
  assert loop[-2].mnemonic=='subs' and loop[-2].op_str=='x3, x3, #1' and loop[-1].mnemonic=='b.ne' and int(loop[-1].op_str[1:],0)==64
  anchor=[i for i in loop if i.mnemonic=='fsqrt'];assert len(anchor)==cfg['anchors_per_iteration'] and all(i.op_str=='d0, d0' for i in anchor)
  fillers=[i for i in loop[:-2] if i.mnemonic!='fsqrt'];assert len(fillers)==cfg['fillers_per_iteration']
  if cfg['class']=='nop':assert all(i.mnemonic=='nop' for i in fillers)
  else:
   allowed={f'd{i}' for i in range(4,8)} if cfg['class']=='fadd' else {f'x{i}' for i in range(4,12)}
   assert all(i.op_str.split(',')[0] in allowed for i in fillers)
  if cfg['class'] in ('movi','mov0'):assert all(i.mnemonic=='mov' and i.op_str.split(', ')[1]==('#0' if cfg['class']=='mov0' else '#1') for i in fillers)
  if cfg['class']=='movr':assert all(i.mnemonic=='mov' and i.op_str.split(', ')[1]=='x16' for i in fillers)
  assert code==expected_code(p)
  rows.append(dict(condition=p['name'],code_sha256=hashlib.sha256(code).hexdigest(),config=cfg,body_mnemonics=dict(collections.Counter(i.mnemonic for i in loop)),filler_destination_registers=sorted({i.op_str.split(',')[0] for i in fillers if i.mnemonic!='nop'}),branch=f'{loop[-1].address:#x}->{64:#x}'))
(Path(__file__).resolve().parent/'code-audit.json').write_text(json.dumps(dict(capstone_version=capstone.__version__,actual_exported_cases=64,cases=rows),indent=2)+'\n')
print('64 real exported code streams independently decoded; branch, counts and register contracts passed')
