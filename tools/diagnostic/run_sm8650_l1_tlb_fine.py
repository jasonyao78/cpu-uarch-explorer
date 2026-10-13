#!/usr/bin/env python3
"""Purpose: finite adjacent-page L1 contrast; original controller keeps its guards.

Both actual controller source and wrapper are SHA-bound in the new build.
No policy change; new version/grid requires its own N32 qualification.
"""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.diagnostic import run_sm8650_l1_tlb_reach as controller
from tools.diagnostic import l1_tlb_fine_analysis as model
def main(argv=None):
 controller.model=model
 return controller.main(argv)
if __name__=='__main__':raise SystemExit(main())
