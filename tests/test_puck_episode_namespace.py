"""Held episode namespaces: staged v6 natives, per-worker outputs, read-only source run.

Command construction only (authored paths); no bwrap runs. Worker A (source)
writes its run under /output. Worker B (replay) sees worker A's output read-only
at /puck/source-run and writes its own fresh /output. Both see only staged
inputs, the original nine baseline paths and the control tree with the staged
EGL vendor JSON; v6 metadata may carry up to 256 native leaves.
"""
import copy

import pytest

from test_puck_cpu_namespace import BASELINE, BASE_PATHS, NATIVE, PARENT_ENVIRONMENT, PYTHON, api, arguments, binds, build  # noqa: F401


EPISODE_ENVIRONMENT=dict(PARENT_ENVIRONMENT,PYGLFW_LIBRARY='/usr/lib/libglfw.so.3',MESA_SHADER_CACHE_DISABLE='true',
    PYGAME_HIDE_SUPPORT_PROMPT='hide',__EGL_VENDOR_LIBRARY_FILENAMES='/puck/control/egl-vendor.json')


def native_v6(count=None):
    value=copy.deepcopy(NATIVE)
    value.update(kind='puck-cpu-characterization-native-metadata-v6')
    if count:
        extra=['/usr/lib/libmesa%03d.so'%i for i in range(count-len(value['native_files']))]
        value['native_files']=sorted(value['native_files']+[dict(path=p,size_bytes=1,sha256='a'*64) for p in extra],
                                     key=lambda r:r['path'])
    return value


@pytest.fixture
def episode(tmp_path):
    paths={};base=tmp_path/'episode';base.mkdir(mode=0o700)
    for key in ('stage_parent','source_root','control_root','output_root','source_run_root'):
        path=base/key;path.mkdir(mode=0o700);paths[key]=str(path)
    (base/'stage_parent/inputs').mkdir(mode=0o700)
    return dict(command=[PYTHON,'-I','-B','-S','-c','pass'],environment=dict(EPISODE_ENVIRONMENT),**paths)


def source(arguments):
    return dict({k:v for k,v in arguments.items() if k!='source_run_root'},phase='episode-source')


def test_source_worker_writes_only_its_own_output_and_sees_staged_inputs(episode):
    command=build(source(episode),native=native_v6())
    assert binds(command,'--bind')==[(episode['output_root'],'/output')]
    readonly=binds(command,'--ro-bind')
    assert (episode['stage_parent']+'/inputs','/puck/staged/inputs') in readonly
    assert (episode['control_root'],'/puck/control') in readonly and (episode['source_root'],'/puck/source') in readonly
    assert not any(target=='/puck/source-run' for _,target in readonly)
    assert '--as-pid-1' not in command
    for key,value in EPISODE_ENVIRONMENT.items():
        index=command.index(key) if key in command else None
        assert index is not None and command[index-1]=='--setenv' and command[index+1]==value


def test_replay_worker_mounts_the_source_run_read_only_and_a_fresh_output(episode):
    command=build(dict(episode,phase='episode-replay'),native=native_v6())
    assert binds(command,'--bind')==[(episode['output_root'],'/output')]
    assert (episode['source_run_root'],'/puck/source-run') in binds(command,'--ro-bind')


def test_episode_phases_bind_staged_native_copies_except_the_original_baseline(episode):
    native=native_v6(200)
    command=build(source(episode),native=native)
    readonly=dict((target,origin) for origin,target in binds(command,'--ro-bind'))
    for row in native['native_files']:
        path=row['path']
        if path in BASE_PATHS:assert readonly[path]==path
        else:
            root='root-0001' if path.startswith('/usr/') else 'root-0002'
            assert readonly[path]==episode['stage_parent']+'/inputs/'+root+'/'+path[5:]


@pytest.mark.parametrize('defect',['replay-without-run','source-with-run','run-overlaps-output','v5-too-many','v6-too-many','unknown-phase'])
def test_episode_namespace_refusals(episode,defect):
    arguments=dict(episode,phase='episode-replay');native=native_v6()
    if defect=='replay-without-run':arguments['source_run_root']=None
    elif defect=='source-with-run':arguments['phase']='episode-source'
    elif defect=='run-overlaps-output':arguments['source_run_root']=episode['output_root']
    elif defect=='v5-too-many':native=dict(native_v6(129),kind=NATIVE['kind'])
    elif defect=='v6-too-many':native=native_v6(257)
    else:arguments['phase']='episode'
    with pytest.raises(ValueError):build(arguments,native=native)


def test_existing_phases_refuse_a_source_run_and_keep_their_mounts(episode,arguments):
    with pytest.raises(ValueError):build(dict(arguments,source_run_root=episode['source_run_root']))
    command=build(arguments)
    assert binds(command,'--bind')==[(arguments['stage_parent'],'/puck/staged'),(arguments['output_root'],'/output')]
