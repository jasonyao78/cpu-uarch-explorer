# Runbook：在 Xeon 服务器上构建 gem5（D9300 overlay）

> 前置约定（v0.3 §2.2）：代码与构建目录放 **NVMe**（2TB Samsung 990 PRO），不要放 HDD 的 `/hdd_10T/...` 工作目录。gem5 全量构建约 20–40 分钟（56C + NVMe）。

## 0. 获取代码（二选一）

**方式 A：GitHub 克隆（推荐，私有仓需认证）**

```bash
# 服务器上先完成 gh 认证（jasonyao78 账号）：
#   gh auth login
gh repo clone jasonyao78/cpu-uarch-explorer -- --recurse-submodules
cd cpu-uarch-explorer
# 若已克隆但未带子模块：
#   git submodule update --init
```

**方式 B：rsync 本机直传（服务器无法访问 GitHub 时用）**

```bash
# 在 M4 Pro 本机执行。注意：
# 1. macOS 自带 openrsync（2.6.9 兼容）不支持 --info=progress2，用 --progress；
#    想要总进度条可 brew install rsync 后用 rsync3 的 --info=progress2。
# 2. 必须排除构建产物（third_party/gem5/build/ 有 ~1.5GB macOS Mach-O 对象，
#    在 Linux 上完全无用；rsync 的 'build/' 模式按目录名匹配任意层级）。
# 3. 目标路径放 NVMe（先 lsblk / findmnt 确认挂载点；home 目录可能在 HDD 上）。
rsync -a --progress \
  --exclude '.DS_Store' \
  --exclude 'build/' \
  --exclude 'build-x86/' \
  --exclude 'build-ubsan/' \
  --exclude 'third_party/gem5/build-macos-arm64.log' \
  /Users/michaelyao/workspace/cpu-uarch-explorer/ \
  <server>:/path/on/nvme/cpu-uarch-explorer/
# submodule 说明：absorbgitdirs 后 third_party/gem5/.git 是指向
# ../../.git/modules/third_party/gem5 的相对指针，rsync -a 带上 .git 即在服务器侧可用。
```

## 1. Python 环境（uv，ADR-0007）

```bash
# 服务器已装 uv（~/.local/bin/uv；如需重装：curl -LsSf https://astral.sh/uv/install.sh | sh）
cd /path/on/nvme/cpu-uarch-explorer
uv sync        # 按 uv.lock 建 .venv（uv 托管 CPython 3.12 + scons + protobuf）
# gem5 构建前：让 SConstruct 找到与 venv 同源的 python3-config（已实测通过 gem5 embed 检查）
export PATH="$(uv run python -c 'import sys; print(sys.base_prefix)')/bin:$PATH"
```

## 1b. 系统依赖（Ubuntu 24.04，已具备）

`build-essential`（gcc/g++/make/elf.h）、`protobuf-compiler`（protoc 3.21）、`python3-dev` 已在系统内；scons/protobuf 的 Python 侧由 uv 提供，**无需 apt/pip 混合安装**。tcmalloc / capstone / png 为可选增强，缺失只产生警告。

## 1c. 旧方式存档（勿用）

conda Python（gem5 链接检查失败）；系统 pip 直装（PEP 668 漂移）。详见 ADR-0007。

## 2. 同步 D9300 overlay

```bash
sh third_party/gem5-d9300-patch/gem5/apply_patchset.sh
```

## 3. 构建

```bash
cd third_party/gem5
uv run scons build/ARM/gem5.opt -j56 2>&1 | tee build-xeon-arm64.log
```

## 4. 验证与回传

```bash
./build/ARM/gem5.opt --version
tail -5 build-xeon-arm64.log
```

把 **scons 退出码** 和日志尾部贴回 OI-1（Issue #1），并注明构建目录所在磁盘（NVMe/HDD）。

## 附：macOS 构建结论（2026-09-24 实测，勿重复踩坑）

configure 通过，922 个对象编译成功（含 delta 的 `coral_backend` / `coral_stagea_backend` / `npu_device`），唯一硬错误：

```
src/dev/npu/coral_verilated_backend.cc: fatal error: 'elf.h' file not found
```

`<elf.h>` 是 glibc 专属头文件，macOS（Mach-O）不提供。verilated NPU 后端本身就是 Linux + Verilator + NPU RTL 流程，**macOS 不做 gem5 构建平台**。若将来需要 macOS 本地构建非 verilated 变体，可在 delta 中对 verilated 后端加 `__APPLE__` 守卫（backlog，需 NPU 流程负责人确认）。
