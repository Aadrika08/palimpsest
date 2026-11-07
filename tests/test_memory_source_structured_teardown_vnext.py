"""Authored resources only; structured source opt-ins preserve original errors."""
import hashlib
import os
import time
import pytest
from scripts.memory_family_replay_custody_v4 import HeldReplayFiles
from scripts.memory_source_runtime_closure_v1 import RuntimeHandle, _SourceNamespaceFiles
from palimpsest.records import RunWriter
from test_memory_source_bootstrap_vnext import route


def flatten(error):
    if isinstance(error, BaseExceptionGroup):
        return [leaf for child in error.exceptions for leaf in flatten(child)]
    return [error]


def test_replay_holder_structured_body_and_all_fd_failures(tmp_path, monkeypatch):
    leaf = tmp_path / 'leaf'; leaf.write_bytes(b'authored')
    holder = HeldReplayFiles(str(tmp_path), [dict(path='leaf', size_bytes=8,
        sha256=hashlib.sha256(b'authored').hexdigest())], time.monotonic()+30,
        structured_teardown=True)
    body = KeyboardInterrupt('body')
    original_close = os.close; failures = []; attempted = []
    with pytest.raises(BaseExceptionGroup) as caught:
        with holder:
            owned = set(holder._fds)
            def close(fd):
                original_close(fd)
                if fd in owned:
                    attempted.append(fd); failure = OSError(str(fd)); failures.append(failure); raise failure
            monkeypatch.setattr(os, 'close', close)
            raise body
    assert flatten(caught.value) == [body, *failures]
    assert len(attempted) == len(owned)
    assert holder._fds == []


@pytest.mark.parametrize('bad', [0, 1, None, 'true'])
def test_exact_bool_optins_before_acquisition(tmp_path, bad):
    with pytest.raises(ValueError, match='bool'):
        HeldReplayFiles(str(tmp_path), [], 0, structured_teardown=bad)
    with pytest.raises(ValueError, match='bool'):
        _SourceNamespaceFiles([], [], 0, lambda: None, structured_teardown=bad)
    with pytest.raises(ValueError, match='bool'):
        RuntimeHandle({}, required_roots=(), required_pins={}, output_root='/',
            deadline=0, check=lambda: None, structured_teardown=bad)


def test_preserved_recorder_has_no_research_script_dependency(tmp_path,monkeypatch):
    import builtins
    real_import=builtins.__import__
    def guarded(name,*args,**kwargs):
        if name=='scripts' or name.startswith('scripts.'): raise AssertionError('Library imported research scripts')
        return real_import(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',guarded)
    writer=RunWriter(tmp_path/'recording',{},preserve_failed=True)
    writer.close()
    assert writer._events.closed
    writer=RunWriter(tmp_path/'failure',{},preserve_failed=True)
    failure=KeyboardInterrupt('flush')
    monkeypatch.setattr(writer,'_flush',lambda:(_ for _ in ()).throw(failure))
    with pytest.raises(BaseExceptionGroup) as caught: writer.close()
    assert flatten(caught.value)==[failure] and writer._events.closed


def test_engine_source_close_drains_independent_baseexceptions(route,monkeypatch):
    engine=route.open(); renderer=KeyboardInterrupt('renderer'); environment=OSError('environment'); writer=RuntimeError('writer')
    def throw(error):
        def fail(): raise error
        return fail
    monkeypatch.setattr(engine.env.renderer,'close',throw(renderer))
    monkeypatch.setattr(engine.env,'close',throw(environment))
    real_close=engine.writer.close
    def close(): real_close(); raise writer
    monkeypatch.setattr(engine.writer,'close',close)
    with pytest.raises(BaseExceptionGroup) as caught: engine.close()
    assert flatten(caught.value)==[renderer,environment,writer]
    assert engine._closed and engine.writer._events.closed
    engine.close()


def test_runtime_nested_holders_preserve_body_and_each_original_close_error(tmp_path,monkeypatch):
    from test_memory_source_runtime_closure_v1 import authored
    p=authored(tmp_path); module,reference,manifest,recipe,ledger,pins=p
    handle=RuntimeHandle(reference,required_roots=tuple(row['root'] for row in manifest['roots']),required_pins=pins,output_root=str(tmp_path/'output'),deadline=time.monotonic()+30,check=lambda:None,structured_teardown=True)
    handle.__enter__(); owned={fd for holder in handle._holders for fd in holder._fds}
    body=KeyboardInterrupt('body'); closes=[]; original=os.close
    def close(fd):
        original(fd)
        if fd in owned:
            error=OSError('close '+str(fd)); closes.append(error); raise error
    monkeypatch.setattr(os,'close',close)
    with pytest.raises(BaseExceptionGroup) as caught: handle.__exit__(type(body),body,body.__traceback__)
    assert flatten(caught.value)==[body,*closes] and len(closes)==len(owned)
    assert handle._holders==[]
    with pytest.raises(RuntimeError): handle.summary()


def test_canonical_open_error_cleanup_has_no_research_script_dependency(route,monkeypatch):
    import builtins
    route.stage.fail,route.stage.close_error='policy',True
    original=builtins.__import__
    def guarded(name,*args,**kwargs):
        if name=='scripts' or name.startswith('scripts.'): raise AssertionError('Library imported research scripts')
        return original(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',guarded)
    with pytest.raises(BaseExceptionGroup) as caught: route.open()
    leaves=flatten(caught.value)
    assert [str(error) for error in leaves]==['policy boundary','renderer close boundary']
    assert route.envs[0].closed


def test_error_aggregation_deduplicates_only_object_identity():
    from palimpsest.records import _source_errors
    first=ValueError('equal'); distinct=ValueError('equal')
    nested=_source_errors('inner',[first,distinct])
    group=_source_errors('outer',[first,nested,first,distinct])
    assert group.exceptions==(first,distinct)
    foreign=ExceptionGroup('foreign',[first])
    assert _source_errors('outer',[foreign]).exceptions==(foreign,)
