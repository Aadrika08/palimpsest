"""Copy registered data to tmpfs, without imports or qualification authority.

The caller owns capacity admission, an outer hard watchdog and partial-tree
cleanup. This helper checks one deadline cooperatively and closes its handles;
the eventual consumer must independently rehash, census and lease the result.
"""
from contextlib import contextmanager
import copy
import hashlib
import os
from pathlib import Path
import stat

from .bounded_qualification import publication_directory
from .puck_dependency_files import (HeldDependencyNamespace, MAX_METADATA_BYTES,
                                    _absolute, _canonical)
from .puck_execution_files import _identity
from .puck_native_identity import TMPFS_IDENTITY_POLICY, require_tmpfs_descriptor
from .puck_runtime_registration import (_Snapshot, _clock, MiB, MAX_CENSUS_ENTRIES,
                                        MAX_REGISTRATION_BYTES)


def _planning(registration, deadline):
    snapshot=_Snapshot(deadline);plans=[];entries=0
    try:
        for root in registration['roots']:
            census=snapshot.census(root['root']) if root['kind']=='package' else None
            if census is not None and {p for p,s in census.items() if stat.S_ISREG(s[2])}!={r['path'] for r in root['files']}:
                raise ValueError('Staging source has extra or missing registered files')
            directories={p for p,s in (census or {}).items() if stat.S_ISDIR(s[2])}
            states={}
            for row in root['files']:
                state=snapshot.leaf_state(root['root'],row['path']);snapshot.admit(state)
                if state[3]!=row['size_bytes']:raise ValueError('Staging source file size differs')
                states[row['path']]=state
                directories.update(str(p) for p in Path(row['path']).parents if str(p)!='.')
            fd=snapshot.directory(Path(root['root']).parts[1:])
            plans.append(dict(census=census,directories=sorted(directories),files=states,
                              root_identity=_identity(os.fstat(fd))))
            entries+=len(census) if census is not None else len(states)+len(directories)
            if entries>MAX_CENSUS_ENTRIES or len(_canonical(plans))>MAX_METADATA_BYTES:
                raise ValueError('Staging source census or metadata ceiling exceeded')
        snapshot.recheck_directories()
        return plans
    finally:snapshot.close()


@contextmanager
def _destination_directories(staging_root,plans,deadline):
    """Create every destination directory before any source custody starts."""
    entries={}
    with publication_directory(Path(staging_root).parent) as parent:
        try:
            wanted={''}
            for index,plan in enumerate(plans):
                prefix='root-'+str(index).zfill(4);wanted.add(prefix)
                wanted.update(prefix+'/'+path for path in plan['directories'])
            for relative in sorted(wanted,key=lambda p:(p.count('/')+bool(p),p)):
                _clock(deadline)
                parent_relative,_,name=relative.rpartition('/')
                held=entries[parent_relative][0] if relative else parent
                if not relative:name=Path(staging_root).name
                os.mkdir(name,mode=0o700,dir_fd=held)
                fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=held)
                entries[relative]=(fd,held,name,None)
                os.fchmod(fd,0o700);state=os.fstat(fd)
                entries[relative]=(fd,held,name,(state.st_dev,state.st_ino,state.st_mode))
            yield {path:row[0] for path,row in entries.items()}
        finally:
            first=None
            for fd,held,name,expected in reversed(tuple(entries.values())):
                try:
                    _clock(deadline);os.fsync(fd)
                    value=os.fstat(fd);named=os.stat(name,dir_fd=held,follow_symlinks=False)
                    if ((value.st_dev,value.st_ino,value.st_mode)!=expected
                            or (named.st_dev,named.st_ino,named.st_mode)!=expected
                            or not stat.S_ISDIR(value.st_mode) or stat.S_IMODE(value.st_mode)!=0o700):
                        raise RuntimeError('Staging destination directory identity differs')
                except BaseException as error:
                    if first is None:first=error
                finally:
                    try:os.close(fd)
                    except BaseException as error:
                        if first is None:first=error
            if first is not None:raise first


def _check_sources(snapshot,registration,plans,*,hashes,admit=False):
    for root,plan in zip(registration['roots'],plans):
        fd=snapshot.directory(Path(root['root']).parts[1:])
        if _identity(os.fstat(fd))!=plan['root_identity']:
            raise RuntimeError('Staging source root changed')
        if plan['census'] is not None and snapshot.census(root['root'])!=plan['census']:
            raise RuntimeError('Staging source namespace changed')
        for row in root['files']:
            expected=plan['files'][row['path']]
            if snapshot.leaf_state(root['root'],row['path'])!=expected:
                raise RuntimeError('Staging source file edge changed')
            if admit:snapshot.admit(expected)
            if hashes and snapshot.hash_leaf(root['root'],row['path'],expected)[0]!=row:
                raise ValueError('Staging source file hash differs')
    snapshot.recheck_directories()


def _copy_leaf(snapshot,root,row,expected,directory,deadline):
    parts=row['path'].split('/');parent=snapshot.directory((*Path(root).parts[1:],*parts[:-1]))
    source=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC,dir_fd=parent)
    target=None
    try:
        def source_check():
            _clock(deadline)
            if (_identity(os.fstat(source))!=expected
                    or _identity(os.stat(parts[-1],dir_fd=parent,follow_symlinks=False))!=expected):
                raise RuntimeError('Staging source changed during copy')
        source_check()
        target=os.open(parts[-1],os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=directory)
        os.fchmod(target,0o600);identity=require_tmpfs_descriptor(target)
        digest=hashlib.sha256();count=0
        while True:
            source_check();block=os.read(source,min(MiB,row['size_bytes']+1-count))
            if not block:break
            count+=len(block)
            if count>row['size_bytes']:raise RuntimeError('Staging source grew during copy')
            digest.update(block);remaining=memoryview(block)
            while remaining:
                _clock(deadline);written=os.write(target,remaining)
                if written<1:raise OSError('Staging write made no progress')
                remaining=remaining[written:]
        if count!=row['size_bytes'] or digest.hexdigest()!=row['sha256']:
            raise ValueError('Staging copied content differs')
        os.fsync(target);source_check();require_tmpfs_descriptor(target)
        value=os.fstat(target);named=os.stat(parts[-1],dir_fd=directory,follow_symlinks=False)
        if (_identity(value)!=_identity(named) or (value.st_dev,value.st_ino)!=identity
                or value.st_nlink!=1 or value.st_size!=count or stat.S_IMODE(value.st_mode)!=0o600):
            raise RuntimeError('Staging destination leaf changed')
        return _identity(value)
    finally:
        first=None
        for fd in (target,source):
            if fd is not None:
                try:os.close(fd)
                except BaseException as error:
                    if first is None:first=error
        if first is not None:raise first


def _destination_census(snapshot,staging_root,roots):
    directory=snapshot.directory(Path(staging_root).parts[1:])
    wanted={Path(row['root']).name for row in roots};seen=set();result={};count=0
    with os.scandir(directory) as entries:
        for entry in entries:
            _clock(snapshot.deadline)
            if entry.name not in wanted or entry.name in seen:
                raise RuntimeError('Staging destination has an unexpected root entry')
            seen.add(entry.name)
    if seen!=wanted:raise RuntimeError('Staging destination lacks a registered root')
    for row in roots:
        root=row['root'];prefix=Path(root).name
        result[prefix]=_identity(os.fstat(snapshot.directory(Path(root).parts[1:])))
        census=snapshot.census(root);count+=len(census)
        if count>MAX_CENSUS_ENTRIES:raise ValueError('Staging destination census ceiling exceeded')
        result.update((prefix+'/'+path,state) for path,state in census.items())
    return result


def stage_tmpfs_registration(registration_raw:bytes,*,expected_sha256,staging_root:str,deadline:float)->dict:
    """Stage every declared byte, returning a closed, independently checkable v3."""
    staging_root=_absolute(staging_root)
    schema_path=staging_root+'/.registration-schema-only.json'
    validated=HeldDependencyNamespace(registration_raw,expected_sha256=expected_sha256,
                                     deadline=deadline,registration_path=schema_path)
    registration=copy.deepcopy(validated._registration)
    if registration['version'] not in (2,3):raise ValueError('Staging requires dependency registration v2 or v3')
    for root in registration['roots']:
        source=root['root']
        if source==staging_root or source.startswith(staging_root+'/') or staging_root.startswith(source+'/'):
            raise ValueError('Staging and source roots overlap')
    if os.path.lexists(staging_root):raise FileExistsError('Staging destination already exists')
    plans=_planning(registration,deadline)
    result=copy.deepcopy(registration);result.update(kind='puck-worker-dependencies-v3',version=3,native_identity=TMPFS_IDENTITY_POLICY)
    for index,root in enumerate(result['roots']):
        root.update(root=staging_root+'/root-'+str(index).zfill(4),kind='package')
    raw=_canonical(result)
    metadata_bytes=len(registration_raw)+len(raw)+len(_canonical(plans))
    if len(raw)>MAX_REGISTRATION_BYTES or metadata_bytes>MAX_METADATA_BYTES:
        raise ValueError('Staging registration or metadata ceiling exceeded')
    HeldDependencyNamespace(raw,expected_sha256=hashlib.sha256(raw).hexdigest(),deadline=deadline,registration_path=schema_path)
    with _destination_directories(staging_root,plans,deadline) as directories:
        source=_Snapshot(deadline)
        try:
            _check_sources(source,registration,plans,hashes=True,admit=True)
            targets={};expected_directories=set(directories)-{''}
            for index,root in enumerate(registration['roots']):
                prefix='root-'+str(index).zfill(4)
                for row in root['files']:
                    path=prefix+'/'+row['path'];parent=path.rpartition('/')[0]
                    targets[path]=_copy_leaf(source,root['root'],row,plans[index]['files'][row['path']],directories[parent],deadline)
            _check_sources(source,registration,plans,hashes=True)
            destination=_Snapshot(deadline)
            try:
                census=_destination_census(destination,staging_root,result['roots'])
                if (set(census)!=expected_directories|set(targets)
                        or any(not stat.S_ISDIR(census[p][2]) for p in expected_directories)
                        or any(census[p]!=identity for p,identity in targets.items())):
                    raise RuntimeError('Staging destination namespace or identity differs')
                if metadata_bytes+len(_canonical(census))>MAX_METADATA_BYTES:
                    raise ValueError('Staging destination metadata ceiling exceeded')
                for index,root in enumerate(result['roots']):
                    for row in root['files']:
                        expected=targets['root-'+str(index).zfill(4)+'/'+row['path']]
                        destination.admit(expected)
                        if destination.hash_leaf(root['root'],row['path'],expected)[0]!=row:
                            raise ValueError('Staging destination hash differs')
                if _destination_census(destination,staging_root,result['roots'])!=census:
                    raise RuntimeError('Staging destination changed during verification')
                destination.recheck_directories()
            finally:destination.close()
            _check_sources(source,registration,plans,hashes=False)
        finally:source.close()
    _clock(deadline)
    return result
