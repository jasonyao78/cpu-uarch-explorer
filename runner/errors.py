# SPDX-License-Identifier: Apache-2.0
"""统一错误类型与 CLI 退出码阶梯（OI-9 蓝图：exit code 阶梯）。

0 = 全部成功；1 = 配置/输入错误；2 = 运行期有 case 失败（数据已落盘）。
"""

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_RUN_FAILURES = 2


class RunnerError(Exception):
    """配置/输入类错误（对应退出码 1）。"""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class ParseError(RunnerError):
    """probe 输出解析失败——绝不据此编造测量值。"""

    def __init__(self, message: str):
        super().__init__("parse-error", message)
