import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build_male_v4_development as b


def test_retained_counts_match_the_recorded_result():
    v = b.compute(json.loads(b.REPORT.read_text()))
    assert v['goals'] == {'10:old-corpus': 1, '10:augmented': 0, '11:old-corpus': 2,
                          '11:augmented': 0, '12:old-corpus': 1, '12:augmented': 0}
    assert (v['augmented']['goal'], v['augmented']['stalled'], v['augmented']['time_limit']) == (0, 9, 3)
    assert (v['old-corpus']['goal'], v['old-corpus']['stalled'], v['old-corpus']['time_limit']) == (4, 6, 2)
    assert round(v['augmented']['median'], 1) == 10.0 and round(v['old-corpus']['median'], 1) == 1.8


def test_a_modified_report_refuses():
    raw = json.loads(b.REPORT.read_text())
    raw['admission']['status'] = 'admitted'
    with pytest.raises(ValueError):
        b.compute(raw)
    raw = json.loads(b.REPORT.read_text())
    next(iter(raw['cases'].values()))['goal_reached'] = not next(iter(raw['cases'].values()))['goal_reached']
    with pytest.raises(ValueError):
        b.compute(raw)


def test_generated_output_is_current():
    assert b.OUTPUT.read_text() == b.render(b.compute(json.loads(b.REPORT.read_text())))
