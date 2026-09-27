# Runbook：Redmi `manet` 使用 KernelSU LKM 修补并刷写 `init_boot` 完整指南

> **入库说明（2026-09-27）**：本文由 Michael 在一次**已成功完成的实际操作**后整理，作为本仓 Android Target（`redmi-k70pro-01`，见 `docs/open-items.md` OI-2）的 root 闭环证据与 OTA 后重修补手册。证据等级：**MEASURED**（全部命令与输出来自实测）。
> **适用范围**：仅适用于下述精确设备与固件组合；其他设备/版本必须重新完成全部核验，**严禁复用 patched 镜像**。
> **镜像归档**（不入库，100MB 级二进制 + 可再生成）：`~/Downloads/manet-rom/manet_images_OS2.0.208.0.VNMCNXM_15.0/images/`——`init_boot_stock.img`（回滚件）/ `init_boot_kernelsu_lkm.img` / `SHA256SUMS` / `device-info.txt`。
> **信任链**：官方 ROM（bigota/cdnorg 小米 CDN）→ 手机端 KernelSU Manager 本地打补丁（LKM）→ 仅刷 init_boot 当前槽。不经第三方补丁镜像站。

---

## 1. 已验证环境

### 1.1 设备与系统

| 项目 | 实际值 |
|---|---|
| 品牌/设备 | Redmi |
| Device Codename | `manet` |
| Android 版本 | Android 15 |
| ROM 版本 | `OS2.0.208.0.VNMCNXM` |
| Build Fingerprint | `Redmi/manet/manet:15/AQ3A.240912.001/OS2.0.208.0.VNMCNXM:user/release-keys` |
| Linux 内核 | `6.1.118-android14-11-ga3b9c44908dd-ab13320413` |
| KernelSU KMI | `android14-6.1` |
| Bootloader 状态 | 已解锁 |
| Verified Boot 状态 | `orange` |
| 当前活动槽 | `_b` |
| Root 实现 | KernelSU LKM |

### 1.2 使用的镜像

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

本次操作只修改：

```text
init_boot_b
```

没有修改：

```text
boot
vendor_boot
vbmeta
```

---

## 2. 风险说明

刷写启动链相关分区具有一定风险，错误操作可能导致：

- 无法启动或启动循环；
- AVB 校验失败；
- Root 失效；
- OTA 更新失败；
- 刷错设备、版本或槽位后无法正常启动。

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

## 3. 整体流程

```text
核对设备和ROM版本 → 确认内核与KMI → KernelSU修补原始init_boot
→ 拉取patched镜像到Mac → 校验大小/哈希/镜像头 → 确认BL已解锁
→ 读取当前活动槽 → 进入Fastboot → 确认槽位和分区容量
→ 只刷当前槽init_boot → 重启 → 验证boot_completed和Root
→ 保存原始镜像和校验值
```

---

# 第一阶段：准备环境

## 4. 检查 ADB 和 Fastboot

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

## 5. 确认设备、ROM 和内核

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

## 6. 确认 ROM 镜像目录

```bash
cd ~/Downloads/manet-rom/manet_images_OS2.0.208.0.VNMCNXM_15.0/images
ls -al    # 至少应存在 boot.img / init_boot.img / vbmeta.img
```

本次修补对象是 `init_boot.img`（不是 `boot.img`——Android 13+ 的 ramdisk 在 init_boot 分区）。

---

# 第二阶段：使用 KernelSU Manager 修补镜像

## 7. 将原始 init_boot.img 放入手机

```bash
adb push init_boot.img /sdcard/Download/init_boot.img
adb shell ls -l /sdcard/Download/init_boot.img    # 预期 8388608（8 MiB）
```

## 8. 在 KernelSU Manager 中修补

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

# 第三阶段：拉回 Mac 并校验

## 9. 拉取 patched image

```bash
cd ~/Downloads/manet-rom/manet_images_OS2.0.208.0.VNMCNXM_15.0/images
adb pull /sdcard/Download/kernelsu_patched_20260927_064607.img ./kernelsu_patched_20260927_064607.img
ls -lh init_boot.img kernelsu_patched_20260927_064607.img   # 两者均为 8388608
```

## 10. 计算 SHA-256

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

## 11. 检查 Android Boot Image Magic

```bash
xxd -l 8 init_boot.img                     # 实测: 414e 4452 4f49 4421  ANDROID!
xxd -l 8 kernelsu_patched_20260927_064607.img   # 同上
```

两者都应以 `ANDROID!` 开头；否则不要刷写。

---

# 第四阶段：确认 Bootloader 和活动槽

## 12. 确认 Bootloader 已解锁

```bash
adb shell getprop ro.boot.flash.locked      # 实测: 0（0=已解锁，1=锁定）
adb shell getprop ro.boot.verifiedbootstate # 实测: orange
```

`flash.locked=1` 时**立即停止**，不要尝试刷写。

## 13. 读取当前活动槽

```bash
adb shell getprop ro.boot.slot_suffix       # 实测: _b → 目标分区 init_boot_b
```

不能凭经验猜槽位，必须以实际查询为准。

---

# 第五阶段：进入 Fastboot 并刷写

## 14. 进入 Bootloader

```bash
adb reboot bootloader
fastboot devices                            # 预期: <SERIAL>  fastboot
```

无输出时：检查数据线（排除充电线）、换 USB 口、确认确实处于 Fastboot。

## 15. 在 Fastboot 中再次确认槽位

```bash
fastboot getvar current-slot                # 实测: b（与 Android 侧 _b 一致）
```

不一致时停止刷写并重新核查。

## 16. 再次确认解锁状态

```bash
fastboot getvar unlocked                    # 实测: yes
```

## 17. 关于 has-slot:init_boot 查询失败

```bash
fastboot getvar has-slot:init_boot
# 实测: FAILED (remote: 'GetVar Variable Not found')
```

部分 bootloader 未实现该可选变量——**不代表分区不存在**，应直接查询分区大小（下一步）。

## 18. 查询目标分区大小

```bash
fastboot getvar partition-size:init_boot_b  # 实测: 0x800000 = 8388608 = 8 MiB
```

分区大小与 patched image 完全匹配 → 可以继续。

## 19. 刷写当前槽的 init_boot

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

## 20. 本次禁止执行的操作

```bash
fastboot flash boot boot.img                                    # 不需要
fastboot flash vbmeta vbmeta.img                                # 不需要
fastboot flash vendor_boot vendor_boot.img                      # 不需要
fastboot --disable-verity --disable-verification flash vbmeta vbmeta.img  # 禁止
fastboot flash init_boot_a kernelsu_patched_20260927_064607.img # 不刷另一槽
fastboot set_active a                                           # 不无理由切槽
```

本次唯一目标：`init_boot_b`。

## 21. 重启系统

```bash
fastboot reboot
```

首次启动可能略慢；启动动画期间不要强制关机，长时间无响应再进回滚流程。

---

# 第六阶段：验证 Root

## 22. 等待 ADB 恢复并确认启动完成

```bash
adb wait-for-device
adb shell getprop sys.boot_completed        # 实测: 1
adb shell getprop ro.boot.slot_suffix        # 实测: _b（从已刷写的 b 槽启动）
```

## 23. 验证 Root 权限

```bash
adb shell su -c id
```

首次执行 Manager 可能弹出授权请求，需手机端允许。实测输出：

```text
uid=0(root) gid=0(root) groups=0(root) context=u:r:ksu:s0
```

含义：UID/GID=0、进入 KernelSU 的 `ksu` SELinux 域、LKM 正常工作。

## 24. 检查 SELinux

```bash
adb shell su -c 'id; getenforce'
# 实测: ... context=u:r:ksu:s0 / Enforcing
```

`Enforcing` 为理想状态；不建议为兼容应用全局关闭 SELinux。

---

# 第七阶段：保存恢复资料（已执行，2026-09-27）

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

# 第八阶段：故障回滚

## 25. Bootloop 恢复原始 init_boot

1. 长按进 Fastboot（关机态 电源+音量下）；
2. `fastboot devices` 确认连接；
3. `fastboot getvar current-slot` 确认槽位（本次为 b）；
4. 刷回：

```bash
fastboot flash init_boot_b init_boot.img
fastboot reboot
```

回滚时**不要**额外刷 boot/vendor_boot/vbmeta，也不要立即切槽。

## 26. Root 命令无效时的检查顺序

`su -c id` 返回 `su: not found` 或未 uid=0 时，按序检查：

1. 当前槽是否仍为 patched 所在槽：`getprop ro.boot.slot_suffix`；
2. KernelSU Manager 是否显示已安装/LKM 正常/KMI=android14-6.1/Shell 已授权；
3. Shell 的 Root 请求是否被拒绝（Manager 超级用户页）；
4. 内核版本是否仍为 `6.1.118-android14-11-...`；
5. 是否发生 OTA 或槽位切换（新槽无 patched init_boot → Root 消失但系统正常）。

---

# 第九阶段：OTA 更新注意事项

## 27. 不要跨版本复用 patched image

本文 patched 镜像仅适用于 `manet + OS2.0.208.0.VNMCNXM + 6.1.118-android14-11-...`。升级后即使代号仍为 manet 也禁止复用（ramdisk/内核 ABI/AVB 元数据/A-B 槽都可能变化）。

## 28. OTA 后的正确处理

1. 确认新系统正常启动；
2. 查询新活动槽；
3. 获取**新 ROM** 对应的 init_boot.img；
4. 用当前兼容版本 Manager **重新修补**；
5. 核对新内核 KMI；
6. 只刷新系统当前活动槽的 init_boot。

```bash
adb shell getprop ro.build.version.incremental
adb shell uname -r
adb shell getprop ro.boot.slot_suffix
```

---

# 第十阶段：Root 安全建议

- 只给可信应用 Root；不给浏览器/普通文件管理器；不默认批准所有请求；
- 调试结束可撤销 ADB Shell 的长期授权；装模块前查源码与兼容性；
- 保持 SELinux `Enforcing`（`adb shell su -c getenforce` 复核）；
- 无必要不改 vbmeta（本次成功安装不需要 disable-verity）——改动会扩大启动链变更面，影响 OTA/Verified Boot/恢复流程。

---

# 附录 A：最简命令清单

```bash
cd ~/Downloads/manet-rom/manet_images_OS2.0.208.0.VNMCNXM_15.0/images
adb shell getprop ro.product.device
adb shell getprop ro.build.version.incremental
adb shell getprop ro.build.fingerprint
adb shell uname -r
adb shell getprop ro.boot.flash.locked
adb shell getprop ro.boot.verifiedbootstate
adb shell getprop ro.boot.slot_suffix
shasum -a 256 init_boot.img kernelsu_patched_20260927_064607.img
xxd -l 8 init_boot.img; xxd -l 8 kernelsu_patched_20260927_064607.img
adb reboot bootloader
fastboot devices
fastboot getvar current-slot
fastboot getvar unlocked
fastboot getvar partition-size:init_boot_b
fastboot flash init_boot_b kernelsu_patched_20260927_064607.img
fastboot reboot
adb wait-for-device
adb shell getprop sys.boot_completed
adb shell su -c id
adb shell su -c getenforce
```

# 附录 B：最简回滚命令

```bash
cd ~/Downloads/manet-rom/manet_images_OS2.0.208.0.VNMCNXM_15.0/images
fastboot devices
fastboot getvar current-slot
fastboot flash init_boot_b init_boot.img
fastboot reboot
```

# 附录 C：关键判断表

| 检查项 | 正常结果 | 异常时处理 |
|---|---|---|
| `ro.product.device` | `manet` | 停止刷写 |
| ROM 版本 | `OS2.0.208.0.VNMCNXM` | 换完全匹配的 ROM 镜像 |
| 内核 | `6.1.118-android14-11-...` | 重新判断 KMI |
| KMI | `android14-6.1` | 不选其他 KMI |
| `ro.boot.flash.locked` | `0` | 未解锁，停止 |
| `ro.boot.verifiedbootstate` | `orange` | 结合解锁状态检查 |
| Android 当前槽 | `_b` | 按实际槽调整目标分区 |
| Fastboot 当前槽 | `b` | 不一致时停止 |
| patched 镜像大小 | `8388608` | 重新修补 |
| 分区大小 | `0x800000` | 镜像不得超分区 |
| 镜像头 | `ANDROID!` | 不刷 |
| SHA-256 | stock 与 patched 不同 | 相同则重新修补 |
| 刷写输出 | Sending/Writing 均 OKAY | 不重启，先分析 |
| `sys.boot_completed` | `1` | 查启动状态 |
| Root UID | `uid=0(root)` | 查槽位/授权/LKM |
| SELinux context | `u:r:ksu:s0` | 查 KernelSU 状态 |
| SELinux 模式 | `Enforcing` | 不建议长期 Permissive |

---

## 最终验证结果（2026-09-27 实测）

```text
Device: manet / ROM: OS2.0.208.0.VNMCNXM / Kernel: 6.1.118-android14-11-ga3b9c44908dd-ab13320413
KMI: android14-6.1 / Bootloader: unlocked / Verified Boot: orange / Active Slot: _b
Patched Partition: init_boot_b (0x800000) / KernelSU Mode: LKM
Root: uid=0, context=u:r:ksu:s0 / SELinux: Enforcing / boot_completed: 1
```

**置信度：极高。** 设备、固件、槽位、镜像大小、SHA-256、分区容量与最终 Root 状态均来自本次实际执行日志。其他设备/版本必须重新完成全部核验。

---

*关联：OI-2（红米 root 闭环）｜平台配置 `configs/platforms/redmi-k70pro-01.json`｜能力清单 `data/public/capabilities/redmi-k70pro-01-*.json`*
