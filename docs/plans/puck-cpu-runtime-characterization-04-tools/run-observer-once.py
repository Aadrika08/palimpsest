"""Run the sole characterization-04 observer once after a fresh enforced preflight; no retry.

Writes /tmp/palimpsest-char04-observer-terminal.json and its project-disk copy under
runs/palimpsest-char04-tools/. Exit 0 only for a normal observed characterization whose
transport, parent stdout, result and both reports bind by hash on an unchanged boot, with
the preparation02/03 stage and output identities unchanged.
"""
from pathlib import Path
import importlib.util,json,sys,traceback

HERE=Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location('char04_preflight',HERE/'preflight.py')
P=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(P)
C=P.C


def main():
    require=C.require;require(len(sys.argv)==1,__doc__)
    preflight=P.check('observer')
    freeze=json.loads(C.read(C.ROOT/C.FREEZE));config_raw=C.read(C.ROOT/C.CONFIG);sha=C.sha(config_raw)
    command=C.observer_command(C.ROOT,sha)
    require(sha==freeze['pins']['configuration']['sha256'] and command==freeze['command'],'Observer argv differs from the freeze')
    boot_before=C.boot_id();require(boot_before==preflight['boot_id'],'Boot changed after preflight')
    untouched_before=C.untouched();require(untouched_before==preflight['untouched'],'Preparation02/03 identity changed after preflight')
    # The observer's own clocks are 420 s (normal) and 435 s (alarm); 460 s only bounds a wedged observer.
    terminal=C.run_once(command,C.OBSERVER_STDOUT,C.OBSERVER_STDERR,timeout=C.OBSERVER_BOUND)
    terminal.update(kind='palimpsest-char04-observer-terminal-v1',boot_id_before=boot_before,boot_id_after=C.boot_id(),
        untouched_before=untouched_before,untouched_after=C.untouched(),preflight=preflight,stdout_equals_transport=False,
        observation=None,error=None)
    try:
        transport_raw=C.read(C.ROOT/C.TRANSPORT)
        terminal['stdout_equals_transport']=C.read(C.OBSERVER_STDOUT)==transport_raw
        terminal['transport']=dict(path=C.TRANSPORT,size_bytes=len(transport_raw),sha256=C.sha(transport_raw))
        result_raw=C.read(C.ROOT/C.OUTPUT/'result.json');result=json.loads(result_raw)
        terminal['result']=dict(path=C.OUTPUT+'/result.json',size_bytes=len(result_raw),sha256=C.sha(result_raw),
            status=result.get('status'),error=result.get('error'),error_type=result.get('error_type'),elapsed_seconds=result.get('elapsed_seconds'))
        terminal['observation']=C.observed(C.ROOT,config_raw)
    except Exception as error:
        terminal['error']=type(error).__name__+': '+str(error)[:1024];traceback.print_exc()
    ok=(terminal['returncode']==0 and terminal['outer_timeout'] is False and terminal['error'] is None
        and terminal['stdout_equals_transport'] is True and terminal['boot_id_before']==terminal['boot_id_after']
        and terminal['untouched_before']==terminal['untouched_after'])
    terminal['status']='PASS_OBSERVED' if ok else 'FAILED_CONSUMED'
    C.write_record(C.OBSERVER_TERMINAL,C.pretty(terminal))
    print(json.dumps({k:terminal[k] for k in ('status','returncode','outer_timeout','elapsed_seconds','boot_id_before','boot_id_after','error')},sort_keys=True))
    return 0 if ok else 1


if __name__=='__main__':raise SystemExit(main())
