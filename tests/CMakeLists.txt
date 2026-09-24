# SPDX-License-Identifier: Apache-2.0
# Fast boundary/contract tests for probes (run by CTest).
# These are NOT hardware smoke tests: microbenchmark sweeps are too slow
# and too machine-dependent to be unit tests. Valid-input tests assert
# exit code 0 and a numeric latency field; invalid-input tests assert
# non-zero exit (WILL_FAIL) so a silent nan/inf record can never pass.

set(PT $<TARGET_FILE:ptr_chase>)

add_test(NAME ptr_chase_valid_small COMMAND ${PT} -b 64 -s 64 -n 8000)
set_tests_properties(ptr_chase_valid_small PROPERTIES
    PASS_REGULAR_EXPRESSION "latency_ns=[0-9]+\\.[0-9]+")

add_test(NAME ptr_chase_rejects_tiny_loads COMMAND ${PT} -n 1)
set_tests_properties(ptr_chase_rejects_tiny_loads PROPERTIES WILL_FAIL TRUE)

add_test(NAME ptr_chase_rejects_misaligned_stride COMMAND ${PT} -b 64 -s 9 -n 8000)
set_tests_properties(ptr_chase_rejects_misaligned_stride PROPERTIES WILL_FAIL TRUE)

add_test(NAME ptr_chase_rejects_stride_gt_buffer COMMAND ${PT} -b 4 -s 999999 -n 8000)
set_tests_properties(ptr_chase_rejects_stride_gt_buffer PROPERTIES WILL_FAIL TRUE)

add_test(NAME ptr_chase_rejects_zero_buffer COMMAND ${PT} -b 0 -s 64 -n 8000)
set_tests_properties(ptr_chase_rejects_zero_buffer PROPERTIES WILL_FAIL TRUE)

# hugepage 能力分级（Probe ABI 退出码 2 = unsupported；fallback 标注）：
# macOS 无 MAP_HUGETLB → 期望非零退出；Linux 无页池 → 期望成功且输出显式标注
if(APPLE)
  add_test(NAME ptr_chase_hugepage_unsupported COMMAND ${PT} -b 4096 -s 64 -n 8000 -h)
  set_tests_properties(ptr_chase_hugepage_unsupported PROPERTIES WILL_FAIL TRUE)
else()
  add_test(NAME ptr_chase_hugepage_fallback_or_ok
           COMMAND ${PT} -b 4096 -s 64 -n 8000 -h)
  set_tests_properties(ptr_chase_hugepage_fallback_or_ok PROPERTIES
      PASS_REGULAR_EXPRESSION "page_policy=")
endif()
