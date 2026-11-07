import json
import math
from fractions import Fraction
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build_audit_affordability as b


def test_log_budget_is_certified_and_tight():
    b.certify_log_upper(b.LOG_UPPER, b.K / b.ALPHA)
    assert math.log(60) < float(b.LOG_UPPER) < math.log(60) + 1e-3
    with pytest.raises(ValueError):
        b.certify_log_upper(Fraction(4), b.K / b.ALPHA)  # 4 < log 60


def test_retained_numbers_and_conservative_rounding():
    v = b.compute(json.loads(b.ACCOUNTING.read_text()))
    assert v['charged'] == Fraction('1222.455497')
    assert v['per_scenario'] == Fraction('1214.384515') / 4
    # Feasibility report: 205 / 819 / 3,276 scenarios for radius .2/.1/.05.
    assert [n for _, n, _ in v['required']] == [205, 819, 3276]
    assert v['affordable'] == {'audit': 7, 'total': 280}
    for key, n in v['affordable'].items():
        assert v['radius'][key] ** 2 >= 2 * b.LOG_UPPER / n
    assert v['radius']['audit'] > 1  # vacuous for contrasts in [-1, 1]


def test_incomplete_accounting_refuses():
    raw = json.loads(b.ACCOUNTING.read_text())
    raw['accounting']['accounting_complete'] = False
    with pytest.raises(ValueError):
        b.compute(raw)


def test_generated_output_is_current():
    assert b.OUTPUT.read_text() == b.render(b.compute(json.loads(b.ACCOUNTING.read_text())))
