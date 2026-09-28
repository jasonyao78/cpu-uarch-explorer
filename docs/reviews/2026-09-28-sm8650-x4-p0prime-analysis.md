<!-- 本文件由入库分析器生成（analysis/sm8650_x4_p0prime.py，含全失败 run 报告修复），命令：
     ../../.venv/bin/python -m analysis.sm8650_x4_p0prime --samples \
       --run data/public/runs/20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base \
       --run data/public/runs/20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base \
       --run data/public/runs/20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a \
       --run data/public/runs/20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b \
       --run data/public/runs/20260928T025226Z-ptr-chase-sm8650-x4-p0prime-short-thp \
       --run data/public/runs/20260928T122738Z-ptr-chase-sm8650-x4-p0prime-short-thp
     裁定见 2026-09-28-sm8650-x4-p0prime.md。两个 short-THP run 共
     16 条全失败记录均纳入 rejected 清单；long-THP 未执行。 -->

# P0″ demand/prefetch per-sample analysis

All numeric cells are median [p25, p75]; rates are per 1,000 timed loads.
PMU rows are accepted only when time_running_ns == time_enabled_ns for every event.

| run | buffer KiB | seed | backing | passes | n | latency ns | cyc/load | mem rd/1k | l1 miss/1k | l1 hwprf/1k | l2 miss/1k | l2 hwprf/1k | bimodal |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 448 | seed=7 | base | 8 | 10 | 2.183 [2.182, 2.218] | 6.251 [6.234, 6.347] | 1062.291 [1060.486, 1063.097] | 184.623 [184.331, 185.974] | 821.734 [820.408, 822.348] | 2.781 [2.625, 4.739] | 275.984 [275.142, 278.891] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=7 s0: lat=2.2116 cyc=6.357 mem_rd=1062.67 l1miss=186.33 l1hwprf=820.17 l2miss=5.266 l2hwprf=275.13 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=7 s1: lat=2.1689 cyc=6.239 mem_rd=1061.35 l1miss=183.45 l1hwprf=823.77 l2miss=2.511 l2hwprf=275.18 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=7 s2: lat=2.1771 cyc=6.200 mem_rd=1063.20 l1miss=184.90 l1hwprf=822.34 l2miss=2.616 l2hwprf=274.68 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=7 s3: lat=2.2243 cyc=6.335 mem_rd=1063.30 l1miss=186.75 l1hwprf=819.61 l2miss=5.232 l2hwprf=311.70 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=7 s4: lat=2.2479 cyc=6.431 mem_rd=1059.69 l1miss=183.02 l1hwprf=827.17 l2miss=5.877 l2hwprf=321.25 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=7 s5: lat=2.1816 cyc=6.196 mem_rd=1061.91 l1miss=184.34 l1hwprf=821.11 l2miss=2.651 l2hwprf=277.88 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=7 s6: lat=2.1844 cyc=6.245 mem_rd=1062.80 l1miss=184.66 l1hwprf=821.46 l2miss=3.261 l2hwprf=276.00 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=7 s7: lat=2.1816 cyc=6.232 mem_rd=1060.18 l1miss=184.59 l1hwprf=822.35 l2miss=2.912 l2hwprf=279.23 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=7 s8: lat=2.1816 cyc=6.258 mem_rd=1064.02 l1miss=184.33 l1hwprf=822.00 l2miss=2.546 l2hwprf=273.89 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=7 s9: lat=2.2198 cyc=6.350 mem_rd=1060.20 l1miss=193.99 l1hwprf=813.08 l2miss=2.651 l2hwprf=275.97 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 448 | seed=42 | base | 8 | 10 | 2.178 [2.176, 2.187] | 6.267 [6.229, 6.279] | 1062.134 [1060.804, 1062.836] | 185.573 [184.884, 185.887] | 822.213 [821.817, 822.780] | 2.764 [2.027, 3.278] | 271.598 [268.642, 272.749] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=42 s0: lat=2.1762 cyc=6.272 mem_rd=1063.90 l1miss=185.84 l1hwprf=821.83 l2miss=3.313 l2hwprf=267.86 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=42 s1: lat=2.1780 cyc=6.223 mem_rd=1061.98 l1miss=185.30 l1hwprf=822.47 l2miss=1.360 l2hwprf=264.35 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=42 s2: lat=2.2016 cyc=6.292 mem_rd=1062.74 l1miss=186.23 l1hwprf=822.54 l2miss=3.174 l2hwprf=271.64 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=42 s3: lat=2.1871 cyc=6.262 mem_rd=1060.39 l1miss=187.31 l1hwprf=819.61 l2miss=3.680 l2hwprf=274.55 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=42 s4: lat=2.1907 cyc=6.279 mem_rd=1060.48 l1miss=185.90 l1hwprf=821.76 l2miss=3.610 l2hwprf=273.44 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=42 s5: lat=2.1644 cyc=6.178 mem_rd=1063.01 l1miss=184.78 l1hwprf=824.22 l2miss=1.674 l2hwprf=268.21 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=42 s6: lat=2.1780 cyc=6.248 mem_rd=1059.88 l1miss=185.86 l1hwprf=821.81 l2miss=1.848 l2hwprf=272.36 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=42 s7: lat=2.1853 cyc=6.208 mem_rd=1061.79 l1miss=185.20 l1hwprf=822.86 l2miss=2.930 l2hwprf=269.95 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=42 s8: lat=2.1753 cyc=6.299 mem_rd=1062.87 l1miss=184.64 l1hwprf=821.95 l2miss=2.598 l2hwprf=271.55 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=42 s9: lat=2.1762 cyc=6.278 mem_rd=1062.29 l1miss=184.10 l1hwprf=823.28 l2miss=2.563 l2hwprf=272.88 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 448 | seed=1337 | base | 8 | 10 | 2.188 [2.177, 2.197] | 6.274 [6.231, 6.288] | 1060.817 [1059.919, 1062.273] | 184.658 [184.252, 185.747] | 822.318 [822.065, 825.749] | 2.712 [2.411, 3.087] | 273.420 [271.977, 273.725] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=1337 s0: lat=2.2207 cyc=6.358 mem_rd=1060.65 l1miss=187.85 l1hwprf=819.98 l2miss=5.615 l2hwprf=271.57 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=1337 s1: lat=2.1680 cyc=6.227 mem_rd=1062.41 l1miss=185.09 l1hwprf=822.04 l2miss=2.581 l2hwprf=270.18 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=1337 s2: lat=2.1771 cyc=6.241 mem_rd=1061.85 l1miss=184.54 l1hwprf=821.81 l2miss=3.174 l2hwprf=269.71 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=1337 s3: lat=2.1844 cyc=6.195 mem_rd=1063.08 l1miss=185.97 l1hwprf=822.75 l2miss=2.790 l2hwprf=273.19 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=1337 s4: lat=2.1989 cyc=6.293 mem_rd=1059.67 l1miss=181.64 l1hwprf=827.64 l2miss=2.825 l2hwprf=273.39 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=1337 s5: lat=2.1907 cyc=6.274 mem_rd=1059.59 l1miss=184.29 l1hwprf=822.35 l2miss=3.610 l2hwprf=278.27 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=1337 s6: lat=2.1771 cyc=6.212 mem_rd=1062.81 l1miss=184.78 l1hwprf=822.14 l2miss=2.354 l2hwprf=274.19 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=1337 s7: lat=2.2071 cyc=6.327 mem_rd=1058.86 l1miss=184.24 l1hwprf=828.39 l2miss=2.633 l2hwprf=273.59 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=1337 s8: lat=2.1916 cyc=6.276 mem_rd=1060.91 l1miss=183.16 l1hwprf=826.75 l2miss=2.075 l2hwprf=273.77 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=1337 s9: lat=2.1780 cyc=6.274 mem_rd=1060.72 l1miss=186.52 l1hwprf=822.28 l2miss=2.162 l2hwprf=273.45 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 448 | seed=20260928 | base | 8 | 10 | 2.165 [2.158, 2.177] | 6.181 [6.151, 6.215] | 1062.422 [1061.999, 1062.962] | 185.529 [184.588, 185.978] | 821.812 [820.539, 823.155] | 1.639 [1.386, 1.731] | 270.360 [269.544, 271.445] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=20260928 s0: lat=2.1925 cyc=6.249 mem_rd=1061.02 l1miss=187.41 l1hwprf=820.43 l2miss=2.895 l2hwprf=269.50 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=20260928 s1: lat=3.4923 cyc=8.969 mem_rd=1252.98 l1miss=252.21 l1hwprf=782.14 l2miss=56.449 l2hwprf=273.75 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=20260928 s2: lat=2.1617 cyc=6.140 mem_rd=1063.08 l1miss=185.97 l1hwprf=820.85 l2miss=1.692 l2hwprf=271.64 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=20260928 s3: lat=2.1644 cyc=6.175 mem_rd=1059.45 l1miss=184.20 l1hwprf=822.68 l2miss=1.744 l2hwprf=265.68 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=20260928 s4: lat=2.1571 cyc=6.145 mem_rd=1064.07 l1miss=184.74 l1hwprf=823.31 l2miss=1.343 l2hwprf=269.69 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=20260928 s5: lat=2.1562 cyc=6.141 mem_rd=1062.62 l1miss=184.17 l1hwprf=823.43 l2miss=1.674 l2hwprf=270.86 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=20260928 s6: lat=2.1807 cyc=6.224 mem_rd=1062.38 l1miss=185.16 l1hwprf=824.38 l2miss=1.325 l2hwprf=274.59 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=20260928 s7: lat=2.1553 cyc=6.167 mem_rd=1062.47 l1miss=184.54 l1hwprf=821.81 l2miss=1.308 l2hwprf=267.56 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=20260928 s8: lat=2.1653 cyc=6.186 mem_rd=1061.98 l1miss=185.90 l1hwprf=821.81 l2miss=1.604 l2hwprf=270.16 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b448K seed=20260928 s9: lat=2.1653 cyc=6.189 mem_rd=1062.06 l1miss=185.98 l1hwprf=819.65 l2miss=1.517 l2hwprf=270.56 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 512 | seed=7 | base | 8 | 10 | 2.655 [2.645, 2.671] | 7.504 [7.472, 7.552] | 1054.665 [1053.619, 1055.962] | 350.395 [348.644, 351.830] | 654.953 [653.194, 656.990] | 2.403 [1.720, 3.090] | 232.063 [229.637, 233.936] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=7 s0: lat=2.5193 cyc=7.197 mem_rd=1053.38 l1miss=275.51 l1hwprf=731.77 l2miss=5.569 l2hwprf=250.89 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=7 s1: lat=2.6433 cyc=7.486 mem_rd=1056.09 l1miss=350.89 l1hwprf=654.88 l2miss=1.709 l2hwprf=232.28 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=7 s2: lat=2.4811 cyc=7.034 mem_rd=1054.61 l1miss=273.39 l1hwprf=733.63 l2miss=2.975 l2hwprf=255.98 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=7 s3: lat=2.6727 cyc=7.558 mem_rd=1052.64 l1miss=350.10 l1hwprf=655.03 l2miss=3.815 l2hwprf=232.71 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=7 s4: lat=2.6750 cyc=7.620 mem_rd=1056.81 l1miss=350.69 l1hwprf=654.65 l2miss=3.128 l2hwprf=234.34 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=7 s5: lat=2.6552 cyc=7.491 mem_rd=1054.72 l1miss=348.27 l1hwprf=657.36 l2miss=2.487 l2hwprf=231.84 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=7 s6: lat=2.6504 cyc=7.467 mem_rd=1057.72 l1miss=349.78 l1hwprf=655.87 l2miss=2.319 l2hwprf=231.49 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=7 s7: lat=2.6679 cyc=7.532 mem_rd=1055.57 l1miss=357.93 l1hwprf=648.18 l2miss=1.755 l2hwprf=224.52 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=7 s8: lat=2.6544 cyc=7.517 mem_rd=1054.35 l1miss=352.14 l1hwprf=652.71 l2miss=1.617 l2hwprf=229.02 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=7 s9: lat=2.6758 cyc=7.578 mem_rd=1053.22 l1miss=359.27 l1hwprf=646.47 l2miss=1.663 l2hwprf=228.73 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 512 | seed=42 | base | 8 | 10 | 2.655 [2.577, 2.697] | 7.563 [7.328, 7.663] | 1054.916 [1054.150, 1055.225] | 349.312 [309.151, 360.989] | 655.861 [643.349, 696.472] | 2.563 [2.338, 3.151] | 232.742 [227.970, 242.943] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=42 s0: lat=2.5495 cyc=7.298 mem_rd=1055.01 l1miss=289.15 l1hwprf=718.20 l2miss=4.974 l2hwprf=251.82 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=42 s1: lat=2.6989 cyc=7.705 mem_rd=1054.41 l1miss=365.88 l1hwprf=639.04 l2miss=2.335 l2hwprf=224.62 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=42 s2: lat=2.6997 cyc=7.683 mem_rd=1054.90 l1miss=364.09 l1hwprf=640.12 l2miss=2.350 l2hwprf=229.72 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=42 s3: lat=2.6465 cyc=7.569 mem_rd=1055.30 l1miss=347.31 l1hwprf=657.35 l2miss=1.648 l2hwprf=227.39 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=42 s4: lat=2.6639 cyc=7.605 mem_rd=1053.30 l1miss=351.68 l1hwprf=653.03 l2miss=2.106 l2hwprf=230.10 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=42 s5: lat=2.6274 cyc=7.421 mem_rd=1054.93 l1miss=327.48 l1hwprf=677.84 l2miss=2.747 l2hwprf=235.46 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=42 s6: lat=2.5606 cyc=7.271 mem_rd=1051.54 l1miss=303.04 l1hwprf=702.68 l2miss=3.128 l2hwprf=245.44 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=42 s7: lat=2.7251 cyc=7.710 mem_rd=1054.06 l1miss=371.95 l1hwprf=632.87 l2miss=2.380 l2hwprf=225.28 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=42 s8: lat=2.6918 cyc=7.557 mem_rd=1056.92 l1miss=351.32 l1hwprf=654.37 l2miss=3.571 l2hwprf=235.38 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=42 s9: lat=2.5185 cyc=7.070 mem_rd=1055.76 l1miss=281.97 l1hwprf=723.82 l2miss=3.159 l2hwprf=253.88 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 512 | seed=1337 | base | 8 | 10 | 2.649 [2.541, 2.684] | 7.493 [7.243, 7.638] | 1054.451 [1052.929, 1055.008] | 345.398 [304.291, 356.228] | 662.674 [648.891, 708.496] | 1.663 [1.312, 1.736] | 230.019 [227.528, 243.362] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=1337 s0: lat=2.6917 cyc=7.723 mem_rd=1053.65 l1miss=342.24 l1hwprf=698.15 l2miss=5.798 l2hwprf=243.87 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=1337 s1: lat=2.6139 cyc=7.456 mem_rd=1056.32 l1miss=335.92 l1hwprf=669.36 l2miss=1.740 l2hwprf=230.87 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=1337 s2: lat=2.6862 cyc=7.666 mem_rd=1054.84 l1miss=364.82 l1hwprf=639.22 l2miss=1.190 l2hwprf=227.63 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=1337 s3: lat=2.5129 cyc=7.172 mem_rd=1054.06 l1miss=293.75 l1hwprf=711.94 l2miss=1.236 l2hwprf=244.95 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=1337 s4: lat=2.6504 cyc=7.530 mem_rd=1055.04 l1miss=350.36 l1hwprf=655.33 l2miss=1.205 l2hwprf=227.01 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=1337 s5: lat=2.9508 cyc=8.384 mem_rd=1052.69 l1miss=473.69 l1hwprf=531.27 l2miss=1.663 l2hwprf=184.66 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=1337 s6: lat=2.6790 cyc=7.554 mem_rd=1055.60 l1miss=358.18 l1hwprf=646.74 l2miss=1.663 l2hwprf=227.49 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=1337 s7: lat=2.6472 cyc=7.454 mem_rd=1054.92 l1miss=348.56 l1hwprf=655.99 l2miss=1.541 l2hwprf=229.17 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=1337 s8: lat=2.4033 cyc=6.801 mem_rd=1052.46 l1miss=237.58 l1hwprf=771.00 l2miss=2.167 l2hwprf=259.12 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=1337 s9: lat=2.5161 cyc=7.138 mem_rd=1052.58 l1miss=292.57 l1hwprf=713.38 l2miss=1.724 l2hwprf=241.85 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 512 | seed=20260928 | base | 8 | 10 | 2.664 [2.640, 2.704] | 7.528 [7.438, 7.658] | 1054.871 [1053.673, 1055.748] | 349.770 [342.674, 362.301] | 655.357 [642.635, 663.589] | 2.632 [1.968, 4.204] | 230.721 [226.551, 235.779] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=20260928 s0: lat=2.5249 cyc=7.191 mem_rd=1056.44 l1miss=276.54 l1hwprf=736.56 l2miss=4.913 l2hwprf=246.90 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=20260928 s1: lat=2.6401 cyc=7.462 mem_rd=1054.57 l1miss=342.42 l1hwprf=664.02 l2miss=2.304 l2hwprf=232.59 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=20260928 s2: lat=3.0629 cyc=8.508 mem_rd=1091.19 l1miss=403.87 l1hwprf=608.84 l2miss=24.353 l2hwprf=222.02 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=20260928 s3: lat=2.7053 cyc=7.660 mem_rd=1055.08 l1miss=354.05 l1hwprf=651.73 l2miss=4.410 l2hwprf=236.65 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=20260928 s4: lat=2.7021 cyc=7.654 mem_rd=1052.41 l1miss=367.90 l1hwprf=637.83 l2miss=1.892 l2hwprf=226.32 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=20260928 s5: lat=2.6703 cyc=7.536 mem_rd=1053.38 l1miss=348.66 l1hwprf=656.65 l2miss=3.586 l2hwprf=233.17 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=20260928 s6: lat=2.7092 cyc=7.661 mem_rd=1053.25 l1miss=365.05 l1hwprf=639.60 l2miss=2.960 l2hwprf=227.25 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=20260928 s7: lat=2.5519 cyc=7.213 mem_rd=1055.05 l1miss=302.81 l1hwprf=703.54 l2miss=2.197 l2hwprf=243.32 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=20260928 s8: lat=2.6401 cyc=7.429 mem_rd=1055.97 l1miss=343.43 l1hwprf=662.31 l2miss=1.846 l2hwprf=228.85 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b512K seed=20260928 s9: lat=2.6584 cyc=7.520 mem_rd=1054.69 l1miss=350.88 l1hwprf=654.07 l2miss=1.373 l2hwprf=225.39 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 544 | seed=7 | base | 8 | 10 | 3.519 [3.149, 3.559] | 9.892 [8.897, 10.006] | 1051.155 [1050.228, 1052.404] | 663.352 [511.809, 669.839] | 340.648 [335.245, 493.871] | 3.217 [2.007, 3.985] | 136.309 [129.969, 181.429] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=7 s0: lat=3.0592 cyc=8.671 mem_rd=1052.50 l1miss=471.74 l1hwprf=534.81 l2miss=4.366 l2hwprf=194.26 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=7 s1: lat=3.5147 cyc=9.893 mem_rd=1050.38 l1miss=662.47 l1hwprf=341.87 l2miss=2.125 l2hwprf=130.18 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=7 s2: lat=3.0405 cyc=8.580 mem_rd=1049.98 l1miss=474.61 l1hwprf=531.62 l2miss=1.522 l2hwprf=193.91 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=7 s3: lat=3.5230 cyc=9.891 mem_rd=1051.11 l1miss=664.23 l1hwprf=339.43 l2miss=1.967 l2hwprf=125.88 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=7 s4: lat=3.5566 cyc=9.959 mem_rd=1052.10 l1miss=671.20 l1hwprf=333.91 l2miss=3.231 l2hwprf=129.90 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=7 s5: lat=3.0173 cyc=8.492 mem_rd=1049.12 l1miss=460.78 l1hwprf=545.41 l2miss=3.317 l2hwprf=203.20 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=7 s6: lat=3.4198 cyc=9.575 mem_rd=1051.20 l1miss=623.41 l1hwprf=380.62 l2miss=1.867 l2hwprf=144.00 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=7 s7: lat=3.9710 cyc=11.083 mem_rd=1050.18 l1miss=827.78 l1hwprf=176.00 l2miss=3.203 l2hwprf=67.51 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=7 s8: lat=3.9471 cyc=10.957 mem_rd=1107.42 l1miss=699.78 l1hwprf=312.13 l2miss=29.986 l2hwprf=133.42 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=7 s9: lat=3.5604 cyc=10.022 mem_rd=1052.86 l1miss=665.76 l1hwprf=339.24 l2miss=4.208 l2hwprf=139.20 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 544 | seed=42 | base | 8 | 10 | 3.598 [3.560, 3.637] | 10.107 [10.004, 10.232] | 1052.792 [1051.456, 1053.352] | 683.903 [665.272, 695.133] | 320.363 [309.308, 338.813] | 2.729 [2.319, 3.562] | 123.535 [121.686, 131.667] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=42 s0: lat=3.6165 cyc=10.175 mem_rd=1053.73 l1miss=691.84 l1hwprf=312.83 l2miss=3.088 l2hwprf=117.53 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=42 s1: lat=3.4557 cyc=9.706 mem_rd=1052.85 l1miss=635.71 l1hwprf=368.70 l2miss=2.255 l2hwprf=134.13 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=42 s2: lat=3.4991 cyc=9.823 mem_rd=1051.18 l1miss=649.46 l1hwprf=355.90 l2miss=2.312 l2hwprf=135.66 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=42 s3: lat=3.6442 cyc=10.252 mem_rd=1050.78 l1miss=696.23 l1hwprf=308.13 l2miss=4.208 l2hwprf=122.08 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=42 s4: lat=4.2949 cyc=11.833 mem_rd=1154.11 l1miss=746.58 l1hwprf=272.32 l2miss=39.407 l2hwprf=123.02 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=42 s5: lat=3.5813 cyc=10.053 mem_rd=1052.27 l1miss=680.61 l1hwprf=323.16 l2miss=2.341 l2hwprf=124.05 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=42 s6: lat=3.5529 cyc=9.987 mem_rd=1053.31 l1miss=660.85 l1hwprf=343.38 l2miss=3.720 l2hwprf=138.53 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=42 s7: lat=3.5866 cyc=10.093 mem_rd=1053.37 l1miss=678.55 l1hwprf=325.12 l2miss=2.212 l2hwprf=124.27 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=42 s8: lat=3.6097 cyc=10.120 mem_rd=1050.94 l1miss=687.20 l1hwprf=317.57 l2miss=2.958 l2hwprf=121.55 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=42 s9: lat=3.9778 cyc=11.124 mem_rd=1052.73 l1miss=830.49 l1hwprf=172.32 l2miss=2.499 l2hwprf=67.87 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 544 | seed=1337 | base | 8 | 10 | 3.581 [3.543, 3.723] | 10.075 [9.982, 10.366] | 1051.147 [1050.121, 1071.318] | 673.785 [663.596, 697.994] | 332.678 [310.734, 340.332] | 3.095 [1.479, 15.417] | 125.948 [119.711, 130.834] | YES |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=1337 s0: lat=4.1124 cyc=11.428 mem_rd=1150.15 l1miss=723.29 l1hwprf=293.14 l2miss=30.690 l2hwprf=116.80 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=1337 s1: lat=3.5417 cyc=9.975 mem_rd=1051.17 l1miss=661.92 l1hwprf=341.90 l2miss=2.700 l2hwprf=131.22 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=1337 s2: lat=3.0435 cyc=8.617 mem_rd=1050.98 l1miss=461.96 l1hwprf=544.00 l2miss=3.490 l2hwprf=199.16 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=1337 s3: lat=3.7407 cyc=10.401 mem_rd=1077.87 l1miss=673.93 l1hwprf=334.33 l2miss=19.287 l2hwprf=129.68 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=1337 s4: lat=3.5477 cyc=10.003 mem_rd=1049.83 l1miss=668.62 l1hwprf=335.64 l2miss=1.192 l2hwprf=124.08 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=1337 s5: lat=3.6696 cyc=10.261 mem_rd=1049.20 l1miss=718.22 l1hwprf=285.72 l2miss=1.321 l2hwprf=110.01 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=1337 s6: lat=3.6038 cyc=10.120 mem_rd=1051.67 l1miss=691.35 l1hwprf=313.28 l2miss=1.565 l2hwprf=119.64 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=1337 s7: lat=3.8573 cyc=10.708 mem_rd=1083.11 l1miss=700.21 l1hwprf=309.89 l2miss=21.298 l2hwprf=119.92 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=1337 s8: lat=3.5589 cyc=10.031 mem_rd=1049.33 l1miss=673.64 l1hwprf=331.03 l2miss=1.450 l2hwprf=127.81 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=1337 s9: lat=3.3614 cyc=9.466 mem_rd=1051.13 l1miss=585.66 l1hwprf=419.20 l2miss=3.806 l2hwprf=156.65 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 544 | seed=20260928 | base | 8 | 10 | 3.584 [3.253, 3.605] | 10.030 [9.120, 10.117] | 1051.499 [1050.914, 1051.837] | 675.200 [528.848, 686.470] | 329.748 [318.359, 476.509] | 1.853 [1.766, 2.230] | 129.854 [123.323, 176.460] | YES |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=20260928 s0: lat=3.3502 cyc=9.379 mem_rd=1051.82 l1miss=525.78 l1hwprf=479.75 l2miss=13.528 l2hwprf=221.61 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=20260928 s1: lat=4.4206 cyc=12.336 mem_rd=1051.18 l1miss=987.61 l1hwprf=14.94 l2miss=1.680 l2hwprf=6.74 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=20260928 s2: lat=3.0675 cyc=8.647 mem_rd=1051.84 l1miss=479.88 l1hwprf=526.71 l2miss=1.853 l2hwprf=192.81 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=20260928 s3: lat=3.5836 cyc=10.035 mem_rd=1051.76 l1miss=675.97 l1hwprf=329.16 l2miss=2.283 l2hwprf=125.70 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=20260928 s4: lat=3.6090 cyc=10.132 mem_rd=1049.99 l1miss=687.56 l1hwprf=317.58 l2miss=1.853 l2hwprf=122.53 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=20260928 s5: lat=3.1580 cyc=8.898 mem_rd=1051.24 l1miss=514.61 l1hwprf=490.42 l2miss=2.068 l2hwprf=178.42 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=20260928 s6: lat=3.5851 cyc=10.024 mem_rd=1052.30 l1miss=674.43 l1hwprf=330.34 l2miss=1.853 l2hwprf=127.74 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=20260928 s7: lat=3.9733 cyc=11.013 mem_rd=1116.05 l1miss=698.14 l1hwprf=315.43 l2miss=33.806 l2hwprf=131.97 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=20260928 s8: lat=3.5948 cyc=10.072 mem_rd=1049.60 l1miss=683.21 l1hwprf=320.69 l2miss=1.738 l2hwprf=122.10 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b544K seed=20260928 s9: lat=3.2201 cyc=9.033 mem_rd=1050.82 l1miss=538.06 l1hwprf=466.78 l2miss=1.723 l2hwprf=170.57 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 576 | seed=7 | base | 8 | 10 | 4.140 [4.110, 4.178] | 11.548 [11.475, 11.678] | 1048.197 [1047.757, 1048.777] | 868.103 [855.367, 876.424] | 135.362 [127.268, 147.641] | 1.662 [1.492, 2.563] | 51.880 [48.421, 59.048] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=7 s0: lat=4.1849 cyc=11.705 mem_rd=1048.58 l1miss=876.60 l1hwprf=127.06 l2miss=3.689 l2hwprf=48.23 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=7 s1: lat=4.0400 cyc=11.270 mem_rd=1048.84 l1miss=830.12 l1hwprf=173.04 l2miss=1.736 l2hwprf=66.95 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=7 s2: lat=4.1192 cyc=11.520 mem_rd=1048.34 l1miss=855.18 l1hwprf=147.95 l2miss=2.699 l2hwprf=60.86 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=7 s3: lat=4.1312 cyc=11.506 mem_rd=1048.06 l1miss=864.18 l1hwprf=139.36 l2miss=1.465 l2hwprf=52.59 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=7 s4: lat=4.8136 cyc=13.326 mem_rd=1107.04 l1miss=1010.23 l1hwprf=1.33 l2miss=29.107 l2hwprf=6.10 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=7 s5: lat=4.5006 cyc=12.557 mem_rd=1047.88 l1miss=1000.35 l1hwprf=2.01 l2miss=1.438 l2hwprf=1.59 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=7 s6: lat=4.1064 cyc=11.451 mem_rd=1050.01 l1miss=855.92 l1hwprf=146.71 l2miss=1.533 l2hwprf=56.99 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=7 s7: lat=4.1015 cyc=11.464 mem_rd=1047.59 l1miss=852.44 l1hwprf=151.99 l2miss=2.157 l2hwprf=59.73 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=7 s8: lat=4.1580 cyc=11.597 mem_rd=1047.72 l1miss=875.90 l1hwprf=127.89 l2miss=1.587 l2hwprf=48.99 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=7 s9: lat=4.1488 cyc=11.577 mem_rd=1047.05 l1miss=872.03 l1hwprf=131.36 l2miss=1.478 l2hwprf=51.17 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 576 | seed=42 | base | 8 | 10 | 4.145 [4.083, 4.195] | 11.573 [11.392, 11.721] | 1048.638 [1047.621, 1049.269] | 859.734 [834.086, 876.411] | 144.687 [127.207, 170.176] | 1.879 [1.614, 2.370] | 55.149 [49.435, 65.850] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=42 s0: lat=3.9934 cyc=11.223 mem_rd=1049.64 l1miss=795.91 l1hwprf=207.63 l2miss=4.001 l2hwprf=86.55 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=42 s1: lat=4.1411 cyc=11.556 mem_rd=1049.33 l1miss=859.00 l1hwprf=145.40 l2miss=1.600 l2hwprf=54.29 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=42 s2: lat=4.2082 cyc=11.752 mem_rd=1047.38 l1miss=880.74 l1hwprf=122.99 l2miss=1.926 l2hwprf=47.08 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=42 s3: lat=3.9588 cyc=11.069 mem_rd=1048.35 l1miss=793.70 l1hwprf=209.77 l2miss=1.506 l2hwprf=82.67 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=42 s4: lat=4.0810 cyc=11.414 mem_rd=1048.83 l1miss=837.00 l1hwprf=166.67 l2miss=1.831 l2hwprf=62.51 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=42 s5: lat=4.1488 cyc=11.589 mem_rd=1049.09 l1miss=860.47 l1hwprf=143.98 l2miss=1.655 l2hwprf=56.00 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=42 s6: lat=4.2124 cyc=11.753 mem_rd=1046.83 l1miss=882.43 l1hwprf=120.69 l2miss=2.075 l2hwprf=48.15 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=42 s7: lat=4.0874 cyc=11.384 mem_rd=1047.25 l1miss=833.12 l1hwprf=171.35 l2miss=2.970 l2hwprf=66.96 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=42 s8: lat=4.1566 cyc=11.629 mem_rd=1048.45 l1miss=863.43 l1hwprf=139.85 l2miss=1.600 l2hwprf=53.29 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=42 s9: lat=4.4717 cyc=12.447 mem_rd=1049.52 l1miss=976.10 l1hwprf=26.88 l2miss=2.469 l2hwprf=11.58 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 576 | seed=1337 | base | 8 | 10 | 4.134 [4.084, 4.163] | 11.514 [11.379, 11.595] | 1048.604 [1048.150, 1049.381] | 869.303 [854.892, 879.140] | 134.515 [124.318, 149.370] | 2.190 [1.729, 3.998] | 52.985 [47.133, 58.726] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=1337 s0: lat=3.9072 cyc=10.931 mem_rd=1048.10 l1miss=776.18 l1hwprf=224.42 l2miss=4.300 l2hwprf=87.40 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=1337 s1: lat=4.4745 cyc=12.478 mem_rd=1048.31 l1miss=1001.36 l1hwprf=0.88 l2miss=1.723 l2hwprf=0.81 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=1337 s2: lat=4.1347 cyc=11.491 mem_rd=1047.24 l1miss=870.17 l1hwprf=134.21 l2miss=2.075 l2hwprf=52.37 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=1337 s3: lat=4.1036 cyc=11.415 mem_rd=1048.04 l1miss=860.77 l1hwprf=143.38 l2miss=1.709 l2hwprf=53.60 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=1337 s4: lat=4.1637 cyc=11.585 mem_rd=1049.37 l1miss=873.37 l1hwprf=129.88 l2miss=3.337 l2hwprf=51.32 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=1337 s5: lat=4.1333 cyc=11.537 mem_rd=1048.50 l1miss=868.44 l1hwprf=134.82 l2miss=2.306 l2hwprf=56.27 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=1337 s6: lat=3.9277 cyc=10.965 mem_rd=1049.38 l1miss=782.04 l1hwprf=221.56 l2miss=4.218 l2hwprf=90.22 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=1337 s7: lat=4.1608 cyc=11.598 mem_rd=1048.71 l1miss=881.06 l1hwprf=122.46 l2miss=1.750 l2hwprf=45.74 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=1337 s8: lat=4.7338 cyc=13.057 mem_rd=1082.85 l1miss=1005.76 l1hwprf=2.51 l2miss=24.251 l2hwprf=3.78 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=1337 s9: lat=4.0768 cyc=11.366 mem_rd=1049.42 l1miss=852.93 l1hwprf=151.37 l2miss=1.438 l2hwprf=59.54 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 576 | seed=20260928 | base | 8 | 10 | 4.146 [4.128, 4.462] | 11.582 [11.526, 12.470] | 1048.123 [1047.536, 1048.645] | 868.951 [859.663, 984.918] | 134.738 [17.978, 143.731] | 1.777 [1.472, 2.241] | 53.413 [8.416, 56.498] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=20260928 s0: lat=4.4081 cyc=12.333 mem_rd=1049.66 l1miss=954.52 l1hwprf=49.33 l2miss=4.395 l2hwprf=25.44 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=20260928 s1: lat=4.4795 cyc=12.516 mem_rd=1047.27 l1miss=995.05 l1hwprf=7.53 l2miss=1.804 l2hwprf=2.74 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=20260928 s2: lat=4.1276 cyc=11.509 mem_rd=1048.81 l1miss=864.15 l1hwprf=139.58 l2miss=1.750 l2hwprf=54.40 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=20260928 s3: lat=4.0478 cyc=11.282 mem_rd=1048.04 l1miss=825.26 l1hwprf=178.68 l2miss=2.957 l2hwprf=74.72 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=20260928 s4: lat=4.1495 cyc=11.557 mem_rd=1048.65 l1miss=869.56 l1hwprf=134.22 l2miss=1.573 l2hwprf=54.01 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=20260928 s5: lat=4.1432 cyc=11.608 mem_rd=1047.53 l1miss=868.34 l1hwprf=135.25 l2miss=1.302 l2hwprf=52.82 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=20260928 s6: lat=4.1121 cyc=11.525 mem_rd=1046.44 l1miss=858.17 l1hwprf=145.11 l2miss=1.289 l2hwprf=57.20 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=20260928 s7: lat=4.5013 cyc=12.579 mem_rd=1048.62 l1miss=1000.01 l1hwprf=2.50 l2miss=1.438 l2hwprf=2.44 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=20260928 s8: lat=4.1276 cyc=11.530 mem_rd=1048.20 l1miss=852.12 l1hwprf=150.25 l2miss=2.252 l2hwprf=60.47 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b576K seed=20260928 s9: lat=4.4950 cyc=12.583 mem_rd=1047.57 l1miss=1000.99 l1hwprf=1.32 l2miss=2.211 l2hwprf=1.32 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 608 | seed=7 | base | 8 | 10 | 4.409 [4.405, 4.421] | 12.274 [12.255, 12.337] | 1045.648 [1044.954, 1046.226] | 940.642 [939.678, 942.743] | 62.416 [60.197, 62.995] | 1.818 [1.532, 2.056] | 24.260 [23.299, 25.420] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=7 s0: lat=4.4250 cyc=12.349 mem_rd=1046.54 l1miss=931.74 l1hwprf=71.16 l2miss=5.474 l2hwprf=31.71 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=7 s1: lat=4.4110 cyc=12.301 mem_rd=1046.62 l1miss=943.13 l1hwprf=59.70 l2miss=1.863 l2hwprf=23.10 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=7 s2: lat=4.4324 cyc=12.353 mem_rd=1046.17 l1miss=952.26 l1hwprf=50.59 l2miss=1.221 l2hwprf=18.49 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=7 s3: lat=4.4070 cyc=12.271 mem_rd=1044.70 l1miss=939.56 l1hwprf=63.08 l2miss=1.773 l2hwprf=23.94 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=7 s4: lat=4.4438 cyc=12.402 mem_rd=1045.40 l1miss=953.28 l1hwprf=50.14 l2miss=2.172 l2hwprf=20.58 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=7 s5: lat=4.4043 cyc=12.244 mem_rd=1045.73 l1miss=940.04 l1hwprf=62.74 l2miss=1.516 l2hwprf=23.89 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=7 s6: lat=4.4083 cyc=12.277 mem_rd=1046.25 l1miss=941.59 l1hwprf=61.69 l2miss=1.979 l2hwprf=24.70 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=7 s7: lat=4.4103 cyc=12.272 mem_rd=1044.68 l1miss=940.47 l1hwprf=62.69 l2miss=2.082 l2hwprf=26.64 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=7 s8: lat=4.3983 cyc=12.239 mem_rd=1044.81 l1miss=938.13 l1hwprf=65.08 l2miss=1.580 l2hwprf=25.66 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=7 s9: lat=4.4030 cyc=12.250 mem_rd=1045.56 l1miss=940.82 l1hwprf=62.14 l2miss=1.118 l2hwprf=24.58 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 608 | seed=42 | base | 8 | 10 | 4.401 [4.385, 4.447] | 12.305 [12.261, 12.435] | 1045.327 [1044.234, 1046.310] | 935.039 [930.523, 953.880] | 67.736 [49.602, 73.011] | 1.651 [1.510, 1.956] | 25.667 [19.078, 29.178] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=42 s0: lat=4.4010 cyc=12.317 mem_rd=1044.45 l1miss=927.98 l1hwprf=75.23 l2miss=4.163 l2hwprf=30.93 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=42 s1: lat=4.4418 cyc=12.437 mem_rd=1045.20 l1miss=953.29 l1hwprf=49.92 l2miss=1.401 l2hwprf=18.93 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=42 s2: lat=4.3795 cyc=12.239 mem_rd=1047.13 l1miss=926.90 l1hwprf=76.09 l2miss=1.979 l2hwprf=29.50 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=42 s3: lat=4.3849 cyc=12.268 mem_rd=1045.45 l1miss=931.68 l1hwprf=71.70 l2miss=1.683 l2hwprf=28.20 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=42 s4: lat=4.3816 cyc=12.254 mem_rd=1043.75 l1miss=930.30 l1hwprf=73.45 l2miss=1.619 l2hwprf=31.20 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=42 s5: lat=4.5743 cyc=12.776 mem_rd=1044.16 l1miss=1001.98 l1hwprf=0.24 l2miss=1.529 l2hwprf=2.57 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=42 s6: lat=4.4016 cyc=12.293 mem_rd=1046.41 l1miss=938.40 l1hwprf=64.18 l2miss=1.401 l2hwprf=23.27 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=42 s7: lat=4.3869 cyc=12.259 mem_rd=1047.75 l1miss=931.18 l1hwprf=71.29 l2miss=1.503 l2hwprf=28.06 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=42 s8: lat=4.4491 cyc=12.428 mem_rd=1046.00 l1miss=954.08 l1hwprf=49.50 l2miss=1.889 l2hwprf=19.53 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=42 s9: lat=4.5790 cyc=12.804 mem_rd=1044.00 l1miss=1001.82 l1hwprf=0.51 l2miss=2.172 l2hwprf=4.74 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 608 | seed=1337 | base | 8 | 10 | 4.433 [4.405, 4.525] | 12.356 [12.264, 12.612] | 1046.464 [1045.320, 1047.428] | 942.775 [936.462, 949.829] | 60.226 [55.076, 66.381] | 2.827 [2.342, 3.726] | 25.243 [22.393, 28.192] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=1337 s0: lat=4.4813 cyc=12.509 mem_rd=1045.36 l1miss=946.22 l1hwprf=56.70 l2miss=6.091 l2hwprf=24.43 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=1337 s1: lat=4.5843 cyc=12.758 mem_rd=1046.93 l1miss=1000.14 l1hwprf=2.58 l2miss=3.071 l2hwprf=4.36 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=1337 s2: lat=4.4110 cyc=12.265 mem_rd=1046.76 l1miss=939.32 l1hwprf=63.32 l2miss=2.236 l2hwprf=26.53 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=1337 s3: lat=4.3923 cyc=12.255 mem_rd=1045.31 l1miss=931.85 l1hwprf=70.80 l2miss=2.351 l2hwprf=28.78 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=1337 s4: lat=4.4511 cyc=12.423 mem_rd=1043.80 l1miss=948.69 l1hwprf=54.53 l2miss=3.945 l2hwprf=23.00 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=1337 s5: lat=4.3996 cyc=12.240 mem_rd=1047.59 l1miss=938.67 l1hwprf=64.68 l2miss=1.850 l2hwprf=26.06 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=1337 s6: lat=4.4030 cyc=12.263 mem_rd=1047.65 l1miss=934.94 l1hwprf=68.17 l2miss=2.711 l2hwprf=31.84 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=1337 s7: lat=4.5395 cyc=12.647 mem_rd=1043.97 l1miss=988.08 l1hwprf=14.56 l2miss=2.339 l2hwprf=5.33 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=1337 s8: lat=4.6392 cyc=12.825 mem_rd=1075.86 l1miss=950.21 l1hwprf=57.13 l2miss=21.883 l2hwprf=22.19 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=1337 s9: lat=4.4157 cyc=12.290 mem_rd=1046.17 l1miss=935.73 l1hwprf=66.95 l2miss=2.943 l2hwprf=28.74 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 608 | seed=20260928 | base | 8 | 10 | 4.443 [4.407, 4.464] | 12.424 [12.328, 12.471] | 1046.400 [1045.021, 1047.110] | 939.016 [930.683, 945.242] | 64.331 [58.019, 73.265] | 3.591 [2.204, 4.247] | 34.225 [30.212, 42.028] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=20260928 s0: lat=4.4993 cyc=12.555 mem_rd=1044.92 l1miss=940.73 l1hwprf=63.22 l2miss=7.967 l2hwprf=33.46 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=20260928 s1: lat=4.5047 cyc=12.554 mem_rd=1046.01 l1miss=945.88 l1hwprf=57.39 l2miss=6.335 l2hwprf=70.03 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=20260928 s2: lat=4.3836 cyc=12.197 mem_rd=1044.52 l1miss=928.51 l1hwprf=75.67 l2miss=1.735 l2hwprf=29.48 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=20260928 s3: lat=4.3541 cyc=12.202 mem_rd=1047.76 l1miss=917.65 l1hwprf=85.81 l2miss=1.516 l2hwprf=34.99 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=20260928 s4: lat=4.4686 cyc=12.474 mem_rd=1046.79 l1miss=946.57 l1hwprf=56.52 l2miss=4.189 l2hwprf=26.70 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=20260928 s5: lat=4.4030 cyc=12.316 mem_rd=1047.32 l1miss=926.04 l1hwprf=76.85 l2miss=3.778 l2hwprf=43.77 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=20260928 s6: lat=4.4384 cyc=12.417 mem_rd=1044.50 l1miss=937.31 l1hwprf=66.05 l2miss=4.266 l2hwprf=43.43 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=20260928 s7: lat=4.4498 cyc=12.431 mem_rd=1047.13 l1miss=943.33 l1hwprf=59.92 l2miss=3.405 l2hwprf=37.82 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=20260928 s8: lat=4.4485 cyc=12.460 mem_rd=1045.32 l1miss=951.43 l1hwprf=50.91 l2miss=2.146 l2hwprf=23.64 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b608K seed=20260928 s9: lat=4.4177 cyc=12.363 mem_rd=1047.04 l1miss=937.22 l1hwprf=65.44 l2miss=2.377 l2hwprf=32.42 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 640 | seed=7 | base | 8 | 10 | 4.633 [4.600, 4.699] | 12.883 [12.799, 13.055] | 1043.896 [1042.609, 1044.757] | 981.354 [977.588, 983.649] | 21.600 [19.208, 27.274] | 3.369 [2.277, 6.137] | 13.641 [11.676, 17.871] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=7 s0: lat=4.5668 cyc=12.787 mem_rd=1042.36 l1miss=968.81 l1hwprf=34.16 l2miss=2.588 l2hwprf=14.28 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=7 s1: lat=4.6730 cyc=12.985 mem_rd=1044.91 l1miss=984.17 l1hwprf=18.74 l2miss=6.262 l2hwprf=13.00 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=7 s2: lat=4.6024 cyc=12.796 mem_rd=1044.30 l1miss=981.13 l1hwprf=21.75 l2miss=2.173 l2hwprf=12.35 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=7 s3: lat=4.5986 cyc=12.809 mem_rd=1044.29 l1miss=981.58 l1hwprf=21.45 l2miss=2.173 l2hwprf=8.75 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=7 s4: lat=4.6552 cyc=12.947 mem_rd=1043.36 l1miss=991.41 l1hwprf=11.91 l2miss=3.845 l2hwprf=11.45 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=7 s5: lat=4.8141 cyc=13.323 mem_rd=1072.53 l1miss=979.93 l1hwprf=27.80 l2miss=20.972 l2hwprf=17.32 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=7 s6: lat=4.5764 cyc=12.731 mem_rd=1041.93 l1miss=976.81 l1hwprf=25.71 l2miss=1.587 l2hwprf=9.47 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=7 s7: lat=4.7080 cyc=13.078 mem_rd=1043.51 l1miss=998.08 l1hwprf=4.37 l2miss=5.762 l2hwprf=18.05 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=7 s8: lat=4.7309 cyc=13.156 mem_rd=1045.47 l1miss=969.53 l1hwprf=33.31 l2miss=13.391 l2hwprf=93.14 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=7 s9: lat=4.6101 cyc=12.820 mem_rd=1042.10 l1miss=982.09 l1hwprf=20.62 l2miss=2.893 l2hwprf=25.78 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 640 | seed=42 | base | 8 | 10 | 4.598 [4.588, 4.633] | 12.832 [12.770, 12.894] | 1043.451 [1042.822, 1043.805] | 981.311 [976.630, 997.025] | 21.454 [5.359, 25.943] | 2.161 [1.797, 2.866] | 10.901 [5.484, 11.230] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=42 s0: lat=4.5974 cyc=12.838 mem_rd=1042.93 l1miss=977.09 l1hwprf=25.11 l2miss=4.285 l2hwprf=13.27 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=42 s1: lat=4.5980 cyc=12.827 mem_rd=1043.49 l1miss=981.96 l1hwprf=20.78 l2miss=2.893 l2hwprf=11.18 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=42 s2: lat=4.5713 cyc=12.730 mem_rd=1042.79 l1miss=976.44 l1hwprf=26.22 l2miss=1.880 l2hwprf=10.62 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=42 s3: lat=4.6342 cyc=12.896 mem_rd=1044.74 l1miss=992.82 l1hwprf=9.57 l2miss=3.284 l2hwprf=12.04 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=42 s4: lat=4.6469 cyc=12.928 mem_rd=1041.75 l1miss=1001.38 l1hwprf=0.98 l2miss=2.100 l2hwprf=3.76 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=42 s5: lat=4.5592 cyc=12.693 mem_rd=1044.15 l1miss=973.72 l1hwprf=29.42 l2miss=1.538 l2hwprf=11.23 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=42 s6: lat=4.6304 cyc=12.888 mem_rd=1043.43 l1miss=998.43 l1hwprf=3.96 l2miss=1.599 l2hwprf=2.69 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=42 s7: lat=4.5897 cyc=12.767 mem_rd=1043.47 l1miss=976.48 l1hwprf=26.84 l2miss=2.783 l2hwprf=10.62 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=42 s8: lat=4.6438 cyc=12.905 mem_rd=1043.91 l1miss=1001.65 l1hwprf=0.32 l2miss=1.770 l2hwprf=3.77 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=42 s9: lat=4.5878 cyc=12.781 mem_rd=1042.35 l1miss=980.66 l1hwprf=22.13 l2miss=2.222 l2hwprf=11.23 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 640 | seed=1337 | base | 8 | 10 | 4.632 [4.590, 4.777] | 12.929 [12.810, 13.282] | 1043.427 [1043.210, 1043.878] | 983.630 [978.156, 990.372] | 21.539 [12.433, 24.777] | 3.235 [2.380, 14.749] | 34.320 [26.035, 54.950] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=1337 s0: lat=4.9019 cyc=13.684 mem_rd=1043.90 l1miss=993.02 l1hwprf=9.20 l2miss=20.178 l2hwprf=471.90 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=1337 s1: lat=4.7728 cyc=13.365 mem_rd=1043.55 l1miss=991.39 l1hwprf=11.44 l2miss=12.817 l2hwprf=184.72 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=1337 s2: lat=4.5923 cyc=12.817 mem_rd=1043.20 l1miss=981.35 l1hwprf=21.59 l2miss=2.173 l2hwprf=35.12 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=1337 s3: lat=4.5865 cyc=12.779 mem_rd=1044.37 l1miss=980.15 l1hwprf=22.90 l2miss=2.112 l2hwprf=24.83 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=1337 s4: lat=4.5834 cyc=12.795 mem_rd=1041.75 l1miss=975.85 l1hwprf=27.34 l2miss=2.710 l2hwprf=35.74 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=1337 s5: lat=4.6571 cyc=13.006 mem_rd=1043.30 l1miss=999.04 l1hwprf=2.99 l2miss=3.357 l2hwprf=29.65 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=1337 s6: lat=4.7779 cyc=13.296 mem_rd=1042.96 l1miss=974.66 l1hwprf=28.74 l2miss=15.393 l2hwprf=61.35 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=1337 s7: lat=4.5891 cyc=12.808 mem_rd=1043.82 l1miss=977.49 l1hwprf=25.40 l2miss=3.113 l2hwprf=33.52 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=1337 s8: lat=4.7805 cyc=13.240 mem_rd=1066.32 l1miss=985.91 l1hwprf=21.48 l2miss=18.604 l2hwprf=10.47 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=1337 s9: lat=4.6063 cyc=12.851 mem_rd=1043.24 l1miss=987.30 l1hwprf=15.42 l2miss=2.271 l2hwprf=9.38 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 640 | seed=20260928 | base | 8 | 10 | 4.586 [4.569, 4.643] | 12.768 [12.729, 12.930] | 1043.951 [1042.957, 1045.493] | 981.689 [976.276, 991.141] | 21.362 [15.210, 26.633] | 2.283 [1.550, 3.656] | 9.955 [8.572, 14.761] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=20260928 s0: lat=4.5662 cyc=12.727 mem_rd=1043.24 l1miss=968.85 l1hwprf=34.73 l2miss=3.271 l2hwprf=14.92 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=20260928 s1: lat=4.6145 cyc=12.855 mem_rd=1045.45 l1miss=992.53 l1hwprf=9.81 l2miss=1.501 l2hwprf=1.01 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=20260928 s2: lat=4.6520 cyc=12.955 mem_rd=1044.67 l1miss=992.30 l1hwprf=9.77 l2miss=3.784 l2hwprf=10.47 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=20260928 s3: lat=4.8027 cyc=13.308 mem_rd=1064.33 l1miss=992.54 l1hwprf=15.87 l2miss=8.643 l2hwprf=8.91 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=20260928 s4: lat=4.5636 cyc=12.699 mem_rd=1042.81 l1miss=975.24 l1hwprf=27.66 l2miss=1.208 l2hwprf=8.46 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=20260928 s5: lat=4.5764 cyc=12.715 mem_rd=1045.59 l1miss=979.94 l1hwprf=22.84 l2miss=1.367 l2hwprf=8.14 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=20260928 s6: lat=4.5821 cyc=12.737 mem_rd=1045.51 l1miss=979.37 l1hwprf=23.55 l2miss=1.807 l2hwprf=9.44 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=20260928 s7: lat=4.7944 cyc=13.325 mem_rd=1043.21 l1miss=987.67 l1hwprf=14.99 l2miss=14.856 l2hwprf=62.32 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=20260928 s8: lat=4.5903 cyc=12.800 mem_rd=1042.87 l1miss=983.44 l1hwprf=19.89 l2miss=1.697 l2hwprf=14.29 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b640K seed=20260928 s9: lat=4.5643 cyc=12.737 mem_rd=1042.00 l1miss=968.54 l1hwprf=33.90 l2miss=2.759 l2hwprf=36.28 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 768 | seed=7 | base | 8 | 10 | 4.876 [4.866, 4.949] | 13.618 [13.572, 13.806] | 1046.672 [1045.809, 1047.938] | 1002.345 [1001.638, 1002.650] | 0.575 [0.292, 1.444] | 4.517 [3.845, 10.440] | 11.241 [8.433, 13.453] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=7 s0: lat=4.9708 cyc=13.859 mem_rd=1046.86 l1miss=1000.76 l1hwprf=2.17 l2miss=12.126 l2hwprf=13.69 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=7 s1: lat=4.8659 cyc=13.558 mem_rd=1046.48 l1miss=1001.67 l1hwprf=1.65 l2miss=3.825 l2hwprf=12.74 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=7 s2: lat=4.8643 cyc=13.545 mem_rd=1044.27 l1miss=1001.63 l1hwprf=1.23 l2miss=3.906 l2hwprf=5.68 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=7 s3: lat=5.1716 cyc=14.348 mem_rd=1087.27 l1miss=1008.25 l1hwprf=0.26 l2miss=25.065 l2hwprf=8.17 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=7 s4: lat=4.8812 cyc=13.647 mem_rd=1044.33 l1miss=1002.56 l1hwprf=0.14 l2miss=5.381 l2hwprf=9.23 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=7 s5: lat=4.8818 cyc=13.646 mem_rd=1045.60 l1miss=1002.13 l1hwprf=0.45 l2miss=4.913 l2hwprf=12.51 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=7 s6: lat=5.0746 cyc=14.065 mem_rd=1071.21 l1miss=1006.73 l1hwprf=0.70 l2miss=21.230 l2hwprf=17.19 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=7 s7: lat=4.8701 cyc=13.582 mem_rd=1048.19 l1miss=1002.66 l1hwprf=0.08 l2miss=4.120 l2hwprf=9.97 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=7 s8: lat=4.8664 cyc=13.590 mem_rd=1046.43 l1miss=1001.60 l1hwprf=1.52 l2miss=3.754 l2hwprf=14.43 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=7 s9: lat=4.8606 cyc=13.569 mem_rd=1047.19 l1miss=1002.63 l1hwprf=0.38 l2miss=3.530 l2hwprf=6.77 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 768 | seed=42 | base | 8 | 10 | 4.871 [4.858, 4.894] | 13.575 [13.552, 13.622] | 1045.654 [1044.828, 1045.845] | 1002.167 [1002.024, 1002.482] | 0.712 [0.532, 0.956] | 4.206 [3.354, 5.692] | 9.033 [5.417, 14.081] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=42 s0: lat=5.2849 cyc=14.615 mem_rd=1117.50 l1miss=1010.78 l1hwprf=1.30 l2miss=29.378 l2hwprf=10.00 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=42 s1: lat=4.8606 cyc=13.570 mem_rd=1045.58 l1miss=1002.56 l1hwprf=0.13 l2miss=3.682 l2hwprf=6.59 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=42 s2: lat=4.8574 cyc=13.547 mem_rd=1046.04 l1miss=1002.20 l1hwprf=0.53 l2miss=3.245 l2hwprf=1.84 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=42 s3: lat=4.9056 cyc=13.676 mem_rd=1044.25 l1miss=1002.73 l1hwprf=0.04 l2miss=5.941 l2hwprf=20.00 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=42 s4: lat=4.8738 cyc=13.577 mem_rd=1044.66 l1miss=1001.98 l1hwprf=0.86 l2miss=4.323 l2hwprf=8.07 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=42 s5: lat=4.8367 cyc=13.434 mem_rd=1045.78 l1miss=1001.99 l1hwprf=0.99 l2miss=1.729 l2hwprf=1.10 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=42 s6: lat=4.8537 cyc=13.497 mem_rd=1045.73 l1miss=1002.14 l1hwprf=0.76 l2miss=2.757 l2hwprf=5.03 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=42 s7: lat=4.8976 cyc=13.632 mem_rd=1045.00 l1miss=1002.24 l1hwprf=0.66 l2miss=6.053 l2hwprf=14.70 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=42 s8: lat=4.8680 cyc=13.573 mem_rd=1044.77 l1miss=1001.76 l1hwprf=1.15 l2miss=4.089 l2hwprf=12.23 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=42 s9: lat=4.8844 cyc=13.592 mem_rd=1045.87 l1miss=1002.12 l1hwprf=0.54 l2miss=4.944 l2hwprf=15.88 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 768 | seed=1337 | base | 8 | 10 | 4.876 [4.872, 4.963] | 13.599 [13.577, 13.807] | 1046.341 [1045.296, 1047.663] | 1001.572 [1001.460, 1002.380] | 1.200 [0.834, 1.500] | 5.870 [5.135, 11.236] | 12.975 [11.917, 26.466] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=1337 s0: lat=4.8722 cyc=13.584 mem_rd=1044.85 l1miss=996.49 l1hwprf=0.20 l2miss=6.165 l2hwprf=3.08 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=1337 s1: lat=4.8722 cyc=13.597 mem_rd=1046.24 l1miss=1001.45 l1hwprf=1.76 l2miss=5.402 l2hwprf=12.18 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=1337 s2: lat=5.4269 cyc=14.894 mem_rd=1135.25 l1miss=1013.91 l1hwprf=1.08 l2miss=43.345 l2hwprf=25.97 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=1337 s3: lat=4.8685 cyc=13.561 mem_rd=1045.03 l1miss=1001.48 l1hwprf=1.32 l2miss=4.679 l2hwprf=11.83 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=1337 s4: lat=4.8791 cyc=13.600 mem_rd=1047.98 l1miss=1001.00 l1hwprf=1.85 l2miss=5.575 l2hwprf=12.81 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=1337 s5: lat=4.8457 cyc=13.484 mem_rd=1046.44 l1miss=1002.53 l1hwprf=0.31 l2miss=2.869 l2hwprf=4.48 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=1337 s6: lat=4.8918 cyc=13.611 mem_rd=1044.96 l1miss=1001.67 l1hwprf=1.45 l2miss=6.765 l2hwprf=26.63 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=1337 s7: lat=4.8717 cyc=13.574 mem_rd=1046.08 l1miss=1001.48 l1hwprf=1.52 l2miss=5.046 l2hwprf=13.14 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=1337 s8: lat=4.9867 cyc=13.872 mem_rd=1046.70 l1miss=1001.92 l1hwprf=0.81 l2miss=12.726 l2hwprf=161.59 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=1337 s9: lat=5.3014 cyc=14.668 mem_rd=1066.03 l1miss=1005.56 l1hwprf=0.90 l2miss=34.790 l2hwprf=774.30 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 768 | seed=20260928 | base | 8 | 10 | 4.872 [4.851, 5.066] | 13.582 [13.515, 14.128] | 1046.254 [1044.856, 1047.442] | 1002.075 [1001.877, 1002.782] | 0.829 [0.717, 1.254] | 5.178 [4.285, 17.741] | 85.409 [15.511, 275.640] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=20260928 s0: lat=5.3893 cyc=14.920 mem_rd=1096.63 l1miss=1008.13 l1hwprf=0.76 l2miss=37.872 l2hwprf=325.00 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=20260928 s1: lat=4.8712 cyc=13.579 mem_rd=1047.44 l1miss=1001.87 l1hwprf=0.84 l2miss=4.893 l2hwprf=121.31 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=20260928 s2: lat=5.0767 cyc=14.178 mem_rd=1045.97 l1miss=1001.80 l1hwprf=1.37 l2miss=17.751 l2hwprf=624.43 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=20260928 s3: lat=5.0343 cyc=13.977 mem_rd=1067.05 l1miss=1005.08 l1hwprf=1.58 l2miss=21.118 l2hwprf=24.26 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=20260928 s4: lat=4.8478 cyc=13.515 mem_rd=1046.54 l1miss=1001.89 l1hwprf=0.90 l2miss=4.120 l2hwprf=12.59 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=20260928 s5: lat=5.1249 cyc=14.305 mem_rd=1043.99 l1miss=1002.68 l1hwprf=0.13 l2miss=17.710 l2hwprf=1617.56 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=20260928 s6: lat=4.8727 cyc=13.585 mem_rd=1047.43 l1miss=1001.46 l1hwprf=1.44 l2miss=5.463 l2hwprf=127.55 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=20260928 s7: lat=4.8595 cyc=13.516 mem_rd=1045.48 l1miss=1002.13 l1hwprf=0.81 l2miss=4.781 l2hwprf=49.51 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=20260928 s8: lat=4.8309 cyc=13.465 mem_rd=1044.31 l1miss=1002.02 l1hwprf=0.70 l2miss=3.286 l2hwprf=5.02 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b768K seed=20260928 s9: lat=4.8367 cyc=13.495 mem_rd=1044.65 l1miss=1002.82 l1hwprf=0.21 l2miss=3.387 l2hwprf=10.17 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 1024 | seed=7 | base | 8 | 10 | 5.244 [5.162, 5.278] | 14.507 [14.288, 14.612] | 1027.420 [1026.943, 1028.061] | 1001.690 [1001.667, 1001.717] | 0.046 [0.025, 0.053] | 11.566 [7.332, 13.126] | 360.912 [213.491, 541.229] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=7 s0: lat=5.4121 cyc=14.993 mem_rd=1026.71 l1miss=1001.41 l1hwprf=0.11 l2miss=23.178 l2hwprf=579.67 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=7 s1: lat=5.1065 cyc=14.136 mem_rd=1028.88 l1miss=1001.72 l1hwprf=0.05 l2miss=3.914 l2hwprf=96.48 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=7 s2: lat=5.1085 cyc=14.155 mem_rd=1028.66 l1miss=1001.79 l1hwprf=0.05 l2miss=3.426 l2hwprf=28.08 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=7 s3: lat=5.2841 cyc=14.632 mem_rd=1028.26 l1miss=1001.69 l1hwprf=0.02 l2miss=13.245 l2hwprf=1004.59 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=7 s4: lat=5.3998 cyc=14.941 mem_rd=1027.47 l1miss=1001.68 l1hwprf=0.02 l2miss=19.562 l2hwprf=1412.77 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=7 s5: lat=5.1427 cyc=14.236 mem_rd=1026.98 l1miss=1001.66 l1hwprf=0.08 l2miss=6.210 l2hwprf=201.46 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=7 s6: lat=5.2599 cyc=14.553 mem_rd=1027.43 l1miss=1001.69 l1hwprf=0.05 l2miss=12.772 l2hwprf=318.63 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=7 s7: lat=5.2353 cyc=14.487 mem_rd=1025.98 l1miss=1001.66 l1hwprf=0.05 l2miss=10.696 l2hwprf=403.19 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=7 s8: lat=5.2536 cyc=14.528 mem_rd=1026.93 l1miss=1001.72 l1hwprf=0.03 l2miss=12.009 l2hwprf=425.90 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=7 s9: lat=5.2214 cyc=14.442 mem_rd=1027.41 l1miss=1001.74 l1hwprf=0.02 l2miss=11.124 l2hwprf=249.58 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 1024 | seed=42 | base | 8 | 10 | 5.315 [5.209, 5.522] | 14.701 [14.415, 15.276] | 1027.229 [1026.854, 1028.172] | 1001.698 [1001.656, 1001.709] | 0.076 [0.040, 0.097] | 15.610 [9.527, 25.394] | 514.565 [171.970, 1163.189] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=42 s0: lat=5.8313 cyc=16.163 mem_rd=1027.11 l1miss=1001.87 l1hwprf=0.20 l2miss=45.074 l2hwprf=1254.81 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=42 s1: lat=5.1550 cyc=14.259 mem_rd=1027.63 l1miss=1001.70 l1hwprf=0.10 l2miss=5.783 l2hwprf=84.16 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=42 s2: lat=5.2667 cyc=14.578 mem_rd=1027.35 l1miss=1001.63 l1hwprf=0.04 l2miss=13.268 l2hwprf=199.15 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=42 s3: lat=5.3640 cyc=14.824 mem_rd=1026.29 l1miss=1001.69 l1hwprf=0.06 l2miss=17.952 l2hwprf=791.34 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=42 s4: lat=5.2206 cyc=14.449 mem_rd=1028.35 l1miss=1001.71 l1hwprf=0.09 l2miss=10.437 l2hwprf=162.91 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=42 s5: lat=5.8818 cyc=16.219 mem_rd=1046.49 l1miss=1004.84 l1hwprf=0.14 l2miss=55.145 l2hwprf=1478.12 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=42 s6: lat=5.4904 cyc=15.187 mem_rd=1026.94 l1miss=1001.65 l1hwprf=0.05 l2miss=25.642 l2hwprf=888.34 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=42 s7: lat=5.2055 cyc=14.404 mem_rd=1026.82 l1miss=1001.68 l1hwprf=0.09 l2miss=9.224 l2hwprf=237.79 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=42 s8: lat=5.5325 cyc=15.306 mem_rd=1026.82 l1miss=1001.71 l1hwprf=0.02 l2miss=24.651 l2hwprf=1473.24 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=42 s9: lat=5.1117 cyc=14.151 mem_rd=1028.50 l1miss=1001.65 l1hwprf=0.03 l2miss=3.281 l2hwprf=30.69 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 1024 | seed=1337 | base | 8 | 10 | 5.300 [5.242, 5.344] | 14.674 [14.521, 14.812] | 1027.504 [1027.048, 1027.990] | 1001.694 [1001.671, 1001.734] | 0.053 [0.040, 0.069] | 13.802 [11.305, 17.765] | 310.387 [118.887, 1072.287] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=1337 s0: lat=5.3469 cyc=14.827 mem_rd=1027.01 l1miss=1001.74 l1hwprf=0.05 l2miss=19.318 l2hwprf=105.95 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=1337 s1: lat=5.2126 cyc=14.428 mem_rd=1028.56 l1miss=1001.67 l1hwprf=0.02 l2miss=9.590 l2hwprf=108.36 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=1337 s2: lat=5.1681 cyc=14.297 mem_rd=1027.59 l1miss=1001.65 l1hwprf=0.05 l2miss=6.836 l2hwprf=49.08 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=1337 s3: lat=5.2997 cyc=14.674 mem_rd=1027.64 l1miss=1001.69 l1hwprf=0.05 l2miss=15.350 l2hwprf=187.50 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=1337 s4: lat=5.2345 cyc=14.502 mem_rd=1028.11 l1miss=1001.75 l1hwprf=0.07 l2miss=11.238 l2hwprf=150.47 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=1337 s5: lat=5.3366 cyc=14.769 mem_rd=1027.42 l1miss=1001.50 l1hwprf=0.04 l2miss=14.175 l2hwprf=1402.85 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=1337 s6: lat=5.4208 cyc=14.998 mem_rd=1027.04 l1miss=1001.79 l1hwprf=0.13 l2miss=18.570 l2hwprf=1359.23 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=1337 s7: lat=5.2639 cyc=14.578 mem_rd=1026.60 l1miss=1001.70 l1hwprf=0.08 l2miss=11.505 l2hwprf=433.27 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=1337 s8: lat=5.2997 cyc=14.674 mem_rd=1027.08 l1miss=1001.72 l1hwprf=0.04 l2miss=13.428 l2hwprf=534.13 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=1337 s9: lat=5.5917 cyc=15.476 mem_rd=1029.17 l1miss=1001.67 l1hwprf=0.07 l2miss=29.472 l2hwprf=1251.67 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 1024 | seed=20260928 | base | 8 | 10 | 5.349 [5.168, 5.685] | 14.808 [14.306, 15.659] | 1027.618 [1026.983, 1028.408] | 1001.732 [1001.678, 1001.804] | 0.065 [0.044, 0.120] | 16.682 [6.475, 37.756] | 415.184 [146.955, 1110.998] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=20260928 s0: lat=5.7352 cyc=15.619 mem_rd=1072.36 l1miss=1009.25 l1hwprf=0.40 l2miss=38.010 l2hwprf=245.19 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=20260928 s1: lat=5.6748 cyc=15.716 mem_rd=1026.93 l1miss=1001.67 l1hwprf=0.03 l2miss=36.995 l2hwprf=1472.15 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=20260928 s2: lat=5.3839 cyc=14.912 mem_rd=1027.14 l1miss=1001.65 l1hwprf=0.04 l2miss=18.654 l2hwprf=1180.62 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=20260928 s3: lat=5.1399 cyc=14.229 mem_rd=1027.39 l1miss=1001.82 l1hwprf=0.14 l2miss=4.860 l2hwprf=114.21 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=20260928 s4: lat=5.2535 cyc=14.536 mem_rd=1028.54 l1miss=1001.72 l1hwprf=0.06 l2miss=11.322 l2hwprf=245.40 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=20260928 s5: lat=5.6887 cyc=15.673 mem_rd=1049.57 l1miss=1004.79 l1hwprf=0.04 l2miss=40.215 l2hwprf=902.14 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=20260928 s6: lat=5.1216 cyc=14.180 mem_rd=1028.01 l1miss=1001.70 l1hwprf=0.07 l2miss=3.845 l2hwprf=26.34 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=20260928 s7: lat=5.7224 cyc=15.825 mem_rd=1026.41 l1miss=1001.75 l1hwprf=0.07 l2miss=39.696 l2hwprf=1573.08 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=20260928 s8: lat=5.1292 cyc=14.196 mem_rd=1027.85 l1miss=1001.66 l1hwprf=0.14 l2miss=3.944 l2hwprf=22.41 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1024K seed=20260928 s9: lat=5.3136 cyc=14.704 mem_rd=1026.18 l1miss=1001.74 l1hwprf=0.06 l2miss=14.709 l2hwprf=584.97 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 1216 | seed=7 | base | 8 | 10 | 5.628 [5.557, 5.738] | 15.527 [15.349, 15.813] | 1029.602 [1023.181, 1035.694] | 1002.570 [1001.446, 1003.746] | 0.042 [0.032, 0.055] | 30.829 [26.997, 39.307] | 930.150 [546.857, 1176.464] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=7 s0: lat=5.7013 cyc=15.757 mem_rd=1023.12 l1miss=1001.43 l1hwprf=0.06 l2miss=34.257 l2hwprf=607.92 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=7 s1: lat=5.5216 cyc=15.267 mem_rd=1023.28 l1miss=1001.45 l1hwprf=0.03 l2miss=19.692 l2hwprf=1129.73 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=7 s2: lat=5.5487 cyc=15.341 mem_rd=1023.15 l1miss=1001.43 l1hwprf=0.03 l2miss=21.748 l2hwprf=1302.57 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=7 s3: lat=5.6478 cyc=15.614 mem_rd=1022.21 l1miss=1001.45 l1hwprf=0.02 l2miss=28.866 l2hwprf=1192.04 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=7 s4: lat=5.5818 cyc=15.374 mem_rd=1035.69 l1miss=1003.75 l1hwprf=0.04 l2miss=29.888 l2hwprf=526.50 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=7 s5: lat=5.8623 cyc=16.196 mem_rd=1023.66 l1miss=1001.48 l1hwprf=0.04 l2miss=43.213 l2hwprf=1229.33 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=7 s6: lat=5.8117 cyc=16.010 mem_rd=1035.70 l1miss=1003.73 l1hwprf=0.04 l2miss=44.446 l2hwprf=839.93 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=7 s7: lat=5.6073 cyc=15.441 mem_rd=1035.54 l1miss=1003.66 l1hwprf=0.07 l2miss=31.770 l2hwprf=460.06 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=7 s8: lat=5.7508 cyc=15.831 mem_rd=1036.70 l1miss=1004.11 l1hwprf=0.03 l2miss=40.990 l2hwprf=1020.37 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=7 s9: lat=5.5025 cyc=15.149 mem_rd=1046.63 l1miss=1004.65 l1hwprf=0.10 l2miss=26.374 l2hwprf=126.23 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 1216 | seed=42 | base | 8 | 10 | 5.706 [5.627, 5.856] | 15.763 [15.577, 16.161] | 1023.778 [1023.140, 1032.610] | 1001.452 [1001.425, 1003.130] | 0.061 [0.039, 0.080] | 34.437 [26.908, 44.045] | 1043.046 [891.655, 1097.046] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=42 s0: lat=5.8897 cyc=16.288 mem_rd=1023.84 l1miss=1001.50 l1hwprf=0.14 l2miss=45.719 l2hwprf=1036.14 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=42 s1: lat=5.7970 cyc=16.030 mem_rd=1022.76 l1miss=1001.45 l1hwprf=0.07 l2miss=39.024 l2hwprf=1098.45 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=42 s2: lat=5.5828 cyc=15.445 mem_rd=1023.52 l1miss=1001.41 l1hwprf=0.02 l2miss=24.350 l2hwprf=1041.86 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=42 s3: lat=5.4617 cyc=15.116 mem_rd=1023.72 l1miss=1001.39 l1hwprf=0.03 l2miss=16.910 l2hwprf=593.83 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=42 s4: lat=5.6879 cyc=15.732 mem_rd=1024.24 l1miss=1001.45 l1hwprf=0.06 l2miss=29.888 l2hwprf=1395.33 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=42 s5: lat=5.6257 cyc=15.567 mem_rd=1023.01 l1miss=1001.44 l1hwprf=0.06 l2miss=26.701 l2hwprf=1183.79 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=42 s6: lat=5.6314 cyc=15.607 mem_rd=1022.64 l1miss=1001.42 l1hwprf=0.02 l2miss=27.530 l2hwprf=1092.84 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=42 s7: lat=5.7247 cyc=15.794 mem_rd=1035.40 l1miss=1003.75 l1hwprf=0.12 l2miss=38.985 l2hwprf=843.49 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=42 s8: lat=5.8760 cyc=16.204 mem_rd=1045.87 l1miss=1004.55 l1hwprf=0.06 l2miss=48.031 l2hwprf=1044.23 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=42 s9: lat=5.8887 cyc=16.224 mem_rd=1035.50 l1miss=1003.67 l1hwprf=0.08 l2miss=50.820 l2hwprf=815.78 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 1216 | seed=1337 | base | 8 | 10 | 5.586 [5.579, 5.689] | 15.435 [15.418, 15.709] | 1023.454 [1022.872, 1024.472] | 1001.430 [1001.415, 1001.468] | 0.055 [0.035, 0.069] | 24.938 [23.947, 31.658] | 1026.589 [742.374, 1116.956] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=1337 s0: lat=5.5142 cyc=15.257 mem_rd=1023.43 l1miss=1001.43 l1hwprf=0.05 l2miss=20.366 l2hwprf=409.75 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=1337 s1: lat=5.7083 cyc=15.761 mem_rd=1024.56 l1miss=1001.43 l1hwprf=0.03 l2miss=32.837 l2hwprf=1132.20 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=1337 s2: lat=5.5818 cyc=15.416 mem_rd=1023.48 l1miss=1001.42 l1hwprf=0.04 l2miss=24.202 l2hwprf=1063.42 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=1337 s3: lat=5.6330 cyc=15.555 mem_rd=1023.10 l1miss=1001.39 l1hwprf=0.06 l2miss=28.121 l2hwprf=969.85 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=1337 s4: lat=5.5879 cyc=15.440 mem_rd=1021.81 l1miss=1001.41 l1hwprf=0.07 l2miss=25.146 l2hwprf=1071.24 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=1337 s5: lat=5.5842 cyc=15.429 mem_rd=1024.20 l1miss=1001.41 l1hwprf=0.02 l2miss=23.862 l2hwprf=1210.74 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=1337 s6: lat=5.5778 cyc=15.424 mem_rd=1022.80 l1miss=1001.44 l1hwprf=0.07 l2miss=24.729 l2hwprf=989.76 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=1337 s7: lat=5.7418 cyc=15.824 mem_rd=1048.28 l1miss=1003.71 l1hwprf=0.06 l2miss=38.767 l2hwprf=1205.73 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=1337 s8: lat=5.5330 cyc=15.291 mem_rd=1022.42 l1miss=1001.48 l1hwprf=0.03 l2miss=21.812 l2hwprf=666.55 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=1337 s9: lat=5.9797 cyc=16.180 mem_rd=1058.19 l1miss=1005.62 l1hwprf=0.08 l2miss=51.951 l2hwprf=500.04 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 1216 | seed=20260928 | base | 8 | 10 | 5.612 [5.583, 5.693] | 15.529 [15.448, 15.758] | 1023.466 [1023.266, 1023.703] | 1001.449 [1001.434, 1001.476] | 0.032 [0.021, 0.063] | 28.401 [25.526, 31.552] | 915.473 [750.957, 998.225] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=20260928 s0: lat=5.6638 cyc=15.690 mem_rd=1023.35 l1miss=1001.44 l1hwprf=0.03 l2miss=31.224 l2hwprf=1002.74 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=20260928 s1: lat=6.1212 cyc=16.586 mem_rd=1059.92 l1miss=1005.99 l1hwprf=0.10 l2miss=56.377 l2hwprf=728.89 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=20260928 s2: lat=5.5788 cyc=15.430 mem_rd=1023.61 l1miss=1001.46 l1hwprf=0.01 l2miss=24.960 l2hwprf=984.67 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=20260928 s3: lat=5.5397 cyc=15.332 mem_rd=1023.24 l1miss=1001.44 l1hwprf=0.02 l2miss=21.992 l2hwprf=733.50 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=20260928 s4: lat=5.4724 cyc=15.140 mem_rd=1023.58 l1miss=1001.38 l1hwprf=0.00 l2miss=17.038 l2hwprf=1063.41 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=20260928 s5: lat=5.7033 cyc=15.780 mem_rd=1023.73 l1miss=1001.42 l1hwprf=0.06 l2miss=31.661 l2hwprf=1454.72 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=20260928 s6: lat=5.5976 cyc=15.501 mem_rd=1022.87 l1miss=1001.43 l1hwprf=0.03 l2miss=27.222 l2hwprf=856.38 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=20260928 s7: lat=5.5976 cyc=15.503 mem_rd=1023.01 l1miss=1001.47 l1hwprf=0.03 l2miss=27.440 l2hwprf=974.56 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=20260928 s8: lat=5.8047 cyc=15.967 mem_rd=1037.85 l1miss=1004.15 l1hwprf=0.08 l2miss=44.671 l2hwprf=803.33 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1216K seed=20260928 s9: lat=5.6270 cyc=15.555 mem_rd=1023.35 l1miss=1001.48 l1hwprf=0.06 l2miss=29.361 l2hwprf=570.29 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 1408 | seed=7 | base | 8 | 10 | 5.929 [5.893, 5.955] | 16.377 [16.255, 16.448] | 1020.294 [1019.952, 1020.638] | 1001.268 [1001.248, 1001.285] | 0.039 [0.028, 0.054] | 44.101 [41.759, 45.031] | 732.758 [688.221, 819.081] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=7 s0: lat=5.8813 cyc=16.238 mem_rd=1020.74 l1miss=1001.25 l1hwprf=0.05 l2miss=41.393 l2hwprf=545.20 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=7 s1: lat=5.9885 cyc=16.537 mem_rd=1020.31 l1miss=1001.27 l1hwprf=0.08 l2miss=47.164 l2hwprf=830.58 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=7 s2: lat=5.9316 cyc=16.390 mem_rd=1020.33 l1miss=1001.27 l1hwprf=0.03 l2miss=43.363 l2hwprf=784.59 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=7 s3: lat=5.9564 cyc=16.457 mem_rd=1019.71 l1miss=1001.22 l1hwprf=0.02 l2miss=45.077 l2hwprf=755.47 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=7 s4: lat=5.9495 cyc=16.420 mem_rd=1020.10 l1miss=1001.24 l1hwprf=0.03 l2miss=44.839 l2hwprf=703.10 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=7 s5: lat=5.9255 cyc=16.363 mem_rd=1019.54 l1miss=1001.29 l1hwprf=0.07 l2miss=42.858 l2hwprf=881.99 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=7 s6: lat=5.8113 cyc=16.044 mem_rd=1020.27 l1miss=1001.28 l1hwprf=0.03 l2miss=34.846 l2hwprf=914.65 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=7 s7: lat=5.8882 cyc=16.254 mem_rd=1019.90 l1miss=1001.25 l1hwprf=0.04 l2miss=40.783 l2hwprf=683.26 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=7 s8: lat=5.9093 cyc=16.258 mem_rd=1032.81 l1miss=1003.36 l1hwprf=0.06 l2miss=44.894 l2hwprf=534.67 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=7 s9: lat=5.9882 cyc=16.476 mem_rd=1043.82 l1miss=1003.19 l1hwprf=0.03 l2miss=51.774 l2hwprf=710.04 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 1408 | seed=42 | base | 8 | 10 | 6.007 [5.962, 6.210] | 16.613 [16.445, 17.148] | 1020.352 [1019.843, 1029.917] | 1001.298 [1001.250, 1002.724] | 0.031 [0.022, 0.047] | 50.102 [45.862, 61.701] | 717.499 [655.361, 746.754] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=42 s0: lat=6.0232 cyc=16.662 mem_rd=1020.44 l1miss=1001.38 l1hwprf=0.02 l2miss=50.049 l2hwprf=706.13 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=42 s1: lat=6.7116 cyc=18.466 mem_rd=1058.53 l1miss=1007.35 l1hwprf=0.07 l2miss=78.158 l2hwprf=711.05 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=42 s2: lat=6.3047 cyc=17.424 mem_rd=1019.73 l1miss=1001.31 l1hwprf=0.03 l2miss=62.084 l2hwprf=862.03 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=42 s3: lat=5.8752 cyc=16.242 mem_rd=1020.20 l1miss=1001.21 l1hwprf=0.03 l2miss=36.149 l2hwprf=746.19 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=42 s4: lat=5.9905 cyc=16.564 mem_rd=1020.89 l1miss=1001.29 l1hwprf=0.02 l2miss=46.437 l2hwprf=910.68 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=42 s5: lat=6.1443 cyc=16.928 mem_rd=1038.57 l1miss=1003.17 l1hwprf=0.06 l2miss=60.552 l2hwprf=746.94 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=42 s6: lat=5.9613 cyc=16.434 mem_rd=1032.93 l1miss=1003.48 l1hwprf=0.04 l2miss=50.154 l2hwprf=582.60 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=42 s7: lat=5.9648 cyc=16.478 mem_rd=1020.27 l1miss=1001.25 l1hwprf=0.05 l2miss=45.671 l2hwprf=638.44 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=42 s8: lat=6.2324 cyc=17.221 mem_rd=1018.97 l1miss=1001.25 l1hwprf=0.02 l2miss=64.237 l2hwprf=723.94 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=42 s9: lat=5.7509 cyc=15.891 mem_rd=1018.94 l1miss=1001.23 l1hwprf=0.01 l2miss=32.027 l2hwprf=529.20 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 1408 | seed=1337 | base | 8 | 10 | 5.889 [5.869, 6.030] | 16.268 [16.203, 16.647] | 1020.144 [1019.775, 1020.358] | 1001.276 [1001.261, 1001.286] | 0.036 [0.025, 0.055] | 40.733 [38.947, 49.782] | 810.616 [697.248, 831.858] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=1337 s0: lat=6.1301 cyc=16.940 mem_rd=1020.24 l1miss=1001.25 l1hwprf=0.02 l2miss=57.495 l2hwprf=870.06 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=1337 s1: lat=5.8868 cyc=16.270 mem_rd=1019.40 l1miss=1001.27 l1hwprf=0.06 l2miss=40.699 l2hwprf=685.06 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=1337 s2: lat=5.7888 cyc=15.989 mem_rd=1020.40 l1miss=1001.30 l1hwprf=0.11 l2miss=34.679 l2hwprf=564.43 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=1337 s3: lat=5.8336 cyc=16.104 mem_rd=1020.10 l1miss=1001.30 l1hwprf=0.06 l2miss=36.427 l2hwprf=795.50 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=1337 s4: lat=5.8894 cyc=16.257 mem_rd=1020.40 l1miss=1001.28 l1hwprf=0.03 l2miss=40.250 l2hwprf=831.99 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=1337 s5: lat=6.0607 cyc=16.726 mem_rd=1019.76 l1miss=1001.26 l1hwprf=0.01 l2miss=52.124 l2hwprf=831.47 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=1337 s6: lat=5.9423 cyc=16.411 mem_rd=1020.52 l1miss=1001.28 l1hwprf=0.03 l2miss=43.773 l2hwprf=825.73 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=1337 s7: lat=6.0590 cyc=16.729 mem_rd=1019.44 l1miss=1001.28 l1hwprf=0.04 l2miss=51.786 l2hwprf=882.88 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=1337 s8: lat=5.8891 cyc=16.267 mem_rd=1020.19 l1miss=1001.24 l1hwprf=0.02 l2miss=40.766 l2hwprf=667.86 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=1337 s9: lat=5.8634 cyc=16.185 mem_rd=1019.81 l1miss=1001.29 l1hwprf=0.06 l2miss=38.513 l2hwprf=733.81 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 1408 | seed=20260928 | base | 8 | 10 | 5.782 [5.696, 5.839] | 15.983 [15.745, 16.144] | 1019.731 [1019.480, 1020.035] | 1001.268 [1001.261, 1001.283] | 0.044 [0.017, 0.049] | 32.709 [27.405, 37.335] | 894.920 [773.866, 950.689] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=20260928 s0: lat=5.8160 cyc=16.070 mem_rd=1020.86 l1miss=1001.29 l1hwprf=0.06 l2miss=35.184 l2hwprf=765.30 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=20260928 s1: lat=5.6960 cyc=15.755 mem_rd=1019.24 l1miss=1001.33 l1hwprf=0.05 l2miss=26.284 l2hwprf=1000.16 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=20260928 s2: lat=5.7625 cyc=15.937 mem_rd=1019.59 l1miss=1001.27 l1hwprf=0.04 l2miss=31.644 l2hwprf=921.54 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=20260928 s3: lat=5.6851 cyc=15.723 mem_rd=1019.44 l1miss=1001.30 l1hwprf=0.07 l2miss=27.166 l2hwprf=703.67 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=20260928 s4: lat=5.8469 cyc=16.169 mem_rd=1019.68 l1miss=1001.26 l1hwprf=0.04 l2miss=38.053 l2hwprf=799.55 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=20260928 s5: lat=6.0596 cyc=16.751 mem_rd=1020.36 l1miss=1001.22 l1hwprf=0.02 l2miss=51.852 l2hwprf=868.30 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=20260928 s6: lat=5.8024 cyc=16.030 mem_rd=1019.79 l1miss=1001.26 l1hwprf=0.01 l2miss=33.775 l2hwprf=945.95 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=20260928 s7: lat=5.6874 cyc=15.717 mem_rd=1020.09 l1miss=1001.27 l1hwprf=0.04 l2miss=25.785 l2hwprf=1083.00 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=20260928 s8: lat=5.9668 cyc=16.492 mem_rd=1019.86 l1miss=1001.27 l1hwprf=0.02 l2miss=48.956 l2hwprf=952.27 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1408K seed=20260928 s9: lat=5.6955 cyc=15.742 mem_rd=1019.07 l1miss=1001.27 l1hwprf=0.00 l2miss=28.121 l2hwprf=503.57 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 1792 | seed=7 | base | 8 | 10 | 6.512 [6.381, 6.601] | 17.944 [17.583, 18.143] | 1020.645 [1016.040, 1027.035] | 1001.757 [1000.999, 1002.570] | 0.026 [0.022, 0.029] | 75.612 [68.420, 80.579] | 670.140 [546.335, 729.682] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=7 s0: lat=6.7125 cyc=18.550 mem_rd=1015.42 l1miss=1001.00 l1hwprf=0.01 l2miss=81.486 l2hwprf=736.20 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=7 s1: lat=6.5061 cyc=17.905 mem_rd=1024.99 l1miss=1002.51 l1hwprf=0.03 l2miss=77.859 l2hwprf=656.60 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=7 s2: lat=6.3690 cyc=17.547 mem_rd=1032.85 l1miss=1002.55 l1hwprf=0.02 l2miss=68.630 l2hwprf=532.47 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=7 s3: lat=6.5186 cyc=17.982 mem_rd=1016.31 l1miss=1001.00 l1hwprf=0.03 l2miss=74.790 l2hwprf=814.37 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=7 s4: lat=6.6035 cyc=18.149 mem_rd=1028.95 l1miss=1002.76 l1hwprf=0.03 l2miss=82.323 l2hwprf=758.71 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=7 s5: lat=6.5933 cyc=18.123 mem_rd=1026.92 l1miss=1002.82 l1hwprf=0.07 l2miss=76.433 l2hwprf=550.33 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=7 s6: lat=6.4166 cyc=17.691 mem_rd=1015.92 l1miss=1001.00 l1hwprf=0.03 l2miss=68.351 l2hwprf=710.12 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=7 s7: lat=6.3179 cyc=17.404 mem_rd=1027.07 l1miss=1002.58 l1hwprf=0.04 l2miss=66.153 l2hwprf=437.81 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=7 s8: lat=6.6358 cyc=18.298 mem_rd=1016.01 l1miss=1000.95 l1hwprf=0.02 l2miss=83.592 l2hwprf=683.68 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=7 s9: lat=6.1296 cyc=16.914 mem_rd=1016.14 l1miss=1000.98 l1hwprf=0.02 l2miss=49.303 l2hwprf=545.00 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 1792 | seed=42 | base | 8 | 10 | 6.595 [6.478, 6.679] | 18.169 [17.832, 18.417] | 1020.081 [1015.969, 1030.754] | 1001.777 [1000.990, 1002.887] | 0.024 [0.019, 0.031] | 79.163 [74.171, 85.915] | 713.248 [584.966, 723.058] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=42 s0: lat=6.6971 cyc=18.465 mem_rd=1016.02 l1miss=1000.99 l1hwprf=0.03 l2miss=87.036 l2hwprf=825.74 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=42 s1: lat=6.5547 cyc=18.020 mem_rd=1031.50 l1miss=1002.95 l1hwprf=0.03 l2miss=79.585 l2hwprf=578.33 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=42 s2: lat=6.6258 cyc=18.263 mem_rd=1016.28 l1miss=1000.96 l1hwprf=0.00 l2miss=74.956 l2hwprf=732.92 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=42 s3: lat=6.4017 cyc=17.655 mem_rd=1015.57 l1miss=1000.99 l1hwprf=0.03 l2miss=66.568 l2hwprf=712.38 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=42 s4: lat=6.4523 cyc=17.769 mem_rd=1023.88 l1miss=1002.56 l1hwprf=0.02 l2miss=73.909 l2hwprf=604.88 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=42 s5: lat=6.6226 cyc=18.273 mem_rd=1015.95 l1miss=1000.97 l1hwprf=0.03 l2miss=82.642 l2hwprf=714.12 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=42 s6: lat=5.8472 cyc=16.114 mem_rd=1015.82 l1miss=1000.99 l1hwprf=0.02 l2miss=29.393 l2hwprf=189.24 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=42 s7: lat=6.7220 cyc=18.483 mem_rd=1028.52 l1miss=1002.92 l1hwprf=0.03 l2miss=88.361 l2hwprf=722.49 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=42 s8: lat=6.5679 cyc=18.075 mem_rd=1032.53 l1miss=1003.18 l1hwprf=0.02 l2miss=78.740 l2hwprf=564.71 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=42 s9: lat=6.7593 cyc=18.601 mem_rd=1031.94 l1miss=1002.79 l1hwprf=0.02 l2miss=87.006 l2hwprf=723.25 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 1792 | seed=1337 | base | 8 | 10 | 6.648 [6.428, 6.714] | 18.269 [17.721, 18.472] | 1026.587 [1018.986, 1033.297] | 1002.740 [1001.425, 1002.888] | 0.028 [0.026, 0.035] | 80.739 [68.796, 86.595] | 667.777 [637.253, 689.556] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=1337 s0: lat=6.6941 cyc=18.443 mem_rd=1036.76 l1miss=1003.49 l1hwprf=0.03 l2miss=80.981 l2hwprf=591.37 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=1337 s1: lat=6.6230 cyc=18.209 mem_rd=1035.33 l1miss=1002.75 l1hwprf=0.03 l2miss=78.360 l2hwprf=693.62 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=1337 s2: lat=6.6523 cyc=18.298 mem_rd=1026.43 l1miss=1002.72 l1hwprf=0.03 l2miss=80.497 l2hwprf=701.34 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=1337 s3: lat=6.8426 cyc=18.805 mem_rd=1026.35 l1miss=1002.90 l1hwprf=0.03 l2miss=91.801 l2hwprf=662.53 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=1337 s4: lat=6.1878 cyc=17.070 mem_rd=1016.53 l1miss=1000.98 l1hwprf=0.02 l2miss=53.410 l2hwprf=551.72 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=1337 s5: lat=6.3056 cyc=17.396 mem_rd=1015.78 l1miss=1000.99 l1hwprf=0.03 l2miss=61.877 l2hwprf=628.83 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=1337 s6: lat=6.3631 cyc=17.558 mem_rd=1015.29 l1miss=1000.99 l1hwprf=0.03 l2miss=65.608 l2hwprf=667.10 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=1337 s7: lat=6.7200 cyc=18.481 mem_rd=1037.66 l1miss=1002.86 l1hwprf=0.00 l2miss=88.248 l2hwprf=677.36 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=1337 s8: lat=6.8908 cyc=18.949 mem_rd=1026.75 l1miss=1002.73 l1hwprf=0.03 l2miss=102.517 l2hwprf=740.47 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=1337 s9: lat=6.6439 cyc=18.240 mem_rd=1027.18 l1miss=1002.90 l1hwprf=0.03 l2miss=81.635 l2hwprf=668.46 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 1792 | seed=20260928 | base | 8 | 10 | 6.442 [6.337, 6.555] | 17.779 [17.472, 18.054] | 1016.211 [1015.641, 1025.684] | 1001.016 [1001.001, 1002.727] | 0.028 [0.023, 0.048] | 68.172 [62.901, 75.519] | 641.159 [468.813, 667.478] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=20260928 s0: lat=6.6784 cyc=18.421 mem_rd=1029.31 l1miss=1002.77 l1hwprf=0.03 l2miss=80.457 l2hwprf=618.59 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=20260928 s1: lat=6.3258 cyc=17.453 mem_rd=1016.27 l1miss=1001.01 l1hwprf=0.05 l2miss=61.885 l2hwprf=665.86 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=20260928 s2: lat=6.4064 cyc=17.677 mem_rd=1015.45 l1miss=1000.99 l1hwprf=0.05 l2miss=68.547 l2hwprf=668.02 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=20260928 s3: lat=6.5588 cyc=18.078 mem_rd=1016.15 l1miss=1001.02 l1hwprf=0.02 l2miss=77.837 l2hwprf=765.86 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=20260928 s4: lat=6.5440 cyc=17.984 mem_rd=1026.91 l1miss=1002.79 l1hwprf=0.07 l2miss=67.797 l2hwprf=458.80 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=20260928 s5: lat=6.4768 cyc=17.880 mem_rd=1015.59 l1miss=1001.00 l1hwprf=0.01 l2miss=65.948 l2hwprf=677.06 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=20260928 s6: lat=6.3694 cyc=17.530 mem_rd=1025.20 l1miss=1002.60 l1hwprf=0.03 l2miss=68.564 l2hwprf=498.86 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=20260928 s7: lat=5.9541 cyc=16.428 mem_rd=1015.62 l1miss=1001.01 l1hwprf=0.05 l2miss=36.669 l2hwprf=364.52 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=20260928 s8: lat=5.9568 cyc=16.399 mem_rd=1025.84 l1miss=1002.77 l1hwprf=0.03 l2miss=40.009 l2hwprf=182.15 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b1792K seed=20260928 s9: lat=6.7030 cyc=18.471 mem_rd=1015.69 l1miss=1000.98 l1hwprf=0.02 l2miss=80.632 l2hwprf=663.73 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 2048 | seed=7 | base | 8 | 10 | 6.804 [6.750, 6.940] | 18.650 [18.607, 19.093] | 1022.020 [1014.024, 1027.214] | 1002.155 [1000.857, 1002.381] | 0.029 [0.019, 0.040] | 90.687 [87.287, 93.025] | 729.868 [684.560, 776.033] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=7 s0: lat=6.8996 cyc=19.027 mem_rd=1013.81 l1miss=1000.85 l1hwprf=0.03 l2miss=88.703 l2hwprf=779.09 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=7 s1: lat=6.7447 cyc=18.570 mem_rd=1021.85 l1miss=1002.28 l1hwprf=0.04 l2miss=89.348 l2hwprf=637.03 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=7 s2: lat=6.6157 cyc=18.239 mem_rd=1013.95 l1miss=1000.84 l1hwprf=0.00 l2miss=78.045 l2hwprf=718.00 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=7 s3: lat=6.9541 cyc=19.115 mem_rd=1032.76 l1miss=1002.41 l1hwprf=0.03 l2miss=92.419 l2hwprf=665.47 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=7 s4: lat=6.8263 cyc=18.632 mem_rd=1028.64 l1miss=1003.14 l1hwprf=0.04 l2miss=93.227 l2hwprf=679.02 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=7 s5: lat=6.9714 cyc=19.437 mem_rd=1022.93 l1miss=1002.07 l1hwprf=0.02 l2miss=110.806 l2hwprf=812.46 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=7 s6: lat=6.7455 cyc=18.598 mem_rd=1013.48 l1miss=1000.85 l1hwprf=0.03 l2miss=86.815 l2hwprf=741.73 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=7 s7: lat=7.3502 cyc=20.173 mem_rd=1047.03 l1miss=1004.72 l1hwprf=0.05 l2miss=118.916 l2hwprf=766.85 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=7 s8: lat=6.7641 cyc=18.642 mem_rd=1014.23 l1miss=1000.87 l1hwprf=0.02 l2miss=80.318 l2hwprf=784.41 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=7 s9: lat=6.7816 cyc=18.658 mem_rd=1022.19 l1miss=1002.24 l1hwprf=0.00 l2miss=92.026 l2hwprf=701.19 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 2048 | seed=42 | base | 8 | 10 | 6.859 [6.752, 6.936] | 18.872 [18.566, 19.062] | 1021.513 [1015.805, 1023.538] | 1002.289 [1001.223, 1002.485] | 0.029 [0.020, 0.038] | 92.237 [85.283, 99.937] | 725.197 [674.463, 769.570] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=42 s0: lat=6.8104 cyc=18.734 mem_rd=1029.75 l1miss=1002.61 l1hwprf=0.05 l2miss=84.293 l2hwprf=500.21 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=42 s1: lat=6.8905 cyc=18.982 mem_rd=1013.61 l1miss=1000.89 l1hwprf=0.02 l2miss=88.253 l2hwprf=809.23 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=42 s2: lat=6.7319 cyc=18.510 mem_rd=1021.22 l1miss=1002.22 l1hwprf=0.02 l2miss=88.745 l2hwprf=666.53 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=42 s3: lat=6.8283 cyc=18.780 mem_rd=1022.56 l1miss=1002.33 l1hwprf=0.04 l2miss=95.730 l2hwprf=710.86 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=42 s4: lat=6.6940 cyc=18.452 mem_rd=1013.80 l1miss=1000.84 l1hwprf=0.01 l2miss=83.473 l2hwprf=739.53 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=42 s5: lat=6.9507 cyc=19.089 mem_rd=1039.49 l1miss=1004.72 l1hwprf=0.04 l2miss=102.268 l2hwprf=771.10 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=42 s6: lat=6.9950 cyc=19.232 mem_rd=1023.86 l1miss=1002.54 l1hwprf=0.01 l2miss=97.294 l2hwprf=698.26 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=42 s7: lat=6.5412 cyc=18.037 mem_rd=1014.03 l1miss=1000.86 l1hwprf=0.03 l2miss=67.726 l2hwprf=620.66 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=42 s8: lat=6.9648 cyc=19.163 mem_rd=1021.12 l1miss=1002.26 l1hwprf=0.03 l2miss=104.839 l2hwprf=839.55 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=42 s9: lat=6.8895 cyc=18.964 mem_rd=1021.80 l1miss=1002.32 l1hwprf=0.04 l2miss=100.819 l2hwprf=764.97 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 2048 | seed=1337 | base | 8 | 10 | 6.803 [6.720, 6.850] | 18.718 [18.505, 18.874] | 1018.852 [1013.955, 1024.547] | 1001.570 [1000.878, 1002.434] | 0.036 [0.023, 0.052] | 88.573 [81.964, 91.076] | 688.129 [641.160, 771.757] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=1337 s0: lat=7.2000 cyc=19.759 mem_rd=1037.71 l1miss=1004.19 l1hwprf=0.09 l2miss=103.951 l2hwprf=704.97 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=1337 s1: lat=6.8565 cyc=18.907 mem_rd=1014.60 l1miss=1000.87 l1hwprf=0.03 l2miss=86.975 l2hwprf=782.92 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=1337 s2: lat=6.7699 cyc=18.607 mem_rd=1027.56 l1miss=1002.23 l1hwprf=0.06 l2miss=90.641 l2hwprf=633.40 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=1337 s3: lat=6.5915 cyc=18.163 mem_rd=1013.93 l1miss=1000.86 l1hwprf=0.02 l2miss=76.332 l2hwprf=738.28 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=1337 s4: lat=6.7949 cyc=18.719 mem_rd=1013.96 l1miss=1000.84 l1hwprf=0.02 l2miss=90.172 l2hwprf=827.16 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=1337 s5: lat=6.8114 cyc=18.716 mem_rd=1023.10 l1miss=1002.45 l1hwprf=0.01 l2miss=91.221 l2hwprf=671.29 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=1337 s6: lat=6.9775 cyc=19.175 mem_rd=1025.02 l1miss=1002.70 l1hwprf=0.05 l2miss=95.356 l2hwprf=664.45 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=1337 s7: lat=6.8293 cyc=18.777 mem_rd=1023.11 l1miss=1002.38 l1hwprf=0.02 l2miss=81.215 l2hwprf=468.09 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=1337 s8: lat=6.3711 cyc=17.551 mem_rd=1013.95 l1miss=1000.89 l1hwprf=0.05 l2miss=56.839 l2hwprf=342.31 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=1337 s9: lat=6.7037 cyc=18.471 mem_rd=1013.45 l1miss=1000.91 l1hwprf=0.05 l2miss=84.213 l2hwprf=803.36 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 2048 | seed=20260928 | base | 8 | 10 | 6.718 [6.541, 6.835] | 18.508 [18.034, 18.790] | 1014.002 [1013.684, 1019.810] | 1000.885 [1000.867, 1001.896] | 0.027 [0.016, 0.034] | 80.324 [72.645, 86.466] | 673.817 [639.991, 749.682] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=20260928 s0: lat=7.0004 cyc=19.307 mem_rd=1014.24 l1miss=1000.84 l1hwprf=0.01 l2miss=84.515 l2hwprf=767.28 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=20260928 s1: lat=6.3990 cyc=17.634 mem_rd=1013.72 l1miss=1000.89 l1hwprf=0.00 l2miss=62.408 l2hwprf=569.08 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=20260928 s2: lat=6.8541 cyc=18.822 mem_rd=1041.98 l1miss=1004.84 l1hwprf=0.05 l2miss=96.344 l2hwprf=681.24 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=20260928 s3: lat=7.1385 cyc=19.594 mem_rd=1024.58 l1miss=1002.63 l1hwprf=0.02 l2miss=100.723 l2hwprf=645.71 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=20260928 s4: lat=6.7790 cyc=18.695 mem_rd=1013.66 l1miss=1000.90 l1hwprf=0.03 l2miss=81.596 l2hwprf=747.70 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=20260928 s5: lat=6.7075 cyc=18.457 mem_rd=1021.67 l1miss=1002.23 l1hwprf=0.03 l2miss=87.116 l2hwprf=638.08 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=20260928 s6: lat=6.0419 cyc=16.662 mem_rd=1013.67 l1miss=1000.85 l1hwprf=0.03 l2miss=37.479 l2hwprf=307.59 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=20260928 s7: lat=6.7286 cyc=18.559 mem_rd=1014.19 l1miss=1000.87 l1hwprf=0.03 l2miss=78.270 l2hwprf=776.76 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=20260928 s8: lat=6.6284 cyc=18.280 mem_rd=1013.08 l1miss=1000.89 l1hwprf=0.02 l2miss=79.052 l2hwprf=750.34 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2048K seed=20260928 s9: lat=6.5122 cyc=17.952 mem_rd=1013.81 l1miss=1000.87 l1hwprf=0.03 l2miss=70.770 l2hwprf=666.39 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 2304 | seed=7 | base | 8 | 10 | 7.095 [7.030, 7.168] | 19.501 [19.330, 19.719] | 1015.554 [1012.289, 1020.794] | 1001.399 [1000.787, 1002.085] | 0.020 [0.014, 0.025] | 104.587 [100.549, 111.982] | 821.908 [777.822, 849.897] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=7 s0: lat=7.2497 cyc=19.943 mem_rd=1026.84 l1miss=1002.09 l1hwprf=0.01 l2miss=108.765 l2hwprf=774.42 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=7 s1: lat=6.9544 cyc=19.159 mem_rd=1012.29 l1miss=1000.79 l1hwprf=0.02 l2miss=98.456 l2hwprf=853.45 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=7 s2: lat=7.0288 cyc=19.312 mem_rd=1020.83 l1miss=1002.19 l1hwprf=0.01 l2miss=100.376 l2hwprf=711.71 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=7 s3: lat=7.0356 cyc=19.382 mem_rd=1012.30 l1miss=1000.79 l1hwprf=0.02 l2miss=95.951 l2hwprf=738.54 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=7 s4: lat=7.0560 cyc=19.401 mem_rd=1018.64 l1miss=1002.00 l1hwprf=0.02 l2miss=107.751 l2hwprf=822.47 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=7 s5: lat=7.1771 cyc=19.733 mem_rd=1020.70 l1miss=1002.06 l1hwprf=0.03 l2miss=113.054 l2hwprf=839.22 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=7 s6: lat=7.3908 cyc=20.371 mem_rd=1012.10 l1miss=1000.80 l1hwprf=0.02 l2miss=117.055 l2hwprf=940.33 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=7 s7: lat=7.0030 cyc=19.292 mem_rd=1012.13 l1miss=1000.77 l1hwprf=0.04 l2miss=101.067 l2hwprf=860.67 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=7 s8: lat=7.1338 cyc=19.602 mem_rd=1036.18 l1miss=1004.22 l1hwprf=0.04 l2miss=113.515 l2hwprf=788.04 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=7 s9: lat=7.1416 cyc=19.678 mem_rd=1012.47 l1miss=1000.74 l1hwprf=0.01 l2miss=101.423 l2hwprf=821.35 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 2304 | seed=42 | base | 8 | 10 | 7.106 [7.037, 7.167] | 19.543 [19.367, 19.717] | 1015.801 [1012.341, 1023.643] | 1001.368 [1000.777, 1001.992] | 0.017 [0.011, 0.020] | 105.164 [101.928, 108.951] | 808.511 [781.207, 855.873] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=42 s0: lat=7.2403 cyc=19.927 mem_rd=1018.77 l1miss=1001.95 l1hwprf=0.01 l2miss=108.890 l2hwprf=774.45 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=42 s1: lat=6.9993 cyc=19.280 mem_rd=1011.62 l1miss=1000.78 l1hwprf=0.02 l2miss=102.210 l2hwprf=757.49 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=42 s2: lat=7.0145 cyc=19.273 mem_rd=1020.72 l1miss=1001.97 l1hwprf=0.01 l2miss=102.525 l2hwprf=805.62 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=42 s3: lat=7.3152 cyc=20.150 mem_rd=1012.83 l1miss=1000.78 l1hwprf=0.01 l2miss=99.969 l2hwprf=877.46 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=42 s4: lat=7.1821 cyc=19.749 mem_rd=1024.62 l1miss=1002.38 l1hwprf=0.02 l2miss=116.235 l2hwprf=894.44 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=42 s5: lat=7.0198 cyc=19.334 mem_rd=1012.35 l1miss=1000.75 l1hwprf=0.01 l2miss=101.834 l2hwprf=811.40 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=42 s6: lat=7.1229 cyc=19.622 mem_rd=1011.98 l1miss=1000.75 l1hwprf=0.01 l2miss=100.071 l2hwprf=822.78 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=42 s7: lat=7.0893 cyc=19.492 mem_rd=1026.08 l1miss=1002.00 l1hwprf=0.03 l2miss=109.616 l2hwprf=801.46 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=42 s8: lat=7.1156 cyc=19.595 mem_rd=1012.34 l1miss=1000.78 l1hwprf=0.02 l2miss=108.971 l2hwprf=866.90 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=42 s9: lat=7.0955 cyc=19.466 mem_rd=1039.58 l1miss=1004.22 l1hwprf=0.05 l2miss=107.802 l2hwprf=715.84 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 2304 | seed=1337 | base | 8 | 10 | 7.138 [6.993, 7.299] | 19.631 [19.259, 20.041] | 1020.567 [1019.383, 1025.448] | 1002.107 [1001.942, 1002.163] | 0.025 [0.017, 0.036] | 104.506 [98.152, 110.812] | 764.926 [733.766, 790.926] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=1337 s0: lat=7.2532 cyc=19.892 mem_rd=1027.84 l1miss=1002.28 l1hwprf=0.03 l2miss=111.026 l2hwprf=750.39 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=1337 s1: lat=7.3306 cyc=20.148 mem_rd=1020.82 l1miss=1002.15 l1hwprf=0.02 l2miss=110.168 l2hwprf=780.53 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=1337 s2: lat=7.0243 cyc=19.313 mem_rd=1020.24 l1miss=1002.10 l1hwprf=0.02 l2miss=97.666 l2hwprf=680.60 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=1337 s3: lat=6.9827 cyc=19.241 mem_rd=1012.64 l1miss=1000.79 l1hwprf=0.05 l2miss=99.708 l2hwprf=867.00 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=1337 s4: lat=7.1104 cyc=19.554 mem_rd=1027.84 l1miss=1002.17 l1hwprf=0.03 l2miss=99.609 l2hwprf=728.22 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=1337 s5: lat=7.3149 cyc=20.091 mem_rd=1019.10 l1miss=1001.89 l1hwprf=0.01 l2miss=113.881 l2hwprf=794.39 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=1337 s6: lat=6.8516 cyc=18.875 mem_rd=1012.10 l1miss=1000.75 l1hwprf=0.00 l2miss=93.299 l2hwprf=765.73 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=1337 s7: lat=7.1647 cyc=19.708 mem_rd=1020.32 l1miss=1002.12 l1hwprf=0.02 l2miss=109.304 l2hwprf=764.13 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=1337 s8: lat=7.4242 cyc=20.408 mem_rd=1025.68 l1miss=1002.53 l1hwprf=0.04 l2miss=112.732 l2hwprf=826.51 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=1337 s9: lat=6.8657 cyc=18.887 mem_rd=1024.76 l1miss=1002.09 l1hwprf=0.04 l2miss=95.662 l2hwprf=667.25 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 2304 | seed=20260928 | base | 8 | 10 | 7.199 [7.063, 7.230] | 19.731 [19.435, 19.846] | 1019.731 [1014.013, 1024.267] | 1002.001 [1001.075, 1002.456] | 0.020 [0.014, 0.034] | 105.784 [101.935, 109.474] | 809.075 [754.360, 833.304] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=20260928 s0: lat=7.1976 cyc=19.781 mem_rd=1035.37 l1miss=1004.23 l1hwprf=0.04 l2miss=109.565 l2hwprf=675.52 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=20260928 s1: lat=7.2347 cyc=19.867 mem_rd=1025.52 l1miss=1002.58 l1hwprf=0.01 l2miss=103.946 l2hwprf=744.62 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=20260928 s2: lat=7.2568 cyc=19.973 mem_rd=1018.82 l1miss=1001.93 l1hwprf=0.02 l2miss=120.639 l2hwprf=909.22 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=20260928 s3: lat=7.0356 cyc=19.371 mem_rd=1012.40 l1miss=1000.78 l1hwprf=0.04 l2miss=103.590 l2hwprf=824.18 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=20260928 s4: lat=7.2001 cyc=19.627 mem_rd=1020.52 l1miss=1002.09 l1hwprf=0.02 l2miss=109.202 l2hwprf=783.57 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=20260928 s5: lat=7.1453 cyc=19.681 mem_rd=1012.37 l1miss=1000.79 l1hwprf=0.01 l2miss=101.383 l2hwprf=836.34 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=20260928 s6: lat=7.2156 cyc=19.784 mem_rd=1019.38 l1miss=1002.02 l1hwprf=0.01 l2miss=107.622 l2hwprf=794.62 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=20260928 s7: lat=6.9191 cyc=19.037 mem_rd=1020.08 l1miss=1001.98 l1hwprf=0.01 l2miss=99.036 l2hwprf=666.45 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=20260928 s8: lat=6.9714 cyc=19.209 mem_rd=1012.41 l1miss=1000.77 l1hwprf=0.02 l2miss=99.121 l2hwprf=823.53 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b2304K seed=20260928 s9: lat=7.3685 cyc=20.233 mem_rd=1041.90 l1miss=1005.05 l1hwprf=0.04 l2miss=122.545 l2hwprf=838.63 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 3072 | seed=7 | base | 8 | 10 | 7.743 [7.595, 7.890] | 21.274 [20.894, 21.688] | 1014.923 [1010.538, 1017.697] | 1001.420 [1000.795, 1001.634] | 0.019 [0.013, 0.023] | 138.393 [130.582, 143.781] | 957.490 [922.666, 978.751] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=7 s0: lat=8.0989 cyc=22.264 mem_rd=1027.59 l1miss=1003.24 l1hwprf=0.02 l2miss=156.189 l2hwprf=985.28 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=7 s1: lat=7.5757 cyc=20.852 mem_rd=1009.30 l1miss=1000.58 l1hwprf=0.02 l2miss=136.973 l2hwprf=961.72 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=7 s2: lat=7.9000 cyc=21.737 mem_rd=1009.17 l1miss=1000.57 l1hwprf=0.02 l2miss=128.883 l2hwprf=953.26 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=7 s3: lat=7.3961 cyc=20.363 mem_rd=1008.79 l1miss=1000.59 l1hwprf=0.02 l2miss=120.900 l2hwprf=913.95 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=7 s4: lat=7.8926 cyc=21.698 mem_rd=1014.38 l1miss=1001.42 l1hwprf=0.01 l2miss=144.104 l2hwprf=982.32 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=7 s5: lat=7.7666 cyc=21.343 mem_rd=1021.52 l1miss=1002.32 l1hwprf=0.01 l2miss=147.118 l2hwprf=968.06 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=7 s6: lat=7.8809 cyc=21.659 mem_rd=1014.25 l1miss=1001.42 l1hwprf=0.02 l2miss=142.812 l2hwprf=994.53 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=7 s7: lat=7.6519 cyc=21.019 mem_rd=1015.81 l1miss=1001.65 l1hwprf=0.03 l2miss=135.679 l2hwprf=905.55 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=7 s8: lat=6.3823 cyc=17.530 mem_rd=1018.33 l1miss=1001.42 l1hwprf=0.04 l2miss=50.687 l2hwprf=493.99 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=7 s9: lat=7.7187 cyc=21.205 mem_rd=1015.46 l1miss=1001.60 l1hwprf=0.01 l2miss=139.814 l2hwprf=948.80 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 3072 | seed=42 | base | 8 | 10 | 7.762 [7.723, 7.965] | 21.337 [21.233, 21.880] | 1015.004 [1014.730, 1015.612] | 1001.507 [1001.472, 1001.558] | 0.018 [0.013, 0.023] | 142.700 [135.462, 145.817] | 952.850 [901.316, 984.669] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=42 s0: lat=8.2309 cyc=22.649 mem_rd=1015.06 l1miss=1001.49 l1hwprf=0.02 l2miss=146.695 l2hwprf=947.38 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=42 s1: lat=7.7914 cyc=21.414 mem_rd=1015.45 l1miss=1001.51 l1hwprf=0.01 l2miss=137.383 l2hwprf=958.32 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=42 s2: lat=7.7250 cyc=21.237 mem_rd=1014.70 l1miss=1001.51 l1hwprf=0.02 l2miss=145.358 l2hwprf=1030.66 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=42 s3: lat=6.6099 cyc=18.200 mem_rd=1008.73 l1miss=1000.57 l1hwprf=0.01 l2miss=61.770 l2hwprf=708.64 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=42 s4: lat=7.7217 cyc=21.232 mem_rd=1018.69 l1miss=1001.56 l1hwprf=0.02 l2miss=143.725 l2hwprf=935.82 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=42 s5: lat=7.7457 cyc=21.313 mem_rd=1014.10 l1miss=1001.45 l1hwprf=0.02 l2miss=134.735 l2hwprf=836.81 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=42 s6: lat=8.0231 cyc=22.036 mem_rd=1026.63 l1miss=1003.10 l1hwprf=0.03 l2miss=148.226 l2hwprf=987.17 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=42 s7: lat=7.5689 cyc=20.819 mem_rd=1014.82 l1miss=1001.47 l1hwprf=0.01 l2miss=134.822 l2hwprf=889.82 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=42 s8: lat=8.3176 cyc=22.872 mem_rd=1015.67 l1miss=1001.61 l1hwprf=0.02 l2miss=141.675 l2hwprf=977.15 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=42 s9: lat=7.7780 cyc=21.360 mem_rd=1014.95 l1miss=1001.54 l1hwprf=0.04 l2miss=145.971 l2hwprf=1016.48 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 3072 | seed=1337 | base | 8 | 10 | 7.633 [7.496, 7.814] | 20.980 [20.614, 21.484] | 1014.590 [1009.402, 1015.443] | 1001.511 [1000.585, 1001.630] | 0.018 [0.013, 0.024] | 130.189 [123.784, 134.410] | 898.911 [862.314, 953.616] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=1337 s0: lat=7.7306 cyc=21.262 mem_rd=1015.77 l1miss=1001.62 l1hwprf=0.04 l2miss=144.381 l2hwprf=967.20 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=1337 s1: lat=6.6172 cyc=18.212 mem_rd=1009.40 l1miss=1000.57 l1hwprf=0.01 l2miss=73.021 l2hwprf=531.10 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=1337 s2: lat=7.6911 cyc=21.146 mem_rd=1015.12 l1miss=1001.63 l1hwprf=0.03 l2miss=117.274 l2hwprf=723.72 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=1337 s3: lat=7.4960 cyc=20.607 mem_rd=1014.81 l1miss=1001.56 l1hwprf=0.03 l2miss=132.207 l2hwprf=879.30 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=1337 s4: lat=7.9617 cyc=21.908 mem_rd=1009.12 l1miss=1000.58 l1hwprf=0.02 l2miss=130.458 l2hwprf=900.86 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=1337 s5: lat=7.5750 cyc=20.815 mem_rd=1014.37 l1miss=1001.46 l1hwprf=0.01 l2miss=135.145 l2hwprf=896.96 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=1337 s6: lat=8.0576 cyc=22.146 mem_rd=1016.82 l1miss=1001.74 l1hwprf=0.01 l2miss=141.017 l2hwprf=960.91 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=1337 s7: lat=7.4960 cyc=20.635 mem_rd=1009.42 l1miss=1000.59 l1hwprf=0.02 l2miss=128.126 l2hwprf=966.78 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=1337 s8: lat=7.8422 cyc=21.558 mem_rd=1015.55 l1miss=1001.65 l1hwprf=0.02 l2miss=129.921 l2hwprf=856.65 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=1337 s9: lat=7.4173 cyc=20.412 mem_rd=1009.30 l1miss=1000.58 l1hwprf=0.01 l2miss=122.337 l2hwprf=931.74 -->
| 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base | 3072 | seed=20260928 | base | 8 | 10 | 7.785 [7.680, 7.879] | 21.352 [21.103, 21.576] | 1014.982 [1014.097, 1016.263] | 1001.518 [1001.434, 1001.594] | 0.019 [0.016, 0.031] | 141.270 [135.762, 142.158] | 911.812 [870.485, 941.800] | no |
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=20260928 s0: lat=7.9150 cyc=21.770 mem_rd=1016.48 l1miss=1001.70 l1hwprf=0.02 l2miss=136.149 l2hwprf=898.86 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=20260928 s1: lat=7.4796 cyc=20.566 mem_rd=1014.71 l1miss=1001.50 l1hwprf=0.02 l2miss=135.633 l2hwprf=907.40 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=20260928 s2: lat=7.9721 cyc=21.928 mem_rd=1018.93 l1miss=1001.57 l1hwprf=0.03 l2miss=141.472 l2hwprf=860.90 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=20260928 s3: lat=7.8201 cyc=21.505 mem_rd=1014.00 l1miss=1001.41 l1hwprf=0.02 l2miss=141.068 l2hwprf=916.64 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=20260928 s4: lat=7.7985 cyc=21.424 mem_rd=1015.61 l1miss=1001.54 l1hwprf=0.03 l2miss=143.166 l2hwprf=966.37 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=20260928 s5: lat=7.8989 cyc=21.600 mem_rd=1014.09 l1miss=1001.49 l1hwprf=0.04 l2miss=142.288 l2hwprf=916.23 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=20260928 s6: lat=7.6767 cyc=21.081 mem_rd=1015.26 l1miss=1001.60 l1hwprf=0.00 l2miss=141.767 l2hwprf=954.62 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=20260928 s7: lat=7.6894 cyc=21.170 mem_rd=1008.78 l1miss=1000.57 l1hwprf=0.01 l2miss=114.939 l2hwprf=861.03 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=20260928 s8: lat=7.7720 cyc=21.279 mem_rd=1031.15 l1miss=1003.26 l1hwprf=0.06 l2miss=146.993 l2hwprf=950.19 -->
<!-- sample 20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base b3072K seed=20260928 s9: lat=6.8253 cyc=18.783 mem_rd=1014.13 l1miss=1001.35 l1hwprf=0.02 l2miss=76.909 l2hwprf=579.73 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 448 | seed=7 | base | 512 | 10 | 1.925 [1.913, 1.948] | 5.281 [5.253, 5.349] | 1003.134 [1002.306, 1003.612] | 73.136 [72.174, 74.267] | 928.851 [928.282, 929.362] | 0.456 [0.324, 0.654] | 303.496 [302.858, 304.158] | no |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=7 s0: lat=1.9121 cyc=5.251 mem_rd=1002.32 l1miss=72.62 l1hwprf=928.88 l2miss=0.302 l2hwprf=303.56 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=7 s1: lat=1.9154 cyc=5.259 mem_rd=1002.30 l1miss=72.85 l1hwprf=928.82 l2miss=0.392 l2hwprf=303.43 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=7 s2: lat=1.9257 cyc=5.283 mem_rd=1005.17 l1miss=73.55 l1hwprf=928.33 l2miss=0.914 l2hwprf=303.43 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=7 s3: lat=1.9488 cyc=5.350 mem_rd=1003.69 l1miss=74.51 l1hwprf=929.65 l2miss=0.692 l2hwprf=305.77 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=7 s4: lat=1.9042 cyc=5.231 mem_rd=1001.67 l1miss=71.56 l1hwprf=929.40 l2miss=0.222 l2hwprf=304.00 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=7 s5: lat=1.9238 cyc=5.278 mem_rd=1003.36 l1miss=73.42 l1hwprf=928.26 l2miss=0.507 l2hwprf=302.67 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=7 s6: lat=2.0873 cyc=5.731 mem_rd=1004.51 l1miss=149.86 l1hwprf=844.87 l2miss=0.849 l2hwprf=282.11 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=7 s7: lat=1.9479 cyc=5.350 mem_rd=1002.25 l1miss=85.39 l1hwprf=919.93 l2miss=0.405 l2hwprf=300.50 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=7 s8: lat=1.9475 cyc=5.348 mem_rd=1002.91 l1miss=71.98 l1hwprf=933.33 l2miss=0.541 l2hwprf=307.35 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=7 s9: lat=1.9088 cyc=5.242 mem_rd=1003.37 l1miss=72.02 l1hwprf=929.25 l2miss=0.253 l2hwprf=304.21 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 448 | seed=42 | base | 512 | 10 | 1.923 [1.911, 1.946] | 5.280 [5.248, 5.337] | 1003.397 [1002.464, 1003.743] | 72.072 [71.418, 75.103] | 929.696 [928.279, 929.973] | 0.562 [0.413, 0.695] | 301.916 [301.440, 302.873] | no |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=42 s0: lat=1.9139 cyc=5.257 mem_rd=1002.92 l1miss=72.32 l1hwprf=929.59 l2miss=0.418 l2hwprf=301.37 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=42 s1: lat=1.9478 cyc=5.338 mem_rd=1003.75 l1miss=77.39 l1hwprf=925.03 l2miss=0.776 l2hwprf=300.98 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=42 s2: lat=1.9568 cyc=5.371 mem_rd=1003.59 l1miss=71.31 l1hwprf=934.10 l2miss=0.784 l2hwprf=306.30 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=42 s3: lat=1.9106 cyc=5.247 mem_rd=1002.30 l1miss=72.22 l1hwprf=929.81 l2miss=0.476 l2hwprf=301.90 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=42 s4: lat=1.9531 cyc=5.363 mem_rd=1003.72 l1miss=71.28 l1hwprf=934.16 l2miss=0.658 l2hwprf=306.72 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=42 s5: lat=1.9084 cyc=5.241 mem_rd=1002.31 l1miss=71.93 l1hwprf=929.80 l2miss=0.395 l2hwprf=301.93 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=42 s6: lat=1.9124 cyc=5.251 mem_rd=1003.84 l1miss=71.73 l1hwprf=929.47 l2miss=0.647 l2hwprf=302.26 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=42 s7: lat=1.9315 cyc=5.302 mem_rd=1004.21 l1miss=87.42 l1hwprf=913.82 l2miss=0.708 l2hwprf=303.08 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=42 s8: lat=1.9078 cyc=5.236 mem_rd=1002.31 l1miss=71.02 l1hwprf=930.03 l2miss=0.384 l2hwprf=301.64 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=42 s9: lat=1.9426 cyc=5.335 mem_rd=1003.20 l1miss=76.03 l1hwprf=927.88 l2miss=0.412 l2hwprf=300.67 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 448 | seed=1337 | base | 512 | 10 | 1.939 [1.909, 1.945] | 5.326 [5.242, 5.339] | 1002.837 [1002.427, 1003.471] | 71.501 [71.238, 72.743] | 929.957 [929.627, 934.146] | 0.470 [0.349, 0.710] | 302.289 [301.617, 305.135] | no |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=1337 s0: lat=1.9395 cyc=5.327 mem_rd=1003.20 l1miss=82.37 l1hwprf=922.44 l2miss=0.271 l2hwprf=298.73 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=1337 s1: lat=1.9091 cyc=5.241 mem_rd=1002.85 l1miss=71.53 l1hwprf=929.56 l2miss=0.654 l2hwprf=301.59 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=1337 s2: lat=1.9439 cyc=5.337 mem_rd=1003.56 l1miss=71.16 l1hwprf=934.17 l2miss=0.740 l2hwprf=305.32 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=1337 s3: lat=1.9538 cyc=5.360 mem_rd=1005.19 l1miss=71.47 l1hwprf=934.08 l2miss=1.101 l2hwprf=305.25 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=1337 s4: lat=1.9066 cyc=5.238 mem_rd=1001.66 l1miss=72.69 l1hwprf=929.90 l2miss=0.184 l2hwprf=302.05 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=1337 s5: lat=1.9455 cyc=5.340 mem_rd=1004.25 l1miss=71.14 l1hwprf=934.26 l2miss=0.729 l2hwprf=305.34 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=1337 s6: lat=1.9392 cyc=5.325 mem_rd=1002.83 l1miss=70.40 l1hwprf=934.39 l2miss=0.372 l2hwprf=304.78 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=1337 s7: lat=1.9061 cyc=5.234 mem_rd=1002.30 l1miss=71.46 l1hwprf=930.01 l2miss=0.341 l2hwprf=301.70 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=1337 s8: lat=2.0635 cyc=5.666 mem_rd=1002.82 l1miss=148.28 l1hwprf=857.75 l2miss=0.504 l2hwprf=286.09 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=1337 s9: lat=1.9097 cyc=5.244 mem_rd=1002.29 l1miss=72.76 l1hwprf=929.83 l2miss=0.436 l2hwprf=302.53 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 448 | seed=20260928 | base | 512 | 10 | 1.918 [1.911, 1.929] | 5.262 [5.246, 5.297] | 1003.125 [1002.805, 1003.578] | 72.604 [71.585, 75.059] | 929.208 [927.564, 929.806] | 0.536 [0.416, 0.646] | 302.189 [301.580, 302.668] | no |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=20260928 s0: lat=1.9731 cyc=5.419 mem_rd=1002.83 l1miss=100.44 l1hwprf=904.94 l2miss=0.390 l2hwprf=297.53 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=20260928 s1: lat=1.9360 cyc=5.315 mem_rd=1003.56 l1miss=75.70 l1hwprf=925.63 l2miss=0.683 l2hwprf=302.65 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=20260928 s2: lat=1.9239 cyc=5.278 mem_rd=1003.58 l1miss=76.32 l1hwprf=927.11 l2miss=0.671 l2hwprf=301.16 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=20260928 s3: lat=1.8983 cyc=5.215 mem_rd=1002.01 l1miss=70.14 l1hwprf=930.19 l2miss=0.158 l2hwprf=301.80 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=20260928 s4: lat=1.9140 cyc=5.256 mem_rd=1004.18 l1miss=72.48 l1hwprf=929.48 l2miss=0.572 l2hwprf=302.58 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=20260928 s5: lat=1.9085 cyc=5.241 mem_rd=1002.73 l1miss=71.94 l1hwprf=929.92 l2miss=0.537 l2hwprf=302.79 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=20260928 s6: lat=1.9311 cyc=5.304 mem_rd=1003.24 l1miss=69.19 l1hwprf=934.16 l2miss=0.385 l2hwprf=304.93 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=20260928 s7: lat=1.9227 cyc=5.268 mem_rd=1005.44 l1miss=72.72 l1hwprf=929.46 l2miss=0.908 l2hwprf=302.67 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=20260928 s8: lat=1.9130 cyc=5.253 mem_rd=1002.80 l1miss=73.14 l1hwprf=928.92 l2miss=0.494 l2hwprf=301.55 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b448K seed=20260928 s9: lat=1.9101 cyc=5.244 mem_rd=1003.01 l1miss=71.47 l1hwprf=928.95 l2miss=0.535 l2hwprf=301.67 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 512 | seed=7 | base | 512 | 10 | 2.384 [2.305, 2.410] | 6.543 [6.326, 6.611] | 1003.482 [1003.249, 1004.137] | 239.349 [206.855, 251.201] | 762.077 [749.669, 794.676] | 0.625 [0.533, 0.736] | 265.361 [261.593, 273.621] | no |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=7 s0: lat=2.3822 cyc=6.539 mem_rd=1004.42 l1miss=238.23 l1hwprf=763.25 l2miss=0.841 l2hwprf=266.03 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=7 s1: lat=2.4075 cyc=6.612 mem_rd=1003.37 l1miss=251.61 l1hwprf=749.14 l2miss=0.515 l2hwprf=261.45 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=7 s2: lat=2.1274 cyc=5.842 mem_rd=1002.02 l1miss=123.11 l1hwprf=881.36 l2miss=0.360 l2hwprf=294.39 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=7 s3: lat=2.3653 cyc=6.495 mem_rd=1003.41 l1miss=233.16 l1hwprf=767.90 l2miss=0.587 l2hwprf=267.11 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=7 s4: lat=2.3863 cyc=6.547 mem_rd=1004.27 l1miss=240.46 l1hwprf=760.91 l2miss=0.719 l2hwprf=264.70 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=7 s5: lat=2.4144 cyc=6.629 mem_rd=1003.21 l1miss=254.31 l1hwprf=746.75 l2miss=0.631 l2hwprf=260.72 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=7 s6: lat=2.4126 cyc=6.620 mem_rd=1002.76 l1miss=253.02 l1hwprf=747.65 l2miss=0.619 l2hwprf=260.87 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=7 s7: lat=2.2853 cyc=6.270 mem_rd=1003.74 l1miss=198.09 l1hwprf=803.60 l2miss=0.774 l2hwprf=275.79 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=7 s8: lat=2.4108 cyc=6.609 mem_rd=1004.40 l1miss=249.98 l1hwprf=751.27 l2miss=0.741 l2hwprf=262.03 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=7 s9: lat=2.2629 cyc=6.211 mem_rd=1003.56 l1miss=188.94 l1hwprf=812.62 l2miss=0.502 l2hwprf=278.22 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 512 | seed=42 | base | 512 | 10 | 2.411 [2.309, 2.441] | 6.619 [6.338, 6.696] | 1003.280 [1002.472, 1004.746] | 250.100 [203.885, 255.984] | 750.542 [745.113, 797.555] | 0.565 [0.414, 0.711] | 261.340 [258.879, 278.270] | no |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=42 s0: lat=2.4439 cyc=6.703 mem_rd=1006.98 l1miss=255.98 l1hwprf=745.21 l2miss=0.910 l2hwprf=258.83 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=42 s1: lat=2.4328 cyc=6.675 mem_rd=1004.77 l1miss=255.98 l1hwprf=745.08 l2miss=0.655 l2hwprf=258.35 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=42 s2: lat=2.7849 cyc=7.633 mem_rd=1006.51 l1miss=367.38 l1hwprf=625.00 l2miss=5.493 l2hwprf=281.49 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=42 s3: lat=2.4825 cyc=6.815 mem_rd=1003.72 l1miss=279.02 l1hwprf=737.71 l2miss=0.664 l2hwprf=255.57 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=42 s4: lat=2.3972 cyc=6.582 mem_rd=1002.54 l1miss=244.70 l1hwprf=756.04 l2miss=0.397 l2hwprf=261.58 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=42 s5: lat=2.4218 cyc=6.648 mem_rd=1002.84 l1miss=254.03 l1hwprf=746.64 l2miss=0.475 l2hwprf=259.04 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=42 s6: lat=2.2153 cyc=6.083 mem_rd=1002.07 l1miss=165.88 l1hwprf=835.95 l2miss=0.405 l2hwprf=281.93 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=42 s7: lat=2.2414 cyc=6.154 mem_rd=1002.45 l1miss=177.30 l1hwprf=824.00 l2miss=0.443 l2hwprf=278.89 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=42 s8: lat=2.2791 cyc=6.256 mem_rd=1004.66 l1miss=190.28 l1hwprf=811.39 l2miss=0.726 l2hwprf=276.41 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=42 s9: lat=2.3999 cyc=6.590 mem_rd=1002.36 l1miss=246.17 l1hwprf=754.45 l2miss=0.230 l2hwprf=261.10 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 512 | seed=1337 | base | 512 | 10 | 2.412 [2.391, 2.421] | 6.622 [6.565, 6.640] | 1003.279 [1003.012, 1003.766] | 250.565 [243.354, 253.735] | 752.120 [747.158, 757.490] | 0.549 [0.542, 0.568] | 262.047 [260.605, 263.314] | no |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=1337 s0: lat=2.2704 cyc=6.232 mem_rd=1005.92 l1miss=189.11 l1hwprf=812.88 l2miss=0.666 l2hwprf=277.21 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=1337 s1: lat=2.4215 cyc=6.648 mem_rd=1003.27 l1miss=255.59 l1hwprf=745.33 l2miss=0.551 l2hwprf=259.95 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=1337 s2: lat=2.4180 cyc=6.640 mem_rd=1003.28 l1miss=254.14 l1hwprf=746.77 l2miss=0.547 l2hwprf=260.94 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=1337 s3: lat=2.6604 cyc=7.303 mem_rd=1003.09 l1miss=360.20 l1hwprf=631.90 l2miss=0.541 l2hwprf=216.44 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=1337 s4: lat=2.4241 cyc=6.639 mem_rd=1006.04 l1miss=250.55 l1hwprf=753.86 l2miss=0.926 l2hwprf=262.46 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=1337 s5: lat=2.4128 cyc=6.624 mem_rd=1002.99 l1miss=252.52 l1hwprf=748.33 l2miss=0.547 l2hwprf=260.49 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=1337 s6: lat=2.4121 cyc=6.620 mem_rd=1003.89 l1miss=250.58 l1hwprf=750.38 l2miss=0.570 l2hwprf=261.64 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=1337 s7: lat=2.3899 cyc=6.561 mem_rd=1002.46 l1miss=242.88 l1hwprf=757.94 l2miss=0.540 l2hwprf=263.44 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=1337 s8: lat=2.3953 cyc=6.577 mem_rd=1003.38 l1miss=244.77 l1hwprf=756.13 l2miss=0.563 l2hwprf=262.94 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=1337 s9: lat=2.2149 cyc=6.081 mem_rd=1002.06 l1miss=167.72 l1hwprf=834.05 l2miss=0.405 l2hwprf=282.97 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 512 | seed=20260928 | base | 512 | 10 | 2.419 [2.393, 2.425] | 6.640 [6.569, 6.652] | 1003.796 [1003.136, 1004.230] | 251.981 [241.569, 253.605] | 749.348 [747.778, 760.094] | 0.540 [0.466, 0.699] | 259.735 [259.547, 262.852] | no |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=20260928 s0: lat=2.4261 cyc=6.659 mem_rd=1004.19 l1miss=255.41 l1hwprf=746.51 l2miss=0.498 l2hwprf=258.65 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=20260928 s1: lat=2.4163 cyc=6.632 mem_rd=1004.24 l1miss=250.72 l1hwprf=750.76 l2miss=0.733 l2hwprf=260.11 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=20260928 s2: lat=2.4124 cyc=6.623 mem_rd=1001.97 l1miss=251.67 l1hwprf=749.62 l2miss=0.328 l2hwprf=259.70 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=20260928 s3: lat=2.3864 cyc=6.551 mem_rd=1003.49 l1miss=238.52 l1hwprf=763.21 l2miss=0.622 l2hwprf=263.76 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=20260928 s4: lat=2.4231 cyc=6.649 mem_rd=1003.02 l1miss=253.02 l1hwprf=748.66 l2miss=0.472 l2hwprf=259.52 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=20260928 s5: lat=2.4217 cyc=6.647 mem_rd=1002.59 l1miss=253.92 l1hwprf=747.48 l2miss=0.366 l2hwprf=259.36 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=20260928 s6: lat=2.4273 cyc=6.654 mem_rd=1003.77 l1miss=253.80 l1hwprf=747.32 l2miss=0.583 l2hwprf=259.61 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=20260928 s7: lat=2.1820 cyc=5.990 mem_rd=1003.82 l1miss=147.21 l1hwprf=856.47 l2miss=0.724 l2hwprf=285.73 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=20260928 s8: lat=2.4256 cyc=6.654 mem_rd=1005.62 l1miss=252.29 l1hwprf=749.07 l2miss=0.909 l2hwprf=259.77 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b512K seed=20260928 s9: lat=2.2983 cyc=6.307 mem_rd=1005.04 l1miss=200.52 l1hwprf=801.70 l2miss=0.465 l2hwprf=273.58 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 544 | seed=7 | base | 512 | 10 | 3.368 [3.053, 3.409] | 9.244 [8.381, 9.352] | 1004.136 [1003.258, 1005.940] | 601.018 [478.723, 610.225] | 400.565 [394.667, 532.964] | 0.484 [0.405, 0.689] | 170.384 [147.959, 199.927] | no |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=7 s0: lat=3.4164 cyc=9.373 mem_rd=1006.83 l1miss=616.06 l1hwprf=385.00 l2miss=0.650 l2hwprf=144.88 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=7 s1: lat=3.0433 cyc=8.354 mem_rd=1004.40 l1miss=474.72 l1hwprf=537.52 l2miss=0.375 l2hwprf=195.53 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=7 s2: lat=2.9189 cyc=8.010 mem_rd=1005.98 l1miss=424.49 l1hwprf=590.94 l2miss=0.744 l2hwprf=213.30 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=7 s3: lat=3.3865 cyc=9.290 mem_rd=1003.26 l1miss=606.29 l1hwprf=394.26 l2miss=0.481 l2hwprf=147.81 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=7 s4: lat=3.4172 cyc=9.379 mem_rd=1005.82 l1miss=616.97 l1hwprf=383.90 l2miss=0.702 l2hwprf=144.34 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=7 s5: lat=3.3775 cyc=9.272 mem_rd=1003.87 l1miss=604.75 l1hwprf=395.87 l2miss=0.404 l2hwprf=148.41 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=7 s6: lat=3.0838 cyc=8.464 mem_rd=1002.87 l1miss=490.74 l1hwprf=519.30 l2miss=0.410 l2hwprf=189.20 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=7 s7: lat=3.6001 cyc=9.881 mem_rd=1007.12 l1miss=611.54 l1hwprf=396.06 l2miss=12.268 l2hwprf=588.94 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=7 s8: lat=3.0008 cyc=8.237 mem_rd=1003.26 l1miss=457.83 l1hwprf=554.64 l2miss=0.488 l2hwprf=201.39 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=7 s9: lat=3.3577 cyc=9.217 mem_rd=1003.03 l1miss=597.29 l1hwprf=405.07 l2miss=0.343 l2hwprf=151.57 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 544 | seed=42 | base | 512 | 10 | 3.116 [2.948, 3.230] | 8.553 [8.086, 8.863] | 1004.459 [1003.242, 1004.936] | 499.289 [432.528, 541.517] | 509.284 [472.784, 575.276] | 0.594 [0.504, 0.711] | 185.671 [173.765, 206.319] | no |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=42 s0: lat=3.0684 cyc=8.421 mem_rd=1004.51 l1miss=480.60 l1hwprf=526.17 l2miss=0.479 l2hwprf=190.02 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=42 s1: lat=3.0223 cyc=8.294 mem_rd=1002.99 l1miss=461.65 l1hwprf=540.27 l2miss=0.507 l2hwprf=196.27 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=42 s2: lat=3.3956 cyc=9.321 mem_rd=1005.86 l1miss=603.79 l1hwprf=402.76 l2miss=0.942 l2hwprf=150.33 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=42 s3: lat=3.2125 cyc=8.816 mem_rd=1004.63 l1miss=534.45 l1hwprf=481.11 l2miss=0.687 l2hwprf=177.09 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=42 s4: lat=3.1644 cyc=8.685 mem_rd=1004.00 l1miss=517.98 l1hwprf=492.40 l2miss=0.639 l2hwprf=181.32 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=42 s5: lat=3.2363 cyc=8.878 mem_rd=1005.04 l1miss=543.87 l1hwprf=470.01 l2miss=0.719 l2hwprf=172.66 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=42 s6: lat=2.9236 cyc=8.017 mem_rd=1002.80 l1miss=422.82 l1hwprf=586.95 l2miss=0.460 l2hwprf=209.67 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=42 s7: lat=2.8064 cyc=7.703 mem_rd=1004.41 l1miss=376.07 l1hwprf=651.28 l2miss=0.724 l2hwprf=232.17 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=42 s8: lat=2.8219 cyc=7.744 mem_rd=1002.84 l1miss=383.29 l1hwprf=618.17 l2miss=0.548 l2hwprf=220.56 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=42 s9: lat=3.2377 cyc=8.885 mem_rd=1005.27 l1miss=545.52 l1hwprf=468.23 l2miss=0.504 l2hwprf=172.34 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 544 | seed=1337 | base | 512 | 10 | 3.301 [3.078, 3.364] | 9.061 [8.450, 9.233] | 1003.739 [1003.352, 1004.530] | 568.882 [481.191, 591.343] | 442.293 [419.835, 530.884] | 0.534 [0.345, 0.671] | 164.868 [157.064, 193.035] | no |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=1337 s0: lat=3.0297 cyc=8.317 mem_rd=1003.55 l1miss=462.65 l1hwprf=547.38 l2miss=0.296 l2hwprf=198.20 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=1337 s1: lat=3.2805 cyc=9.005 mem_rd=1003.81 l1miss=560.95 l1hwprf=449.88 l2miss=0.464 l2hwprf=167.42 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=1337 s2: lat=2.9572 cyc=8.116 mem_rd=1002.87 l1miss=435.61 l1hwprf=577.13 l2miss=0.451 l2hwprf=208.24 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=1337 s3: lat=3.3716 cyc=9.254 mem_rd=1005.45 l1miss=593.17 l1hwprf=418.42 l2miss=1.016 l2hwprf=156.75 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=1337 s4: lat=3.3403 cyc=9.171 mem_rd=1003.18 l1miss=585.88 l1hwprf=424.09 l2miss=0.309 l2hwprf=158.00 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=1337 s5: lat=3.3794 cyc=9.276 mem_rd=1003.29 l1miss=599.37 l1hwprf=406.67 l2miss=0.307 l2hwprf=152.39 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=1337 s6: lat=2.9774 cyc=8.173 mem_rd=1003.66 l1miss=443.37 l1hwprf=567.63 l2miss=0.603 l2hwprf=205.06 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=1337 s7: lat=3.2237 cyc=8.847 mem_rd=1004.53 l1miss=536.82 l1hwprf=481.41 l2miss=0.692 l2hwprf=177.54 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=1337 s8: lat=3.4150 cyc=9.371 mem_rd=1006.03 l1miss=610.31 l1hwprf=392.86 l2miss=0.786 l2hwprf=147.38 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=1337 s9: lat=3.3214 cyc=9.118 mem_rd=1004.52 l1miss=576.82 l1hwprf=434.71 l2miss=0.605 l2hwprf=162.31 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 544 | seed=20260928 | base | 512 | 10 | 3.229 [3.137, 3.280] | 8.861 [8.613, 9.002] | 1003.961 [1003.379, 1004.521] | 538.391 [505.782, 558.767] | 472.131 [453.306, 514.010] | 0.557 [0.515, 0.607] | 173.452 [166.921, 186.972] | no |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=20260928 s0: lat=2.9059 cyc=7.964 mem_rd=1005.90 l1miss=412.32 l1hwprf=589.87 l2miss=0.563 l2hwprf=210.97 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=20260928 s1: lat=3.2206 cyc=8.838 mem_rd=1003.27 l1miss=535.27 l1hwprf=465.25 l2miss=0.621 l2hwprf=171.45 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=20260928 s2: lat=3.2910 cyc=9.033 mem_rd=1003.80 l1miss=563.50 l1hwprf=449.32 l2miss=0.415 l2hwprf=165.41 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=20260928 s3: lat=3.0775 cyc=8.447 mem_rd=1006.26 l1miss=478.91 l1hwprf=535.34 l2miss=0.911 l2hwprf=193.56 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=20260928 s4: lat=3.3159 cyc=9.102 mem_rd=1003.72 l1miss=571.76 l1hwprf=442.00 l2miss=0.539 l2hwprf=163.36 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=20260928 s5: lat=3.2453 cyc=8.908 mem_rd=1004.65 l1miss=544.56 l1hwprf=470.32 l2miss=0.661 l2hwprf=172.39 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=20260928 s6: lat=3.5489 cyc=9.741 mem_rd=1004.12 l1miss=659.70 l1hwprf=322.10 l2miss=0.551 l2hwprf=113.13 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=20260928 s7: lat=3.1304 cyc=8.594 mem_rd=1002.86 l1miss=503.19 l1hwprf=517.88 l2miss=0.334 l2hwprf=188.30 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=20260928 s8: lat=3.1584 cyc=8.671 mem_rd=1002.94 l1miss=513.56 l1hwprf=502.41 l2miss=0.507 l2hwprf=182.99 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b544K seed=20260928 s9: lat=3.2375 cyc=8.883 mem_rd=1004.13 l1miss=541.51 l1hwprf=473.94 l2miss=0.565 l2hwprf=174.51 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 576 | seed=7 | base | 512 | 10 | 3.674 [3.600, 3.730] | 10.083 [9.880, 10.234] | 1005.805 [1003.848, 1006.706] | 685.404 [656.951, 689.312] | 306.255 [302.382, 339.410] | 0.745 [0.595, 0.949] | 116.568 [114.246, 141.439] | no |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=7 s0: lat=4.3334 cyc=11.896 mem_rd=1003.70 l1miss=930.33 l1hwprf=43.85 l2miss=0.279 l2hwprf=15.57 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=7 s1: lat=3.4684 cyc=9.520 mem_rd=1003.12 l1miss=611.43 l1hwprf=389.98 l2miss=0.586 l2hwprf=145.08 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=7 s2: lat=3.6899 cyc=10.115 mem_rd=1006.79 l1miss=688.24 l1hwprf=303.70 l2miss=0.935 l2hwprf=114.17 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=7 s3: lat=3.6738 cyc=10.081 mem_rd=1004.30 l1miss=682.83 l1hwprf=309.26 l2miss=1.190 l2hwprf=117.65 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=7 s4: lat=3.6697 cyc=10.073 mem_rd=1005.25 l1miss=684.18 l1hwprf=307.70 l2miss=0.622 l2hwprf=115.49 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=7 s5: lat=3.8218 cyc=10.488 mem_rd=1006.44 l1miss=689.67 l1hwprf=301.94 l2miss=9.058 l2hwprf=229.64 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=7 s6: lat=3.4833 cyc=9.555 mem_rd=1006.89 l1miss=613.11 l1hwprf=389.43 l2miss=0.836 l2hwprf=145.15 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=7 s7: lat=3.6740 cyc=10.085 mem_rd=1003.61 l1miss=686.63 l1hwprf=304.81 l2miss=0.654 l2hwprf=114.47 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=7 s8: lat=3.5771 cyc=9.816 mem_rd=1006.93 l1miss=648.33 l1hwprf=349.46 l2miss=0.954 l2hwprf=130.51 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=7 s9: lat=3.7430 cyc=10.274 mem_rd=1006.36 l1miss=711.04 l1hwprf=282.95 l2miss=0.582 l2hwprf=106.37 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 576 | seed=42 | base | 512 | 10 | 3.702 [3.666, 3.710] | 10.161 [10.060, 10.182] | 1005.574 [1004.180, 1005.862] | 688.007 [674.383, 690.970] | 304.482 [300.912, 319.306] | 0.755 [0.665, 0.820] | 114.454 [113.114, 119.854] | no |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=42 s0: lat=3.7063 cyc=10.175 mem_rd=1003.91 l1miss=690.81 l1hwprf=301.27 l2miss=0.454 l2hwprf=113.11 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=42 s1: lat=3.4779 cyc=9.536 mem_rd=1007.41 l1miss=602.24 l1hwprf=402.07 l2miss=1.078 l2hwprf=149.80 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=42 s2: lat=3.7111 cyc=10.184 mem_rd=1005.88 l1miss=690.23 l1hwprf=302.35 l2miss=0.827 l2hwprf=113.81 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=42 s3: lat=3.6985 cyc=10.147 mem_rd=1005.75 l1miss=685.78 l1hwprf=306.61 l2miss=0.798 l2hwprf=115.10 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=42 s4: lat=3.7193 cyc=10.200 mem_rd=1007.00 l1miss=691.70 l1hwprf=300.69 l2miss=0.905 l2hwprf=112.85 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=42 s5: lat=3.6573 cyc=10.033 mem_rd=1004.98 l1miss=670.83 l1hwprf=323.40 l2miss=0.739 l2hwprf=121.21 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=42 s6: lat=3.5928 cyc=9.859 mem_rd=1005.81 l1miss=647.82 l1hwprf=356.31 l2miss=0.772 l2hwprf=133.39 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=42 s7: lat=3.7719 cyc=10.355 mem_rd=1005.40 l1miss=713.80 l1hwprf=279.92 l2miss=0.641 l2hwprf=105.72 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=42 s8: lat=3.6940 cyc=10.140 mem_rd=1003.13 l1miss=685.04 l1hwprf=307.01 l2miss=0.737 l2hwprf=115.80 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=42 s9: lat=3.7068 cyc=10.176 mem_rd=1003.35 l1miss=691.02 l1hwprf=300.79 l2miss=0.547 l2hwprf=113.12 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 576 | seed=1337 | base | 512 | 10 | 3.683 [3.678, 3.802] | 10.108 [10.094, 10.436] | 1005.260 [1004.651, 1006.206] | 691.091 [689.835, 737.800] | 300.271 [249.548, 301.233] | 0.726 [0.628, 0.934] | 113.046 [94.011, 113.989] | no |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=1337 s0: lat=3.7761 cyc=10.361 mem_rd=1006.39 l1miss=727.24 l1hwprf=267.01 l2miss=0.626 l2hwprf=101.01 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=1337 s1: lat=4.0307 cyc=11.061 mem_rd=1005.93 l1miss=820.28 l1hwprf=156.20 l2miss=0.676 l2hwprf=58.52 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=1337 s2: lat=3.6807 cyc=10.102 mem_rd=1005.05 l1miss=690.96 l1hwprf=300.41 l2miss=0.776 l2hwprf=112.93 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=1337 s3: lat=4.3331 cyc=11.893 mem_rd=1004.09 l1miss=935.60 l1hwprf=30.66 l2miss=0.502 l2hwprf=10.45 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=1337 s4: lat=3.8110 cyc=10.461 mem_rd=1005.19 l1miss=741.32 l1hwprf=243.73 l2miss=0.500 l2hwprf=91.68 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=1337 s5: lat=3.6755 cyc=10.089 mem_rd=1003.48 l1miss=689.97 l1hwprf=301.09 l2miss=0.634 l2hwprf=113.38 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=1337 s6: lat=3.6855 cyc=10.114 mem_rd=1006.30 l1miss=691.22 l1hwprf=300.14 l2miss=0.952 l2hwprf=113.16 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=1337 s7: lat=3.6798 cyc=10.100 mem_rd=1005.33 l1miss=689.79 l1hwprf=301.28 l2miss=0.935 l2hwprf=114.19 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=1337 s8: lat=3.6771 cyc=10.091 mem_rd=1006.65 l1miss=687.88 l1hwprf=303.64 l2miss=1.019 l2hwprf=115.09 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=1337 s9: lat=3.6739 cyc=10.084 mem_rd=1004.52 l1miss=687.62 l1hwprf=303.58 l2miss=0.931 l2hwprf=115.25 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 576 | seed=20260928 | base | 512 | 10 | 3.689 [3.686, 3.709] | 10.127 [10.118, 10.172] | 1003.572 [1003.187, 1005.201] | 689.877 [643.830, 693.913] | 301.677 [297.787, 355.764] | 0.639 [0.599, 0.862] | 113.860 [112.454, 133.412] | no |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=20260928 s0: lat=4.2827 cyc=11.755 mem_rd=1007.27 l1miss=907.67 l1hwprf=69.11 l2miss=0.928 l2hwprf=25.43 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=20260928 s1: lat=3.6900 cyc=10.130 mem_rd=1003.09 l1miss=690.41 l1hwprf=300.75 l2miss=0.615 l2hwprf=113.25 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=20260928 s2: lat=3.6871 cyc=10.122 mem_rd=1002.72 l1miss=688.91 l1hwprf=302.30 l2miss=0.602 l2hwprf=114.16 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=20260928 s3: lat=3.4885 cyc=9.577 mem_rd=1003.07 l1miss=614.55 l1hwprf=387.05 l2miss=0.665 l2hwprf=144.94 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=20260928 s4: lat=3.7221 cyc=10.217 mem_rd=1003.61 l1miss=702.88 l1hwprf=289.24 l2miss=0.598 l2hwprf=108.69 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=20260928 s5: lat=3.6882 cyc=10.125 mem_rd=1003.53 l1miss=614.47 l1hwprf=387.02 l2miss=12.710 l2hwprf=825.67 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=20260928 s6: lat=3.5237 cyc=9.673 mem_rd=1003.49 l1miss=628.80 l1hwprf=373.59 l2miss=0.529 l2hwprf=139.83 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=20260928 s7: lat=3.6951 cyc=10.142 mem_rd=1005.70 l1miss=691.04 l1hwprf=301.08 l2miss=0.664 l2hwprf=113.98 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=20260928 s8: lat=3.6852 cyc=10.117 mem_rd=1003.70 l1miss=689.35 l1hwprf=302.27 l2miss=0.422 l2hwprf=113.74 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b576K seed=20260928 s9: lat=3.7131 cyc=10.182 mem_rd=1006.84 l1miss=694.87 l1hwprf=296.80 l2miss=0.935 l2hwprf=112.19 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 608 | seed=7 | base | 512 | 10 | 4.183 [4.145, 4.226] | 11.480 [11.370, 11.591] | 1005.500 [1004.424, 1007.052] | 848.099 [833.489, 863.183] | 134.538 [123.653, 150.984] | 0.667 [0.627, 0.733] | 51.927 [47.808, 58.337] | no |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=7 s0: lat=4.2387 cyc=11.626 mem_rd=1008.42 l1miss=867.71 l1hwprf=120.41 l2miss=0.870 l2hwprf=46.56 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=7 s1: lat=4.1340 cyc=11.337 mem_rd=1007.18 l1miss=828.14 l1hwprf=157.53 l2miss=0.923 l2hwprf=60.75 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=7 s2: lat=4.4659 cyc=12.259 mem_rd=1003.76 l1miss=953.60 l1hwprf=17.43 l2miss=0.531 l2hwprf=6.45 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=7 s3: lat=4.1805 cyc=11.474 mem_rd=1004.09 l1miss=848.50 l1hwprf=134.10 l2miss=0.696 l2hwprf=51.84 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=7 s4: lat=4.1249 cyc=11.322 mem_rd=1004.39 l1miss=828.82 l1hwprf=156.14 l2miss=0.718 l2hwprf=60.29 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=7 s5: lat=4.1867 cyc=11.486 mem_rd=1007.93 l1miss=847.69 l1hwprf=135.52 l2miss=0.738 l2hwprf=52.47 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=7 s6: lat=4.4000 cyc=12.075 mem_rd=1005.86 l1miss=927.58 l1hwprf=46.31 l2miss=0.625 l2hwprf=18.12 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=7 s7: lat=4.1785 cyc=11.468 mem_rd=1004.51 l1miss=847.49 l1hwprf=134.97 l2miss=0.583 l2hwprf=52.01 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=7 s8: lat=4.1860 cyc=11.487 mem_rd=1006.68 l1miss=849.59 l1hwprf=133.40 l2miss=0.637 l2hwprf=51.56 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=7 s9: lat=4.1230 cyc=11.311 mem_rd=1005.14 l1miss=826.76 l1hwprf=158.68 l2miss=0.631 l2hwprf=61.15 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 608 | seed=42 | base | 512 | 10 | 4.182 [4.170, 4.195] | 11.480 [11.446, 11.510] | 1005.135 [1003.852, 1006.753] | 847.635 [842.545, 848.612] | 134.615 [133.438, 140.299] | 0.673 [0.566, 0.755] | 52.244 [51.634, 54.168] | no |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=42 s0: lat=4.1386 cyc=11.361 mem_rd=1005.05 l1miss=831.75 l1hwprf=153.69 l2miss=0.443 l2hwprf=59.32 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=42 s1: lat=4.1845 cyc=11.487 mem_rd=1003.67 l1miss=848.48 l1hwprf=133.26 l2miss=0.663 l2hwprf=51.56 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=42 s2: lat=4.1472 cyc=11.376 mem_rd=1007.37 l1miss=831.28 l1hwprf=153.25 l2miss=0.960 l2hwprf=59.24 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=42 s3: lat=4.1938 cyc=11.501 mem_rd=1007.07 l1miss=848.63 l1hwprf=133.98 l2miss=0.752 l2hwprf=51.84 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=42 s4: lat=4.1691 cyc=11.444 mem_rd=1003.77 l1miss=843.54 l1hwprf=138.89 l2miss=0.588 l2hwprf=53.62 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=42 s5: lat=4.1960 cyc=11.512 mem_rd=1007.85 l1miss=848.56 l1hwprf=134.22 l2miss=1.067 l2hwprf=52.52 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=42 s6: lat=4.4505 cyc=12.216 mem_rd=1003.80 l1miss=947.09 l1hwprf=24.27 l2miss=0.529 l2hwprf=9.19 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=42 s7: lat=4.4064 cyc=12.083 mem_rd=1005.22 l1miss=927.05 l1hwprf=46.60 l2miss=0.683 l2hwprf=17.80 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=42 s8: lat=4.1732 cyc=11.452 mem_rd=1005.81 l1miss=842.22 l1hwprf=140.77 l2miss=0.756 l2hwprf=54.35 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=42 s9: lat=4.1798 cyc=11.473 mem_rd=1004.02 l1miss=846.79 l1hwprf=135.01 l2miss=0.559 l2hwprf=51.97 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 608 | seed=1337 | base | 512 | 10 | 4.188 [4.177, 4.389] | 11.490 [11.463, 12.048] | 1004.977 [1004.407, 1005.409] | 848.164 [846.935, 912.441] | 134.334 [64.547, 135.897] | 0.666 [0.550, 0.871] | 52.911 [51.743, 57.098] | YES |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=1337 s0: lat=4.3642 cyc=11.981 mem_rd=1004.13 l1miss=867.73 l1hwprf=119.79 l2miss=9.831 l2hwprf=173.76 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=1337 s1: lat=4.1902 cyc=11.491 mem_rd=1008.12 l1miss=847.26 l1hwprf=135.98 l2miss=0.926 l2hwprf=52.80 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=1337 s2: lat=4.1767 cyc=11.464 mem_rd=1005.30 l1miss=846.84 l1hwprf=135.64 l2miss=0.695 l2hwprf=52.22 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=1337 s3: lat=4.6854 cyc=12.860 mem_rd=1005.44 l1miss=967.11 l1hwprf=3.19 l2miss=11.583 l2hwprf=151.71 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=1337 s4: lat=4.1757 cyc=11.462 mem_rd=1004.66 l1miss=847.23 l1hwprf=135.31 l2miss=0.399 l2hwprf=53.02 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=1337 s5: lat=4.1783 cyc=11.461 mem_rd=1005.78 l1miss=845.40 l1hwprf=137.54 l2miss=0.705 l2hwprf=53.87 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=1337 s6: lat=4.1866 cyc=11.489 mem_rd=1005.30 l1miss=849.07 l1hwprf=133.36 l2miss=0.636 l2hwprf=51.58 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=1337 s7: lat=4.1342 cyc=11.347 mem_rd=1003.75 l1miss=832.70 l1hwprf=151.35 l2miss=0.529 l2hwprf=58.17 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=1337 s8: lat=4.5073 cyc=12.370 mem_rd=1004.48 l1miss=966.80 l1hwprf=3.25 l2miss=0.505 l2hwprf=1.37 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=1337 s9: lat=4.3972 cyc=12.070 mem_rd=1004.38 l1miss=927.34 l1hwprf=46.13 l2miss=0.612 l2hwprf=17.71 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 608 | seed=20260928 | base | 512 | 10 | 4.199 [4.190, 4.205] | 11.517 [11.496, 11.534] | 1005.444 [1004.820, 1007.005] | 847.961 [847.389, 849.652] | 134.407 [132.973, 135.428] | 0.639 [0.488, 0.751] | 51.533 [51.145, 52.046] | no |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=20260928 s0: lat=4.5373 cyc=12.453 mem_rd=1005.21 l1miss=974.87 l1hwprf=2.42 l2miss=0.486 l2hwprf=0.91 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=20260928 s1: lat=4.1879 cyc=11.495 mem_rd=1003.76 l1miss=847.29 l1hwprf=135.01 l2miss=0.559 l2hwprf=51.85 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=20260928 s2: lat=4.1269 cyc=11.325 mem_rd=1004.74 l1miss=825.05 l1hwprf=160.27 l2miss=0.474 l2hwprf=61.58 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=20260928 s3: lat=4.2055 cyc=11.535 mem_rd=1007.94 l1miss=849.16 l1hwprf=133.74 l2miss=0.751 l2hwprf=51.26 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=20260928 s4: lat=4.1300 cyc=11.330 mem_rd=1005.68 l1miss=825.62 l1hwprf=159.62 l2miss=0.453 l2hwprf=61.02 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=20260928 s5: lat=4.2061 cyc=11.539 mem_rd=1007.21 l1miss=850.16 l1hwprf=132.64 l2miss=0.801 l2hwprf=51.11 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=20260928 s6: lat=4.1943 cyc=11.500 mem_rd=1004.47 l1miss=847.96 l1hwprf=134.36 l2miss=0.492 l2hwprf=51.49 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=20260928 s7: lat=4.2053 cyc=11.530 mem_rd=1009.85 l1miss=847.96 l1hwprf=135.57 l2miss=1.094 l2hwprf=52.11 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=20260928 s8: lat=4.2043 cyc=11.530 mem_rd=1006.38 l1miss=849.82 l1hwprf=132.72 l2miss=0.751 l2hwprf=50.96 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b608K seed=20260928 s9: lat=4.1945 cyc=11.505 mem_rd=1005.06 l1miss=847.69 l1hwprf=134.45 l2miss=0.719 l2hwprf=51.57 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 640 | seed=7 | base | 512 | 10 | 4.453 [4.450, 4.464] | 12.220 [12.208, 12.244] | 1006.955 [1006.241, 1007.460] | 918.139 [915.787, 919.297] | 62.075 [61.753, 65.261] | 0.789 [0.734, 0.844] | 24.400 [24.200, 25.818] | no |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=7 s0: lat=4.4686 cyc=12.263 mem_rd=1006.15 l1miss=924.96 l1hwprf=60.84 l2miss=0.736 l2hwprf=24.07 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=7 s1: lat=4.5566 cyc=12.503 mem_rd=1006.95 l1miss=954.88 l1hwprf=21.64 l2miss=0.733 l2hwprf=8.55 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=7 s2: lat=4.4538 cyc=12.224 mem_rd=1006.51 l1miss=918.23 l1hwprf=62.14 l2miss=0.758 l2hwprf=24.36 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=7 s3: lat=4.4433 cyc=12.193 mem_rd=1007.67 l1miss=914.18 l1hwprf=67.13 l2miss=0.822 l2hwprf=26.33 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=7 s4: lat=4.4649 cyc=12.248 mem_rd=1009.60 l1miss=919.51 l1hwprf=61.67 l2miss=1.083 l2hwprf=24.35 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=7 s5: lat=4.4531 cyc=12.207 mem_rd=1007.50 l1miss=915.33 l1hwprf=65.85 l2miss=1.098 l2hwprf=26.11 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=7 s6: lat=4.4518 cyc=12.217 mem_rd=1006.96 l1miss=917.15 l1hwprf=63.48 l2miss=0.820 l2hwprf=24.94 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=7 s7: lat=4.4349 cyc=12.172 mem_rd=1004.35 l1miss=913.61 l1hwprf=67.16 l2miss=0.487 l2hwprf=26.23 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=7 s8: lat=4.4495 cyc=12.212 mem_rd=1004.55 l1miss=918.04 l1hwprf=62.01 l2miss=0.723 l2hwprf=24.15 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=7 s9: lat=4.4599 cyc=12.233 mem_rd=1007.35 l1miss=918.66 l1hwprf=62.01 l2miss=0.852 l2hwprf=24.44 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 640 | seed=42 | base | 512 | 10 | 4.440 [4.435, 4.447] | 12.186 [12.166, 12.202] | 1006.324 [1004.969, 1006.910] | 918.739 [917.754, 918.905] | 61.981 [61.641, 62.418] | 0.682 [0.593, 0.888] | 24.227 [24.041, 24.395] | no |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=42 s0: lat=4.5864 cyc=12.586 mem_rd=1008.49 l1miss=966.98 l1hwprf=14.81 l2miss=0.975 l2hwprf=6.16 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=42 s1: lat=4.4387 cyc=12.181 mem_rd=1006.34 l1miss=918.82 l1hwprf=61.72 l2miss=0.560 l2hwprf=24.03 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=42 s2: lat=4.4373 cyc=12.176 mem_rd=1004.55 l1miss=917.88 l1hwprf=62.29 l2miss=0.591 l2hwprf=24.23 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=42 s3: lat=4.4488 cyc=12.205 mem_rd=1007.64 l1miss=918.79 l1hwprf=62.07 l2miss=1.101 l2hwprf=24.41 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=42 s4: lat=4.4310 cyc=12.159 mem_rd=1007.08 l1miss=914.96 l1hwprf=66.44 l2miss=0.875 l2hwprf=25.92 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=42 s5: lat=4.5538 cyc=12.494 mem_rd=1004.87 l1miss=959.28 l1hwprf=16.31 l2miss=0.736 l2hwprf=6.51 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=42 s6: lat=4.4298 cyc=12.159 mem_rd=1005.27 l1miss=915.75 l1hwprf=65.01 l2miss=0.599 l2hwprf=25.41 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=42 s7: lat=4.4432 cyc=12.192 mem_rd=1006.31 l1miss=918.94 l1hwprf=61.62 l2miss=0.893 l2hwprf=24.23 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=42 s8: lat=4.4338 cyc=12.163 mem_rd=1003.82 l1miss=917.71 l1hwprf=62.46 l2miss=0.523 l2hwprf=24.34 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=42 s9: lat=4.4421 cyc=12.191 mem_rd=1006.39 l1miss=918.68 l1hwprf=61.90 l2miss=0.627 l2hwprf=24.07 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 640 | seed=1337 | base | 512 | 10 | 4.435 [4.433, 4.440] | 12.172 [12.166, 12.184] | 1005.632 [1004.861, 1006.328] | 917.800 [917.450, 918.373] | 62.158 [61.937, 62.771] | 0.520 [0.409, 0.658] | 24.135 [23.958, 24.233] | no |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=1337 s0: lat=4.4443 cyc=12.200 mem_rd=1004.64 l1miss=923.38 l1hwprf=62.06 l2miss=0.424 l2hwprf=23.95 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=1337 s1: lat=4.5577 cyc=12.503 mem_rd=1006.40 l1miss=960.94 l1hwprf=14.89 l2miss=0.605 l2hwprf=5.80 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=1337 s2: lat=4.4309 cyc=12.162 mem_rd=1005.62 l1miss=917.39 l1hwprf=62.84 l2miss=0.388 l2hwprf=24.24 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=1337 s3: lat=4.4169 cyc=12.123 mem_rd=1003.98 l1miss=911.46 l1hwprf=68.93 l2miss=0.529 l2hwprf=26.56 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=1337 s4: lat=4.4350 cyc=12.168 mem_rd=1006.73 l1miss=915.31 l1hwprf=65.41 l2miss=0.807 l2hwprf=25.36 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=1337 s5: lat=4.4380 cyc=12.180 mem_rd=1006.12 l1miss=918.38 l1hwprf=61.88 l2miss=0.404 l2hwprf=24.11 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=1337 s6: lat=4.4358 cyc=12.175 mem_rd=1005.53 l1miss=917.62 l1hwprf=62.57 l2miss=0.697 l2hwprf=24.21 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=1337 s7: lat=4.4323 cyc=12.165 mem_rd=1005.65 l1miss=917.82 l1hwprf=62.21 l2miss=0.329 l2hwprf=24.16 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=1337 s8: lat=4.4337 cyc=12.169 mem_rd=1004.34 l1miss=917.78 l1hwprf=62.11 l2miss=0.512 l2hwprf=23.97 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=1337 s9: lat=4.4410 cyc=12.185 mem_rd=1006.75 l1miss=918.35 l1hwprf=61.90 l2miss=0.675 l2hwprf=23.88 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 640 | seed=20260928 | base | 512 | 10 | 4.432 [4.425, 4.434] | 12.163 [12.146, 12.169] | 1006.017 [1004.075, 1007.123] | 915.364 [914.111, 917.009] | 65.641 [63.148, 66.547] | 0.596 [0.426, 0.746] | 25.498 [24.529, 25.841] | no |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=20260928 s0: lat=4.4623 cyc=12.247 mem_rd=1006.35 l1miss=928.91 l1hwprf=57.26 l2miss=0.390 l2hwprf=22.18 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=20260928 s1: lat=4.4193 cyc=12.129 mem_rd=1003.99 l1miss=912.75 l1hwprf=67.91 l2miss=0.533 l2hwprf=26.26 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=20260928 s2: lat=4.4504 cyc=12.209 mem_rd=1009.59 l1miss=919.59 l1hwprf=61.39 l2miss=0.874 l2hwprf=23.88 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=20260928 s3: lat=4.4334 cyc=12.165 mem_rd=1006.92 l1miss=915.72 l1hwprf=65.08 l2miss=0.703 l2hwprf=25.25 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=20260928 s4: lat=4.4342 cyc=12.171 mem_rd=1005.68 l1miss=916.50 l1hwprf=64.06 l2miss=0.643 l2hwprf=24.88 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=20260928 s5: lat=4.4308 cyc=12.160 mem_rd=1007.19 l1miss=914.62 l1hwprf=66.56 l2miss=0.761 l2hwprf=25.86 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=20260928 s6: lat=4.4235 cyc=12.141 mem_rd=1004.07 l1miss=913.94 l1hwprf=66.52 l2miss=0.549 l2hwprf=25.78 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=20260928 s7: lat=4.4330 cyc=12.165 mem_rd=1007.92 l1miss=915.01 l1hwprf=66.20 l2miss=0.869 l2hwprf=25.75 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=20260928 s8: lat=4.4305 cyc=12.161 mem_rd=1004.08 l1miss=917.18 l1hwprf=62.84 l2miss=0.301 l2hwprf=24.41 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b640K seed=20260928 s9: lat=4.4147 cyc=12.119 mem_rd=1003.15 l1miss=912.59 l1hwprf=67.90 l2miss=0.234 l2hwprf=26.43 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 768 | seed=7 | base | 512 | 10 | 4.829 [4.823, 4.831] | 13.252 [13.237, 13.257] | 1006.592 [1005.983, 1006.971] | 986.374 [985.058, 987.821] | 3.049 [0.746, 3.270] | 0.843 [0.747, 0.949] | 1.651 [0.694, 1.739] | no |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=7 s0: lat=4.8424 cyc=13.290 mem_rd=1006.78 l1miss=992.96 l1hwprf=2.66 l2miss=0.869 l2hwprf=1.75 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=7 s1: lat=4.8362 cyc=13.261 mem_rd=1007.98 l1miss=985.04 l1hwprf=3.46 l2miss=1.422 l2hwprf=2.62 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=7 s2: lat=4.8295 cyc=13.256 mem_rd=1004.19 l1miss=989.00 l1hwprf=2.94 l2miss=0.976 l2hwprf=1.55 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=7 s3: lat=4.8312 cyc=13.257 mem_rd=1007.92 l1miss=985.28 l1hwprf=3.36 l2miss=1.254 l2hwprf=2.20 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=7 s4: lat=4.8275 cyc=13.248 mem_rd=1005.95 l1miss=987.62 l1hwprf=0.11 l2miss=0.739 l2hwprf=0.41 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=7 s5: lat=4.8214 cyc=13.231 mem_rd=1006.08 l1miss=985.04 l1hwprf=3.16 l2miss=0.822 l2hwprf=1.71 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=7 s6: lat=4.8217 cyc=13.235 mem_rd=1004.02 l1miss=987.46 l1hwprf=0.06 l2miss=0.420 l2hwprf=0.24 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=7 s7: lat=4.8241 cyc=13.239 mem_rd=1006.53 l1miss=985.10 l1hwprf=3.19 l2miss=0.865 l2hwprf=1.64 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=7 s8: lat=4.8225 cyc=13.236 mem_rd=1007.03 l1miss=985.03 l1hwprf=3.30 l2miss=0.716 l2hwprf=1.66 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=7 s9: lat=4.8303 cyc=13.257 mem_rd=1006.65 l1miss=987.89 l1hwprf=0.09 l2miss=0.774 l2hwprf=0.27 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 768 | seed=42 | base | 512 | 10 | 4.822 [4.820, 4.839] | 13.232 [13.225, 13.279] | 1006.286 [1005.980, 1006.576] | 985.161 [984.995, 985.244] | 3.211 [3.036, 3.275] | 0.818 [0.623, 1.169] | 2.077 [1.607, 2.550] | YES |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=42 s0: lat=4.8417 cyc=13.288 mem_rd=1006.25 l1miss=995.72 l1hwprf=0.01 l2miss=0.507 l2hwprf=0.28 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=42 s1: lat=4.9552 cyc=13.589 mem_rd=1006.60 l1miss=985.09 l1hwprf=3.19 l2miss=9.521 l2hwprf=116.62 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=42 s2: lat=4.8242 cyc=13.234 mem_rd=1008.16 l1miss=985.23 l1hwprf=3.18 l2miss=1.001 l2hwprf=1.53 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=42 s3: lat=4.8167 cyc=13.222 mem_rd=1004.25 l1miss=987.38 l1hwprf=0.08 l2miss=0.291 l2hwprf=0.11 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=42 s4: lat=4.8310 cyc=13.250 mem_rd=1008.38 l1miss=985.22 l1hwprf=3.35 l2miss=1.225 l2hwprf=2.08 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=42 s5: lat=4.8200 cyc=13.229 mem_rd=1006.51 l1miss=985.10 l1hwprf=3.23 l2miss=0.937 l2hwprf=1.84 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=42 s6: lat=5.2177 cyc=14.320 mem_rd=1006.05 l1miss=985.25 l1hwprf=2.99 l2miss=24.730 l2hwprf=1069.12 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=42 s7: lat=4.8199 cyc=13.225 mem_rd=1005.96 l1miss=984.55 l1hwprf=3.50 l2miss=0.698 l2hwprf=2.29 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=42 s8: lat=4.8202 cyc=13.226 mem_rd=1006.33 l1miss=984.96 l1hwprf=3.26 l2miss=0.603 l2hwprf=2.64 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=42 s9: lat=4.8177 cyc=13.220 mem_rd=1005.08 l1miss=984.67 l1hwprf=3.28 l2miss=0.684 l2hwprf=2.08 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 768 | seed=1337 | base | 512 | 10 | 4.819 [4.814, 4.820] | 13.225 [13.213, 13.227] | 1006.476 [1005.412, 1007.219] | 985.124 [984.913, 985.375] | 3.158 [3.022, 3.239] | 0.688 [0.647, 0.888] | 1.397 [1.338, 1.474] | no |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=1337 s0: lat=4.8348 cyc=13.261 mem_rd=1007.87 l1miss=991.76 l1hwprf=2.99 l2miss=0.649 l2hwprf=1.31 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=1337 s1: lat=4.8200 cyc=13.227 mem_rd=1007.70 l1miss=985.30 l1hwprf=3.29 l2miss=0.907 l2hwprf=1.39 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=1337 s2: lat=4.8122 cyc=13.208 mem_rd=1005.35 l1miss=984.87 l1hwprf=3.20 l2miss=0.632 l2hwprf=1.39 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=1337 s3: lat=4.8185 cyc=13.223 mem_rd=1007.24 l1miss=985.04 l1hwprf=3.25 l2miss=0.832 l2hwprf=1.42 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=1337 s4: lat=4.8202 cyc=13.227 mem_rd=1007.17 l1miss=985.40 l1hwprf=2.93 l2miss=0.932 l2hwprf=1.32 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=1337 s5: lat=4.8261 cyc=13.244 mem_rd=1004.24 l1miss=987.40 l1hwprf=0.07 l2miss=0.678 l2hwprf=0.42 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=1337 s6: lat=4.8199 cyc=13.226 mem_rd=1006.78 l1miss=985.18 l1hwprf=3.12 l2miss=0.917 l2hwprf=1.49 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=1337 s7: lat=4.8124 cyc=13.206 mem_rd=1005.01 l1miss=984.74 l1hwprf=3.20 l2miss=0.500 l2hwprf=1.62 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=1337 s8: lat=4.8156 cyc=13.217 mem_rd=1006.17 l1miss=984.71 l1hwprf=3.38 l2miss=0.697 l2hwprf=1.54 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=1337 s9: lat=4.8135 cyc=13.211 mem_rd=1005.61 l1miss=985.07 l1hwprf=3.12 l2miss=0.646 l2hwprf=1.40 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 768 | seed=20260928 | base | 512 | 10 | 4.944 [4.933, 4.992] | 13.561 [13.537, 13.700] | 1007.168 [1006.763, 1007.936] | 985.313 [985.110, 987.320] | 3.115 [3.047, 3.291] | 9.833 [9.482, 12.188] | 116.442 [107.882, 446.687] | no |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=20260928 s0: lat=4.8335 cyc=13.261 mem_rd=1007.97 l1miss=991.66 l1hwprf=3.08 l2miss=1.216 l2hwprf=1.86 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=20260928 s1: lat=4.9436 cyc=13.563 mem_rd=1004.98 l1miss=984.69 l1hwprf=3.30 l2miss=9.870 l2hwprf=129.52 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=20260928 s2: lat=4.9488 cyc=13.582 mem_rd=1006.73 l1miss=987.84 l1hwprf=0.07 l2miss=9.517 l2hwprf=116.93 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=20260928 s3: lat=4.9441 cyc=13.558 mem_rd=1009.31 l1miss=985.77 l1hwprf=3.15 l2miss=10.061 l2hwprf=103.82 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=20260928 s4: lat=4.9311 cyc=13.532 mem_rd=1006.85 l1miss=985.05 l1hwprf=3.33 l2miss=9.470 l2hwprf=107.90 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=20260928 s5: lat=4.9283 cyc=13.526 mem_rd=1005.87 l1miss=984.82 l1hwprf=3.27 l2miss=9.328 l2hwprf=107.88 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=20260928 s6: lat=4.9383 cyc=13.551 mem_rd=1008.76 l1miss=985.28 l1hwprf=3.48 l2miss=9.796 l2hwprf=115.95 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=20260928 s7: lat=5.0062 cyc=13.739 mem_rd=1007.33 l1miss=985.32 l1hwprf=3.07 l2miss=12.897 l2hwprf=586.55 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=20260928 s8: lat=5.0189 cyc=13.774 mem_rd=1007.01 l1miss=987.93 l1hwprf=0.01 l2miss=13.164 l2hwprf=604.17 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b768K seed=20260928 s9: lat=5.0098 cyc=13.744 mem_rd=1007.82 l1miss=985.31 l1hwprf=3.04 l2miss=13.146 l2hwprf=552.41 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 1024 | seed=7 | base | 512 | 10 | 5.441 [5.353, 5.475] | 14.929 [14.686, 15.025] | 1007.054 [1006.282, 1008.047] | 1000.905 [1000.797, 1001.047] | 0.011 [0.008, 0.013] | 22.319 [15.232, 23.666] | 1073.115 [961.811, 1214.068] | YES |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=7 s0: lat=5.1128 cyc=14.028 mem_rd=1009.05 l1miss=1001.19 l1hwprf=0.02 l2miss=1.909 l2hwprf=5.52 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=7 s1: lat=5.1026 cyc=13.996 mem_rd=1005.60 l1miss=1000.75 l1hwprf=0.01 l2miss=1.668 l2hwprf=4.22 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=7 s2: lat=5.3506 cyc=14.680 mem_rd=1008.46 l1miss=1001.07 l1hwprf=0.01 l2miss=15.032 l2hwprf=1157.09 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=7 s3: lat=5.3588 cyc=14.705 mem_rd=1006.97 l1miss=1000.89 l1hwprf=0.01 l2miss=15.832 l2hwprf=1233.06 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=7 s4: lat=5.4811 cyc=15.041 mem_rd=1006.78 l1miss=1000.90 l1hwprf=0.00 l2miss=23.650 l2hwprf=1464.85 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=7 s5: lat=5.4583 cyc=14.974 mem_rd=1008.29 l1miss=1001.13 l1hwprf=0.01 l2miss=23.671 l2hwprf=1032.90 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=7 s6: lat=5.5298 cyc=15.175 mem_rd=1006.12 l1miss=1000.75 l1hwprf=0.01 l2miss=27.859 l2hwprf=1337.34 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=7 s7: lat=5.4992 cyc=15.087 mem_rd=1007.13 l1miss=1000.96 l1hwprf=0.01 l2miss=25.448 l2hwprf=1054.75 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=7 s8: lat=5.4230 cyc=14.884 mem_rd=1005.73 l1miss=1000.76 l1hwprf=0.01 l2miss=21.872 l2hwprf=1091.48 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=7 s9: lat=5.4584 cyc=14.976 mem_rd=1007.32 l1miss=1000.91 l1hwprf=0.01 l2miss=22.767 l2hwprf=938.11 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 1024 | seed=42 | base | 512 | 10 | 5.481 [5.384, 5.567] | 15.036 [14.773, 15.276] | 1007.611 [1006.772, 1009.221] | 1000.965 [1000.877, 1001.203] | 0.014 [0.012, 0.018] | 21.626 [17.169, 28.207] | 1310.284 [1240.293, 1390.723] | no |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=42 s0: lat=5.3570 cyc=14.699 mem_rd=1010.17 l1miss=1001.31 l1hwprf=0.02 l2miss=15.816 l2hwprf=737.55 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=42 s1: lat=5.3404 cyc=14.655 mem_rd=1006.75 l1miss=1000.87 l1hwprf=0.02 l2miss=13.432 l2hwprf=1284.46 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=42 s2: lat=5.4658 cyc=14.997 mem_rd=1006.84 l1miss=1000.89 l1hwprf=0.01 l2miss=21.695 l2hwprf=1225.57 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=42 s3: lat=5.4776 cyc=15.026 mem_rd=1006.65 l1miss=1000.84 l1hwprf=0.01 l2miss=21.225 l2hwprf=1381.09 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=42 s4: lat=5.5721 cyc=15.289 mem_rd=1008.85 l1miss=1001.18 l1hwprf=0.01 l2miss=29.217 l2hwprf=1288.36 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=42 s5: lat=5.3476 cyc=14.674 mem_rd=1007.31 l1miss=1000.91 l1hwprf=0.02 l2miss=15.583 l2hwprf=734.38 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=42 s6: lat=5.6046 cyc=15.371 mem_rd=1009.76 l1miss=1001.24 l1hwprf=0.01 l2miss=30.720 l2hwprf=1567.26 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=42 s7: lat=5.4851 cyc=15.047 mem_rd=1009.34 l1miss=1001.21 l1hwprf=0.04 l2miss=21.556 l2hwprf=1332.21 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=42 s8: lat=5.5519 cyc=15.236 mem_rd=1007.91 l1miss=1001.02 l1hwprf=0.01 l2miss=27.121 l2hwprf=1573.09 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=42 s9: lat=5.5748 cyc=15.297 mem_rd=1006.62 l1miss=1000.80 l1hwprf=0.01 l2miss=28.569 l2hwprf=1393.93 -->
| 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base | 1024 | seed=1337 | base | 512 | 10 | 5.230 [5.214, 5.275] | 14.351 [14.307, 14.467] | 1007.093 [1006.427, 1008.323] | 1000.874 [1000.781, 1001.004] | 0.018 [0.015, 0.028] | 8.512 [7.850, 10.388] | 210.367 [143.089, 435.852] | no |
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=1337 s0: lat=5.3836 cyc=14.770 mem_rd=1006.53 l1miss=1000.82 l1hwprf=0.01 l2miss=15.362 l2hwprf=1272.52 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=1337 s1: lat=5.2185 cyc=14.316 mem_rd=1008.38 l1miss=1000.92 l1hwprf=0.03 l2miss=8.076 l2hwprf=178.02 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=1337 s2: lat=5.2433 cyc=14.379 mem_rd=1009.48 l1miss=1001.19 l1hwprf=0.02 l2miss=8.820 l2hwprf=242.71 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=1337 s3: lat=5.2131 cyc=14.305 mem_rd=1006.93 l1miss=1000.93 l1hwprf=0.03 l2miss=7.775 l2hwprf=144.06 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=1337 s4: lat=5.4372 cyc=14.914 mem_rd=1009.05 l1miss=1001.18 l1hwprf=0.02 l2miss=19.141 l2hwprf=1254.68 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=1337 s5: lat=5.2196 cyc=14.324 mem_rd=1006.05 l1miss=1000.79 l1hwprf=0.03 l2miss=8.205 l2hwprf=142.77 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=1337 s6: lat=5.2850 cyc=14.496 mem_rd=1008.16 l1miss=1001.03 l1hwprf=0.01 l2miss=10.794 l2hwprf=478.01 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=1337 s7: lat=5.2054 cyc=14.286 mem_rd=1004.18 l1miss=1000.21 l1hwprf=0.03 l2miss=7.516 l2hwprf=96.75 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=1337 s8: lat=5.1435 cyc=14.114 mem_rd=1006.39 l1miss=1000.78 l1hwprf=0.02 l2miss=2.739 l2hwprf=17.42 -->
<!-- sample 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base b1024K seed=1337 s9: lat=5.2402 cyc=14.378 mem_rd=1007.26 l1miss=1000.37 l1hwprf=0.01 l2miss=9.173 l2hwprf=309.38 -->
| 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a | 1024 | seed=7 | base | 512 | 10 | 5.255 [5.227, 5.258] | 14.418 [14.342, 14.429] | 1007.226 [1006.470, 1007.881] | 1000.999 [1000.862, 1001.028] | 0.013 [0.010, 0.017] | 10.493 [9.532, 11.031] | 484.251 [314.354, 536.949] | no |
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=7 s0: lat=5.2540 cyc=14.418 mem_rd=1008.46 l1miss=1001.10 l1hwprf=0.01 l2miss=10.461 l2hwprf=514.93 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=7 s1: lat=5.2551 cyc=14.419 mem_rd=1006.61 l1miss=1000.89 l1hwprf=0.01 l2miss=11.072 l2hwprf=543.49 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=7 s2: lat=5.2844 cyc=14.489 mem_rd=1008.20 l1miss=1001.04 l1hwprf=0.01 l2miss=10.295 l2hwprf=1236.50 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=7 s3: lat=5.2552 cyc=14.418 mem_rd=1007.41 l1miss=1001.00 l1hwprf=0.03 l2miss=11.259 l2hwprf=410.27 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=7 s4: lat=5.2207 cyc=14.324 mem_rd=1007.04 l1miss=1001.00 l1hwprf=0.01 l2miss=9.278 l2hwprf=282.38 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=7 s5: lat=5.2593 cyc=14.432 mem_rd=1005.29 l1miss=1000.65 l1hwprf=0.01 l2miss=11.114 l2hwprf=453.57 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=7 s6: lat=5.1104 cyc=14.016 mem_rd=1007.95 l1miss=1001.03 l1hwprf=0.01 l2miss=1.940 l2hwprf=8.67 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=7 s7: lat=5.2605 cyc=14.436 mem_rd=1005.47 l1miss=1000.75 l1hwprf=0.01 l2miss=10.911 l2hwprf=544.74 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=7 s8: lat=5.1937 cyc=14.248 mem_rd=1007.68 l1miss=1001.01 l1hwprf=0.02 l2miss=8.043 l2hwprf=125.56 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=7 s9: lat=5.2465 cyc=14.396 mem_rd=1006.42 l1miss=1000.85 l1hwprf=0.03 l2miss=10.526 l2hwprf=517.31 -->
| 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a | 1024 | seed=42 | base | 512 | 10 | 5.125 [5.115, 5.182] | 14.062 [14.038, 14.221] | 1006.944 [1005.864, 1007.788] | 1000.805 [1000.709, 1000.973] | 0.017 [0.013, 0.019] | 2.162 [1.606, 6.233] | 11.581 [4.427, 72.893] | no |
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=42 s0: lat=5.1123 cyc=14.028 mem_rd=1007.85 l1miss=999.79 l1hwprf=0.02 l2miss=1.518 l2hwprf=3.01 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=42 s1: lat=5.1224 cyc=14.056 mem_rd=1006.77 l1miss=1000.85 l1hwprf=0.02 l2miss=2.085 l2hwprf=6.57 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=42 s2: lat=5.1060 cyc=14.009 mem_rd=1007.12 l1miss=1000.93 l1hwprf=0.01 l2miss=0.775 l2hwprf=0.77 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=42 s3: lat=5.1129 cyc=14.032 mem_rd=1005.48 l1miss=1000.69 l1hwprf=0.02 l2miss=1.487 l2hwprf=3.71 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=42 s4: lat=5.2011 cyc=14.272 mem_rd=1005.26 l1miss=1000.65 l1hwprf=0.02 l2miss=7.462 l2hwprf=91.86 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=42 s5: lat=5.1241 cyc=14.061 mem_rd=1007.61 l1miss=1000.99 l1hwprf=0.02 l2miss=2.239 l2hwprf=14.14 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=42 s6: lat=5.1261 cyc=14.066 mem_rd=1005.75 l1miss=1000.76 l1hwprf=0.02 l2miss=2.547 l2hwprf=15.98 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=42 s7: lat=5.2089 cyc=14.294 mem_rd=1006.21 l1miss=1000.75 l1hwprf=0.01 l2miss=7.944 l2hwprf=159.38 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=42 s8: lat=5.2037 cyc=14.280 mem_rd=1008.04 l1miss=1001.06 l1hwprf=0.01 l2miss=7.581 l2hwprf=143.12 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=42 s9: lat=5.1251 cyc=14.062 mem_rd=1008.52 l1miss=1001.09 l1hwprf=0.01 l2miss=1.871 l2hwprf=9.02 -->
| 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a | 1024 | seed=1337 | base | 512 | 10 | 5.339 [5.235, 5.395] | 14.648 [14.364, 14.802] | 1007.830 [1006.905, 1008.302] | 1000.968 [1000.890, 1001.032] | 0.018 [0.016, 0.020] | 13.090 [8.630, 16.228] | 1229.349 [263.113, 1312.095] | no |
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=1337 s0: lat=5.3316 cyc=14.628 mem_rd=1006.76 l1miss=1000.89 l1hwprf=0.02 l2miss=12.554 l2hwprf=1173.38 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=1337 s1: lat=5.2194 cyc=14.321 mem_rd=1007.71 l1miss=1001.03 l1hwprf=0.02 l2miss=8.002 l2hwprf=184.48 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=1337 s2: lat=5.2150 cyc=14.313 mem_rd=1005.45 l1miss=1000.62 l1hwprf=0.02 l2miss=7.859 l2hwprf=179.89 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=1337 s3: lat=5.2101 cyc=14.298 mem_rd=1005.56 l1miss=1000.38 l1hwprf=0.01 l2miss=7.792 l2hwprf=154.65 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=1337 s4: lat=5.3585 cyc=14.693 mem_rd=1008.23 l1miss=1001.03 l1hwprf=0.02 l2miss=13.838 l2hwprf=1350.51 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=1337 s5: lat=5.2826 cyc=14.494 mem_rd=1008.33 l1miss=1001.12 l1hwprf=0.01 l2miss=10.513 l2hwprf=499.01 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=1337 s6: lat=5.4078 cyc=14.838 mem_rd=1007.95 l1miss=1000.97 l1hwprf=0.02 l2miss=17.025 l2hwprf=1306.23 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=1337 s7: lat=5.4338 cyc=14.906 mem_rd=1008.33 l1miss=1000.96 l1hwprf=0.02 l2miss=19.976 l2hwprf=1314.05 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=1337 s8: lat=5.4627 cyc=14.988 mem_rd=1008.51 l1miss=1001.15 l1hwprf=0.03 l2miss=20.762 l2hwprf=1436.31 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=1337 s9: lat=5.3460 cyc=14.668 mem_rd=1007.34 l1miss=1000.90 l1hwprf=0.02 l2miss=13.626 l2hwprf=1285.32 -->
| 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a | 1024 | seed=20260928 | base | 512 | 10 | 5.273 [5.218, 5.360] | 14.466 [14.321, 14.706] | 1007.504 [1006.515, 1008.548] | 1001.010 [1000.782, 1001.123] | 0.015 [0.012, 0.017] | 10.444 [8.166, 14.738] | 520.005 [221.680, 1221.208] | no |
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=20260928 s0: lat=5.1204 cyc=14.049 mem_rd=1007.22 l1miss=1000.21 l1hwprf=0.02 l2miss=1.456 l2hwprf=2.43 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=20260928 s1: lat=5.3001 cyc=14.541 mem_rd=1008.79 l1miss=1001.14 l1hwprf=0.01 l2miss=10.734 l2hwprf=1180.47 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=20260928 s2: lat=5.2244 cyc=14.336 mem_rd=1008.52 l1miss=1001.09 l1hwprf=0.02 l2miss=8.289 l2hwprf=220.21 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=20260928 s3: lat=5.2165 cyc=14.316 mem_rd=1004.53 l1miss=1000.59 l1hwprf=0.01 l2miss=8.124 l2hwprf=226.08 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=20260928 s4: lat=5.5518 cyc=15.236 mem_rd=1007.35 l1miss=1001.01 l1hwprf=0.02 l2miss=26.602 l2hwprf=1470.05 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=20260928 s5: lat=5.2159 cyc=14.310 mem_rd=1008.95 l1miss=1001.13 l1hwprf=0.02 l2miss=7.872 l2hwprf=143.54 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=20260928 s6: lat=5.2644 cyc=14.447 mem_rd=1005.87 l1miss=1000.77 l1hwprf=0.02 l2miss=10.359 l2hwprf=515.49 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=20260928 s7: lat=5.2812 cyc=14.485 mem_rd=1007.66 l1miss=1001.01 l1hwprf=0.01 l2miss=10.529 l2hwprf=524.52 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=20260928 s8: lat=5.3796 cyc=14.761 mem_rd=1008.56 l1miss=1001.13 l1hwprf=0.02 l2miss=16.073 l2hwprf=1234.79 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1024K seed=20260928 s9: lat=5.4076 cyc=14.840 mem_rd=1006.28 l1miss=1000.82 l1hwprf=0.01 l2miss=17.599 l2hwprf=1331.09 -->
| 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a | 1216 | seed=7 | base | 512 | 10 | 5.457 [5.438, 5.483] | 14.973 [14.921, 15.045] | 1007.886 [1007.346, 1008.571] | 1001.044 [1000.934, 1001.118] | 0.012 [0.010, 0.013] | 15.006 [14.035, 15.735] | 1001.338 [761.616, 1083.159] | no |
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=7 s0: lat=5.4512 cyc=14.959 mem_rd=1009.41 l1miss=1001.36 l1hwprf=0.03 l2miss=13.759 l2hwprf=993.46 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=7 s1: lat=5.5086 cyc=15.116 mem_rd=1007.71 l1miss=1001.02 l1hwprf=0.01 l2miss=16.715 l2hwprf=1155.57 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=7 s2: lat=5.4271 cyc=14.894 mem_rd=1007.29 l1miss=1000.91 l1hwprf=0.02 l2miss=11.989 l2hwprf=1074.44 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=7 s3: lat=5.4633 cyc=14.987 mem_rd=1008.28 l1miss=1001.09 l1hwprf=0.01 l2miss=15.126 l2hwprf=717.12 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=7 s4: lat=5.4885 cyc=15.061 mem_rd=1008.07 l1miss=1001.06 l1hwprf=0.01 l2miss=15.800 l2hwprf=1086.07 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=7 s5: lat=5.4361 cyc=14.916 mem_rd=1007.51 l1miss=1001.01 l1hwprf=0.01 l2miss=14.864 l2hwprf=358.36 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=7 s6: lat=5.4432 cyc=14.935 mem_rd=1006.39 l1miss=1000.83 l1hwprf=0.01 l2miss=15.542 l2hwprf=324.88 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=7 s7: lat=5.5363 cyc=15.186 mem_rd=1009.12 l1miss=1001.19 l1hwprf=0.01 l2miss=19.356 l2hwprf=1303.47 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=7 s8: lat=5.4265 cyc=14.889 mem_rd=1008.67 l1miss=1001.13 l1hwprf=0.01 l2miss=11.942 l2hwprf=895.12 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=7 s9: lat=5.4655 cyc=14.999 mem_rd=1006.56 l1miss=1000.85 l1hwprf=0.01 l2miss=14.887 l2hwprf=1009.21 -->
| 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a | 1216 | seed=42 | base | 512 | 10 | 5.505 [5.464, 5.561] | 15.104 [14.994, 15.259] | 1007.881 [1007.010, 1008.582] | 1001.058 [1000.922, 1001.172] | 0.010 [0.008, 0.015] | 16.524 [14.323, 20.483] | 1087.149 [1021.158, 1120.439] | no |
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=42 s0: lat=5.5408 cyc=15.203 mem_rd=1009.64 l1miss=1001.23 l1hwprf=0.02 l2miss=19.546 l2hwprf=1028.37 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=42 s1: lat=5.4599 cyc=14.983 mem_rd=1006.62 l1miss=1000.84 l1hwprf=0.01 l2miss=14.146 l2hwprf=957.72 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=42 s2: lat=5.6011 cyc=15.369 mem_rd=1006.95 l1miss=1000.89 l1hwprf=0.01 l2miss=23.566 l2hwprf=1280.08 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=42 s3: lat=5.5683 cyc=15.278 mem_rd=1008.03 l1miss=1001.14 l1hwprf=0.01 l2miss=21.499 l2hwprf=1071.69 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=42 s4: lat=5.5742 cyc=15.289 mem_rd=1009.29 l1miss=1001.19 l1hwprf=0.02 l2miss=20.795 l2hwprf=1105.09 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=42 s5: lat=5.4492 cyc=14.951 mem_rd=1007.81 l1miss=1001.06 l1hwprf=0.01 l2miss=13.357 l2hwprf=1018.75 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=42 s6: lat=5.4977 cyc=15.086 mem_rd=1007.18 l1miss=1000.98 l1hwprf=0.01 l2miss=15.907 l2hwprf=1125.56 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=42 s7: lat=5.5115 cyc=15.122 mem_rd=1008.76 l1miss=1001.18 l1hwprf=0.01 l2miss=17.141 l2hwprf=1102.61 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=42 s8: lat=5.4759 cyc=15.025 mem_rd=1006.79 l1miss=1000.90 l1hwprf=0.01 l2miss=14.855 l2hwprf=1199.45 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=42 s9: lat=5.4449 cyc=14.940 mem_rd=1007.95 l1miss=1001.06 l1hwprf=0.01 l2miss=12.749 l2hwprf=949.81 -->
| 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a | 1216 | seed=1337 | base | 512 | 10 | 5.438 [5.406, 5.495] | 14.923 [14.834, 15.078] | 1006.843 [1006.120, 1008.217] | 1000.930 [1000.843, 1001.079] | 0.009 [0.007, 0.017] | 12.962 [10.882, 16.225] | 949.224 [858.766, 1032.328] | no |
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=1337 s0: lat=5.4141 cyc=14.852 mem_rd=1009.19 l1miss=1001.32 l1hwprf=0.02 l2miss=11.339 l2hwprf=957.89 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=1337 s1: lat=5.3270 cyc=14.618 mem_rd=1005.71 l1miss=1000.78 l1hwprf=0.01 l2miss=7.803 l2hwprf=286.91 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=1337 s2: lat=5.4529 cyc=14.961 mem_rd=1007.57 l1miss=1001.02 l1hwprf=0.02 l2miss=13.571 l2hwprf=1096.77 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=1337 s3: lat=5.3836 cyc=14.775 mem_rd=1005.93 l1miss=1000.84 l1hwprf=0.01 l2miss=9.461 l2hwprf=1010.83 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=1337 s4: lat=5.5086 cyc=15.117 mem_rd=1006.99 l1miss=1000.94 l1hwprf=0.01 l2miss=17.109 l2hwprf=1149.69 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=1337 s5: lat=5.4329 cyc=14.908 mem_rd=1006.68 l1miss=1000.92 l1hwprf=0.01 l2miss=12.536 l2hwprf=1039.50 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=1337 s6: lat=5.4438 cyc=14.938 mem_rd=1006.69 l1miss=1000.86 l1hwprf=0.01 l2miss=13.388 l2hwprf=940.55 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=1337 s7: lat=5.5396 cyc=15.201 mem_rd=1008.43 l1miss=1001.10 l1hwprf=0.01 l2miss=21.265 l2hwprf=843.08 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=1337 s8: lat=5.5667 cyc=15.273 mem_rd=1009.84 l1miss=1001.27 l1hwprf=0.02 l2miss=22.771 l2hwprf=799.94 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=1337 s9: lat=5.4028 cyc=14.828 mem_rd=1005.17 l1miss=1000.71 l1hwprf=0.01 l2miss=10.729 l2hwprf=905.83 -->
| 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a | 1216 | seed=20260928 | base | 512 | 10 | 5.494 [5.441, 5.572] | 15.074 [14.927, 15.291] | 1007.388 [1007.028, 1007.993] | 1000.954 [1000.931, 1001.040] | 0.011 [0.009, 0.011] | 17.450 [13.882, 23.325] | 981.682 [904.456, 1049.744] | no |
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=20260928 s0: lat=5.4354 cyc=14.912 mem_rd=1008.12 l1miss=1001.11 l1hwprf=0.01 l2miss=13.633 l2hwprf=1055.33 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=20260928 s1: lat=5.4571 cyc=14.970 mem_rd=1007.29 l1miss=1000.97 l1hwprf=0.01 l2miss=14.629 l2hwprf=1179.62 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=20260928 s2: lat=5.5916 cyc=15.343 mem_rd=1007.26 l1miss=1000.96 l1hwprf=0.01 l2miss=24.223 l2hwprf=902.46 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=20260928 s3: lat=5.4062 cyc=14.831 mem_rd=1006.43 l1miss=1000.87 l1hwprf=0.01 l2miss=12.415 l2hwprf=790.04 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=20260928 s4: lat=5.5796 cyc=15.311 mem_rd=1007.48 l1miss=1000.93 l1hwprf=0.02 l2miss=23.911 l2hwprf=1027.92 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=20260928 s5: lat=5.5505 cyc=15.229 mem_rd=1007.79 l1miss=1000.95 l1hwprf=0.01 l2miss=21.566 l2hwprf=935.45 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=20260928 s6: lat=5.6597 cyc=15.529 mem_rd=1008.06 l1miss=1001.06 l1hwprf=0.01 l2miss=28.553 l2hwprf=1032.98 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=20260928 s7: lat=5.5114 cyc=15.120 mem_rd=1008.36 l1miss=1001.12 l1hwprf=0.01 l2miss=17.399 l2hwprf=1147.61 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=20260928 s8: lat=5.4768 cyc=15.029 mem_rd=1006.95 l1miss=1000.93 l1hwprf=0.01 l2miss=17.500 l2hwprf=910.45 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1216K seed=20260928 s9: lat=5.3032 cyc=14.553 mem_rd=1006.92 l1miss=1000.92 l1hwprf=0.01 l2miss=6.885 l2hwprf=127.67 -->
| 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a | 1408 | seed=7 | base | 512 | 10 | 5.694 [5.645, 5.745] | 15.620 [15.485, 15.763] | 1007.585 [1007.123, 1008.701] | 1001.017 [1000.929, 1001.181] | 0.010 [0.009, 0.013] | 25.119 [22.203, 28.978] | 765.568 [702.314, 848.053] | no |
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=7 s0: lat=5.7580 cyc=15.797 mem_rd=1006.96 l1miss=1000.91 l1hwprf=0.01 l2miss=29.849 l2hwprf=719.91 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=7 s1: lat=5.6944 cyc=15.623 mem_rd=1007.07 l1miss=1000.92 l1hwprf=0.01 l2miss=25.588 l2hwprf=696.45 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=7 s2: lat=5.6939 cyc=15.617 mem_rd=1009.36 l1miss=1001.27 l1hwprf=0.01 l2miss=24.650 l2hwprf=868.90 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=7 s3: lat=5.6283 cyc=15.433 mem_rd=1009.72 l1miss=1001.30 l1hwprf=0.02 l2miss=21.491 l2hwprf=583.40 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=7 s4: lat=5.6159 cyc=15.409 mem_rd=1007.57 l1miss=1001.03 l1hwprf=0.01 l2miss=19.977 l2hwprf=910.24 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=7 s5: lat=5.7075 cyc=15.661 mem_rd=1007.27 l1miss=1000.94 l1hwprf=0.01 l2miss=26.363 l2hwprf=762.89 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=7 s6: lat=5.7711 cyc=15.836 mem_rd=1007.70 l1miss=1001.08 l1hwprf=0.01 l2miss=31.174 l2hwprf=768.24 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=7 s7: lat=5.6831 cyc=15.594 mem_rd=1006.61 l1miss=1000.92 l1hwprf=0.01 l2miss=24.340 l2hwprf=938.76 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=7 s8: lat=5.8128 cyc=15.942 mem_rd=1007.60 l1miss=1001.00 l1hwprf=0.01 l2miss=33.379 l2hwprf=785.50 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=7 s9: lat=5.6318 cyc=15.449 mem_rd=1009.03 l1miss=1001.22 l1hwprf=0.02 l2miss=21.273 l2hwprf=674.84 -->
| 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a | 1408 | seed=42 | base | 512 | 10 | 5.692 [5.628, 5.703] | 15.619 [15.441, 15.644] | 1007.525 [1007.381, 1007.824] | 1001.033 [1000.975, 1001.088] | 0.010 [0.009, 0.012] | 24.923 [21.103, 26.085] | 811.571 [722.698, 872.467] | no |
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=42 s0: lat=5.7097 cyc=15.671 mem_rd=1006.47 l1miss=1000.92 l1hwprf=0.01 l2miss=27.170 l2hwprf=702.01 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=42 s1: lat=5.7032 cyc=15.646 mem_rd=1008.26 l1miss=1001.13 l1hwprf=0.01 l2miss=24.922 l2hwprf=909.08 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=42 s2: lat=5.5298 cyc=15.172 mem_rd=1007.46 l1miss=1001.02 l1hwprf=0.01 l2miss=14.529 l2hwprf=538.23 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=42 s3: lat=5.6151 cyc=15.405 mem_rd=1007.85 l1miss=1001.10 l1hwprf=0.01 l2miss=20.277 l2hwprf=796.24 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=42 s4: lat=5.6891 cyc=15.610 mem_rd=1007.59 l1miss=1001.04 l1hwprf=0.01 l2miss=24.925 l2hwprf=845.22 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=42 s5: lat=5.7564 cyc=15.779 mem_rd=1007.45 l1miss=1001.01 l1hwprf=0.01 l2miss=28.630 l2hwprf=1001.03 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=42 s6: lat=5.6953 cyc=15.628 mem_rd=1006.26 l1miss=1000.89 l1hwprf=0.01 l2miss=26.020 l2hwprf=609.30 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=42 s7: lat=5.6685 cyc=15.548 mem_rd=1008.48 l1miss=1001.11 l1hwprf=0.01 l2miss=23.580 l2hwprf=826.90 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=42 s8: lat=5.5969 cyc=15.352 mem_rd=1007.75 l1miss=1001.06 l1hwprf=0.01 l2miss=19.098 l2hwprf=784.76 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=42 s9: lat=5.7008 cyc=15.639 mem_rd=1007.36 l1miss=1000.96 l1hwprf=0.01 l2miss=26.106 l2hwprf=881.55 -->
| 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a | 1408 | seed=1337 | base | 512 | 10 | 5.734 [5.706, 5.777] | 15.733 [15.653, 15.850] | 1007.647 [1007.219, 1008.000] | 1001.059 [1001.022, 1001.080] | 0.010 [0.009, 0.010] | 28.291 [26.417, 30.976] | 774.738 [637.055, 818.815] | no |
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=1337 s0: lat=5.7858 cyc=15.876 mem_rd=1007.14 l1miss=1000.98 l1hwprf=0.01 l2miss=31.895 l2hwprf=756.62 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=1337 s1: lat=5.8016 cyc=15.918 mem_rd=1007.58 l1miss=1001.05 l1hwprf=0.01 l2miss=32.950 l2hwprf=867.00 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=1337 s2: lat=5.7870 cyc=15.878 mem_rd=1007.45 l1miss=1001.05 l1hwprf=0.01 l2miss=31.521 l2hwprf=826.73 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=1337 s3: lat=5.7131 cyc=15.670 mem_rd=1008.08 l1miss=1001.08 l1hwprf=0.01 l2miss=26.237 l2hwprf=755.04 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=1337 s4: lat=5.6221 cyc=15.427 mem_rd=1007.04 l1miss=1001.01 l1hwprf=0.01 l2miss=21.398 l2hwprf=502.97 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=1337 s5: lat=5.7216 cyc=15.697 mem_rd=1008.07 l1miss=1001.14 l1hwprf=0.01 l2miss=27.581 l2hwprf=597.73 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=1337 s6: lat=5.7468 cyc=15.769 mem_rd=1006.33 l1miss=1000.89 l1hwprf=0.01 l2miss=29.341 l2hwprf=792.86 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=1337 s7: lat=5.7030 cyc=15.648 mem_rd=1007.72 l1miss=1001.08 l1hwprf=0.01 l2miss=26.960 l2hwprf=795.06 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=1337 s8: lat=5.7488 cyc=15.771 mem_rd=1008.75 l1miss=1001.22 l1hwprf=0.01 l2miss=29.001 l2hwprf=866.26 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=1337 s9: lat=5.6619 cyc=15.533 mem_rd=1007.78 l1miss=1001.07 l1hwprf=0.01 l2miss=23.486 l2hwprf=537.13 -->
| 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a | 1408 | seed=20260928 | base | 512 | 10 | 5.696 [5.651, 5.716] | 15.628 [15.499, 15.679] | 1007.918 [1007.134, 1008.865] | 1001.127 [1001.014, 1001.187] | 0.008 [0.007, 0.010] | 25.517 [22.868, 26.384] | 750.968 [727.920, 789.245] | no |
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=20260928 s0: lat=5.6936 cyc=15.622 mem_rd=1008.92 l1miss=1001.19 l1hwprf=0.01 l2miss=25.584 l2hwprf=818.36 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=20260928 s1: lat=5.6423 cyc=15.475 mem_rd=1008.70 l1miss=1001.17 l1hwprf=0.01 l2miss=21.907 l2hwprf=663.46 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=20260928 s2: lat=5.6352 cyc=15.460 mem_rd=1006.99 l1miss=1001.00 l1hwprf=0.01 l2miss=21.833 l2hwprf=745.51 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=20260928 s3: lat=5.7381 cyc=15.744 mem_rd=1007.09 l1miss=1000.99 l1hwprf=0.01 l2miss=29.211 l2hwprf=717.11 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=20260928 s4: lat=5.6993 cyc=15.634 mem_rd=1007.79 l1miss=1001.11 l1hwprf=0.01 l2miss=25.449 l2hwprf=791.80 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=20260928 s5: lat=5.7472 cyc=15.761 mem_rd=1007.25 l1miss=1001.06 l1hwprf=0.01 l2miss=29.788 l2hwprf=723.46 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=20260928 s6: lat=5.6768 cyc=15.570 mem_rd=1009.63 l1miss=1001.30 l1hwprf=0.01 l2miss=24.069 l2hwprf=812.46 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=20260928 s7: lat=5.7214 cyc=15.693 mem_rd=1008.93 l1miss=1001.21 l1hwprf=0.01 l2miss=26.639 l2hwprf=756.43 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=20260928 s8: lat=5.6984 cyc=15.637 mem_rd=1006.17 l1miss=1000.86 l1hwprf=0.01 l2miss=25.620 l2hwprf=781.58 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1408K seed=20260928 s9: lat=5.6380 cyc=15.467 mem_rd=1008.05 l1miss=1001.14 l1hwprf=0.01 l2miss=22.467 l2hwprf=741.31 -->
| 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a | 1792 | seed=7 | base | 512 | 10 | 5.942 [5.902, 5.983] | 16.302 [16.194, 16.409] | 1008.339 [1007.996, 1008.801] | 1001.175 [1001.123, 1001.179] | 0.011 [0.010, 0.011] | 35.774 [31.913, 38.030] | 557.636 [538.346, 574.063] | no |
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=7 s0: lat=5.9489 cyc=16.322 mem_rd=1008.40 l1miss=1001.18 l1hwprf=0.01 l2miss=36.038 l2hwprf=570.31 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=7 s1: lat=5.8943 cyc=16.172 mem_rd=1006.92 l1miss=1000.99 l1hwprf=0.01 l2miss=31.029 l2hwprf=503.03 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=7 s2: lat=5.9963 cyc=16.451 mem_rd=1008.15 l1miss=1001.18 l1hwprf=0.01 l2miss=40.134 l2hwprf=574.46 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=7 s3: lat=5.8760 cyc=16.119 mem_rd=1007.94 l1miss=1001.11 l1hwprf=0.01 l2miss=31.094 l2hwprf=476.53 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=7 s4: lat=5.9266 cyc=16.259 mem_rd=1008.28 l1miss=1001.17 l1hwprf=0.01 l2miss=34.370 l2hwprf=543.63 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=7 s5: lat=5.8613 cyc=16.078 mem_rd=1008.92 l1miss=1001.22 l1hwprf=0.01 l2miss=30.251 l2hwprf=536.58 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=7 s6: lat=5.9857 cyc=16.417 mem_rd=1008.97 l1miss=1001.18 l1hwprf=0.01 l2miss=37.600 l2hwprf=544.96 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=7 s7: lat=5.9737 cyc=16.385 mem_rd=1008.45 l1miss=1001.16 l1hwprf=0.01 l2miss=38.513 l2hwprf=572.87 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=7 s8: lat=5.9343 cyc=16.281 mem_rd=1007.35 l1miss=1001.02 l1hwprf=0.01 l2miss=35.510 l2hwprf=617.85 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=7 s9: lat=5.9868 cyc=16.422 mem_rd=1008.96 l1miss=1001.24 l1hwprf=0.01 l2miss=38.173 l2hwprf=612.68 -->
| 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a | 1792 | seed=42 | base | 512 | 10 | 5.966 [5.931, 5.980] | 16.368 [16.273, 16.402] | 1008.222 [1007.712, 1008.556] | 1001.132 [1001.074, 1001.190] | 0.011 [0.010, 0.013] | 37.042 [34.115, 37.369] | 568.470 [539.761, 604.738] | no |
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=42 s0: lat=5.9549 cyc=16.339 mem_rd=1008.54 l1miss=1001.19 l1hwprf=0.01 l2miss=37.135 l2hwprf=538.69 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=42 s1: lat=5.9500 cyc=16.326 mem_rd=1007.60 l1miss=1001.07 l1hwprf=0.01 l2miss=35.813 l2hwprf=613.35 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=42 s2: lat=5.9250 cyc=16.255 mem_rd=1008.56 l1miss=1001.19 l1hwprf=0.01 l2miss=33.549 l2hwprf=556.92 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=42 s3: lat=5.9784 cyc=16.400 mem_rd=1009.18 l1miss=1001.27 l1hwprf=0.01 l2miss=36.948 l2hwprf=580.02 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=42 s4: lat=5.8781 cyc=16.125 mem_rd=1007.94 l1miss=1001.13 l1hwprf=0.01 l2miss=31.291 l2hwprf=501.89 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=42 s5: lat=5.8272 cyc=15.987 mem_rd=1006.80 l1miss=1000.99 l1hwprf=0.01 l2miss=27.328 l2hwprf=428.55 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=42 s6: lat=6.0086 cyc=16.486 mem_rd=1007.63 l1miss=1001.05 l1hwprf=0.01 l2miss=39.080 l2hwprf=616.84 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=42 s7: lat=5.9804 cyc=16.402 mem_rd=1008.62 l1miss=1001.19 l1hwprf=0.01 l2miss=37.217 l2hwprf=584.70 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=42 s8: lat=6.0360 cyc=16.561 mem_rd=1008.17 l1miss=1001.10 l1hwprf=0.01 l2miss=41.299 l2hwprf=611.42 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=42 s9: lat=5.9771 cyc=16.396 mem_rd=1008.28 l1miss=1001.13 l1hwprf=0.01 l2miss=37.420 l2hwprf=542.96 -->
| 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a | 1792 | seed=1337 | base | 512 | 10 | 5.954 [5.919, 5.987] | 16.335 [16.238, 16.424] | 1008.088 [1007.854, 1008.554] | 1001.114 [1001.085, 1001.176] | 0.010 [0.009, 0.011] | 37.113 [34.915, 39.748] | 533.019 [506.757, 553.121] | no |
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=1337 s0: lat=5.9916 cyc=16.439 mem_rd=1008.11 l1miss=1001.09 l1hwprf=0.00 l2miss=40.243 l2hwprf=565.91 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=1337 s1: lat=5.9416 cyc=16.295 mem_rd=1008.66 l1miss=1001.15 l1hwprf=0.01 l2miss=37.092 l2hwprf=487.53 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=1337 s2: lat=5.9114 cyc=16.219 mem_rd=1008.06 l1miss=1001.14 l1hwprf=0.01 l2miss=33.479 l2hwprf=545.02 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=1337 s3: lat=6.1167 cyc=16.779 mem_rd=1008.60 l1miss=1001.20 l1hwprf=0.01 l2miss=49.034 l2hwprf=662.11 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=1337 s4: lat=5.9058 cyc=16.204 mem_rd=1007.66 l1miss=1001.05 l1hwprf=0.01 l2miss=34.261 l2hwprf=507.04 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=1337 s5: lat=6.0098 cyc=16.488 mem_rd=1008.43 l1miss=1001.18 l1hwprf=0.01 l2miss=41.568 l2hwprf=555.82 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=1337 s6: lat=5.9714 cyc=16.380 mem_rd=1008.79 l1miss=1001.23 l1hwprf=0.01 l2miss=38.262 l2hwprf=530.05 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=1337 s7: lat=5.9664 cyc=16.368 mem_rd=1007.86 l1miss=1001.09 l1hwprf=0.01 l2miss=37.135 l2hwprf=535.98 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=1337 s8: lat=5.8630 cyc=16.085 mem_rd=1007.43 l1miss=1001.04 l1hwprf=0.01 l2miss=31.186 l2hwprf=472.58 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=1337 s9: lat=5.9425 cyc=16.302 mem_rd=1007.85 l1miss=1001.08 l1hwprf=0.01 l2miss=36.879 l2hwprf=506.66 -->
| 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a | 1792 | seed=20260928 | base | 512 | 10 | 6.009 [5.962, 6.050] | 16.485 [16.355, 16.596] | 1008.595 [1008.014, 1009.176] | 1001.201 [1001.122, 1001.265] | 0.010 [0.008, 0.013] | 40.513 [37.408, 42.822] | 563.077 [536.774, 622.138] | no |
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=20260928 s0: lat=6.0945 cyc=16.718 mem_rd=1010.20 l1miss=1001.40 l1hwprf=0.01 l2miss=45.376 l2hwprf=607.09 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=20260928 s1: lat=6.0084 cyc=16.485 mem_rd=1007.95 l1miss=1001.11 l1hwprf=0.01 l2miss=40.073 l2hwprf=627.16 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=20260928 s2: lat=5.9401 cyc=16.297 mem_rd=1007.33 l1miss=1000.99 l1hwprf=0.01 l2miss=35.117 l2hwprf=537.30 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=20260928 s3: lat=6.0086 cyc=16.484 mem_rd=1008.38 l1miss=1001.15 l1hwprf=0.01 l2miss=40.775 l2hwprf=631.39 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=20260928 s4: lat=5.9464 cyc=16.313 mem_rd=1008.21 l1miss=1001.17 l1hwprf=0.01 l2miss=36.520 l2hwprf=557.04 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=20260928 s5: lat=6.0742 cyc=16.659 mem_rd=1009.20 l1miss=1001.26 l1hwprf=0.01 l2miss=43.694 l2hwprf=569.12 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=20260928 s6: lat=6.0250 cyc=16.528 mem_rd=1009.46 l1miss=1001.30 l1hwprf=0.01 l2miss=42.259 l2hwprf=534.57 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=20260928 s7: lat=6.0579 cyc=16.618 mem_rd=1007.65 l1miss=1001.07 l1hwprf=0.01 l2miss=43.010 l2hwprf=629.15 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=20260928 s8: lat=6.0090 cyc=16.480 mem_rd=1008.81 l1miss=1001.23 l1hwprf=0.01 l2miss=40.251 l2hwprf=521.88 -->
<!-- sample 20260928T024957Z-ptr-chase-sm8650-x4-p0prime-long-base-r2a b1792K seed=20260928 s9: lat=5.8923 cyc=16.163 mem_rd=1009.09 l1miss=1001.27 l1hwprf=0.01 l2miss=32.550 l2hwprf=536.60 -->
| 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b | 2048 | seed=7 | base | 512 | 10 | 6.139 [6.090, 6.172] | 16.839 [16.709, 16.931] | 1008.445 [1008.105, 1008.671] | 1001.154 [1001.137, 1001.201] | 0.010 [0.008, 0.011] | 45.616 [41.987, 47.778] | 541.909 [522.379, 570.814] | no |
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=7 s0: lat=6.0794 cyc=16.681 mem_rd=1007.22 l1miss=1001.02 l1hwprf=0.01 l2miss=41.032 l2hwprf=517.60 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=7 s1: lat=6.1794 cyc=16.952 mem_rd=1009.23 l1miss=1001.26 l1hwprf=0.01 l2miss=47.806 l2hwprf=587.69 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=7 s2: lat=6.1750 cyc=16.938 mem_rd=1008.46 l1miss=1001.16 l1hwprf=0.01 l2miss=47.694 l2hwprf=575.09 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=7 s3: lat=6.1053 cyc=16.750 mem_rd=1007.93 l1miss=1001.11 l1hwprf=0.01 l2miss=42.426 l2hwprf=530.13 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=7 s4: lat=6.1567 cyc=16.891 mem_rd=1008.43 l1miss=1001.14 l1hwprf=0.01 l2miss=46.361 l2hwprf=557.99 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=7 s5: lat=6.2246 cyc=17.076 mem_rd=1009.16 l1miss=1001.25 l1hwprf=0.01 l2miss=50.999 l2hwprf=630.63 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=7 s6: lat=6.1638 cyc=16.908 mem_rd=1008.67 l1miss=1001.21 l1hwprf=0.01 l2miss=48.086 l2hwprf=553.68 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=7 s7: lat=6.0852 cyc=16.695 mem_rd=1008.11 l1miss=1001.14 l1hwprf=0.01 l2miss=41.841 l2hwprf=521.21 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=7 s8: lat=6.0757 cyc=16.667 mem_rd=1008.10 l1miss=1001.17 l1hwprf=0.01 l2miss=40.842 l2hwprf=525.88 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=7 s9: lat=6.1203 cyc=16.787 mem_rd=1008.67 l1miss=1001.15 l1hwprf=0.01 l2miss=44.871 l2hwprf=512.03 -->
| 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b | 2048 | seed=42 | base | 512 | 10 | 6.044 [6.032, 6.132] | 16.581 [16.550, 16.823] | 1008.624 [1008.185, 1009.313] | 1001.170 [1001.116, 1001.279] | 0.011 [0.010, 0.012] | 39.175 [38.746, 44.824] | 466.886 [465.013, 498.695] | no |
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=42 s0: lat=6.1081 cyc=16.756 mem_rd=1008.71 l1miss=1001.14 l1hwprf=0.01 l2miss=42.904 l2hwprf=477.31 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=42 s1: lat=6.0493 cyc=16.595 mem_rd=1008.77 l1miss=1001.20 l1hwprf=0.01 l2miss=39.191 l2hwprf=464.92 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=42 s2: lat=6.0321 cyc=16.550 mem_rd=1007.82 l1miss=1001.10 l1hwprf=0.01 l2miss=39.159 l2hwprf=465.89 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=42 s3: lat=6.1424 cyc=16.851 mem_rd=1009.54 l1miss=1001.33 l1hwprf=0.01 l2miss=45.464 l2hwprf=505.82 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=42 s4: lat=6.1396 cyc=16.845 mem_rd=1008.17 l1miss=1001.13 l1hwprf=0.01 l2miss=46.817 l2hwprf=548.01 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=42 s5: lat=5.9985 cyc=16.456 mem_rd=1008.23 l1miss=1001.11 l1hwprf=0.01 l2miss=36.660 l2hwprf=467.88 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=42 s6: lat=6.1564 cyc=16.888 mem_rd=1009.56 l1miss=1001.32 l1hwprf=0.01 l2miss=45.946 l2hwprf=554.13 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=42 s7: lat=5.9879 cyc=16.422 mem_rd=1008.53 l1miss=1001.20 l1hwprf=0.01 l2miss=36.057 l2hwprf=426.87 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=42 s8: lat=6.0381 cyc=16.566 mem_rd=1007.05 l1miss=1001.02 l1hwprf=0.01 l2miss=38.667 l2hwprf=465.29 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=42 s9: lat=6.0334 cyc=16.549 mem_rd=1009.49 l1miss=1001.30 l1hwprf=0.01 l2miss=38.985 l2hwprf=463.64 -->
| 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b | 2048 | seed=1337 | base | 512 | 10 | 6.131 [6.101, 6.169] | 16.820 [16.739, 16.925] | 1008.136 [1007.861, 1008.615] | 1001.137 [1001.096, 1001.205] | 0.009 [0.009, 0.011] | 45.626 [44.188, 48.460] | 556.565 [530.190, 573.504] | no |
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=1337 s0: lat=6.1393 cyc=16.845 mem_rd=1007.85 l1miss=1001.09 l1hwprf=0.01 l2miss=45.863 l2hwprf=564.29 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=1337 s1: lat=6.0306 cyc=16.544 mem_rd=1007.91 l1miss=1001.10 l1hwprf=0.01 l2miss=38.707 l2hwprf=519.13 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=1337 s2: lat=6.0828 cyc=16.688 mem_rd=1007.93 l1miss=1001.12 l1hwprf=0.01 l2miss=43.177 l2hwprf=548.70 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=1337 s3: lat=6.1790 cyc=16.952 mem_rd=1008.63 l1miss=1001.22 l1hwprf=0.01 l2miss=49.325 l2hwprf=574.79 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=1337 s4: lat=6.1133 cyc=16.773 mem_rd=1008.89 l1miss=1001.23 l1hwprf=0.01 l2miss=45.005 l2hwprf=524.02 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=1337 s5: lat=6.0972 cyc=16.728 mem_rd=1008.84 l1miss=1001.22 l1hwprf=0.01 l2miss=43.916 l2hwprf=517.46 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=1337 s6: lat=6.1240 cyc=16.801 mem_rd=1008.56 l1miss=1001.17 l1hwprf=0.01 l2miss=45.753 l2hwprf=548.84 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=1337 s7: lat=6.2011 cyc=17.013 mem_rd=1007.61 l1miss=1001.07 l1hwprf=0.01 l2miss=51.388 l2hwprf=625.68 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=1337 s8: lat=6.1381 cyc=16.840 mem_rd=1008.34 l1miss=1001.16 l1hwprf=0.01 l2miss=45.500 l2hwprf=569.65 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=1337 s9: lat=6.1985 cyc=17.006 mem_rd=1007.75 l1miss=1001.07 l1hwprf=0.01 l2miss=50.424 l2hwprf=619.46 -->
| 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b | 2048 | seed=20260928 | base | 512 | 10 | 6.068 [6.041, 6.120] | 16.646 [16.574, 16.788] | 1008.568 [1008.276, 1008.789] | 1001.193 [1001.163, 1001.226] | 0.011 [0.009, 0.011] | 41.610 [39.467, 44.997] | 520.118 [496.232, 537.234] | no |
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=20260928 s0: lat=6.0075 cyc=16.482 mem_rd=1008.24 l1miss=1001.14 l1hwprf=0.01 l2miss=36.699 l2hwprf=442.33 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=20260928 s1: lat=6.0647 cyc=16.636 mem_rd=1008.23 l1miss=1001.16 l1hwprf=0.01 l2miss=41.283 l2hwprf=535.07 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=20260928 s2: lat=6.0391 cyc=16.569 mem_rd=1007.69 l1miss=1001.07 l1hwprf=0.01 l2miss=39.286 l2hwprf=497.82 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=20260928 s3: lat=6.1203 cyc=16.789 mem_rd=1008.62 l1miss=1001.22 l1hwprf=0.01 l2miss=44.208 l2hwprf=537.96 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=20260928 s4: lat=6.1186 cyc=16.783 mem_rd=1008.79 l1miss=1001.25 l1hwprf=0.01 l2miss=45.260 l2hwprf=526.65 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=20260928 s5: lat=6.1547 cyc=16.881 mem_rd=1008.37 l1miss=1001.17 l1hwprf=0.01 l2miss=46.388 l2hwprf=596.69 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=20260928 s6: lat=6.1803 cyc=16.952 mem_rd=1008.91 l1miss=1001.23 l1hwprf=0.01 l2miss=49.277 l2hwprf=606.93 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=20260928 s7: lat=6.0480 cyc=16.589 mem_rd=1008.51 l1miss=1001.19 l1hwprf=0.01 l2miss=40.011 l2hwprf=495.70 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=20260928 s8: lat=5.9972 cyc=16.453 mem_rd=1008.79 l1miss=1001.20 l1hwprf=0.01 l2miss=36.271 l2hwprf=473.33 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2048K seed=20260928 s9: lat=6.0715 cyc=16.657 mem_rd=1009.25 l1miss=1001.31 l1hwprf=0.01 l2miss=41.937 l2hwprf=513.59 -->
| 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b | 2304 | seed=7 | base | 512 | 10 | 6.191 [6.163, 6.271] | 16.983 [16.908, 17.203] | 1008.517 [1007.820, 1008.785] | 1001.176 [1001.099, 1001.235] | 0.011 [0.010, 0.012] | 47.187 [44.784, 51.906] | 546.244 [526.087, 565.655] | no |
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=7 s0: lat=6.2050 cyc=17.023 mem_rd=1008.54 l1miss=1001.17 l1hwprf=0.01 l2miss=48.151 l2hwprf=545.26 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=7 s1: lat=6.1627 cyc=16.906 mem_rd=1007.79 l1miss=1001.09 l1hwprf=0.01 l2miss=45.071 l2hwprf=496.54 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=7 s2: lat=6.2877 cyc=17.248 mem_rd=1008.81 l1miss=1001.25 l1hwprf=0.01 l2miss=52.952 l2hwprf=605.73 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=7 s3: lat=6.3050 cyc=17.298 mem_rd=1007.91 l1miss=1001.11 l1hwprf=0.01 l2miss=54.802 l2hwprf=570.49 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=7 s4: lat=6.1766 cyc=16.942 mem_rd=1008.71 l1miss=1001.20 l1hwprf=0.01 l2miss=46.223 l2hwprf=524.35 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=7 s5: lat=6.2216 cyc=17.068 mem_rd=1008.50 l1miss=1001.18 l1hwprf=0.01 l2miss=48.767 l2hwprf=551.14 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=7 s6: lat=6.1303 cyc=16.819 mem_rd=1007.34 l1miss=1001.05 l1hwprf=0.01 l2miss=43.234 l2hwprf=490.72 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=7 s7: lat=6.1595 cyc=16.892 mem_rd=1009.16 l1miss=1001.25 l1hwprf=0.01 l2miss=44.576 l2hwprf=531.29 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=7 s8: lat=6.1659 cyc=16.915 mem_rd=1007.65 l1miss=1001.09 l1hwprf=0.01 l2miss=44.688 l2hwprf=547.22 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=7 s9: lat=6.3053 cyc=17.293 mem_rd=1008.92 l1miss=1001.26 l1hwprf=0.01 l2miss=54.570 l2hwprf=595.12 -->
| 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b | 2304 | seed=42 | base | 512 | 10 | 6.219 [6.174, 6.276] | 17.059 [16.938, 17.215] | 1008.649 [1008.428, 1008.967] | 1001.192 [1001.169, 1001.264] | 0.011 [0.010, 0.011] | 48.555 [45.840, 52.560] | 561.684 [523.616, 582.713] | no |
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=42 s0: lat=6.3903 cyc=17.529 mem_rd=1009.70 l1miss=1001.35 l1hwprf=0.02 l2miss=61.413 l2hwprf=646.72 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=42 s1: lat=6.2146 cyc=17.046 mem_rd=1008.53 l1miss=1001.15 l1hwprf=0.01 l2miss=48.236 l2hwprf=548.84 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=42 s2: lat=6.3105 cyc=17.305 mem_rd=1009.04 l1miss=1001.29 l1hwprf=0.01 l2miss=54.373 l2hwprf=584.27 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=42 s3: lat=6.1395 cyc=16.840 mem_rd=1008.39 l1miss=1001.17 l1hwprf=0.01 l2miss=43.332 l2hwprf=496.54 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=42 s4: lat=6.2783 cyc=17.220 mem_rd=1008.61 l1miss=1001.18 l1hwprf=0.01 l2miss=52.131 l2hwprf=574.53 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=42 s5: lat=6.1641 cyc=16.910 mem_rd=1008.74 l1miss=1001.20 l1hwprf=0.01 l2miss=45.363 l2hwprf=546.51 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=42 s6: lat=6.1244 cyc=16.798 mem_rd=1008.69 l1miss=1001.23 l1hwprf=0.01 l2miss=42.153 l2hwprf=490.44 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=42 s7: lat=6.2705 cyc=17.198 mem_rd=1009.14 l1miss=1001.28 l1hwprf=0.01 l2miss=52.703 l2hwprf=583.64 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=42 s8: lat=6.2056 cyc=17.022 mem_rd=1008.35 l1miss=1001.18 l1hwprf=0.01 l2miss=47.270 l2hwprf=515.99 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=42 s9: lat=6.2229 cyc=17.072 mem_rd=1008.36 l1miss=1001.16 l1hwprf=0.01 l2miss=48.875 l2hwprf=579.93 -->
| 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b | 2304 | seed=1337 | base | 512 | 10 | 6.298 [6.234, 6.324] | 17.277 [17.097, 17.348] | 1008.464 [1008.148, 1008.974] | 1001.179 [1001.138, 1001.252] | 0.010 [0.009, 0.011] | 53.658 [49.292, 56.891] | 568.661 [546.064, 616.993] | no |
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=1337 s0: lat=6.2916 cyc=17.259 mem_rd=1009.68 l1miss=1001.34 l1hwprf=0.01 l2miss=53.168 l2hwprf=563.59 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=1337 s1: lat=6.3084 cyc=17.306 mem_rd=1008.32 l1miss=1001.16 l1hwprf=0.01 l2miss=55.135 l2hwprf=614.11 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=1337 s2: lat=6.3936 cyc=17.538 mem_rd=1008.54 l1miss=1001.16 l1hwprf=0.01 l2miss=59.941 l2hwprf=629.93 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=1337 s3: lat=6.4060 cyc=17.573 mem_rd=1008.39 l1miss=1001.19 l1hwprf=0.01 l2miss=61.442 l2hwprf=617.96 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=1337 s4: lat=6.1893 cyc=16.981 mem_rd=1007.89 l1miss=1001.10 l1hwprf=0.01 l2miss=46.430 l2hwprf=511.09 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=1337 s5: lat=6.3292 cyc=17.362 mem_rd=1009.23 l1miss=1001.29 l1hwprf=0.01 l2miss=57.476 l2hwprf=620.64 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=1337 s6: lat=6.3044 cyc=17.294 mem_rd=1008.55 l1miss=1001.21 l1hwprf=0.01 l2miss=54.148 l2hwprf=545.56 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=1337 s7: lat=6.2808 cyc=17.226 mem_rd=1009.12 l1miss=1001.27 l1hwprf=0.01 l2miss=52.757 l2hwprf=573.73 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=1337 s8: lat=6.1630 cyc=16.907 mem_rd=1007.88 l1miss=1001.13 l1hwprf=0.01 l2miss=44.630 l2hwprf=504.52 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=1337 s9: lat=6.2180 cyc=17.054 mem_rd=1008.09 l1miss=1001.12 l1hwprf=0.01 l2miss=48.136 l2hwprf=547.58 -->
| 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b | 2304 | seed=20260928 | base | 512 | 10 | 6.275 [6.255, 6.330] | 17.213 [17.157, 17.367] | 1008.522 [1008.049, 1009.256] | 1001.176 [1001.133, 1001.292] | 0.010 [0.009, 0.011] | 52.360 [50.635, 55.924] | 578.462 [563.467, 597.118] | no |
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=20260928 s0: lat=6.2616 cyc=17.179 mem_rd=1008.02 l1miss=1001.12 l1hwprf=0.01 l2miss=51.987 l2hwprf=581.39 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=20260928 s1: lat=6.4160 cyc=17.596 mem_rd=1009.39 l1miss=1001.31 l1hwprf=0.01 l2miss=61.404 l2hwprf=633.84 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=20260928 s2: lat=6.1203 cyc=16.783 mem_rd=1007.02 l1miss=1001.00 l1hwprf=0.01 l2miss=41.950 l2hwprf=458.19 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=20260928 s3: lat=6.3706 cyc=17.473 mem_rd=1008.43 l1miss=1001.17 l1hwprf=0.01 l2miss=58.735 l2hwprf=630.78 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=20260928 s4: lat=6.3380 cyc=17.389 mem_rd=1007.76 l1miss=1001.12 l1hwprf=0.01 l2miss=56.200 l2hwprf=597.41 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=20260928 s5: lat=6.2875 cyc=17.248 mem_rd=1008.14 l1miss=1001.16 l1hwprf=0.01 l2miss=52.732 l2hwprf=575.54 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=20260928 s6: lat=6.2579 cyc=17.164 mem_rd=1008.62 l1miss=1001.18 l1hwprf=0.01 l2miss=50.709 l2hwprf=567.01 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=20260928 s7: lat=6.1811 cyc=16.952 mem_rd=1008.87 l1miss=1001.25 l1hwprf=0.01 l2miss=46.361 l2hwprf=528.93 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=20260928 s8: lat=6.3074 cyc=17.301 mem_rd=1009.71 l1miss=1001.33 l1hwprf=0.01 l2miss=55.097 l2hwprf=596.23 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b2304K seed=20260928 s9: lat=6.2538 cyc=17.155 mem_rd=1009.51 l1miss=1001.34 l1hwprf=0.01 l2miss=50.611 l2hwprf=562.29 -->
| 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b | 3072 | seed=7 | base | 512 | 10 | 6.527 [6.499, 6.536] | 17.904 [17.828, 17.930] | 1008.747 [1008.641, 1008.865] | 1001.236 [1001.215, 1001.258] | 0.010 [0.010, 0.012] | 63.053 [62.137, 64.012] | 660.115 [655.710, 671.239] | no |
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=7 s0: lat=6.4945 cyc=17.814 mem_rd=1008.59 l1miss=1001.24 l1hwprf=0.01 l2miss=62.361 l2hwprf=655.18 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=7 s1: lat=6.5253 cyc=17.901 mem_rd=1008.69 l1miss=1001.21 l1hwprf=0.01 l2miss=63.488 l2hwprf=658.39 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=7 s2: lat=6.5890 cyc=18.072 mem_rd=1008.90 l1miss=1001.29 l1hwprf=0.01 l2miss=67.213 l2hwprf=691.71 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=7 s3: lat=6.5345 cyc=17.926 mem_rd=1008.88 l1miss=1001.23 l1hwprf=0.01 l2miss=63.271 l2hwprf=671.16 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=7 s4: lat=6.5718 cyc=18.027 mem_rd=1008.83 l1miss=1001.26 l1hwprf=0.01 l2miss=66.976 l2hwprf=694.20 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=7 s5: lat=6.4637 cyc=17.729 mem_rd=1008.80 l1miss=1001.24 l1hwprf=0.01 l2miss=58.347 l2hwprf=643.15 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=7 s6: lat=6.5145 cyc=17.871 mem_rd=1008.69 l1miss=1001.23 l1hwprf=0.01 l2miss=62.062 l2hwprf=657.31 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=7 s7: lat=6.5280 cyc=17.906 mem_rd=1008.63 l1miss=1001.17 l1hwprf=0.01 l2miss=62.835 l2hwprf=671.27 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=7 s8: lat=6.5368 cyc=17.931 mem_rd=1008.60 l1miss=1001.21 l1hwprf=0.01 l2miss=64.187 l2hwprf=661.84 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=7 s9: lat=6.4325 cyc=17.644 mem_rd=1009.01 l1miss=1001.27 l1hwprf=0.01 l2miss=57.233 l2hwprf=627.06 -->
| 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b | 3072 | seed=42 | base | 512 | 10 | 6.528 [6.505, 6.543] | 17.905 [17.842, 17.945] | 1009.178 [1008.974, 1009.291] | 1001.288 [1001.274, 1001.312] | 0.010 [0.009, 0.011] | 63.097 [61.352, 64.283] | 662.010 [655.235, 663.018] | no |
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=42 s0: lat=6.4377 cyc=17.661 mem_rd=1007.82 l1miss=1001.11 l1hwprf=0.01 l2miss=57.633 l2hwprf=617.24 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=42 s1: lat=6.5396 cyc=17.937 mem_rd=1008.96 l1miss=1001.29 l1hwprf=0.01 l2miss=64.042 l2hwprf=663.23 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=42 s2: lat=6.5043 cyc=17.842 mem_rd=1008.88 l1miss=1001.24 l1hwprf=0.01 l2miss=61.053 l2hwprf=657.83 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=42 s3: lat=6.5436 cyc=17.947 mem_rd=1009.29 l1miss=1001.29 l1hwprf=0.01 l2miss=64.363 l2hwprf=662.09 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=42 s4: lat=6.5196 cyc=17.883 mem_rd=1009.28 l1miss=1001.30 l1hwprf=0.01 l2miss=62.787 l2hwprf=654.37 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=42 s5: lat=6.5061 cyc=17.843 mem_rd=1009.11 l1miss=1001.27 l1hwprf=0.01 l2miss=62.251 l2hwprf=662.39 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=42 s6: lat=6.5592 cyc=17.989 mem_rd=1009.25 l1miss=1001.32 l1hwprf=0.01 l2miss=66.082 l2hwprf=681.62 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=42 s7: lat=6.5667 cyc=18.009 mem_rd=1009.47 l1miss=1001.34 l1hwprf=0.01 l2miss=65.584 l2hwprf=688.89 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=42 s8: lat=6.5363 cyc=17.928 mem_rd=1009.01 l1miss=1001.28 l1hwprf=0.01 l2miss=63.408 l2hwprf=661.93 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=42 s9: lat=6.4022 cyc=17.560 mem_rd=1009.31 l1miss=1001.31 l1hwprf=0.01 l2miss=54.648 l2hwprf=616.22 -->
| 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b | 3072 | seed=1337 | base | 512 | 10 | 6.498 [6.484, 6.524] | 17.823 [17.785, 17.895] | 1008.615 [1008.509, 1009.051] | 1001.226 [1001.218, 1001.254] | 0.009 [0.008, 0.011] | 61.635 [60.026, 62.778] | 655.020 [643.737, 664.380] | no |
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=1337 s0: lat=6.5004 cyc=17.832 mem_rd=1008.44 l1miss=1001.20 l1hwprf=0.01 l2miss=61.552 l2hwprf=642.94 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=1337 s1: lat=6.4935 cyc=17.813 mem_rd=1008.52 l1miss=1001.19 l1hwprf=0.01 l2miss=60.664 l2hwprf=649.13 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=1337 s2: lat=6.4796 cyc=17.771 mem_rd=1008.69 l1miss=1001.23 l1hwprf=0.01 l2miss=59.814 l2hwprf=638.18 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=1337 s3: lat=6.5660 cyc=18.009 mem_rd=1008.50 l1miss=1001.22 l1hwprf=0.01 l2miss=65.847 l2hwprf=668.45 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=1337 s4: lat=6.5265 cyc=17.903 mem_rd=1008.84 l1miss=1001.24 l1hwprf=0.01 l2miss=62.941 l2hwprf=665.44 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=1337 s5: lat=6.4963 cyc=17.815 mem_rd=1009.12 l1miss=1001.26 l1hwprf=0.01 l2miss=61.718 l2hwprf=660.91 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=1337 s6: lat=6.4811 cyc=17.776 mem_rd=1008.54 l1miss=1001.22 l1hwprf=0.01 l2miss=59.554 l2hwprf=646.12 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=1337 s7: lat=6.6109 cyc=18.130 mem_rd=1009.71 l1miss=1001.36 l1hwprf=0.01 l2miss=68.812 l2hwprf=688.65 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=1337 s8: lat=6.5159 cyc=17.873 mem_rd=1009.24 l1miss=1001.29 l1hwprf=0.01 l2miss=62.287 l2hwprf=661.21 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=1337 s9: lat=6.4331 cyc=17.646 mem_rd=1008.46 l1miss=1001.22 l1hwprf=0.01 l2miss=57.836 l2hwprf=621.56 -->
| 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b | 3072 | seed=20260928 | base | 512 | 10 | 6.486 [6.462, 6.497] | 17.789 [17.724, 17.822] | 1008.746 [1008.445, 1009.102] | 1001.241 [1001.198, 1001.284] | 0.010 [0.007, 0.011] | 60.775 [58.833, 61.361] | 646.348 [635.995, 652.700] | no |
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=20260928 s0: lat=6.4473 cyc=17.685 mem_rd=1008.77 l1miss=1001.26 l1hwprf=0.01 l2miss=58.146 l2hwprf=631.06 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=20260928 s1: lat=6.5069 cyc=17.848 mem_rd=1008.50 l1miss=1001.23 l1hwprf=0.01 l2miss=60.891 l2hwprf=656.59 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=20260928 s2: lat=6.4888 cyc=17.794 mem_rd=1009.45 l1miss=1001.33 l1hwprf=0.01 l2miss=61.229 l2hwprf=648.42 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=20260928 s3: lat=6.4982 cyc=17.826 mem_rd=1008.39 l1miss=1001.19 l1hwprf=0.01 l2miss=62.109 l2hwprf=653.72 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=20260928 s4: lat=6.4826 cyc=17.782 mem_rd=1009.19 l1miss=1001.29 l1hwprf=0.01 l2miss=61.404 l2hwprf=640.87 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=20260928 s5: lat=6.4937 cyc=17.810 mem_rd=1009.38 l1miss=1001.33 l1hwprf=0.01 l2miss=60.070 l2hwprf=644.28 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=20260928 s6: lat=6.5913 cyc=18.078 mem_rd=1008.84 l1miss=1001.25 l1hwprf=0.01 l2miss=69.059 l2hwprf=688.01 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=20260928 s7: lat=6.4506 cyc=17.693 mem_rd=1008.72 l1miss=1001.22 l1hwprf=0.01 l2miss=58.421 l2hwprf=634.37 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=20260928 s8: lat=6.4553 cyc=17.704 mem_rd=1008.32 l1miss=1001.17 l1hwprf=0.01 l2miss=57.583 l2hwprf=632.86 -->
<!-- sample 20260928T025119Z-ptr-chase-sm8650-x4-p0prime-long-base-r2b b3072K seed=20260928 s9: lat=6.4834 cyc=17.785 mem_rd=1008.43 l1miss=1001.19 l1hwprf=0.01 l2miss=60.660 l2hwprf=649.66 -->

## rejected samples/records

- 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base/buffer=1024KiB: record status=failed [environment-postcondition-failed]
- 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base/buffer=1216KiB: record status=failed [environment-precondition-failed]
- 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base/buffer=1216KiB: record status=failed [environment-precondition-failed]
- 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base/buffer=1216KiB: record status=failed [environment-precondition-failed]
- 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base/buffer=1216KiB: record status=failed [environment-precondition-failed]
- 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base/buffer=1408KiB: record status=failed [environment-precondition-failed]
- 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base/buffer=1408KiB: record status=failed [environment-precondition-failed]
- 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base/buffer=1408KiB: record status=failed [environment-precondition-failed]
- 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base/buffer=1408KiB: record status=failed [environment-precondition-failed]
- 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base/buffer=1792KiB: record status=failed [environment-precondition-failed]
- 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base/buffer=1792KiB: record status=failed [environment-precondition-failed]
- 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base/buffer=1792KiB: record status=failed [environment-precondition-failed]
- 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base/buffer=1792KiB: record status=failed [environment-precondition-failed]
- 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base/buffer=2048KiB: record status=failed [environment-precondition-failed]
- 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base/buffer=2048KiB: record status=failed [environment-precondition-failed]
- 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base/buffer=2048KiB: record status=failed [environment-precondition-failed]
- 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base/buffer=2048KiB: record status=failed [environment-precondition-failed]
- 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base/buffer=2304KiB: record status=failed [environment-precondition-failed]
- 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base/buffer=2304KiB: record status=failed [environment-precondition-failed]
- 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base/buffer=2304KiB: record status=failed [environment-precondition-failed]
- 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base/buffer=2304KiB: record status=failed [environment-precondition-failed]
- 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base/buffer=3072KiB: record status=failed [environment-precondition-failed]
- 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base/buffer=3072KiB: record status=failed [environment-precondition-failed]
- 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base/buffer=3072KiB: record status=failed [environment-precondition-failed]
- 20260928T024353Z-ptr-chase-sm8650-x4-p0prime-long-base/buffer=3072KiB: record status=failed [environment-precondition-failed]
- 20260928T025226Z-ptr-chase-sm8650-x4-p0prime-short-thp/buffer=2304KiB: record status=failed [environment-precondition-failed]
- 20260928T025226Z-ptr-chase-sm8650-x4-p0prime-short-thp/buffer=2304KiB: record status=failed [environment-precondition-failed]
- 20260928T025226Z-ptr-chase-sm8650-x4-p0prime-short-thp/buffer=2304KiB: record status=failed [environment-precondition-failed]
- 20260928T025226Z-ptr-chase-sm8650-x4-p0prime-short-thp/buffer=2304KiB: record status=failed [environment-precondition-failed]
- 20260928T025226Z-ptr-chase-sm8650-x4-p0prime-short-thp/buffer=3072KiB: record status=failed [environment-precondition-failed]
- 20260928T025226Z-ptr-chase-sm8650-x4-p0prime-short-thp/buffer=3072KiB: record status=failed [environment-precondition-failed]
- 20260928T025226Z-ptr-chase-sm8650-x4-p0prime-short-thp/buffer=3072KiB: record status=failed [environment-precondition-failed]
- 20260928T025226Z-ptr-chase-sm8650-x4-p0prime-short-thp/buffer=3072KiB: record status=failed [environment-precondition-failed]
- 20260928T122738Z-ptr-chase-sm8650-x4-p0prime-short-thp/buffer=2304KiB: record status=failed [environment-precondition-failed]
- 20260928T122738Z-ptr-chase-sm8650-x4-p0prime-short-thp/buffer=2304KiB: record status=failed [environment-precondition-failed]
- 20260928T122738Z-ptr-chase-sm8650-x4-p0prime-short-thp/buffer=2304KiB: record status=failed [environment-precondition-failed]
- 20260928T122738Z-ptr-chase-sm8650-x4-p0prime-short-thp/buffer=2304KiB: record status=failed [environment-precondition-failed]
- 20260928T122738Z-ptr-chase-sm8650-x4-p0prime-short-thp/buffer=3072KiB: record status=failed [environment-precondition-failed]
- 20260928T122738Z-ptr-chase-sm8650-x4-p0prime-short-thp/buffer=3072KiB: record status=failed [environment-precondition-failed]
- 20260928T122738Z-ptr-chase-sm8650-x4-p0prime-short-thp/buffer=3072KiB: record status=failed [environment-precondition-failed]
- 20260928T122738Z-ptr-chase-sm8650-x4-p0prime-short-thp/buffer=3072KiB: record status=failed [environment-precondition-failed]
