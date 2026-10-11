import hashlib,json,struct,sys
from pathlib import Path
import capstone
b=Path(sys.argv[1]).read_bytes();shoff=struct.unpack_from('<Q',b,40)[0];ents,n,strings=struct.unpack_from('<HHH',b,58)
sections=[struct.unpack_from('<IIQQQQIIQQ',b,shoff+i*ents) for i in range(n)]
syms={}
for sec in sections:
 if sec[1]!=2:continue
 st=sections[sec[6]];names=b[st[4]:st[4]+st[5]]
 for offset in range(sec[4],sec[4]+sec[5],sec[9]):
  name,info,other,index,address,size=struct.unpack_from('<IBBHQQ',b,offset);label=names[name:names.index(0,name)].decode();syms[label]=(index,address,size)
md=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_ARM);rows=[]
for k in (1,):
 index,address,size=syms['distribution_k'+str(k)];sec=sections[index];code=b[sec[4]+address-sec[3]:sec[4]+address-sec[3]+size];ins=list(md.disasm(code,address));assert len(ins)*4==size
 branch=next(i for i in ins if i.mnemonic=='b.ne');target=int(branch.op_str.lstrip('#'),16);loop=[i for i in ins if target<=i.address<=branch.address];expected=[('ldr',f'x{i}, [x{i}]') for i in range(k)]+[('subs','x8, x8, #1'),('b.ne',branch.op_str)]
 assert [(i.mnemonic,i.op_str) for i in loop]==expected and loop[-1].address==target+4*(k+1) and ins[-1].mnemonic=='ret'
 rows.append(dict(k=k,symbol='distribution_k'+str(k),address=hex(address),bytes=size,loop_address=hex(target),instructions=[dict(address=hex(i.address),mnemonic=i.mnemonic,operands=i.op_str) for i in ins],loop_loads=k,loop_instructions=k+2,loop_spills=0))
(Path(__file__).resolve().parent/'code-audit.json').write_text(json.dumps(dict(binary_sha256=hashlib.sha256(b).hexdigest(),capstone_version=capstone.__version__,kernels=rows),indent=2)+'\n');print('1 actual ELF kernel independently decoded: self-dependent registers, exact loop, no spills')
