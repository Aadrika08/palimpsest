"""Retire the two consumed preparation stages, recording each one's identity and content census first.

Refuses any argument list other than exactly
    /tmp/palimpsest-puck-cpu-held-02 /tmp/palimpsest-puck-cpu-held-03
Each must be a real directory directly under /tmp on the required boot whose four staged roots
still stat-match its preparation's retained result.staged_roots. For each, the lstat identity and
a census (relative path, type, mode, size, symlink target, SHA-256 of every regular file) are
written to runs/palimpsest-prep04-tools/retire-consumed-stages-census.json BEFORE anything is
removed; then each stage is removed (directories made 0700 first, no symlink is followed) and its
absence verified, and runs/palimpsest-prep04-tools/retire-consumed-stages.json records the result.
Nothing under runs/puck-cpu-held-preparation-0{2,3} is modified.
Usage: python3.11 -I -S -B retire-consumed-stages.py /tmp/palimpsest-puck-cpu-held-02 /tmp/palimpsest-puck-cpu-held-03
"""
from pathlib import Path
import datetime,hashlib,importlib.util,json,os,shutil,stat,sys

HERE=Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location('prep04_common',HERE/'common.py')
C=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(C)
require=C.require
CENSUS=C.RECORDS+'/retire-consumed-stages-census.json'
RESULTS=dict(zip(C.CONSUMED,(o+'/result.json' for o in C.CONSUMED_OUTPUTS)))


def census(stage):
    """Every entry below the stage, never following a symlink; regular files are hashed."""
    rows=[]
    for directory,dirs,files in os.walk(stage,followlinks=False):
        dirs.sort()
        for name in sorted(dirs+files):
            full=os.path.join(directory,name);state=os.lstat(full);row=dict(path=os.path.relpath(full,stage),mode=state.st_mode)
            if stat.S_ISLNK(state.st_mode):row.update(type='symlink',target=os.readlink(full))
            elif stat.S_ISDIR(state.st_mode):row.update(type='directory')
            elif stat.S_ISREG(state.st_mode):
                digest=hashlib.sha256()
                fd=os.open(full,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
                try:
                    while chunk:=os.read(fd,1024**2):digest.update(chunk)
                finally:os.close(fd)
                row.update(type='file',size_bytes=state.st_size,sha256=digest.hexdigest())
            else:row.update(type='other')
            rows.append(row)
    manifest=json.dumps(rows,sort_keys=True,separators=(',',':')).encode()
    return dict(entries=len(rows),files=sum(r['type']=='file' for r in rows),directories=sum(r['type']=='directory' for r in rows),
        symlinks=sum(r['type']=='symlink' for r in rows),other=sum(r['type']=='other' for r in rows),
        file_bytes=sum(r.get('size_bytes',0) for r in rows),census_sha256=hashlib.sha256(manifest).hexdigest()),rows


def main():
    require(sys.argv[1:]==list(C.CONSUMED),__doc__)
    require(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode and str(Path(sys.executable).resolve())==C.PYTHON,
        'Pinned isolated interpreter required')
    require(C.boot_id()==C.BOOT,'Boot differs from the required boot '+C.BOOT)
    records=C.ROOT/C.RECORDS
    require(not os.path.lexists(C.ROOT/CENSUS) and not os.path.lexists(C.ROOT/C.RETIREMENT),'Retirement already recorded')
    stages=[]
    for stage in C.CONSUMED:
        state=os.lstat(stage)
        require(stat.S_ISDIR(state.st_mode) and not stat.S_ISLNK(state.st_mode) and os.path.dirname(stage)=='/tmp'
            and os.path.realpath(stage)==stage,'Real consumed stage directory directly under /tmp required: '+stage)
        result=json.loads(C.read(C.ROOT/RESULTS[stage]))
        require(result.get('stage_parent')==stage and result.get('status')=='prepared','Consumed preparation result differs: '+stage)
        roots=C.stat_roots(stage,result['staged_roots'])
        summary,rows=census(stage)
        stages.append(dict(path=stage,identity=C.identity(stage),staged_roots=roots,result=RESULTS[stage],
            result_sha256=C.sha(C.read(C.ROOT/RESULTS[stage])),census=summary,rows=rows))
    free_before=shutil.disk_usage('/tmp').free
    records.mkdir(mode=0o700,exist_ok=True)
    # Compact bytes: two ~27k-entry censuses stay far below the bounded read.
    C.write_new(C.ROOT/CENSUS,(json.dumps(dict(kind='palimpsest-prep04-consumed-stage-census-v1',boot_id=C.boot_id(),
        at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),tmpfs_free_bytes=free_before,stages=stages),
        sort_keys=True,separators=(',',':'))+'\n').encode())
    census_raw=C.read(C.ROOT/CENSUS,256*1024**2)
    for row in stages:
        require(C.identity(row['path'])==row['identity'],'Stage identity changed after its census: '+row['path'])
        for directory,dirs,_ in os.walk(row['path'],followlinks=False):
            for name in dirs:
                full=os.path.join(directory,name)
                if not os.path.islink(full):os.chmod(full,0o700,follow_symlinks=False)
        shutil.rmtree(row['path'])
        require(not os.path.lexists(row['path']),'Stage still present after removal: '+row['path'])
    value=dict(kind='palimpsest-prep04-consumed-stage-retirement-v1',boot_id=C.boot_id(),
        at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),census=dict(path=CENSUS,size_bytes=len(census_raw),sha256=C.sha(census_raw)),
        tmpfs_free_bytes_before=free_before,tmpfs_free_bytes_after=shutil.disk_usage('/tmp').free,
        stages=[dict(path=r['path'],identity=r['identity'],result_sha256=r['result_sha256'],census=r['census'],status='RETIRED') for r in stages],
        outputs_untouched=[C.identity(C.ROOT/p) for p in C.CONSUMED_OUTPUTS])
    C.write_new(C.ROOT/C.RETIREMENT,C.pretty(value))
    print(json.dumps({k:value[k] for k in ('tmpfs_free_bytes_before','tmpfs_free_bytes_after','stages')},indent=2,sort_keys=True))
    return 0


if __name__=='__main__':raise SystemExit(main())
