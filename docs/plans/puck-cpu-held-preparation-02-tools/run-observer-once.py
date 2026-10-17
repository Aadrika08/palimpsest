"""Run the sole preparation02 observer once after a fresh enforced preflight; no retry.

Writes /tmp/palimpsest-prep02-observer-terminal.json and its project-disk copy under
runs/palimpsest-prep02-tools/. Exit 0 only for a normal prepared allocation whose four
staged roots stat-match result.staged_roots on an unchanged boot.
"""
from pathlib import Path
import importlib.util,json,sys,traceback

HERE=Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location('prep02_preflight',HERE/'preflight.py')
P=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(P)
C=P.C


def main():
    require=C.require;require(len(sys.argv)==1,__doc__)
    preflight=P.check('observer')
    freeze=json.loads(C.read(C.ROOT/C.FREEZE));sha=freeze['pins']['configuration']['sha256']
    command=[C.PYTHON,'-I','-S','-B',str(C.ROOT/'scripts/observe_puck_cpu_held_allocation.py'),'--configuration',str(C.ROOT/C.CONFIG),'--sha256',sha]
    require(command==freeze['command'],'Observer argv differs from the freeze')
    boot_before=C.boot_id();require(boot_before==preflight['boot_id'],'Boot changed after preflight')
    # The observer has its own 210s/225s limits; 260s only bounds a wedged observer.
    terminal=C.run_once(command,C.OBSERVER_STDOUT,C.OBSERVER_STDERR,timeout=260)
    terminal.update(kind='palimpsest-prep02-observer-terminal-v1',boot_id_before=boot_before,boot_id_after=C.boot_id(),
        preflight=preflight,stdout_equals_transport=False,staged_roots=None,error=None)
    try:
        transport_raw=C.read(C.ROOT/C.TRANSPORT)
        terminal['stdout_equals_transport']=C.read(C.OBSERVER_STDOUT)==transport_raw
        terminal['transport']=dict(path=C.TRANSPORT,size_bytes=len(transport_raw),sha256=C.sha(transport_raw))
        result_raw=C.read(C.ROOT/C.OUTPUT/'result.json');result=json.loads(result_raw)
        terminal['result']=dict(path=C.OUTPUT+'/result.json',size_bytes=len(result_raw),sha256=C.sha(result_raw),
            status=result.get('status'),staged_roots=result.get('staged_roots'))
        terminal['staged_roots']=C.stat_roots(C.STAGE,result['staged_roots'])
    except Exception as error:
        terminal['error']=type(error).__name__+': '+str(error)[:1024];traceback.print_exc()
    ok=(terminal['returncode']==0 and terminal['outer_timeout'] is False and terminal['error'] is None
        and terminal['stdout_equals_transport'] is True and terminal.get('result',{}).get('status')=='prepared'
        and terminal['boot_id_before']==terminal['boot_id_after'])
    terminal['status']='PASS_OBSERVED_PREPARED' if ok else 'FAILED_CONSUMED'
    C.write_record(C.OBSERVER_TERMINAL,C.pretty(terminal))
    print(json.dumps({k:terminal[k] for k in ('status','returncode','outer_timeout','elapsed_seconds','boot_id_before','boot_id_after','error')},sort_keys=True))
    return 0 if ok else 1


if __name__=='__main__':raise SystemExit(main())
