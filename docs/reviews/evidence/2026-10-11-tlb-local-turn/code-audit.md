# 局部转折实际窗口审计

目的：核验新 `probes/diagnostic/tlb_local_turn.cpp` binary 中最终F128之后没有重新读取target元数据。

NDK binary SHA256 `cb0400a40d0877e88bcdbb07cb5902728dd7e1376db5f0f6c647e21a83a69e07`。同目录 `measured-window.txt` 为实际llvm-objdump函数：0x2451b0的F链load在第一snapshot前；0x2451d4为两snapshot之间唯一static目标load，由count循环，W1的count0分支跳过。start/count/slot在F前已取得。只核码形，不以此排除PMU包装、证明admission或解释物理ways。真实host全部八地址族/96cell/13824shot链接轨迹在 `tools/diagnostic/tests/test_tlb_turn_producer.py`；host证据不代替目标数据。
