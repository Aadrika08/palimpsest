"""Held episode source closure and import naming; authored registrations only.

The episode worker needs every file the environment event and replay
compatibility read (all src/palimpsest/*.py, pyproject.toml, uv.lock and the
model manifest) plus the four fly-gym modules and the checker model XML that
the manual environment loads, each under its real import name.
"""
import json
from pathlib import Path

import pytest

import frozen_pins

from test_puck_cpu_held_parent import api


ROOT=Path(__file__).resolve().parents[1]
UPSTREAM={'upstream/fly-gym/core/__init__.py':'core','upstream/fly-gym/core/astar.py':'core.astar',
          'upstream/fly-gym/environment/__init__.py':'environment',
          'upstream/fly-gym/environment/mujoco_two_cam_env_random_obstacles.py':'environment.mujoco_two_cam_env_random_obstacles'}
DATA=['model_manifests/flynn-full-vision.json','pyproject.toml','uv.lock',
      'upstream/fly-gym/environment/mujoco_model_random_obstacles.xml']


def rows(paths):
    return [dict(path=path,size_bytes=1,sha256='a'*64) for path in paths]


def test_episode_closure_registers_every_runtime_read_and_nothing_else():
    # The closure is frozen with allocation 16's source commit (its evidence index), not main's
    # current src/palimpsest, which grew after integration (docs/plans/frozen-source-pins-after-integration.md).
    m=api();commit=json.loads((ROOT/'docs/reports/puck-cpu-held-episode-16/evidence-index.json').read_bytes())['source_commit']
    palimpsest=frozen_pins.files_at(commit,'src/palimpsest','.py')
    assert list(m.EPISODE_WORKER_SOURCES)==sorted([m.BOOTSTRAP,*palimpsest,*UPSTREAM,*DATA])
    assert {'src/palimpsest/doctor.py','src/palimpsest/evaluate.py','src/palimpsest/puck_held_episode.py',
            'src/palimpsest/held_provenance.py','src/palimpsest/puck_worker_preflight.py'}<=set(m.EPISODE_WORKER_SOURCES)
    assert 'upstream/fly-gym/environment/mujoco_model_random_obstacles_realistic.xml' not in m.EPISODE_WORKER_SOURCES
    assert len(m.EPISODE_WORKER_SOURCES)<=512


def test_episode_import_names_follow_their_real_package_roots():
    m=api();modules={row['name']:row['path'] for row in m.source_modules(rows(m.EPISODE_WORKER_SOURCES))}
    for path,name in UPSTREAM.items():assert modules[name]==path
    assert modules['palimpsest']=='src/palimpsest/__init__.py'
    assert modules['palimpsest.puck_held_episode']=='src/palimpsest/puck_held_episode.py'
    assert not set(modules.values())&set(DATA) and m.BOOTSTRAP not in modules.values()
    assert len(modules)==len([p for p in m.EPISODE_WORKER_SOURCES if p.endswith('.py')])-1


def test_existing_worker_naming_is_unchanged():
    m=api()
    old=[]
    for row in rows(m.WORKER_SOURCES):
        if row['path']==m.BOOTSTRAP:continue
        name=row['path'][4:-3].replace('/','.')
        if name.endswith('.__init__'):name=name[:-9]
        old.append(dict(name=name,path=row['path']))
    assert m.source_modules(rows(m.WORKER_SOURCES))==old


@pytest.mark.parametrize('path',['scripts/other.py','docs/authored.py','upstream/other/module.py','upstream/fly-gymnasium/x.py'])
def test_sources_without_a_declared_import_root_are_refused(path):
    with pytest.raises(ValueError):api().source_modules(rows([path]))


def test_the_v4_bootstrap_accepts_the_closure_naming_and_its_package_parents():
    import json
    from test_puck_held_episode_bootstrap import episode
    from test_puck_worker_bootstrap import api as bootstrap_api, sha
    m=api();b=bootstrap_api();files=rows(m.EPISODE_WORKER_SOURCES);root=str(Path('/proc/self/exe').resolve().parent)
    reg=dict(kind='puck-worker-source-bootstrap-v4',version=4,source_root='/puck/source',source_files=files,
        modules=m.source_modules(files),namespaces=[],
        runtime=dict(root=root,files=[dict(b.RUNTIME_PIN)],python_version='3.11.15'),
        environment=dict(PATH='/nonexistent'),cwd='/puck/source',argv_prefix=['/authored'],
        dependencies=dict(path='/puck/control/dependencies.json',size_bytes=2,sha256='b'*64),
        deadline_seconds=600,qualification_claims=[],executable=False)
    reg['episode']=episode(root)
    raw=json.dumps(reg,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
    parsed,modules,namespaces=b._parse(raw,sha(raw))
    assert {'core','core.astar','environment','environment.mujoco_two_cam_env_random_obstacles',
            'palimpsest.puck_held_episode',b.ENTRY,b.EPISODE_ENTRY}<=set(modules) and namespaces=={}
