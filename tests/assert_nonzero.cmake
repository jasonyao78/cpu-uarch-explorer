# SPDX-License-Identifier: Apache-2.0
# Assert that a command is rejected for the expected reason. CTest's
# WILL_FAIL reverses the final pass/fail result after regex evaluation, which
# can let an unrelated diagnostic satisfy a negative-input test.

if(NOT DEFINED PROGRAM OR NOT DEFINED EXPECT_REGEX)
  message(FATAL_ERROR "PROGRAM and EXPECT_REGEX are required")
endif()

execute_process(
  COMMAND "${PROGRAM}" ${ARGS}
  RESULT_VARIABLE actual_exit
  OUTPUT_VARIABLE actual_stdout
  ERROR_VARIABLE actual_stderr
)

set(actual_output "${actual_stdout}\n${actual_stderr}")
if(actual_exit EQUAL 0)
  message(FATAL_ERROR
    "command unexpectedly succeeded\nstdout/stderr:\n${actual_output}")
endif()
if(actual_output MATCHES "status=ok")
  message(FATAL_ERROR
    "rejected command emitted status=ok\nstdout/stderr:\n${actual_output}")
endif()
if(NOT actual_output MATCHES "${EXPECT_REGEX}")
  message(FATAL_ERROR
    "missing expected diagnostic '${EXPECT_REGEX}'\n"
    "exit=${actual_exit}\nstdout/stderr:\n${actual_output}")
endif()
