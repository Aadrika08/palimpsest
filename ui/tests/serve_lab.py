"""Actual CPU/manual browser verification server; all outputs stay under ui/."""
from pathlib import Path
import os


def main():
    import uvicorn
    from palimpsest.lab import create_app
    root = Path(__file__).resolve().parents[2]
    output = root / 'ui/.lab-test-runs'
    port = int(os.environ.get('PALIMPSEST_LAB_TEST_PORT', '8766'))
    app = create_app(root, root / 'data/assets/flynn', output,
                     root / 'ui/.lab-test-exports', port=port)
    uvicorn.run(app, host='127.0.0.1', port=port, log_level='warning')


if __name__ == '__main__':
    main()
