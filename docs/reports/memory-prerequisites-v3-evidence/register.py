"""Freeze v3 and protect the original consumed v2 evidence; no SNP decoding."""
import importlib.util
from pathlib import Path

source = Path(__file__).resolve().parents[1]/'memory-prerequisites-v2-evidence/register.py'
spec = importlib.util.spec_from_file_location('shared_prerequisite_preparer',source)
preparer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preparer)

if __name__ == '__main__':
    here = Path(__file__).resolve()
    baseline = here.parents[3].parent/'memory-prerequisites-v2/docs/reports/memory-prerequisites-v2-evidence/registration.json'
    raise SystemExit(preparer.main('v3',evidence=here.parent,baseline_path=baseline,
                                  registration_preparer_path=here))
