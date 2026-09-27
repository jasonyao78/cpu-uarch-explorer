# SPDX-License-Identifier: Apache-2.0
cmake_minimum_required(VERSION 3.16)
project(cpu-uarch-probes LANGUAGES C CXX)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

add_subdirectory(probes/platform)
add_subdirectory(probes/cache-mem)

option(ENABLE_UBSAN "Build probes with UndefinedBehaviorSanitizer" OFF)

if(ENABLE_UBSAN)
  add_executable(ptr_chase_ubsan probes/cache-mem/ptr_chase.cpp)
  if(TARGET linux_perf_counter)
    target_link_libraries(ptr_chase_ubsan PRIVATE linux_perf_counter)
  endif()
  target_compile_options(ptr_chase_ubsan PRIVATE -fsanitize=undefined -g -O1)
  target_link_options(ptr_chase_ubsan PRIVATE -fsanitize=undefined)
endif()

enable_testing()
add_subdirectory(tests)

if(ENABLE_UBSAN)
  add_test(NAME ptr_chase_ubsan_valid
           COMMAND $<TARGET_FILE:ptr_chase_ubsan> -b 64 -s 64 -n 80000)
  set_tests_properties(ptr_chase_ubsan_valid PROPERTIES
      PASS_REGULAR_EXPRESSION "latency_ns=[0-9]+\\.[0-9]+"
      FAIL_REGULAR_EXPRESSION "runtime error")
endif()
