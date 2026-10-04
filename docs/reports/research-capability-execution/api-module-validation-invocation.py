import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    results = []
    for module in ['tests/test_lab.py', 'tests/test_male_lab.py', 'tests/test_memory_branch.py']:
        command = [sys.executable, '/tmp/palimpsest-research-checks.py', '-q', module, '-o', 'faulthandler_timeout=30']
        log = Path('/tmp') / ('palimpsest-' + Path(module).stem + '-isolated.log')
        start = time.monotonic()
        with log.open('w') as output:
            try:
                process = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, timeout=90, check=False, env=os.environ.copy())
                status = process.returncode
            except subprocess.TimeoutExpired:
                status = 'timeout'
        item = {'module': module, 'command': command, 'returncode': status, 'seconds': time.monotonic() - start, 'log': str(log)}
        results.append(item)
        print(json.dumps(item), flush=True)
        Path('/tmp/palimpsest-api-module-checks.json').write_text(json.dumps(results, indent=2) + '\n')
    return 0 if all(item['returncode'] == 0 for item in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
