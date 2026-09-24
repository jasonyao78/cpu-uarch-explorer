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
# 在 M4 Pro 本机执行：
rsync -a --info=progress2 \
  /Users/michaelyao/workspace/cpu-uarch-explorer/ \
  <server>:/path/on/nvme/cpu-uarch-explorer/
# 注意 third_party/gem5 是 submodule：确认 .git 目录/文件一并同步（rsync -a 会带）
```

## 1. 系统依赖（Ubuntu 24.04）

```bash
sudo apt update
sudo apt install -y build-essential scons protobuf-compiler libprotobuf-dev \
    libgoogle-perftools-dev libpng-dev libcapstone-dev python3-dev python3-pip
python3 -m pip install -r third_party/gem5/requirements.txt
```

- `elf.h`（verilated NPU 后端需要）由 `libc6-dev` 提供，已含在 build-essential 内；
- tcmalloc / capstone / png 为可选项，但建议装（性能与调试功能）；
- gem5 官方支持的 Python 版本范围内使用系统 python3 即可（Ubuntu 24.04 = 3.12，验证可行；**不要用 conda Python**，macOS 上它未过 gem5 链接检查）。

## 2. 同步 D9300 overlay

```bash
sh third_party/gem5-d9300-patch/gem5/apply_patchset.sh
```

## 3. 构建

```bash
cd third_party/gem5
scons build/ARM/gem5.opt -j56 2>&1 | tee build-xeon-arm64.log
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
