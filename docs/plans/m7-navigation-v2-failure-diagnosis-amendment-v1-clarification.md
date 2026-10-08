# Navigation-v2 diagnosis amendment v1 metadata-read clarification

8 October 2026. After amendment commit `1d4f98a` and before implementation,
an operator ran the following command from
`/home/utkarsh/Work/shraddha/brain/.worktrees/navigation-v2-diagnosis`:

```sh
sed -n '50,95p' scripts/evaluate_male_navigation_v2.py && sed -n '280,325p' scripts/evaluate_male_navigation_v2.py && python3 - <<'PY'
import json
from pathlib import Path
p=Path('/home/utkarsh/Work/shraddha/brain/.worktrees/male-navigation-development-v2/runs/m7-navigation-development-v2-e3f9a47-v1/report.json')
d=json.loads(p.read_text())
print(type(d), d.keys())
# print compact first result-ish structure
for key in ('results','runs','cases'):
    if key in d:
        print(key, type(d[key]), len(d[key])); print(d[key][0]); break
PY
```

The `sed` commands printed committed producer source only. The Python command
read and parsed the entire retained file
`/home/utkarsh/Work/shraddha/brain/.worktrees/male-navigation-development-v2/runs/m7-navigation-development-v2-e3f9a47-v1/report.json`.
Its exact standard output before failure was:

```text
<class 'dict'> dict_keys(['status', 'study_sha256', 'model_index_sha256', 'profile', 'contact_profile_sha256', 'source_pins', 'owners_completed', 'numeric_ticks', 'qualification_claims', 'cases', 'whole_study_free_required_bytes', 'admission_estimate', 'data_manifest_sha256', 'held_out_status', 'assets_before', 'identities_before', 'matched_scene_initials', 'assets_after', 'identities_after', 'final_source_pins', 'artifacts_sha256', 'finalization_errors', 'admission', 'wall_seconds_before_publication'])
cases <class 'dict'> 24
```

Its exact standard error was:

```text
Traceback (most recent call last):
  File "<stdin>", line 9, in <module>
KeyError: 0
```

The command exited nonzero. It wrote no file. It printed or used no case,
result, outcome or trajectory value. It opened no NPZ, chunk, event or snapshot.
The learned facts are limited to the displayed top-level key names and that
`cases` is a 24-entry dictionary; the count 24 was already frozen.

An independent reviewer who did not author correction `d582eca` ruled that
this is an extra disclosed metadata read, rather than amended invocation two.
It used neither the amended runner nor the exact fresh destination, retained no
success/failure artifact, and did not cross the protocol's NPZ trajectory-decode
boundary. This clarification records the read; it is not retroactive
authorization.

No further retained path may be read outside the sole amended runner. Original
protocol, failure, execution, source, analysis-contract and output bindings in
amendment SHA-256
`94dc0b7ead6942bc13c568f9d8e2c77af7604fe3fbaa5ea55b013f000933c41c`
remain unchanged. The exact fresh output, one amended invocation and no-third-
attempt rule remain unchanged. If this disclosure is incomplete, or if any
case/result/outcome/trajectory value was exposed or used, execution must stop
permanently.
