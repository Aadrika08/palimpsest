# Recorded route SVG names and descriptions repaired

7 October 2026. The [six-mode review preparation](artwork-review-preparation.md)
found that Borrowed body's standalone route SVG had no role, title, description
or accessible label references. The shared route renderer now supplies them,
including the source run ID, the last-recorded-world boundary and recorded-view
limitations. The comparison reuses those nodes with distinct A/B IDs rather
than adding duplicate titles. Coordinates, geometry, embedded provenance and
the PNG/bundle paths are unchanged.

Two existing regression checks failed first on the missing standalone role and
missing comparison description. Both passed after the repair. The focused
artifact, comparison, export-close, offline-handoff and CLI modules then passed
**45 tests in 1.135 seconds**, with no skips. Existing Matplotlib/Pyparsing
deprecation warnings appeared. Reproduce from the documented Python environment:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests python -B -m unittest test_artifacts test_comparison test_export_close test_artwork_handoff test_cli -v
```

Independent code review found no material issue in either shared-renderer caller.
One separately bounded local readback at producer `306b52f` invoked exactly two
existing offline CLI commands against the admitted 19-file source subset:
route SVG export and recorded comparison HTML export. Its outer bound was
120 seconds with a five-second KILL grace, 64 MiB phase storage, 1 GiB free-space
floor and a two-export count cap. No model runtime, physics, historical study
driver or consumed allocation was invoked. The process drained exit zero;
prepublication elapsed was 0.133686784 seconds, not final process-return time.

| New local artifact | Bytes | SHA256 |
| --- | ---: | --- |
| `borrowed-body.svg` | 20,439 | `6186dcf6509591b767b5cef30920105a26abc5178f1d7896b27f0cb55e701aa4` |
| `one-map-many-lives.html` | 64,444 | `38ada5e6e851f9ef34120a14c20e76fd26f278faaf6417526849c4f2f1c3478d` |

The new samples and exact readback script/registration/receipt remain local at:

```text
/home/utkarsh/Work/shraddha/brain/.worktrees/artwork-route-accessibility/.superpowers/sdd/route-accessibility-readback-v1/
```

Independent read-only audit checked the actual output hashes and each SVG's
role and nonempty referenced title/description. The comparison's three SVGs
have globally unique IDs, including separate A/B world descriptions. Removing
only role/label attributes and title/description nodes yields identical complete
SVG trees to the originals; all remaining HTML and embedded metadata match.
All six historical artifacts, the 19 inputs and selected source fingerprints
remain unchanged. The recorded PID/start identity and process group were absent,
and the existing writer lease was free during a read-only probe.

The previous review ZIPs and their reported gap remain immutable historical
evidence; they have not been overwritten or silently upgraded. These two new
exports demonstrate the technical repair. Actual screen-reader testing, user
aesthetic judgment, longer material, independent full-session operation and
the other simulation goal gates remain open. This report makes no human,
scientific, exhibition or physical qualification claim.
