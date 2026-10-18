"""Diagnostic only: build the held-provenance inputs (registration-like pins) offline.

Reads the exported 65b19fa tree, the held site's dist-info METADATA files and the
interpreter binary; writes inputs.json. Executes nothing from those trees.
"""
import hashlib, json, os, sys
from email.parser import HeaderParser

ROOT, SITE, PY, OUT = sys.argv[1:5]
DISTS = ("torch", "torchvision", "numpy", "scipy", "pandas", "scikit-learn", "mujoco", "gymnasium", "glfw",
         "opencv-python", "matplotlib", "seaborn", "networkx", "python-louvain", "py7zr")


def norm(name):
    import re
    return re.sub(r"[-_.]+", "-", name).lower()


def row(path, rel):
    with open(path, 'rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=rel, size_bytes=os.path.getsize(path), sha256=digest)


files = [row(os.path.join(ROOT, name), name) for name in ('pyproject.toml', 'uv.lock')]
upstream = os.path.join(ROOT, 'upstream', 'fly-gym')
for directory, _, names in os.walk(upstream):
    for name in names:
        full = os.path.join(directory, name)
        files.append(row(full, 'upstream/fly-gym/' + os.path.relpath(full, upstream)))
files.sort(key=lambda r: r['path'])
wanted = {norm(d) for d in DISTS}
distributions = []
for entry in sorted(os.listdir(SITE)):
    if not entry.endswith('.dist-info'):
        continue
    meta = HeaderParser().parsestr(open(os.path.join(SITE, entry, 'METADATA'), encoding='utf-8').read())
    if norm(meta['Name']) in wanted:
        distributions.append(dict(name=meta['Name'], version=meta['Version'], root_index=0,
                                  metadata_path=entry + '/METADATA'))
pin = row(PY, 'python3.11')
json.dump(dict(source_files=files, distributions=distributions,
               runtime=dict(root=os.path.dirname(PY), files=[pin], python_version='3.11.15')),
          open(OUT, 'w'), indent=1)
print(len(files), len(distributions), sorted(norm(d['name']) for d in distributions) == sorted(wanted), pin)
