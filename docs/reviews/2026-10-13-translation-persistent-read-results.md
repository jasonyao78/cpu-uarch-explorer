# 持久exact-owned页表观察器：通过（2026-10-13）

## 本次任务的目的（给人类看）

把逐节点加载程序/attach/fork的页表观测改为一个private exactVA登记观察器，为容量附近large-N真实graph/descriptor关联准备可扩展入口。合同 `docs/design/2026-10-13-translation-persistent-read.md` v1.0。

**OWNED_PERSISTENT_DESCRIPTOR_READ，3/3 fresh进程、24/24节点通过。** 每进程只加载entry102/return32两程序，持有1个136B map与2个observer event；8节点逐次登记只改requestVA，PID仍字节码常量。foreign child只1次，每节点wrongVA负控0，正控entry1/return1，原ordinal/PFN/parent类型/index/两个层级关系/同mm/pgd/首次坏状态不重置都过；全部FD在final前关闭。安装CONT24/24为0，仍不认证稳态或HPA。

这是**可扩展观测能力**，未采PMU、未测容量。本次8节点的程序加载次数由逐节点方案16次变2次（8倍减少），fork8次变1次；仅结构开销数量，没有虚报walltime加速倍数。不能将它直接叫large-N性能结论、256set/8way证书。Linux guest PA/IPA域边界不变。

## 实际字节与独立复核

entry先helper14过滤TGID，lookup private map后比较ctx.request VA与slot16，匹配后才helper113读own vmf/mm/pgd/PTE；root offset实际由((selectedVA>>30)&511)<<3计算，无猜测PA-to-VA。成功state13在下个request清零前必须先经实际C gate；sticky read-error或duplicate99不能被reset掩盖。24registration边与144个两端pagemap pair wire直接JSONL独立重算精确；24个实际动态program计划由immutable C再生，全部raw20SHA检查。

公开 `docs/reviews/evidence/2026-10-13-translation-persistent-read/validation.json` 与 `independent-check.json`；私有 `data/private/20261013T050003Z-translation-persistent-read`，kernelVA/PFN/真实PID/serial不入库。模拟VM和软件夹具仅软件证据，24节点才是目标实测。未更改环境事务/security/THP/frequency/HVC；端点环境符合既有walt baseline，不认证窗内恒频。

| 角色 | commit/路径 |
|---|---|
| actual source | `c9a71e2`（C/header首次58c6b57） / `probes/diagnostic/translation_persistent_read.c`、`translation_persistent_bpf.h` |
| typed consumer/raw/driver | `tools/diagnostic/translation_persistent_analysis.py`、`translation_persistent_raw.py`、`run_sm8650_translation_persistent.py` |
| build | `a49c2b0` / NDK27.2/API34/O2/Werror/static两次字节一致 |
| actual launch | `6eb66213241f89563009a494890bf9a83975e4b9` |
| binary SHA256 | `d76b0dfe5fa51f453ac8448580385e2321634671d776d73f9930255be187d00e` |
| branch | `codex/sm8650-tlb-hierarchy-r2` |

23关联测试通过：实际C字节→独立VM/实际C gate→正式driver→writer→immutable-source raw，错PID/VA、动态root边界、缺失/乱序/失败锁存/reset/PFN/parent关系/byteplan/额外文件反例；旁路audit时软件首坏测试RED。完整本批回归另记最终工件（不拿前601当本新模块全量覆盖）。

## 离最终目标还差什么

物理TLB容量/组织、ROB容量仍0/3。TLB现在可直接把真实descriptor身份接到容量附近，不用VA代理替代；下一要同VA/dataPFN改变真实table关联，及同IPA数据的VA/ASID翻译身份倍增对照（上下文切换阴性、直接页表审计必须有），把Stage1 leaf身份与descriptor/组合翻译竞争分开，再定位容量/候选hash。不可把两ASID简单乘2等同条目，因为intermediate tables也变了。

ROB错误路径cache N0仍不通过，详见 `docs/reviews/2026-10-13-rob-cache-marker-results.md`；需要issued vs fill/history的独立控制和实际单位/活跃约束证据，不能拟合第三方384。当前没有完成声明或main/远端合并，后置触发 `docs/open-items.md`。
