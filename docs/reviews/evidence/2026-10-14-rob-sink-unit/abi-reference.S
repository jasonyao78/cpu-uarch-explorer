.text
.global recipe_abi
recipe_abi:
stp x19,x20,[sp,#-64]!
stp x21,x22,[sp,#16]
stp x23,x24,[sp,#32]
stp x25,x26,[sp,#48]
dsb ish
mrs x20,pmccntr_el0
msr pmselr_el0,x11
isb
mrs x21,pmxevcntr_el0
stp x20,x21,[x5,#0]
stp x22,x23,[x5,#16]
stp x24,x25,[x5,#32]
stp x13,x14,[x5,#48]
stp x15,x16,[x5,#64]
stp x17,x19,[x5,#80]
ldp x25,x26,[sp,#48]
ldp x23,x24,[sp,#32]
ldp x21,x22,[sp,#16]
ldp x19,x20,[sp],#64
ret
