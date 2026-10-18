"""Run the source characterization-04 archive tool once, then prove preparation04 binds it.

After a fresh enforced archive preflight, runs scripts/archive_puck_episode_characterization.py
as one bare argv (it alone writes docs/reports/puck-cpu-characterization-04/ and its
evidence-index.json), verifies the index against every archived byte, runs the qualifier's
validate_observation_links and validate_episode_observation (synthetic candidate bound to these
pins), then copies the control records byte-identically into
docs/reports/puck-cpu-characterization-04-records/ with an archive record.
"""
from pathlib import Path
import datetime,importlib.util,json,sys,traceback

HERE=Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location('char04_preflight',HERE/'preflight.py')
P=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(P)
C=P.C


def plan(root=C.ROOT):
    records=Path(root)/C.RECORDS_ARCHIVE;pairs=[]
    for name in (C.AUDIT_OUTPUT,C.AUDIT_STDOUT,C.AUDIT_STDERR,C.AUDIT_RECORD,C.OBSERVER_TERMINAL,C.AUDIT_TERMINAL,
                 C.OBSERVER_STDOUT,C.OBSERVER_STDERR,C.ARCHIVE_TERMINAL,C.ARCHIVE_STDOUT,C.ARCHIVE_STDERR):
        pairs.append((name,records/Path(name).name))
    for name in sorted((Path(root)/C.RECORDS).glob('preflight-*.json')):pairs.append((str(name),records/name.name))
    return pairs


def copy(pairs):
    rows=[]
    for source,target in pairs:
        raw=C.read(source);Path(target).parent.mkdir(mode=0o755,parents=True,exist_ok=True)
        C.write_new(target,raw);C.require(C.read(target)==raw,'Archived copy differs: '+str(target))
        rows.append(dict(source=str(source),archived=str(target),size_bytes=len(raw),sha256=C.sha(raw)))
    return rows


def main():
    require=C.require;require(len(sys.argv)==1,__doc__)
    preflight=P.check('archive')
    freeze=json.loads(C.read(C.ROOT/C.FREEZE));config_raw=C.read(C.ROOT/C.CONFIG);audit_raw=C.read(C.AUDIT_OUTPUT)
    command=C.archive_command(C.ROOT,C.AUDIT_OUTPUT);require(command==freeze['archive']['command'],'Archive argv differs from the freeze')
    boot_before=C.boot_id();untouched_before=C.untouched();require(untouched_before==preflight['untouched'],'Preparation02/03 identity changed after preflight')
    terminal=C.run_once(command,C.ARCHIVE_STDOUT,C.ARCHIVE_STDERR,timeout=C.ARCHIVE_BOUND)
    terminal.update(kind='palimpsest-char04-archive-terminal-v1',boot_id_before=boot_before,boot_id_after=C.boot_id(),
        untouched_before=untouched_before,untouched_after=C.untouched(),preflight=preflight,index=None,binding=None,error=None)
    try:
        require(terminal['outer_timeout'] is False and terminal['returncode']==0,'Normal zero archive return required')
        require(C.read(C.ARCHIVE_STDERR)==b'','Archive stderr must be empty')
        terminal['index']=C.check_archive(C.ROOT,config_raw,audit_raw,C.read(C.ARCHIVE_STDOUT))
        parent=C.load(C.ROOT/C.PARENT,'char04_archive_parent');qualifier=C.load(C.ROOT/C.QUALIFIER,'char04_archive_qualifier')
        terminal['binding']=C.binding(C.ROOT,qualifier,parent,config_raw)
        require(terminal['boot_id_after']==boot_before==preflight['boot_id'] and terminal['untouched_after']==untouched_before,
            'Boot or preparation02/03 identity changed during archive')
    except Exception as error:
        terminal['error']=type(error).__name__+': '+str(error)[:1024];traceback.print_exc()
    terminal['status']='PASS_ARCHIVED_AND_BOUND' if terminal['error'] is None else 'FAILED_ARCHIVE_OR_BINDING'
    C.write_record(C.ARCHIVE_TERMINAL,C.pretty(terminal))
    rows=copy(plan())
    value=dict(kind='palimpsest-char04-archive-record-v1',at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status=terminal['status'],boot_id=preflight['boot_id'],head=preflight['git']['head'],index=terminal['index'],
        binding=terminal['binding'],error=terminal['error'],copies=rows,
        scope='byte-identical records of the characterization-04 one-shot controls; observation evidence only, not runtime qualification')
    C.write_new(C.ROOT/C.RECORDS_ARCHIVE/'archive-record.json',C.pretty(value))
    print(json.dumps(dict(status=terminal['status'],copies=len(rows),index=terminal['index'],binding=terminal['binding'],error=terminal['error']),indent=2,sort_keys=True))
    return 0 if terminal['error'] is None else 1


if __name__=='__main__':raise SystemExit(main())
