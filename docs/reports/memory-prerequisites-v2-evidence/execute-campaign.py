"""One fresh prerequisite campaign under the reviewed whole-invocation watchdog."""
import importlib.util
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

from scripts import memory_decision_pilot as p, memory_restore_diagnostic as d
from scripts import memory_prerequisites_v2 as m

source = Path(__file__).resolve().parents[1]/'restore-qualification-v2-evidence/execute-restore-v2.py'
spec = importlib.util.spec_from_file_location('shared_restore_supervisor', source)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
runner.__file__ = __file__
runner.MODE = 'prerequisites-v2'
runner.PASS_KEY = 'native_prerequisites_passed'
runner.WATCHDOG_SECONDS = 4890
runner.d = SimpleNamespace(sys=sys, validate_v2_registration=m.validate_registration,
    recheck_v2_inputs=m.recheck_inputs, restore_v2_budget=m.budget,
    cleanup_owners=d.cleanup_owners, owner_exited=d.owner_exited,
    replace_control=d.replace_control)


def pipeline(path):
    registration = runner.admission(path)
    driver_code = 1
    try:
        driver_code = m.run(path)
    except BaseException as error:
        print(p.canonical({'driver_error':type(error).__name__, 'message':str(error)}).decode(), flush=True)
    root = Path(registration['output'])
    audit_code = m.audit(path) if root.exists() else 1
    close = p.read_json(root/'scientific-close.json') if (root/'scientific-close.json').exists() else {}
    return 0 if driver_code == audit_code == 0 and close.get('native_prerequisites_passed') is True else 1


runner.pipeline = pipeline


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if args == ['--bounded']:
        return runner.main([])
    if args:
        return runner.main(args)
    # The existing TERM/KILL watchdog leaves five seconds for failed-parent
    # recovery. This ancestor also encloses that recovery under the total cap.
    command = ['timeout','--signal=KILL','4900s',sys.executable,
               str(Path(__file__).resolve()),'--bounded']
    return 0 if subprocess.run(command,cwd=Path(__file__).resolve().parents[3]).returncode == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
