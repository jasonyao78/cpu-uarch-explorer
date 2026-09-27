# SPDX-License-Identifier: Apache-2.0
add_executable(ptr_chase ptr_chase.cpp)
if(TARGET linux_perf_counter)
    target_link_libraries(ptr_chase PRIVATE linux_perf_counter)
endif()
