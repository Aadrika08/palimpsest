"""CLI for puck v4 stage S1 scene-ID admission; default --plan-only (no reads, no writes).

See src/palimpsest/puck_v4_scene_admission.py and the v4 protocol S1 section.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from palimpsest.puck_v4_scene_admission import main  # noqa: E402

if __name__ == '__main__':
    sys.exit(main())
