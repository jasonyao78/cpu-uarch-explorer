# SPDX-License-Identifier: Apache-2.0
# Platform-specific capability probes, scoped by their narrowest platform API
# boundary. A subdir is added only when the target OS provides that API; this
# keeps Mach-specific probes out of Linux builds while allowing Linux UAPI
# probes to be reused across x86-64, AArch64, and future RISC-V targets.
if(APPLE)
    add_subdirectory(macos-arm64)
endif()

if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    add_subdirectory(linux)
endif()

# Android arm64 currently consumes statically linked Linux UAPI probes produced
# by the linux-aarch64 cross preset; Android-specific APIs still belong in a
# separate backend directory when one is needed.
