# 实际 binary 窗口审计

目的：验证 `probes/diagnostic/tlb_address_geometry.cpp` 的最终 filler 与目标 load 之间没有重新读取 target 元数据。

NDK binary SHA256 `0093bbfb6680412c27ad7006328a545ddb643f964c143dd413c7961fde1fd666`。`measured-window.txt` 为该 ELF 的 llvm-objdump 导出函数。0x245210 的 F128链循环在第一 snapshot 之前；start/count/slot 参数已保存。两 snapshot 之间的0x245234仅执行指定count次链接load；count0走跳过分支。编译器生成的包装分支保留，不声称零开销或证明硬件admission。完整实际链接轨迹由 `tools/diagnostic/tests/test_tlb_geometry_producer.py` 验证108cell/15552shot及全部18地址族；host证据不是目标测量。
