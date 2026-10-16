"""Compile the distinct11 templates and derive the pre-observer guard on an isolated fixture.

Never instantiates into /tmp tool paths, runs a guard, admission, observer, auditor or runtime.
"""
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
VALIDATION=ROOT/'docs/plans/puck-cpu-held-qualification-11-control-validation'
TEMPLATES=['pre-admission-guard.py.in','tools/run-admission-once.py.in','tools/make-observer-guard.py','tools/run-observer-once.py.in',
    'tools/bind-audit-command.py','tools/run-audit-once.py.in','tools/collect-outcome.py.in','tools/archive-evidence.py.in','tools/instantiate.py']


def instantiate(name):
    return (VALIDATION/name).read_text().replace('@CONTROL@','f'*40).replace('@COUNT@','99')


class ToolChecks(unittest.TestCase):
    def test_templates_compile_without_unknown_placeholders(self):
        for name in TEMPLATES:
            text=instantiate(name)
            compile(text,name,'exec')
            if name!='tools/make-observer-guard.py':self.assertNotIn('@',text,name)
            self.assertNotIn('held10',text,name)
            self.assertNotIn('qualification-10',text.replace('docs/reports/puck-cpu-held-qualification-10/verify_evidence.py',''),name)

    def test_make_observer_guard_derives_pre_observer_guard_on_fixture(self):
        with tempfile.TemporaryDirectory(prefix='held11-tools-') as directory:
            fixture=Path(directory)
            (fixture/'palimpsest-held11-pre-admission-guard.py').write_text(instantiate('pre-admission-guard.py.in'))
            (fixture/'palimpsest-puck-cpu-held-qualification-11-admission-01.json').write_text('{"fixture":true}\n')
            (fixture/'palimpsest-held11-independent-admission-review.json').write_text('{"decision":"GO"}\n')
            source=(VALIDATION/'tools/make-observer-guard.py').read_text()
            # Redirect only the maker's own four I/O paths; embedded guard paths stay /tmp.
            for line in ("source=Path('/tmp/palimpsest-held11-pre-admission-guard.py').read_text()\n",
                    "admission=Path('/tmp/palimpsest-puck-cpu-held-qualification-11-admission-01.json').read_bytes()\n",
                    "review_path=Path('/tmp/palimpsest-held11-independent-admission-review.json')\nreview_raw",
                    "path=Path('/tmp/palimpsest-held11-pre-observer-guard.py')\n"):
                self.assertEqual(source.count(line),1,line)
                source=source.replace(line,line.replace('/tmp/',str(fixture)+'/'))
            exec(compile(source,'make-observer-guard.py','exec'),{'__name__':'fixture'})
            derived=(fixture/'palimpsest-held11-pre-observer-guard.py').read_text()
        compile(derived,'pre-observer-guard.py','exec')
        for present in ('before the sole runtime observer.',"status='PASS_PRE_OBSERVER_GUARD_ONLY'",
                'absence=dict(future_output_paths=future,historical_missing_receipts=17);resources=module.resources()',
                'historical_records_unchanged=102,admission_main_invoked=True,admission_receipt_sha256=',
                "Path('/tmp/palimpsest-held11-pre-observer-guard01.json').open('x')",'assert len(future)==len(set(future))==12',
                "assert not os.path.lexists('/tmp/palimpsest-puck-cpu-held-qualification-11-admission-02.json')",
                "a['admission_check_id']==1 and a['qualification11_invoked'] is False",
                "before=json.loads((ROOT/(BASE+'-control-validation/historical-before-admission.json')).read_bytes())"):
            self.assertEqual(derived.count(present),1,present)
        for absent in ('PASS_PRE_ADMISSION_GUARD_ONLY','absence=module.absent()','admission_main_invoked=False','@',
                "pre-admission-guard01.json').open('x')"):
            self.assertNotIn(absent,derived)


if __name__=='__main__':unittest.main(verbosity=2)
