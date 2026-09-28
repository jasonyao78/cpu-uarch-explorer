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

add_test(NAME ptr_chase_default_warmup_two_passes
         COMMAND ${PT} -b 64 -s 64 -n 8000)
set_tests_properties(ptr_chase_default_warmup_two_passes PROPERTIES
    PASS_REGULAR_EXPRESSION
    "warmup_loads=2048 warmup_passes_effective=2\\.000000 warmup_state=warm")

add_test(NAME ptr_chase_explicit_warmup_loads
         COMMAND ${PT} -b 64 -s 64 -n 8000 -w 1000)
set_tests_properties(ptr_chase_explicit_warmup_loads PROPERTIES
    PASS_REGULAR_EXPRESSION
    "warmup_loads=1000 warmup_passes_effective=0\\.976562 warmup_state=warm")

add_test(NAME ptr_chase_warmup_zero_is_not_cold
         COMMAND ${PT} -b 64 -s 64 -n 8000 -w 0)
set_tests_properties(ptr_chase_warmup_zero_is_not_cold PROPERTIES
    PASS_REGULAR_EXPRESSION "warmup_state=cold-warm0")

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
  add_test(NAME ptr_chase_thp_unsupported COMMAND ${PT} -b 4096 -s 64 -n 8000 -T)
  set_tests_properties(ptr_chase_thp_unsupported PROPERTIES WILL_FAIL TRUE)
  add_test(NAME ptr_chase_base_pages_unsupported COMMAND ${PT} -b 4096 -s 64 -n 8000 -B)
  set_tests_properties(ptr_chase_base_pages_unsupported PROPERTIES WILL_FAIL TRUE)
else()
  add_test(NAME ptr_chase_default_page_backing_observed
           COMMAND ${PT} -b 4096 -s 64 -n 8000)
  set_tests_properties(ptr_chase_default_page_backing_observed PROPERTIES
      PASS_REGULAR_EXPRESSION
      "page_policy_requested=default page_policy_actual=(base|thp|mixed) anon_huge_kb=[0-9]+")
  add_test(NAME ptr_chase_hugepage_fallback_or_ok
           COMMAND ${PT} -b 4096 -s 64 -n 8000 -h)
  set_tests_properties(ptr_chase_hugepage_fallback_or_ok PROPERTIES
      PASS_REGULAR_EXPRESSION "page_policy=")
  add_test(NAME ptr_chase_thp_requested_and_observed
           COMMAND ${PT} -b 4096 -s 64 -n 8000 -T)
  set_tests_properties(ptr_chase_thp_requested_and_observed PROPERTIES
      PASS_REGULAR_EXPRESSION
      "page_policy_requested=thp-madvise page_policy_actual=(base|thp|mixed) anon_huge_kb=[0-9]+")
  add_test(NAME ptr_chase_base_pages_requested_and_observed
           COMMAND ${PT} -b 4096 -s 64 -n 8000 -B)
  set_tests_properties(ptr_chase_base_pages_requested_and_observed PROPERTIES
      PASS_REGULAR_EXPRESSION
      "page_policy_requested=base-madvise page_policy_actual=base anon_huge_kb=0")
endif()

add_test(NAME ptr_chase_rejects_conflicting_page_requests
         COMMAND ${PT} -b 4096 -s 64 -n 8000 -T -h)
set_tests_properties(ptr_chase_rejects_conflicting_page_requests PROPERTIES WILL_FAIL TRUE)

add_test(NAME ptr_chase_rejects_base_and_thp
         COMMAND ${PT} -b 4096 -s 64 -n 8000 -B -T)
set_tests_properties(ptr_chase_rejects_base_and_thp PROPERTIES WILL_FAIL TRUE)

add_test(NAME ptr_chase_rejects_malformed_pmu_event
         COMMAND ${PT} -b 64 -s 64 -n 8000
                 --pmu-event not-a-descriptor)
set_tests_properties(ptr_chase_rejects_malformed_pmu_event PROPERTIES WILL_FAIL TRUE)

if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
  set(PCS $<TARGET_FILE:pmu_counter_smoke>)

  function(add_pmu_rejection_test name expected_regex)
    add_test(NAME ${name}
      COMMAND ${CMAKE_COMMAND}
        "-DPROGRAM=${PCS}"
        "-DEXPECT_REGEX=${expected_regex}"
        "-DARGS=${ARGN}"
        -P "${CMAKE_CURRENT_SOURCE_DIR}/assert_nonzero.cmake")
  endfunction()

  add_pmu_rejection_test(
    pmu_counter_smoke_rejects_malformed_config
    "config must be a base-0 unsigned integer"
    --pmu software --config xyz --scope thread
    --workload idle --duration-ms 1 --buffer-mib 1)
  add_pmu_rejection_test(
    pmu_counter_smoke_rejects_zero_duration
    "duration-ms must be in 1..600000"
    --pmu software --config 1 --scope thread
    --workload idle --duration-ms 0 --buffer-mib 1)
  add_pmu_rejection_test(
    pmu_counter_smoke_rejects_unknown_workload
    "workload must be idle or stream-read"
    --pmu software --config 1 --scope thread
    --workload guess --duration-ms 1 --buffer-mib 1)
  add_pmu_rejection_test(
    pmu_counter_smoke_requires_cpu_for_cpu_scope
    "cpu scope requires --cpu"
    --pmu software --config 1 --scope cpu
    --workload idle --duration-ms 1 --buffer-mib 1)
  add_pmu_rejection_test(
    pmu_counter_smoke_rejects_missing_type_source
    "exactly one of --pmu or --type is required"
    --config 1 --scope thread --workload idle
    --duration-ms 1 --buffer-mib 1)
  add_pmu_rejection_test(
    pmu_counter_smoke_rejects_conflicting_type_sources
    "exactly one of --pmu or --type is required"
    --pmu software --type 1 --config 1 --scope thread
    --workload idle --duration-ms 1 --buffer-mib 1)
  add_pmu_rejection_test(
    pmu_counter_smoke_rejects_type_overflow
    "type must be a 32-bit unsigned integer"
    --type 4294967296 --config 1 --scope thread
    --workload idle --duration-ms 1 --buffer-mib 1)
endif()

add_test(NAME ptr_chase_seed_is_recorded COMMAND ${PT} -b 64 -s 64 -n 8000 -S 7)
set_tests_properties(ptr_chase_seed_is_recorded PROPERTIES
    PASS_REGULAR_EXPRESSION "seed=7")

add_test(NAME ptr_chase_seed_default_42 COMMAND ${PT} -b 64 -s 64 -n 8000)
set_tests_properties(ptr_chase_seed_default_42 PROPERTIES
    PASS_REGULAR_EXPRESSION "seed=42")

add_test(NAME ptr_chase_rejects_seed_garbage COMMAND ${PT} -b 64 -s 64 -n 8000 -S abc)
set_tests_properties(ptr_chase_rejects_seed_garbage PROPERTIES WILL_FAIL TRUE)
