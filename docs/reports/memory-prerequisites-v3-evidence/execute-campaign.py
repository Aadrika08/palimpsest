"""Fresh v3 namespace with the existing original-clock campaign supervisor."""
import importlib.util
from pathlib import Path

source = Path(__file__).resolve().parents[1]/'memory-prerequisites-v2-evidence/execute-campaign.py'
spec = importlib.util.spec_from_file_location('shared_prerequisite_campaign',source)
campaign = importlib.util.module_from_spec(spec)
spec.loader.exec_module(campaign)
campaign.__file__ = __file__
runner = campaign.runner
runner.__file__ = __file__
runner.MODE = 'prerequisites-v3'
m = campaign.m
pipeline = campaign.pipeline
main = campaign.main

if __name__ == '__main__':
    raise SystemExit(main())
