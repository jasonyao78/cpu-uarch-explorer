# ADR-0007: Python 工具链采用 uv 管理

- 状态：已接受（2026-09-24）

## 背景

gem5 构建调试暴露了三类 Python 环境问题：

1. **conda Python 3.13 未过 gem5 链接检查**（"Can't find a working Python installation"）——其 `python3-config --ldflags` 不含独立链接所需的 `-lpython`；
2. 服务器（Ubuntu 24.04）系统 pip 受 PEP 668 约束，`pip install` 需 `--user`/`--break-system-packages` 之类的绕行，且与系统包管理漂移；
3. 项目要在 M4 Pro / Xeon 服务器 / 未来 CI 之间保持可复现的 Python 环境（与证据等级、artifact manifest 的纪律一致），散装 pip 做不到。

macOS 实测补充：uv 托管的 python-build-standalone 在 macOS 上**未过** gem5 的 pybind11 embed 检查（TryRun 失败，framework/rpath 问题）；Homebrew Python 可过。但 **Linux 上 uv 托管 Python 3.12 实测通过 embed 检查**（`UV_EMBED_OK`，2026-09-24 服务器实测），而 macOS 本就不是 gem5 构建平台（elf.h 阻塞，见 `docs/runbooks/build-gem5-xeon.md`）。

## 决策

- Python 工具链统一为 **uv**：`pyproject.toml` 声明依赖（当前：scons、protobuf~=5.29），`.python-version` 钉 3.12，`uv.lock` **入库**保证跨主机一致。
-  gem5 构建（Linux）：`uv sync` 后用 uv 托管 Python；构建前 `export PATH="$(uv run python -c 'import sys; print(sys.base_prefix)')/bin:$PATH"` 让 SConstruct 找到与 venv 同源的 `python3-config`。
- macOS 特例：uv 正常管理 runner/analysis 依赖；gem5 的 embed 检查若需在 macOS 验证，临时用 Homebrew Python 3.12（构建本身仍归 Linux）。
- 项目 Python 工作**不再混用** conda base、系统 pip `--user`、`--break-system-packages`。

## 后果

- 环境可复现性提升：`uv sync` 一条命令在两台 Host 上得到一致的锁定环境；
- 新增 Python 依赖必须改 `pyproject.toml` 并提交 `uv.lock`；
- 已知平台差异记录在案（macOS embed 检查），不追修——macOS 无 gem5 构建需求。
