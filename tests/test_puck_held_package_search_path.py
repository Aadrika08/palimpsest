"""Registration v4 held packages expose one never-a-directory search path.

The real rehearsal's guarded source worker failed in scipy/_lib/_testutils.py:
``IS_EDITABLE = 'editable' in scipy.__path__[0]`` raised IndexError because held
packages have ``__path__ == []``. Under v4 a held package's ``__path__`` is one
string below ``/dev/null`` (so no path hook can ever open it): an unregistered
present child still poisons, a declared hidden present child still misses like
stock CPython without executing, and v1-v3 keep ``__path__ == []``.
"""
import json
import textwrap

from test_puck_held_episode_bootstrap import ENTRY, ENTRY_PRELUDE, episode, refused, succeeded
from test_puck_tmpfs_dependencies import authored, v3
from test_puck_worker_bootstrap import descriptor
from test_puck_worker_dependencies import dependency_fixture

CHILD_RAN='HELD_CHILD_RAN'


def run(body,*,version=4):
    def mutate(deps,root):
        v3(deps)
        for name in ('stray','hidden_child'):
            (root/'fixture_dep'/(name+'.py')).write_text('import sys\nsys.stderr.write("'+CHILD_RAN+'\\n")\n')
        deps['roots'][0]['files']=[descriptor(p,p.relative_to(root).as_posix())
            for p in sorted((p for p in root.rglob('*') if p.is_file()),key=lambda p:p.relative_to(root).as_posix())]
    def source_change(reg,source):
        if version!=4:return
        path=source/ENTRY;path.write_text(ENTRY_PRELUDE+textwrap.indent(textwrap.dedent(body),'    ')+'\n')
        reg['source_files'].append(descriptor(path,ENTRY));reg['source_files'].sort(key=lambda row:row['path'])
        reg['modules'].append({'name':'palimpsest.puck_held_episode','path':ENTRY})
        reg.update(kind='puck-worker-source-bootstrap-v4',version=4,deadline_seconds=360,episode=episode(reg['runtime']['root']))
        reg['episode']['hidden_imports']=sorted(reg['episode']['hidden_imports']+['fixture_dep.hidden_child'])
    with authored() as base:
        result,_=dependency_fixture(base,textwrap.dedent(body) if version!=4 else 'raise AssertionError("PREFLIGHT_RAN")',
                                    mutate=mutate,source_change=source_change)
    print(json.dumps({'kind':'authored-held-package-path-v1','returncode':result.returncode,
                      'stdout':result.stdout,'stderr':result.stderr},sort_keys=True))
    return result


def test_v4_held_package_search_path_is_one_never_a_directory_string():
    receipt=succeeded(run('''
        import importlib.util, fixture_dep
        path = fixture_dep.__path__
        assert type(path) is list and len(path) == 1 and path[0].startswith('/dev/null/'), path
        assert not os.path.exists(path[0]) and 'editable' not in path[0]
        assert importlib.util.find_spec('fixture_dep.hidden_child') is None
        try:
            import fixture_dep.hidden_child
        except ModuleNotFoundError:
            pass
        owner.recheck()
        return {"kind": "authored-episode", "path": path[0]}
    '''))
    assert receipt['entry_result']['path']=='/dev/null/held-package/fixture_dep'
    assert receipt['denied_imports']==['fixture_dep.hidden_child']


def test_v4_unregistered_present_child_still_poisons():
    result=run('''
        try:
            import fixture_dep.stray
        except ImportError:
            pass
        return {"kind": "authored-episode"}
    ''')
    refused(result,'Unregistered local or external dependency import: fixture_dep.stray',entry_ran=True)
    assert CHILD_RAN not in result.stderr


def test_v3_held_package_search_path_is_unchanged():
    result=run('import fixture_dep\nreturn {"path": fixture_dep.__path__}',version=3)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)['entry_result']=={'path':[]}


# numpy/testing/_private/utils.py compares np_dist.locate_file('numpy') with Path(np.__file__).parent
# at import time; the held distribution refused the registered package directory.
def test_v4_distribution_locates_registered_directories_but_not_unregistered_paths():
    receipt=succeeded(run('''
        import importlib.metadata, pathlib, fixture_dep
        dist = importlib.metadata.distribution('fixture-dep')
        assert dist.locate_file('fixture_dep') == pathlib.Path(fixture_dep.__file__).parent
        refused = []
        for path in ('fixture_dep/missing.py', 'missing', '', '../fixture_dep', '/fixture_dep', 'fixture_dep/'):
            try:
                dist.locate_file(path)
            except ValueError as error:
                refused.append(str(error))
        return {"kind": "authored-episode", "refused": refused}
    '''))
    assert receipt['entry_result']['refused']==['Unregistered distribution file']*6


def test_v3_distribution_still_refuses_directories():
    result=run('import importlib.metadata\ntry:\n    importlib.metadata.distribution("fixture-dep").locate_file("fixture_dep")\n'
               'except ValueError as error:\n    return {"refused": str(error)}\nreturn {"refused": None}',version=3)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)['entry_result']=={'refused':'Unregistered distribution file'}
