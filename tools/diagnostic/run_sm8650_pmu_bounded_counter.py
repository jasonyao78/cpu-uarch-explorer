#!/usr/bin/env python3
"""Purpose: new fixed-budget counter qualification, full restore transaction."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.diagnostic import run_sm8650_pmu_own_counter as controller
from tools.diagnostic import pmu_bounded_counter_analysis as model
def main(argv=None):
 old=(controller.model,controller.PROTOCOL,controller.DRIVER)
 try:
  controller.model=model;controller.PROTOCOL=model.PROTOCOL;controller.DRIVER=model.DRIVER
  return controller.main(argv)
 finally:controller.model,controller.PROTOCOL,controller.DRIVER=old
if __name__=='__main__':raise SystemExit(main())
