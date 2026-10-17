"""Held episode source closure and import naming; authored registrations only.

The episode worker needs every file the environment event and replay
compatibility read (all src/palimpsest/*.py, pyproject.toml, uv.lock and the
model manifest) plus the four fly-gym modules and the checker model XML that
the manual environment loads, each under its real import name.
"""
from pathlib import Path

import pytest

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
    m=api()
    palimpsest=sorted('src/palimpsest/'+p.name for p in (ROOT/'src/palimpsest').glob('*.py'))
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


@pytest.mark.parametrize('path',['scripts/other.py','docs/authored.py','upstream/other/module.py','src/palimpsest'])
def test_sources_without_a_declared_import_root_are_refused(path):
    with pytest.raises(ValueError):api().source_modules(rows([path if path.endswith('.py') else path+'.py']))
