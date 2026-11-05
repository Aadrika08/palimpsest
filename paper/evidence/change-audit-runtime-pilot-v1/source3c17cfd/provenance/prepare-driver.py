"""One admitted input-preparation attempt. No native/model imports or inference."""
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import subprocess
import sys

from paper.studies.change_audit_v1.prepare_inputs import prepare, write_json

ROOT = Path('/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite')
BUNDLE = ROOT/'runs/change-audit-pilot-v1-20261105-source3c17cfd'
ASSETS = Path('/home/utkarsh/Work/shraddha/palimpsest/data/assets/flynn')
EXPECTED_HEAD = '3c17cfda8aa4cb101d93c3936fee85625cbdea7d'
head = subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
if head != EXPECTED_HEAD:
    raise RuntimeError('Unexpected frozen source HEAD')
manifest_path = ROOT/'model_manifests/flynn-full-vision.json'
manifest = json.loads(manifest_path.read_text())
archive = next(row for row in manifest['files'] if row['id']=='graph_archive')
graph = ASSETS/('graph-'+archive['sha256'])
marker = graph/'palimpsest-prepared.json'
prepared = json.loads(marker.read_text())
edge = graph/prepared['edge_path']
if not edge.resolve().is_relative_to(graph.resolve()):
    raise RuntimeError('Prepared edge escaped the existing graph cache')
model_files = [ASSETS/row['path'] for row in manifest['files']]
model_files += [marker,edge]+[edge.parent/row['path'] for row in manifest['graph']['mapping_files']]
tracked = subprocess.check_output(['git','-C',str(ROOT),'ls-files','-z'],text=False).split(b'\0')
source_files = [ROOT/path.decode() for path in tracked if path.startswith(b'src/palimpsest/') and path.endswith(b'.py')]
source_files += [ROOT/'paper/studies/change_audit_v1'/name for name in ('pilot.py','pilot_worker.py','process.py','prepare_inputs.py')]
source_files += [ROOT/name for name in ('pyproject.toml','uv.lock','model_manifests/flynn-full-vision.json','docs/plans/project-completion-2026-11-05.md')]
upstream = ROOT/'upstream/fly-gym'
upstream_files = subprocess.check_output(['git','-C',str(upstream),'ls-files','-z'],text=False).split(b'\0')
runtime_files = [upstream/path.decode() for path in upstream_files if path and
    (path.endswith(b'.py') or path.startswith(b'environment/') or path.startswith(b'connectomes/drosophila adult connectome/'))]
# Installed manifests and selected actual native files are bound independently.
# This is an explicit engineering inventory, not a complete dependency closure.
packages = ('palimpsest','torch','torchvision','numpy','scipy','pandas','scikit-learn','mujoco',
    'gymnasium','glfw','opencv-python','matplotlib','seaborn','networkx','python-louvain','py7zr')
for name in packages:
    distribution = metadata.distribution(name)
    for entry in distribution.files or ():
        value = str(entry)
        if value.endswith(('.dist-info/METADATA','.dist-info/RECORD','.dist-info/WHEEL')):
            runtime_files.append(Path(distribution.locate_file(entry)))
        elif name in ('torch','torchvision','mujoco','numpy') and (value.endswith('.so') or '.so.' in value):
            # CUDA-only kernels are unused by the frozen CPU configuration.
            if 'cuda' not in value.lower() and 'cudnn' not in value.lower():
                runtime_files.append(Path(distribution.locate_file(entry)))
runtime_files.append(Path(sys.executable).parent.parent/'pyvenv.cfg')
runtime_files = sorted({str(path.resolve(strict=True)) for path in runtime_files})
config = {'repo_root':str(ROOT),'asset_root':str(ASSETS),'prepared_graph_directory':str(graph),
    'source_commit':head,'source_files':sorted({str(path) for path in source_files}),
    'runtime_files':runtime_files,'model_files':[str(path) for path in model_files],
    'python_executable':sys.executable}
config_row = write_json(BUNDLE/'preparation-config.json',config)
plan = ROOT/'docs/plans/project-completion-2026-11-05.md'
plan_sha = hashlib.sha256(plan.read_bytes()).hexdigest()
result = prepare(mode='execute-preparation',output=BUNDLE/'inputs',approved_plan=plan,
    expected_plan_sha256=plan_sha,config_path=config_row['path'],expected_config_sha256=config_row['sha256'])
print(json.dumps(result,sort_keys=True,allow_nan=False))
