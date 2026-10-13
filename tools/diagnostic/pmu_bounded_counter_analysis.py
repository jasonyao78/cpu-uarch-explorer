"""Fixed-attempt policy; loss based solely on observed metadata, never signals."""
from tools.diagnostic import pmu_own_counter_analysis as original
_same=original._same
EVIDENCE='docs/reviews/evidence/2026-10-13-pmu-bounded-counter'
PROTOCOL='docs/design/2026-10-13-pmu-bounded-counter.md'
CONSUMER='tools/diagnostic/pmu_bounded_counter_analysis.py'
DRIVER='tools/diagnostic/run_sm8650_pmu_bounded_counter.py'
def expected(epoch):
 p=original.expected(epoch);p.update(version=2,invalid_window_budget=1,attempts=24);return p
def audit_process(rr,p):return original.audit_process(rr,p,bounded=True)
