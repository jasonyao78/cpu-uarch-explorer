# Runbook：Redmi `manet` 使用 KernelSU LKM 修补并刷写 `init_boot` 完整指南

> **入库说明（2026-09-27）**：本文由 Michael 在一次**已成功完成的实际操作**后整理，作为本仓 Android Target（`redmi-k70pro-01`，见 `docs/open-items.md` OI-2）的 root 闭环证据与 OTA 后重修补手册。证据等级：**MEASURED**（全部命令与输出来自实测）。
> **适用范围**：仅适用于下述精确设备与固件组合；其他设备/版本必须重新完成全部核验，**严禁复用 patched 镜像**。
> **快速路径**：已理解原理、仅需照章执行（或 OTA 后重刷）→ 直接看 **第二部分·第 16~22 章** 与 **附录 A 最简命令清单**。
> **镜像归档**（不入库，100MB 级二进制 + 可再生成）：`~/Downloads/manet-rom/manet_images_OS2.0.208.0.VNMCNXM_15.0/images/`——`init_boot_stock.img`（回滚件）/ `init_boot_kernelsu_lkm.img` / `SHA256SUMS` / `device-info.txt`。
> **信任链**：官方 ROM（bigota/cdnorg 小米 CDN）→ 手机端 KernelSU Manager 本地打补丁（LKM）→ 仅刷 init_boot 当前槽。不经第三方补丁镜像站。

---

# 第一部分：原理与前置条件

> 回答"为什么能 Root / 什么条件下才能这么做 / 各验证项在证明什么"。不急于操作的读者从这里读起；急于照章执行的读者可跳到第二部分。

## 1. Root 的本质与 KernelSU 的架构

### 1.1 Root 的本质

Android 的 Root 并不等同于"安装一个具有特殊权限的 APK"。

Android 应用最终运行在 Linux 内核管理的进程模型中。一个进程能够访问哪些资源，主要受以下机制共同约束：

- Linux UID、GID 和 supplementary groups；
- Linux capabilities；
- SELinux domain 与 SELinux policy；
- Android 应用沙箱；
- mount namespace；
- seccomp；
- 内核中的权限检查逻辑。

普通 ADB Shell 的典型身份是：

```text
uid=2000(shell)
gid=2000(shell)
```

成功通过 KernelSU 获取 Root 后，本次实测身份为：

```text
uid=0(root)
gid=0(root)
groups=0(root)
context=u:r:ksu:s0
```

这说明 KernelSU 不只是让一个命令在用户空间"看起来像 Root"，而是由内核侧完成了实际的凭据和安全上下文切换。

### 1.2 KernelSU 的核心架构

KernelSU 是一种基于 Linux 内核的 Android Root 方案，核心组件可以抽象为：

| 组件                      | 所在层级           | 主要职责                                                  |
| ------------------------- | ------------------ | --------------------------------------------------------- |
| KernelSU Kernel Component | 内核态             | Root 请求识别、调用者鉴权、进程凭据与安全上下文控制       |
| KernelSU LKM              | 内核模块           | 在 LKM 模式下将 KernelSU 内核能力动态装载进当前内核       |
| KernelSU Manager          | Android 用户空间   | 管理 Root 授权、App Profile、模块及配置                   |
| `ksud` 等用户空间组件   | Native 用户空间    | 模块脚本、配置、启动阶段任务及内核接口协同                |
| App Profile               | 内核态与用户态协同 | 按应用控制 UID、GID、groups、capabilities 和 SELinux 权限 |
| Module System             | 用户空间及挂载机制 | 实现脚本、属性、SELinux 规则以及 systemless 修改          |

KernelSU 的官方定义是：

```text
A Kernel based root solution for Android.
```

官方源码：

- KernelSU GitHub：[https://github.com/tiann/KernelSU](https://github.com/tiann/KernelSU)
- KernelSU 内核代码：[https://github.com/tiann/KernelSU/tree/main/kernel](https://github.com/tiann/KernelSU/tree/main/kernel)
- KernelSU 用户空间代码：[https://github.com/tiann/KernelSU/tree/main/userspace](https://github.com/tiann/KernelSU/tree/main/userspace)

### 1.3 本次 LKM 模式的工作原理

本次 KernelSU Manager 的修补日志包含：

```text
KMI: android14-6.1
Adding KernelSU LKM
Repacking boot image
```

这表明本次采用的是 `KernelSU LKM mode`（Loadable Kernel Module）：KernelSU 的内核功能不是预先静态编译到设备原始内核中，而是通过与当前 GKI/KMI 兼容的内核模块，在启动过程中加载到内核。

**深入：LKM 究竟如何被加载（当前上游 `ksuinit` 路径）**。当前主线的加载机制**不是**修改 kernel cmdline，也**不是**追加普通 `init.rc` service，而是修补 init_boot ramdisk，让 `ksuinit` 临时充当第一阶段的 `/init`：

1. 内核完成初始化、解包 ramdisk 后执行 `/init`（PID 1）——修补后这个入口是 `ksuinit`；真正的 init 被保留为 `/init.real`（后备路径 `/system/bin/init`）；
2. `ksuinit` 初始化 `/dev/kmsg` 日志、挂载 `/proc`、检查内核中是否已有 KernelSU（`has_kernelsu()`）——避免对已静态编入内核或已加载的场景重复加载；
3. 若尚未加载：读取 `/kernelsu.ko` 与 `/ksu_config`，**由 ksuinit 自身调用内核模块加载接口**（不是 shell 执行 `insmod`）——`.ko` 的 ELF 解析、vermagic/KMI 校验、符号解析、重定位均在内核完成；
4. 加载完成后，`ksuinit` 删除 `/init` 链接、重建指向 `/init.real` 的链接，然后 **`execve("/init")` 把 PID 1 交还真正的 Android init**（非 fork——无额外进程层级），此后 Android init 才开始解析 `init.rc`。

**为什么不走普通 `init.rc` 加载**：init.rc 路径要求 Android init 先启动并加载 SELinux policy、`insmod` 需对应 SELinux 权限、模块加载受签名/SELinux/内核配置限制；且 KernelSU 需要在更早阶段进入内核——在部分安全状态建立前完成加载，再由 `ksuinit` 透明移交。`/init` 包装器让"加载发生得足够早 + 完成后透明移交"同时成立。

**实证方法**（对本文 patched 镜像可做的验证）：分别解包 stock 与 patched `init_boot`，对比 ramdisk 文件清单并检查关键条目：

```bash
cd stock_ramdisk && find . -print | sort > ../stock.list
cd ../patched_ramdisk && find . -print | sort > ../patched.list
cd .. && diff -u stock.list patched.list
ls -l patched_ramdisk/init patched_ramdisk/init.real patched_ramdisk/kernelsu.ko patched_ramdisk/ksu_config
```

稳定不变的核心逻辑是：

1. KernelSU 的可信执行逻辑位于内核；
2. Manager 负责配置授权策略，而不是直接赋予自身 Root；
3. 内核根据调用者身份和授权策略决定是否允许权限提升；
4. 获得授权后，内核为目标进程建立相应的 Linux credentials；
5. 同时应用对应的 SELinux 策略和安全上下文；
6. 未授权应用不能仅靠调用 `su` 获得 Root。

### 1.4 为什么 KernelSU Manager 本身不能单独完成 Root

仅安装 KernelSU Manager APK 不足以获得 Root。

Manager 本质上只是控制面，主要负责：显示内核状态、管理 Root 授权、管理 App Profile、管理模块、与内核组件通信、维护用户可见的策略和配置。真正执行权限判定与权限提升的是内核侧 KernelSU 组件。

状态差异：

| Manager 状态                | 内核侧状态                  | 是否能够 Root                        |
| --------------------------- | --------------------------- | ------------------------------------ |
| 未安装 Manager              | KernelSU 已进入内核         | 内核能力可能存在，但缺少正常管理界面 |
| 已安装 Manager              | KernelSU 未进入内核         | 不能 Root                            |
| 已安装 Manager              | KernelSU 与 Manager 不兼容  | 可能无法连接或功能异常               |
| 已安装 Manager              | KernelSU 正常加载且版本兼容 | 可以进行受控 Root                    |
| Manager 显示`Unsupported` | 当前内核不满足官方支持条件  | 不能直接通过通用方案安装             |

本次设备在刷写 patched `init_boot_b` 之前，Manager 只能完成镜像修补；刷写并重新启动后，KernelSU LKM 被加载，Root 才真正生效。

### 1.5 KernelSU 如何完成权限提升

从 Linux 内核视角看，一个进程的权限由内核维护的 credentials 和安全状态决定。

KernelSU 在内核中对 Root 请求进行识别和鉴权。请求被允许后，内核可以为目标进程建立受控的权限集合：UID、GID、supplementary groups、Linux capabilities、SELinux domain、与 App Profile 对应的限制。

KernelSU 官方 App Profile 文档明确说明，Root Profile 可以控制：

```text
uid / gid / groups / capabilities / SELinux rules
```

因此 KernelSU 并非只能提供"全有或全无"的传统 Root，而是可以根据应用配置实施更接近最小权限原则的授权——防火墙应用只获得网络控制能力、不可信应用不获得 Root、调试 Shell 临时获得完整 Root 完成后再撤销。

官方 App Profile 文档：[https://kernelsu.org/guide/app-profile.html](https://kernelsu.org/guide/app-profile.html)

### 1.6 本次验证结果为什么能够证明 Root 生效

最终执行 `adb shell su -c id` 返回 `uid=0(root) gid=0(root) groups=0(root) context=u:r:ksu:s0`，各字段含义：

| 输出字段               | 含义                                      |
| ---------------------- | ----------------------------------------- |
| `uid=0(root)`        | 有效用户身份已经是 Root                   |
| `gid=0(root)`        | 主组已经是 Root 组                        |
| `groups=0(root)`     | supplementary group 中包含 Root 组        |
| `context=u:r:ksu:s0` | 进程已进入 KernelSU 对应的 SELinux domain |

同时 `getprop sys.boot_completed` 返回 `1`（Framework 已完成启动），`getprop ro.boot.slot_suffix` 返回 `_b`（从已刷写 `init_boot_b` 的槽位启动）。三个结果组成完整证据链：

```text
patched init_boot_b 成功启动 → Framework 正常启动 → KernelSU LKM 正常工作
→ su 请求通过 KernelSU 鉴权 → 进程获得 uid 0 → SELinux 上下文切换到 u:r:ksu:s0
```

### 1.7 KernelSU 模块与 Root 的区别

Root 功能解决"某个进程能否获得更高权限"，依赖内核组件、请求鉴权、App Profile、credentials 与 SELinux 控制。

Module 功能解决"如何在不直接修改只读系统分区的情况下改变系统行为"，可以提供启动脚本、系统属性、SELinux policy 扩展、可执行文件、配置文件、systemless 文件替换。KernelSU 官方文档指出，当前架构中如果模块需要修改 `/system` 文件，需要配合相应的 metamodule；仅使用脚本、`system.prop` 或 SELinux 规则的模块不一定需要 system 挂载 metamodule（官方模块文档：[https://kernelsu.org/guide/module.html](https://kernelsu.org/guide/module.html)）。

因此：

```text
Root 成功 ≠ 所有模块都会兼容或自动生效
```

模块仍可能因为 Android 版本变化、SELinux policy 不兼容、内核接口变化、脚本环境假设错误、启动阶段不匹配、metamodule 未安装、模块不支持当前 KernelSU 版本而失败。

---

### 1.8 SELinux 的两层修改（深入）

KernelSU 对 SELinux 的影响分两类，**不能混为一谈**：

**第一层：扩展全局内存态策略。** SELinux 决策 = 主体 SID + 客体 SID + class + permission 查 `policydb`。KernelSU 上游 `kernel/selinux/`（`sepolicy.c` 操作 policydb/avtab，`rules.c` 注入规则）加锁后向**活动** policydb 增加 KernelSU 所需 type/allow/transition 规则，然后**刷新 AVC**（`avc_ss_reset` 等并发布策略更新通知）——否则旧的拒绝决策仍被缓存生效。这不是把 SELinux 设为 Permissive：**Enforcing 继续，策略被扩展**。

**第二层：切换获准进程的 SID。** SELinux 内核比较用整数 SID 而非字符串。授权时 KernelSU（`selinux.c`：`security_secctx_to_secid`）把目标 context（如 `u:r:ksu:s0`）转换为 SID，写入为新进程准备的新 credentials 的安全结构，再 `commit_creds`——目标进程从原 domain 切换到 KernelSU Root domain。

**修改的是磁盘上的 sepolicy 文件吗？主要不是。** 本次未刷写 `/system`、`/vendor` 的 sepolicy 文件；变化发生在内核活动 policydb、AVC 缓存与获准进程的 SID。重启后原始策略重新加载，KernelSU LKM 再次初始化并重新应用运行时扩展——即"**每次开机动态扩展内存态策略**"，而非永久覆写厂商 sepolicy。

**安全本质**：SELinux 约束普通进程，但 KernelSU LKM 与 SELinux 内核代码同处 EL1 信任边界——它**有能力**添加极宽规则；是否只添加必要规则，需源码审计确认（`kernel/selinux/rules.c`）。

## 2. 安装前置条件（本次 LKM 方式的必要条件）

以下前置条件是本次通过修补并刷写 `init_boot` 安装 KernelSU LKM 的必要条件。

### 2.1 内核兼容条件：GKI 2.0 / kernel 5.10+

KernelSU 上游当前重点支持 Android GKI 2.0 设备，官方仓库给出的主要兼容范围是 `GKI 2.0, Linux kernel 5.10 or newer`。旧版非 GKI 内核曾经可以通过源码集成方式支持，但 KernelSU 官方文档说明 `KernelSU v1.0 及以后不再官方支持 non-GKI 设备`；非 GKI 集成文档目前仅作为历史归档，不能直接套用到当前主线版本。

官方资料：安装说明 [https://kernelsu.org/guide/installation.html](https://kernelsu.org/guide/installation.html)；非 GKI 集成归档 [https://kernelsu.org/guide/how-to-integrate-for-non-gki.html](https://kernelsu.org/guide/how-to-integrate-for-non-gki.html)；源码 [https://github.com/tiann/KernelSU](https://github.com/tiann/KernelSU)。

本次设备内核 `6.1.118-android14-11-ga3b9c44908dd-ab13320413` 属于符合 GKI 时代特征的 6.1 内核，KernelSU Manager 也成功识别并提供 `android14-6.1` LKM 修补路径。

### 2.2 KMI 必须兼容

KMI 是 GKI 设备内核与厂商模块、可加载模块之间的稳定接口约束。KernelSU 官方给出的内核版本格式为 `Version.PatchLevel.SubLevel-AndroidRelease-KmiGeneration-suffix`，本次内核的完整 KMI 标识可理解为 `6.1-android14-11`；Manager 安装界面使用简化类别 `android14-6.1`，其中 `6.1`=内核主版本与 PatchLevel、`118`=SubLevel（不是 KMI 主匹配字段）、`android14`=ACK 分支、`11`=KMI generation。

必须注意：

- Android 用户空间版本不等于内核 ACK 版本；Android 15 系统完全可能继续使用 `android14-6.1` 内核；
- 不能因为系统是 Android 15 就选择 `android15-6.6`；
- KMI 不兼容可能导致模块装载失败或设备 bootloop。

Android GKI 官方说明：[https://source.android.com/docs/core/architecture/kernel/generic-kernel-image](https://source.android.com/docs/core/architecture/kernel/generic-kernel-image)；KernelSU KMI 说明：[https://kernelsu.org/guide/installation.html](https://kernelsu.org/guide/installation.html)。

### 2.3 必须使用当前固件对应的原始启动镜像

本次设备当前版本为 `OS2.0.208.0.VNMCNXM`，因此原始镜像必须来自完全匹配的 ROM `manet_images_OS2.0.208.0.VNMCNXM_15.0`。至少应匹配：设备代号、ROM 分支、ROM build、Android 安全补丁级别、内核版本、启动镜像布局、当前启动链配置。

仅 KMI 相同并不能证明任意版本的 `init_boot.img` 可以互换——init_boot 中还可能包含 ramdisk、first-stage init 配置、启动脚本、SELinux 相关文件、厂商启动配置、与该 build 对应的启动链元数据。最安全的规则是：

```text
只修补手机当前正在运行的同版本官方 init_boot.img
```

### 2.4 必须确定真正需要修补的分区

不同设备和 Android 版本的启动镜像布局可能不同，KernelSU 的修补对象不一定永远是同一个分区（可能涉及 `boot` / `init_boot` / `vendor_boot`）。

本次日志明确显示修补对象是 `init_boot.img`，最终刷写目标为 `init_boot_b`。本次不能把 patched image 刷到 `boot_b` / `vendor_boot_b` / `vbmeta_b`。其他设备必须以其启动布局、官方安装说明和 Manager 识别结果为准，不能机械照搬本例。

### 2.5 Bootloader 必须允许刷入修改后的镜像

本次 fastboot 安装方式中，Bootloader 必须已解锁。本次验证 `getprop ro.boot.flash.locked` 返回 `0`，Fastboot `getvar unlocked` 返回 `unlocked: yes`。

如果 Bootloader 仍然锁定，通常不能通过 fastboot 写入非官方签名的 patched image。

需要区分"KernelSU 运行所需条件"和"通过 fastboot 安装 KernelSU 所需条件"：KernelSU 的内核代码本身并不以 Bootloader 解锁作为运行逻辑条件；但要将修改后的启动镜像写入量产设备，通常必须先解锁 Bootloader。对于已经由 ROM 或内核开发者预集成 KernelSU 的系统，不一定需要用户再次执行 fastboot 刷写。

可把解锁理解为同时打开**两扇门**：

- **写入门禁**：锁定 Bootloader 通常拒绝 fastboot 改写启动信任链分区（boot/init_boot/vendor_boot/vbmeta）——即使 patched 镜像已生成也写不进去；
- **启动信任门禁**：AVB 以 vbmeta 中的公钥与分区摘要校验启动链。patched 镜像的 SHA-256 与 stock 不同（本文实测 `93bf…` vs `9c77…`），Locked 状态下不再匹配 OEM 信任链，典型结果是拒绝启动/红色错误状态/进入恢复，具体行为因 OEM 实现而异。

`orange` 状态的准确含义：设备已解锁、系统完整性不再由锁定的 OEM 信任链完全保证，但 Bootloader **允许用户选择启动该软件**。这不等于"AVB 代码完全不运行"或"dm-verity 全部关闭"——本文不修改 vbmeta、不用 `--disable-verity` 即可启动，是该设备在 unlocked 状态下的行为，**不能推广到所有厂商**。

### 2.6 启动验证链必须允许当前启动状态

本次设备 `getprop ro.boot.verifiedbootstate` 返回 `orange`，符合 Bootloader 已解锁设备的常见 Verified Boot 状态。

本次成功安装过程中没有执行 `fastboot --disable-verity --disable-verification flash vbmeta vbmeta.img`，也没有修改 `vbmeta`——说明本设备在 Bootloader 解锁状态下能够启动修改后的 `init_boot_b`，不需要额外关闭 dm-verity 或 AVB verification。

但这不能推广为所有厂商和设备的绝对行为（AVB 配置、chained vbmeta、rollback index、boot image 签名策略、OEM Bootloader 实现都可能不同）。默认原则是：

```text
如果仅修补 init_boot 即可启动，就不要额外修改 vbmeta
```

### 2.7 必须准确处理 A/B 槽位

本次设备使用 A/B 槽位。Android 中 `getprop ro.boot.slot_suffix` 返回 `_b`，Fastboot 中 `getvar current-slot` 返回 `b`，两者一致，因此唯一正确的刷写目标为 `init_boot_b`。

如果误刷到非活动槽：当前启动不会获得 Root；后续 OTA 切槽后可能出现非预期启动行为；两个槽位状态不一致会增加故障排查难度。如果刷错分区，则可能直接导致无法启动。

### 2.8 patched image 不能超过目标分区容量

本次 patched image 大小 `8388608 bytes`，目标分区查询 `partition-size:init_boot_b: 0x800000`（=8 MiB），两者完全一致。刷写前必须满足 `patched image size <= target partition size`：镜像大于分区时 fastboot 通常会拒绝写入，不应使用手工截断的方式规避。

### 2.9 必须验证 patched image 的基本完整性

本次原始镜像和 patched image 均具有正确的 Android boot image magic（`ANDROID!`），SHA-256 分别为 `93bf…` 与 `9c77…`（见第二部分第 19 章）。判断逻辑：patched 非空、保留合法 boot image 格式、与 stock 哈希不同、不超目标分区、保留 stock 用于回滚。

### 2.10 KernelSU Manager 与内核组件必须兼容

Manager、LKM 和用户空间组件之间存在版本与接口依赖。应优先从 KernelSU 官方 Release 获取 Manager：[https://github.com/tiann/KernelSU/releases](https://github.com/tiann/KernelSU/releases)。

不要使用来源不明的二次打包 APK：Manager 参与 Root 授权控制、可以管理高权限模块，非官方 APK 可能被植入恶意代码，版本不兼容可能导致无法识别内核组件，错误的修补资产可能生成不可启动镜像。官方 Manager 身份与授权管理实现：[https://github.com/tiann/KernelSU/tree/main/kernel/manager](https://github.com/tiann/KernelSU/tree/main/kernel/manager)；SELinux 实现：[https://github.com/tiann/KernelSU/tree/main/kernel/selinux](https://github.com/tiann/KernelSU/tree/main/kernel/selinux)。

### 2.11 必须保留可执行的恢复路径

开始刷写前至少要准备：完全匹配当前 ROM 的原始 `init_boot.img`；可正常工作的 `fastboot`；可进入 Fastboot 的物理按键方式；正确的数据线和 USB 接口；明确刚才修改的是哪个槽位；对应槽位的回滚命令。

本次回滚命令：`fastboot flash init_boot_b init_boot.img && fastboot reboot`。如果没有 stock image，或者无法进入 Fastboot，则不应贸然刷写启动分区。

### 2.12 安全补丁级别与防回滚约束

KernelSU 官方安装文档指出，即使 KMI 相同，过旧的内核或启动镜像仍可能因为安全补丁级别和防回滚机制而无法启动。因此不能仅凭"KMI 相同"就跨 ROM 版本复用启动镜像，还必须考虑 Android Security Patch Level、Bootloader rollback index、AVB rollback protection、厂商固件版本、内核安全补丁、启动 ramdisk 的版本一致性。

推荐策略：

```text
当前 ROM 只使用当前 ROM 提取的 init_boot.img
```

系统 OTA 后，应从新版本 ROM 重新提取并修补，不复用旧 patched image。

### 2.13 工具和操作能力要求

执行本流程前，操作者需要具备：使用 `adb` 查询属性、使用 `fastboot` 查询和刷写分区、识别 A/B 槽位、计算和比较 SHA-256、判断 boot image magic、通过物理按键进入 Fastboot、bootloop 时恢复 stock image 的能力。

macOS 至少应能正常执行：`adb version` / `fastboot --version` / `shasum -a 256` / `xxd`。

---

## 3. 刷写前最终 Gate Checklist

只有下表全部满足，才进入刷写阶段：

| 检查项                       | 本次结果                           | 是否满足 |
| ---------------------------- | ---------------------------------- | -------- |
| 设备代号匹配                 | `manet`                          | 是       |
| ROM build 匹配               | `OS2.0.208.0.VNMCNXM`            | 是       |
| 原始镜像来自当前 ROM         | 同版本官方 ROM                     | 是       |
| 内核满足 GKI/LKM 条件        | `6.1.118-android14-11`           | 是       |
| KernelSU KMI 匹配            | `android14-6.1`                  | 是       |
| Manager 修补成功             | `Adding KernelSU LKM`、`Done!` | 是       |
| Bootloader 已解锁            | `unlocked: yes`                  | 是       |
| Android 与 Fastboot 槽位一致 | `_b` / `b`                     | 是       |
| 目标分区存在                 | `init_boot_b` 可查询容量         | 是       |
| 目标分区容量足够             | `0x800000`                       | 是       |
| patched image 大小合法       | `8388608 bytes`                  | 是       |
| boot image magic 正确        | `ANDROID!`                       | 是       |
| stock 与 patched 哈希不同    | SHA-256 不同                       | 是       |
| 原始镜像已备份               | `init_boot.img`                  | 是       |
| 回滚命令明确                 | 刷回`init_boot_b`                | 是       |
| Fastboot 连接正常            | 设备可见                           | 是       |

只要有任一关键项不满足，应停止刷写。

---

## 4. Root 成功后的安全边界

KernelSU 成功 Root 后，仍应区分以下边界：

### 4.1 SELinux 仍然存在

Root 进程获得 UID 0，不代表 SELinux 自动失效。本次进程上下文为 `u:r:ksu:s0`，应进一步确认系统保持 `Enforcing`（`adb shell su -c getenforce`）。

### 4.2 Root 授权应按应用隔离

每个 Android 应用通常具有独立 UID。KernelSU 应基于应用身份和 App Profile 单独授权，而不是允许任意进程获取 Root。

### 4.3 内核态 Root 扩大了攻击面

KernelSU 运行在内核信任边界内。一旦存在以下问题，影响可能高于普通应用漏洞：使用恶意或非官方 Manager、安装恶意模块、授权不可信应用、使用存在漏洞的 KernelSU 或内核版本、从不可信来源刷入 LKM 或 patched image。

### 4.4 Root 会影响设备完整性判定

即使系统可以正常启动，Root 和解锁状态仍可能影响：Play Integrity、银行和支付应用、DRM、企业设备合规、游戏反作弊、OTA 增量校验、设备保修和售后策略。不能把"系统能够正常启动"等价为"所有完整性检测均会通过"。

---

## 5. 原理总结

KernelSU 能够提供 Root 的根本原因是：**它将可信权限控制逻辑放入 Linux 内核**。

本次 LKM 流程的完整链路：

```text
Bootloader 解锁 → 允许 fastboot 改写 init_boot → 允许启动不匹配 OEM 签名的 patched init_boot
→ 内核解包 patched ramdisk → ksuinit 作为临时 PID 1 执行 → ksuinit 加载 kernelsu.ko
→ KernelSU 进入内核态 → ksuinit execve 真正 Android init → KernelSU 扩展内存态 SELinux policydb
→ 刷新 AVC → 应用请求 Root → KernelSU 检查授权 → 建立 UID 0 credentials
→ 设置 KernelSU 对应 SELinux SID → Root 进程在 Enforcing 状态下运行
```

本次最终输出 `uid=0(root) gid=0(root) groups=0(root) context=u:r:ksu:s0`，证明上述链路已经实际生效。

---

## 6. 官方资料与置信度

KernelSU 官方资料：

- 源码：[https://github.com/tiann/KernelSU](https://github.com/tiann/KernelSU)
- 安装文档：[https://kernelsu.org/guide/installation.html](https://kernelsu.org/guide/installation.html)
- Release：[https://github.com/tiann/KernelSU/releases](https://github.com/tiann/KernelSU/releases)
- App Profile：[https://kernelsu.org/guide/app-profile.html](https://kernelsu.org/guide/app-profile.html)
- Module Guide：[https://kernelsu.org/guide/module.html](https://kernelsu.org/guide/module.html)
- 内核源码目录：[https://github.com/tiann/KernelSU/tree/main/kernel](https://github.com/tiann/KernelSU/tree/main/kernel)
- 内核初始化代码：[https://github.com/tiann/KernelSU/tree/main/kernel/core](https://github.com/tiann/KernelSU/tree/main/kernel/core)
- Manager 身份管理代码：[https://github.com/tiann/KernelSU/tree/main/kernel/manager](https://github.com/tiann/KernelSU/tree/main/kernel/manager)
- SELinux 代码：[https://github.com/tiann/KernelSU/tree/main/kernel/selinux](https://github.com/tiann/KernelSU/tree/main/kernel/selinux)
- 用户空间代码：[https://github.com/tiann/KernelSU/tree/main/userspace](https://github.com/tiann/KernelSU/tree/main/userspace)
- SELinux 策略注入（本文 §1.8 依据）：`kernel/selinux/sepolicy.c`、`rules.c`、`selinux.c`
  [https://github.com/tiann/KernelSU/tree/main/kernel/selinux](https://github.com/tiann/KernelSU/tree/main/kernel/selinux)
- ksuinit 启动加载（本文 §1.3 依据）：`userspace/ksuinit/src/init.rs`、`main.rs`；`userspace/ksud/src/boot_patch.rs`
- 内核初始化入口：`kernel/core/init.c` [https://github.com/tiann/KernelSU/tree/main/kernel/core](https://github.com/tiann/KernelSU/tree/main/kernel/core)
- Android Bootloader 锁定/解锁：[https://source.android.com/docs/core/architecture/bootloader/locking_unlocking](https://source.android.com/docs/core/architecture/bootloader/locking_unlocking)
- Android Verified Boot 设备状态：[https://source.android.com/docs/security/features/verifiedboot/device-state](https://source.android.com/docs/security/features/verifiedboot/device-state)
- 非 GKI 历史集成文档：[https://kernelsu.org/guide/how-to-integrate-for-non-gki.html](https://kernelsu.org/guide/how-to-integrate-for-non-gki.html)

Android 官方资料：Generic Kernel Image [https://source.android.com/docs/core/architecture/kernel/generic-kernel-image](https://source.android.com/docs/core/architecture/kernel/generic-kernel-image)

本部分置信度：

- KernelSU 内核态授权、App Profile、模块体系及 GKI/KMI 原理：**高**；
- 本次设备使用 `init_boot_b`、`android14-6.1` 和 LKM 模式：**极高，来自实际日志**；
- LKM 在启动过程中的具体装载时点和内部 hook 实现：**版本相关**。

KernelSU 主线实现仍在演进。涉及具体函数、hook 点、内核内部接口时，应以所安装版本对应的 Git tag 源码为准，不应仅依据历史实现推断当前版本。

---

---

# 第二部分：操作手册

> 照章执行部分。**前提：第一部分第 3 章的 Gate Checklist 全部满足。**

## 7. 已验证环境

### 7.1 设备与系统

| 项目               | 实际值                                                                         |
| ------------------ | ------------------------------------------------------------------------------ |
| 品牌/设备          | Redmi                                                                          |
| Device Codename    | `manet`                                                                      |
| Android 版本       | Android 15                                                                     |
| ROM 版本           | `OS2.0.208.0.VNMCNXM`                                                        |
| Build Fingerprint  | `Redmi/manet/manet:15/AQ3A.240912.001/OS2.0.208.0.VNMCNXM:user/release-keys` |
| Linux 内核         | `6.1.118-android14-11-ga3b9c44908dd-ab13320413`                              |
| KernelSU KMI       | `android14-6.1`                                                              |
| Bootloader 状态    | 已解锁                                                                         |
| Verified Boot 状态 | `orange`                                                                     |
| 当前活动槽         | `_b`                                                                         |
| Root 实现          | KernelSU LKM                                                                   |

### 7.2 使用的镜像

本机 macOS 路径：`/Users/michaelyao/Downloads/manet-rom/manet_images_OS2.0.208.0.VNMCNXM_15.0/images`

```text
manet_images_OS2.0.208.0.VNMCNXM_15.0/
└── images/
    ├── boot.img
    ├── init_boot.img
    ├── kernelsu_patched_20260927_064607.img
    └── vbmeta.img
```

镜像大小：

```text
boot.img                                 100663296 bytes
init_boot.img                              8388608 bytes
kernelsu_patched_20260927_064607.img       8388608 bytes
vbmeta.img                                    8192 bytes
```

本次操作只修改 `init_boot_b`，没有修改 `boot` / `vendor_boot` / `vbmeta`。

---

## 8. 风险说明

刷写启动链相关分区具有一定风险，错误操作可能导致：无法启动或启动循环、AVB 校验失败、Root 失效、OTA 更新失败、刷错设备/版本/槽位后无法正常启动。

开始前必须满足：

1. Bootloader 已解锁；
2. `adb` 和 `fastboot` 可以正常使用；
3. ROM 包与手机当前运行版本完全一致；
4. 已保存原始 `init_boot.img`；
5. 明确当前活动槽；
6. 知道如何进入 Fastboot；
7. 不刷写来源不明或版本不匹配的镜像。

> 不要把本文中的 patched image 用于其他设备、其他 ROM 版本或其他槽位状态。

---

## 9. 整体流程

```text
核对设备和ROM版本 → 获取官方镜像并提取init_boot → 确认内核与KMI
→ KernelSU修补原始init_boot → 拉取patched镜像到Mac → 校验大小/哈希/镜像头
→ 确认BL已解锁 → 读取当前活动槽 → 进入Fastboot → 确认槽位和分区容量
→ 只刷当前槽init_boot → 重启 → 验证boot_completed和Root → 保存原始镜像和校验值
```

---

## 10. 阶段零：获取官方镜像（下载与提取）

> 信任链起点：文件必须从小米官方 CDN 下载；社区站点只用于**发现文件名**，不用来下载文件本体。

### 10.1 定位官方包

OS2.0.208.0.VNMCNXM 的官方线刷包文件名（经 ONFIX / XiaomiROM 社区索引交叉确认，2025-09-25 发布）：

```text
manet_images_OS2.0.208.0.VNMCNXM_20250918.0000.00_15.0_cn_1306f9617f.tgz   （8.4 GB）
```

小米官方有两个 CDN 镜像同一文件：`bigota.d.miui.com` 与 `cdnorg.d.miui.com`。本次实测 bigota 对直接请求返回 403，`cdnorg` 可用（HTTP 206 分段响应正常）。

### 10.2 下载（12 路并行分块）

单连接下载实测仅 ~0.4MB/s（估 6 小时）；12 路分段并行实测合速 ~6MB/s，全程约 20~25 分钟。命令从本文 `sed -n` 取段执行（防转录纪律）：

```bash
# 建目录并进入
mkdir -p ~/Downloads/manet-rom && cd ~/Downloads/manet-rom

# 探测文件总大小（Content-Range 响应头）
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
URL='https://cdnorg.d.miui.com/OS2.0.208.0.VNMCNXM/manet_images_OS2.0.208.0.VNMCNXM_20250918.0000.00_15.0_cn_1306f9617f.tgz'
TOTAL=$(curl -s -A "$UA" -r 0-0 -D - -o /dev/null "$URL" | grep -i content-range | sed 's/.*\///' | tr -d '\r')
echo "TOTAL=$TOTAL"

# 12 路分段并行下载后拼接
N=12
CHUNK=$((TOTAL / N + 1))
for i in $(seq 0 $((N-1))); do
  S=$((i * CHUNK)); E=$(( (i+1) * CHUNK - 1 )); [ $E -ge $TOTAL ] && E=$((TOTAL-1))
  curl -s -A "$UA" --retry 8 --retry-delay 3 -r "$S-$E" -o "part_$i" "$URL" &
done
wait
cat part_0 part_1 part_2 part_3 part_4 part_5 part_6 part_7 part_8 part_9 part_10 part_11 > manet_OS2.0.208_fastboot.tgz
rm -f part_*

# 大小校验（必须 SIZE_OK）
ACTUAL=$(stat -f%z manet_OS2.0.208_fastboot.tgz)
echo "actual=$ACTUAL expected=$TOTAL"
[ "$ACTUAL" = "$TOTAL" ] && echo SIZE_OK || echo SIZE_MISMATCH
```

过关判据：输出 `SIZE_OK`（实测 TOTAL=9018072638 字节，8.4GB）。

> 备用：单连接慢速版 `curl -sL -A "$UA" --retry 10 -C - -o manet_OS2.0.208_fastboot.tgz "$URL"`（`-C -` 支持断点续传）。

### 10.3 提取所需镜像（不解 super）

完整包 8.4GB，但本次只需要三个小文件——不解包数 GB 的 `super`：

```bash
cd ~/Downloads/manet-rom
# 先看归档里有什么（确认文件名结构）
tar tzf manet_OS2.0.208_fastboot.tgz | grep -E 'init_boot.img|/boot.img|vbmeta.img'

# 只提取三个小镜像
tar xzf manet_OS2.0.208_fastboot.tgz \
  'manet_images_OS2.0.208.0.VNMCNXM_15.0/images/init_boot.img' \
  'manet_images_OS2.0.208.0.VNMCNXM_15.0/images/boot.img' \
  'manet_images_OS2.0.208.0.VNMCNXM_15.0/images/vbmeta.img'

# 校验产物
cd manet_images_OS2.0.208.0.VNMCNXM_15.0/images
ls -la
file init_boot.img    # 预期: Android bootimg
```

过关判据：`init_boot.img` 8388608 字节、`file` 报 `Android bootimg`；`boot.img`（96MB）与 `vbmeta.img`（8KB）作为附带备份一并保留。

---

## 11. 阶段一：准备环境

### 11.1 检查 ADB 和 Fastboot

```bash
adb version
fastboot --version
adb devices
```

预期输出类似：

```text
List of devices attached
<DEVICE_SERIAL>    device
```

如果显示 `unauthorized`，需要在手机上允许 USB 调试授权。

### 11.2 确认设备、ROM 和内核

```bash
adb shell getprop ro.product.device            # 实测: manet
adb shell getprop ro.build.version.incremental # 实测: OS2.0.208.0.VNMCNXM
adb shell getprop ro.build.fingerprint         # 实测: Redmi/manet/manet:15/AQ3A...
adb shell uname -r                             # 实测: 6.1.118-android14-11-...
```

KMI 选择规则（重要）：

- KernelSU Manager 中的简化 KMI 选项：`android14-6.1`；
- Android 用户空间版本是 Android 15，但内核 ACK 分支标识仍是 `android14`；
- **KMI 必须根据内核版本选择，不是看 Android 用户空间版本**；
- 不要选 `android15-6.6`；不要选 `android14-5.15`。

### 11.3 确认 ROM 镜像目录

```bash
cd ~/Downloads/manet-rom/manet_images_OS2.0.208.0.VNMCNXM_15.0/images
ls -al    # 至少应存在 boot.img / init_boot.img / vbmeta.img
```

本次修补对象是 `init_boot.img`（不是 `boot.img`——Android 13+ 的 ramdisk 在 init_boot 分区）。

---

## 12. 阶段二：使用 KernelSU Manager 修补镜像

### 12.1 将原始 init_boot.img 放入手机

```bash
adb push init_boot.img /sdcard/Download/init_boot.img
adb shell ls -l /sdcard/Download/init_boot.img    # 预期 8388608（8 MiB）
```

### 12.2 在 KernelSU Manager 中修补

1. 打开 KernelSU Manager，进入安装/镜像修补页面；
2. 选择"选择文件并修补"；
3. 选中 `/sdcard/Download/init_boot.img`；
4. KMI 选择 `android14-6.1`；
5. 确认开始修补，等待日志出现 `Done!`。

本次实测日志关键内容：

```text
Bootdevice: /data/data/me.weishu.kernelsu/cache/boot.img
Preparing assets
Unpacking boot image
KMI: android14-6.1
Adding KernelSU LKM
Repacking boot image
Output file is written to
/storage/emulated/0/Download/kernelsu_patched_20260927_064607.img
Done!
```

> Manager 页面显示"刷写完成"时，实际完成的是**镜像修补和文件输出**，并未写入设备分区。

---

## 13. 阶段三：拉回 Mac 并校验

### 13.1 拉取 patched image

```bash
cd ~/Downloads/manet-rom/manet_images_OS2.0.208.0.VNMCNXM_15.0/images
adb pull /sdcard/Download/kernelsu_patched_20260927_064607.img ./kernelsu_patched_20260927_064607.img
ls -lh init_boot.img kernelsu_patched_20260927_064607.img   # 两者均为 8388608
```

### 13.2 计算 SHA-256

```bash
shasum -a 256 init_boot.img kernelsu_patched_20260927_064607.img
```

本次实测：

```text
93bf226d73d131c8bf5fbbf178e625a44705814015afcbc4c52d7ef6496e3fc8  init_boot.img
9c7724a8f701e819eee9b82b1256edc7e74cdc83f6651d5c0e1a45071ba0d584  kernelsu_patched_20260927_064607.img
```

判断标准：大小相同或接近；patched 非空；**两个 SHA-256 必须不同**——相同说明修补未生效，禁止刷写。

```bash
cmp -s init_boot.img kernelsu_patched_20260927_064607.img; echo $?
# 预期 1（0=完全相同，1=有差异，2=读取出错）
```

### 13.3 检查 Android Boot Image Magic

```bash
xxd -l 8 init_boot.img                     # 实测: 414e 4452 4f49 4421  ANDROID!
xxd -l 8 kernelsu_patched_20260927_064607.img   # 同上
```

两者都应以 `ANDROID!` 开头；否则不要刷写。

---

## 14. 阶段四：确认 Bootloader 和活动槽

### 14.1 确认 Bootloader 已解锁

```bash
adb shell getprop ro.boot.flash.locked      # 实测: 0（0=已解锁，1=锁定）
adb shell getprop ro.boot.verifiedbootstate # 实测: orange
```

`flash.locked=1` 时**立即停止**，不要尝试刷写。

### 14.2 读取当前活动槽

```bash
adb shell getprop ro.boot.slot_suffix       # 实测: _b → 目标分区 init_boot_b
```

不能凭经验猜槽位，必须以实际查询为准。

---

## 15. 阶段五：进入 Fastboot 并刷写

### 15.1 进入 Bootloader

```bash
adb reboot bootloader
fastboot devices                            # 预期: <SERIAL>  fastboot
```

无输出时：检查数据线（排除充电线）、换 USB 口、确认确实处于 Fastboot。

### 15.2 在 Fastboot 中再次确认槽位

```bash
fastboot getvar current-slot                # 实测: b（与 Android 侧 _b 一致）
```

不一致时停止刷写并重新核查。

### 15.3 再次确认解锁状态

```bash
fastboot getvar unlocked                    # 实测: yes
```

### 15.4 关于 has-slot:init_boot 查询失败

```bash
fastboot getvar has-slot:init_boot
# 实测: FAILED (remote: 'GetVar Variable Not found')
```

部分 bootloader 未实现该可选变量——**不代表分区不存在**，应直接查询分区大小（下一步）。

### 15.5 查询目标分区大小

```bash
fastboot getvar partition-size:init_boot_b  # 实测: 0x800000 = 8388608 = 8 MiB
```

分区大小与 patched image 完全匹配 → 可以继续。

### 15.6 刷写当前槽的 init_boot

```bash
ls -l kernelsu_patched_20260927_064607.img
fastboot flash init_boot_b kernelsu_patched_20260927_064607.img
```

实测输出：

```text
Sending 'init_boot_b' (8192 KB)                    OKAY [  0.189s]
Writing 'init_boot_b'                              OKAY [  0.006s]
Finished. Total time: 0.224s
```

只有 `Sending` 和 `Writing` 都 `OKAY` 才算成功；任何 `FAILED` → 不要重启、不要切槽、不要刷其他分区，保存日志分析。

### 15.7 本次禁止执行的操作

```bash
fastboot flash boot boot.img                                    # 不需要
fastboot flash vbmeta vbmeta.img                                # 不需要
fastboot flash vendor_boot vendor_boot.img                      # 不需要
fastboot --disable-verity --disable-verification flash vbmeta vbmeta.img  # 禁止
fastboot flash init_boot_a kernelsu_patched_20260927_064607.img # 不刷另一槽
fastboot set_active a                                           # 不无理由切槽
```

本次唯一目标：`init_boot_b`。

### 15.8 重启系统

```bash
fastboot reboot
```

首次启动可能略慢；启动动画期间不要强制关机，长时间无响应再进回滚流程。

---

## 16. 阶段六：验证 Root

### 16.1 等待 ADB 恢复并确认启动完成

```bash
adb wait-for-device
adb shell getprop sys.boot_completed        # 实测: 1
adb shell getprop ro.boot.slot_suffix        # 实测: _b（从已刷写的 b 槽启动）
```

### 16.2 验证 Root 权限

```bash
adb shell su -c id
```

首次执行 Manager 可能弹出授权请求，需手机端允许。实测输出：

```text
uid=0(root) gid=0(root) groups=0(root) context=u:r:ksu:s0
```

含义：UID/GID=0、进入 KernelSU 的 `ksu` SELinux 域、LKM 正常工作。

### 16.3 检查 SELinux

```bash
adb shell su -c 'id; getenforce'
# 实测: ... context=u:r:ksu:s0 / Enforcing
```

`Enforcing` 为理想状态；不建议为兼容应用全局关闭 SELinux。

---

## 17. 阶段七：保存恢复资料（已执行，2026-09-27）

归档目录（镜像不入库）：

```text
~/Downloads/manet-rom/manet_images_OS2.0.208.0.VNMCNXM_15.0/images/
├── init_boot.img                     # 官方原始件
├── init_boot_stock.img               # 回滚件（= init_boot.img 副本）
├── init_boot_kernelsu_lkm.img        # 已验证的 patched 件（= kernelsu_patched_... 副本）
├── kernelsu_patched_20260927_064607.img
├── boot.img / vbmeta.img             # 附带备份
├── SHA256SUMS                        # 已 shasum -c 验证 OK
└── device-info.txt                   # 设备指纹/槽位/verified boot 快照
```

以后验证完整性：`shasum -a 256 -c SHA256SUMS`（预期两行均 OK）。

---

## 18. 阶段八：故障回滚

### 18.1 Bootloop 恢复原始 init_boot

1. 长按进 Fastboot（关机态 电源+音量下）；
2. `fastboot devices` 确认连接；
3. `fastboot getvar current-slot` 确认槽位（本次为 b）；
4. 刷回：

```bash
fastboot flash init_boot_b init_boot.img
fastboot reboot
```

回滚时**不要**额外刷 boot/vendor_boot/vbmeta，也不要立即切槽。

### 18.2 Root 命令无效时的检查顺序

`su -c id` 返回 `su: not found` 或未 uid=0 时，按序检查：

1. 当前槽是否仍为 patched 所在槽：`getprop ro.boot.slot_suffix`；
2. KernelSU Manager 是否显示已安装/LKM 正常/KMI=android14-6.1/Shell 已授权；
3. Shell 的 Root 请求是否被拒绝（Manager 超级用户页）；
4. 内核版本是否仍为 `6.1.118-android14-11-...`；
5. 是否发生 OTA 或槽位切换（新槽无 patched init_boot → Root 消失但系统正常）。

---

## 19. 阶段九：OTA 更新注意事项

### 19.1 不要跨版本复用 patched image

本文 patched 镜像仅适用于 `manet + OS2.0.208.0.VNMCNXM + 6.1.118-android14-11-...`。升级后即使代号仍为 manet 也禁止复用（ramdisk/内核 ABI/AVB 元数据/A-B 槽都可能变化）。

### 19.2 OTA 后的正确处理

1. 确认新系统正常启动；
2. 查询新活动槽；
3. 获取**新 ROM** 对应的 init_boot.img（重走第 10 章下载与提取）；
4. 用当前兼容版本 Manager **重新修补**；
5. 核对新内核 KMI；
6. 只刷新系统当前活动槽的 init_boot。

```bash
adb shell getprop ro.build.version.incremental
adb shell uname -r
adb shell getprop ro.boot.slot_suffix
```

---

## 20. 阶段十：Root 安全建议

- 只给可信应用 Root；不给浏览器/普通文件管理器；不默认批准所有请求；
- 调试结束可撤销 ADB Shell 的长期授权；装模块前查源码与兼容性；
- 保持 SELinux `Enforcing`（`adb shell su -c getenforce` 复核）；
- 无必要不改 vbmeta（本次成功安装不需要 disable-verity）——改动会扩大启动链变更面，影响 OTA/Verified Boot/恢复流程。

---

## 21. 最终验证结果（2026-09-27 实测）

```text
Device: manet / ROM: OS2.0.208.0.VNMCNXM / Kernel: 6.1.118-android14-11-ga3b9c44908dd-ab13320413
KMI: android14-6.1 / Bootloader: unlocked / Verified Boot: orange / Active Slot: _b
Patched Partition: init_boot_b (0x800000) / KernelSU Mode: LKM
Root: uid=0, context=u:r:ksu:s0 / SELinux: Enforcing / boot_completed: 1
```

**置信度：极高。** 设备、固件、槽位、镜像大小、SHA-256、分区容量与最终 Root 状态均来自本次实际执行日志。其他设备/版本必须重新完成全部核验。

---

# 附录

## 附录 A：最简命令清单

```bash
# 0. 下载与提取（详见第 10 章；此处仅为索引提醒）
cd ~/Downloads/manet-rom/manet_images_OS2.0.208.0.VNMCNXM_15.0/images

# 1. 设备与前置核验
adb shell getprop ro.product.device
adb shell getprop ro.build.version.incremental
adb shell getprop ro.build.fingerprint
adb shell uname -r
adb shell getprop ro.boot.flash.locked
adb shell getprop ro.boot.verifiedbootstate
adb shell getprop ro.boot.slot_suffix

# 2. 校验 patched 镜像
shasum -a 256 init_boot.img kernelsu_patched_20260927_064607.img
xxd -l 8 init_boot.img; xxd -l 8 kernelsu_patched_20260927_064607.img

# 3. 刷写
adb reboot bootloader
fastboot devices
fastboot getvar current-slot
fastboot getvar unlocked
fastboot getvar partition-size:init_boot_b
fastboot flash init_boot_b kernelsu_patched_20260927_064607.img
fastboot reboot

# 4. 验证
adb wait-for-device
adb shell getprop sys.boot_completed
adb shell su -c id
adb shell su -c getenforce
```

## 附录 B：最简回滚命令

```bash
cd ~/Downloads/manet-rom/manet_images_OS2.0.208.0.VNMCNXM_15.0/images
fastboot devices
fastboot getvar current-slot
fastboot flash init_boot_b init_boot.img
fastboot reboot
```

## 附录 C：关键判断表

| 检查项                        | 正常结果                     | 异常时处理            |
| ----------------------------- | ---------------------------- | --------------------- |
| `ro.product.device`         | `manet`                    | 停止刷写              |
| ROM 版本                      | `OS2.0.208.0.VNMCNXM`      | 换完全匹配的 ROM 镜像 |
| 内核                          | `6.1.118-android14-11-...` | 重新判断 KMI          |
| KMI                           | `android14-6.1`            | 不选其他 KMI          |
| `ro.boot.flash.locked`      | `0`                        | 未解锁，停止          |
| `ro.boot.verifiedbootstate` | `orange`                   | 结合解锁状态检查      |
| Android 当前槽                | `_b`                       | 按实际槽调整目标分区  |
| Fastboot 当前槽               | `b`                        | 不一致时停止          |
| patched 镜像大小              | `8388608`                  | 重新修补              |
| 分区大小                      | `0x800000`                 | 镜像不得超分区        |
| 镜像头                        | `ANDROID!`                 | 不刷                  |
| SHA-256                       | stock 与 patched 不同        | 相同则重新修补        |
| 刷写输出                      | Sending/Writing 均 OKAY      | 不重启，先分析        |
| `sys.boot_completed`        | `1`                        | 查启动状态            |
| Root UID                      | `uid=0(root)`              | 查槽位/授权/LKM       |
| SELinux context               | `u:r:ksu:s0`               | 查 KernelSU 状态      |
| SELinux 模式                  | `Enforcing`                | 不建议长期 Permissive |

---

*关联：OI-2（红米 root 闭环）｜平台配置 `configs/platforms/redmi-k70pro-01.json`｜能力清单 `data/public/capabilities/redmi-k70pro-01-*.json`*
