"""Run the sole preparation04 independent audit once and write its external CLI record.

The auditor runs as the bare 15-element argv (no timeout wrapper; its own alarm is 130 s and
150 s only bounds a wedged auditor). The externally-observed-cpu-auditor-cli-v1 record has
exactly preparation01's keys and byte format, and is written only after the audit is the v15
PASS shape from auditor 4ef23799 and allocation 16's parent validate_configuration,
validate_acceptance and require_declared_misses accept it in memory for a synthetic
allocation-16 configuration. Writes /tmp/palimpsest-prep04-audit-terminal.json and its copy.
"""
from pathlib import Path
import importlib.util,json,sys,traceback

HERE=Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location('prep04_preflight',HERE/'preflight.py')
P=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(P)
C=P.C


def main():
    require=C.require;require(len(sys.argv)==1,__doc__)
    preflight=P.check('audit')
    freeze=json.loads(C.read(C.ROOT/C.FREEZE));config_raw=C.read(C.ROOT/C.CONFIG);config_sha=C.sha(config_raw)
    transport_raw=C.read(C.ROOT/C.TRANSPORT);transport_sha=C.sha(transport_raw)
    result_raw=C.read(C.ROOT/C.OUTPUT/'result.json')
    require(transport_sha==preflight['prepared']['transport_sha256'] and C.sha(result_raw)==preflight['prepared']['result_sha256'],'Transport/result changed after preflight')
    command=C.audit_command(C.ROOT,config_sha,transport_sha,C.AUDIT_OUTPUT)
    require(len(command)==15 and command[:11]==freeze['audit']['command_prefix'] and command[13:]==['--output',freeze['audit']['output']],'Auditor argv differs from the freeze')
    boot_before=C.boot_id();require(boot_before==preflight['boot_id'],'Boot changed after preflight')
    retired=P.retirement();consumed_before=C.consumed(C.ROOT,retired)
    require(consumed_before==preflight['consumed'],'Consumed stage identity changed after preflight')
    terminal=C.run_once(command,C.AUDIT_STDOUT,C.AUDIT_STDERR,timeout=C.AUDIT_BOUND)
    terminal.update(kind='palimpsest-prep04-audit-terminal-v1',boot_id_before=boot_before,boot_id_after=C.boot_id(),
        consumed_before=consumed_before,consumed_after=None,preflight=preflight,record=None,acceptance_proof=None,error=None)
    try:
        terminal['consumed_after']=C.consumed(C.ROOT,retired)
        require(terminal['outer_timeout'] is False and terminal['returncode']==0,'Normal zero auditor return required')
        value,raw=C.build_record(command,terminal['returncode'],terminal['elapsed_seconds'],C.AUDIT_OUTPUT,C.AUDIT_STDOUT,C.AUDIT_STDERR)
        audit_raw=C.read(C.AUDIT_OUTPUT);audit=json.loads(audit_raw)
        C.check_audit(audit,config_sha=config_sha,transport_sha=transport_sha,result_sha=C.sha(result_raw),
            dependencies_sha=preflight['prepared']['dependencies_sha256'],auditor_sha=freeze['pins']['auditor']['sha256'])
        paths=dict(configuration=C.CONFIG,result=C.OUTPUT+'/result.json',independent_audit=C.ARCHIVED_AUDIT,externally_observed_auditor_cli=C.ARCHIVED_RECORD)
        blobs=dict(configuration=config_raw,result=result_raw,independent_audit=audit_raw,externally_observed_auditor_cli=raw)
        _,proof=C.prove_allocation16(C.ROOT,paths,blobs)
        require(terminal['boot_id_after']==boot_before and terminal['consumed_after']==consumed_before,'Boot or consumed identity changed during the audit')
        C.write_record(C.AUDIT_RECORD,raw)
        terminal.update(record=dict(path=C.AUDIT_RECORD,size_bytes=len(raw),sha256=C.sha(raw)),acceptance_proof=proof,
            audit=dict(path=C.AUDIT_OUTPUT,size_bytes=len(audit_raw),sha256=C.sha(audit_raw),status=audit['status'],elapsed_seconds=audit['elapsed_seconds']))
    except Exception as error:
        terminal['error']=type(error).__name__+': '+str(error)[:1024];traceback.print_exc()
    terminal['status']='PASS_RECORD_WRITTEN' if terminal['error'] is None else 'FAILED_NO_ACCEPTANCE_RECORD'
    C.write_record(C.AUDIT_TERMINAL,C.pretty(terminal))
    print(json.dumps({k:terminal[k] for k in ('status','returncode','outer_timeout','elapsed_seconds','boot_id_before','boot_id_after','error')},sort_keys=True))
    return 0 if terminal['error'] is None else 1


if __name__=='__main__':raise SystemExit(main())
