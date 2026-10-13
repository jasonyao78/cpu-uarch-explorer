# 固定1536leaf的描述符剂量：简单预算预测未复制

## 本次任务的目的（给人类看）

保持同memfd、同data PFN/ordinal order、低8VPN直方图，全部stride≥5让每16KiB VA quartet只有一个选leaf；实际捕获PT关联，用有限剂量对照推翻／支持“leaf+PT耗尽2048”最简候选。冻结 `docs/design/2026-10-13-tlb-descriptor-dose.md`，资格 `docs/reviews/2026-10-13-tlb-descriptor-dose-qualification.md`。

**SIMPLE_BUDGET_NOT_REPLICATED。** 27/27fresh、64,896/64,896初始安装观察、324/324PMU窗；全部技术、前后N32 floor、IR/Icache、A基线<.10、同stride5 A/B几何阴性通过。140rawSHA +资格20SHA锁定；独立原始JSONL逐node VA/PFN/word、实际PT grouping及全部窗口empty校正／walk率重算精确，初始同virtual PT bucket没有不同PA（不是稳态证明）。

|stride pages|实际PT数（全部3epoch）|N+PT候选预算|E0全部3round walk/load范围|E1范围|E2范围|
|---:|---:|---:|---|---|---|
|5|15|1551|[0.000096,0.000142]|[0.000036,0.000108]|[0.000062,0.000118]|
|67|201|1737|[0.000018,0.000095]|[0.000075,0.000148]|[0.000029,0.000274]|
|131|393|1929|[0.669700,0.677860]|[0.390964,0.585098]|[0.000031,0.000215]|
|169|507|2043|[0.822635,0.842105]|[0.764678,0.817902]|[0.836933,0.861400]|
|173|519|2055|[0.739805,0.741800]|[0.000075,0.859205]|[0.805850,0.861276]|
|259|777|2313|[0.982156,0.992495]|[0.692257,0.992585]|[0.987586,0.998702]|
|515|1536|3072|[0.957254,0.989107]|[0.979137,0.989574]|[1.000004,1.000004]|

预注册预测是(169,173]；实际E0 onset(67,131]、E1 ambiguous（stride173三个round中一个near0、两个>.85）、E2(131,169]。所有删失／mixed／非严格单调率都保留，不按后验选择round。walk/load>1保持原值，不clip，不将计数叫missing-leaf entries。

## 对最终目标的影响

stride131在三epoch都有393PT、候选总1929；E0约.67，E1约.39–.59，E2近零，不能由同一个N+PT全局阈值唯一解释。**这个简单预算预测不够，不能据它反推物理entry数或way数。** 不推翻r0p1官方2048/256×8规格；也不排除共同占用，只说明地址关联、替换／其他条目／S2/cache/prefetch等可能参与。跨fresh process data PFN和PT PA会不同，不能从同计数的跨process差认定PT PA独因。

相对旧stride3，本次每16KiB selected quartet均single-leaf，仍存在几何差异；不把selected叶合并或CONT0当HPA／全部prefetch排除证据。实际table PA是LinuxPA/IPA、非machine HPA，安装读不认证performance期间table不变。cycle/cache tap全部保留，data node当前offset0，每页一cacheline可有严重cache set压力，不能默认缓存完全匹配所有投机访问。

下一优先是两条同process正交控制：①固定VA/data PFN/order而让实际PT关联变动，激励不足命名NOT_EXCITED、相同ASID/mm约束；②同页／同表／同6ISA内改变in-page cacheline offset（0与轮转），所有位于同页的extra副本不引入新翻译页，几何×offset配对DID。都需新协议／资格，不继续同grid加密拟合2048；physical sethash／ROB容量仍OPEN。

## 源码、验证和原始证据

branch `codex/sm8650-tlb-hierarchy-r2`；sourcef997cb7/buildc1256db/资格launchac1903f/实际formal launch `883fc0875cb15761756a17dcabfead01359fb503`；binarySHA `00955f97ab0541bb557cdfeaa6518fcb43f23c9e1a35ef40775f17d5ed7b2fa4`。NDK27.2/API34双构建相同，28actual plans及真实ELF4ISA/BPF102/32，15production-chain测试；完整674/674通过592.004秒（sourceac1903f），证据regression.json，不包含后来PMU metadata新模块。formal runner/analysis/CTest未改，本轮未重跑。private `data/private/20261013T110726Z-tlb-descriptor-dose-scan`，public `docs/reviews/evidence/2026-10-13-tlb-descriptor-dose/scan-analysis.json` / `scan-independent-check.json` / `scan-windows.csv`，全部324窗含empty。源 `probes/diagnostic/tlb_descriptor_dose.c`，consumer/raw/driver `tools/diagnostic/tlb_descriptor_dose_analysis.py` / `tlb_descriptor_dose_raw.py` / `run_sm8650_tlb_descriptor_dose.py`。CPU端点温度[39.2, 41.6]°C，no journal/global setting write，FD全部关闭。该有限协议完成，未声称三物理目标已完成，未把官方规格与独立target识别混算。
