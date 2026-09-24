# SPDX-License-Identifier: Apache-2.0
cmake_minimum_required(VERSION 3.16)
project(cpu-uarch-probes LANGUAGES C CXX)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

add_subdirectory(probes/cache-mem)
add_subdirectory(probes/platform)
