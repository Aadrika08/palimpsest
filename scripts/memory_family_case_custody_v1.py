"""Private one-shot case publication capability; no execution/qualification grant.

The default HeldReplayFiles class remains read-only. This capability owns its own
instance and permits baseline changes only after a named, verified directory/file
transition. Its held descriptor objects never escape to a public result.
"""
from __future__ import annotations
import copy
import ctypes
import hashlib
import os
from pathlib import Path
import stat
import sys
from palimpsest import memory
from scripts.memory_directory_census_v1 import directory_names
from scripts import memory_family_replay_custody_v4 as custody
from scripts import memory_family_producer_v4 as source

MiB=1024**2
CASE_FILES=('manifest.json','close.json','commit.json')


class CasePublicationIndeterminate(RuntimeError):
    """A successful output creation followed by failure cannot grant acceptance."""


def _rename_case_noreplace(old_parent, name, new_parent):
    if sys.platform!='linux':raise NotImplementedError('Case publication requires Linux renameat2')
    libc=ctypes.CDLL(None,use_errno=True)
    try:rename=libc.renameat2
    except AttributeError as error:raise NotImplementedError('libc has no renameat2') from error
    rename.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
    rename.restype=ctypes.c_int
    encoded=os.fsencode(name)
    if rename(old_parent,encoded,new_parent,encoded,1)!=0:
        code=ctypes.get_errno();raise OSError(code,os.strerror(code),name)


class _CasePublication:
    """Own exact retained inputs until the final move, fsyncs and teardown.

    `entries` are physical .pending/<case_id>/... descriptors, not caller cells.
    Dependency groups are {'root': absolute_path, 'entries': sorted_descriptors};
    they remain ordinary read-only custody and may not overlap mutable case paths.
    """
    def __init__(self,evidence_root,case_id,entries,deadline,*,dependencies=(),recheck_acceptance=None):
        memory._id(case_id)
        if '/' in case_id or '\\' in case_id:raise ValueError('Invalid case path component')
        self._recheck_acceptance=recheck_acceptance
        self.root=Path(evidence_root);self.case_id=case_id
        self.entries=copy.deepcopy(entries);self.dependencies=copy.deepcopy(dependencies)
        if type(dependencies) not in (list,tuple) or len(dependencies)>16:
            raise ValueError('Dependency group bound exceeded')
        if sum(len(g.get('entries',())) for g in dependencies if type(g) is dict)>1024:
            raise ValueError('Dependency file count bound exceeded')
        self.prefix=f'.pending/{case_id}'
        if type(entries) not in (list,tuple) or not 1<=len(entries)<=418:
            raise ValueError('Case retained-file bound exceeded')
        if any(not d['path'].startswith(self.prefix+'/') for d in entries):
            raise ValueError('Case inputs must name the exact staged case')
        directories={self.prefix}
        for d in entries:
            p=d['path'].rsplit('/',1)[0]
            while p!=self.prefix:
                directories.add(p);p=p.rsplit('/',1)[0]
        if len(directories)!=33:raise ValueError('Case requires exactly 33 retained directories')
        self._held=custody.HeldReplayFiles(self.root,self.entries,deadline,exact_subtrees=(self.prefix,))
        self._dependency_holds=[];self._state='new';self._mutated=False;self._moved=False
        self._payloads={};self._case_names={'source','conditions'}
        self._root_key=self.root.parts[1:]
        self._pending_key=(*self._root_key,'.pending')
        self._cases_key=(*self._root_key,'cases')
        self._case_key=(*self._pending_key,case_id)

    def __enter__(self):
        if self._state!='new':raise RuntimeError('Publication capability is one-shot')
        try:
            self._held.__enter__()
            self._pending=self._held._directory(self._pending_key)
            self._cases=self._held._directory(self._cases_key)
            self._case=self._held._directory(self._case_key)
            if os.fstat(self._pending).st_dev!=os.fstat(self._cases).st_dev:
                raise ValueError('Case parents must be on one filesystem')
            self._pending_names=set(directory_names(self._pending,max_entries=4096,deadline=self._held.deadline))
            self._cases_names=set(directory_names(self._cases,max_entries=4096,deadline=self._held.deadline))
            if self.case_id in self._cases_names:raise FileExistsError('Final case already exists')
            if self.case_id not in self._pending_names:raise ValueError('Staged case is absent')
            for group in self.dependencies:
                if type(group) is not dict or set(group)!={'root','entries'}:
                    raise ValueError('Invalid dependency group')
                # An independent dependency hold cannot own a mutable case edge.
                dependency_root=Path(group['root'])
                for descriptor in group['entries']:
                    path=dependency_root/descriptor['path']
                    if path==self.root/'.pending' or path==self.root/'cases' or path.is_relative_to(self.root/self.prefix):
                        raise ValueError('Read-only dependency overlaps mutable case')
                held=custody.HeldReplayFiles(dependency_root,group['entries'],self._held.deadline)
                held.__enter__();self._dependency_holds.append(held)
            self._state='active';self.recheck();return self
        except BaseException as primary:
            try:self._close()
            except BaseException as cleanup:primary.add_note('Admission cleanup also failed: '+str(cleanup))
            self._state='failed';raise

    def _active(self):
        if self._state not in ('active','written','published'):
            raise RuntimeError('Publication capability is inactive')

    def recheck(self):
        self._active();h=self._held
        if self._recheck_acceptance is not None:self._recheck_acceptance()
        # Do not use public recheck's auto-close-on-failure here: quarantine must
        # retain the original case fd after a failed mutation check.
        h._clock();h._check_dirs();self._check_case_tree()
        for path in h._entries:h._check_file(path)
        h._check_dirs()
        for held in self._dependency_holds:held.recheck()
        if set(directory_names(self._case,max_entries=5,deadline=h.deadline))!=self._case_names:
            raise ValueError('Case root namespace differs')
        if set(directory_names(self._pending,max_entries=4096,deadline=h.deadline))!=self._pending_names:
            raise RuntimeError('Staging parent namespace changed')
        if set(directory_names(self._cases,max_entries=4096,deadline=h.deadline))!=self._cases_names:
            raise RuntimeError('Published parent namespace changed')
        h._clock()

    def _check_case_tree(self):
        """Fresh directory descriptions are required after owned Btrfs writes."""
        h=self._held;files=set(h._entries);directories={self.prefix}
        for path in files:
            parent=path.rsplit('/',1)[0]
            while parent!=self.prefix:
                directories.add(parent);parent=parent.rsplit('/',1)[0]
        def walk(relative):
            fd=h._directory((*self._root_key,*relative.split('/')))
            allowed={p[len(relative)+1:].split('/')[0] for p in files|directories if p.startswith(relative+'/')}
            if set(directory_names(fd,max_entries=454,deadline=h.deadline))!=allowed:
                raise ValueError('Case subtree contains missing or unexpected entries')
            for name in allowed:
                child=relative+'/'+name;state=os.stat(name,dir_fd=fd,follow_symlinks=False)
                if child in directories and stat.S_ISDIR(state.st_mode):walk(child)
                elif child not in files or not stat.S_ISREG(state.st_mode):
                    raise ValueError('Case subtree entry type differs')
        walk(self.prefix)

    def _advance_directory(self,key,names,*,link_delta=0):
        """Advance one authorized edge only; all retained leaves remain strict."""
        if key not in (self._case_key,self._pending_key,self._cases_key):
            raise ValueError('Directory baseline is not mutable')
        h=self._held;fd,parent,name,old=h._dirs[key]
        now=custody._identity(os.fstat(fd));named=custody._identity(os.stat(name,dir_fd=parent,follow_symlinks=False))
        # Btrfs reports directory nlink=1 rather than counting child dirs.
        expected_links = 1 if old[-1] == 1 else old[-1] + link_delta
        if now[:3]!=old[:3] or named!=now or now[-1]!=expected_links:
            raise RuntimeError('Authorized directory inode/type/link transition differs')
        if set(directory_names(fd,max_entries=4096,deadline=h.deadline))!=names:
            raise RuntimeError('Unexpected namespace during authorized transition')
        # No blanket reset: other held directories and every old leaf are checked.
        for other,(other_fd,other_parent,other_name,expected) in h._dirs.items():
            if other in (self._case_key,self._pending_key,self._cases_key):continue
            if custody._identity(os.fstat(other_fd))!=expected or custody._identity(os.stat(other_name,dir_fd=other_parent,follow_symlinks=False))!=expected:
                raise RuntimeError('Unrelated held directory changed')
        for path in h._entries:h._check_file(path)
        h._dirs[key]=(fd,parent,name,now)

    def _write(self,name,payload):
        self.recheck();h=self._held;h._clock()
        fd=os.open(name,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=self._case)
        self._mutated=True;h._fds.append(fd)
        created=os.fstat(fd)
        if not stat.S_ISREG(created.st_mode) or created.st_nlink!=1 or created.st_size!=0:
            raise ValueError('New case file creation differs')
        created_identity=(created.st_dev,created.st_ino,created.st_mode,created.st_nlink)
        self._case_names.add(name)
        self._advance_directory(self._case_key,self._case_names)
        view=memoryview(payload)
        while view:
            h._clock();count=os.write(fd,view[:MiB])
            if count<1:raise OSError('Case write made no progress')
            view=view[count:]
        os.fsync(fd)
        state=os.fstat(fd);named=os.stat(name,dir_fd=self._case,follow_symlinks=False)
        if (state.st_dev,state.st_ino,state.st_mode,state.st_nlink)!=created_identity or custody._identity(state)!=custody._identity(named):
            raise RuntimeError('New case file edge differs')
        count,digest,readback=h._hash(fd,len(payload),copy_bytes=True)
        if count!=len(payload) or readback!=payload or digest!=hashlib.sha256(payload).hexdigest():
            raise ValueError('Case file readback differs')
        path=self.prefix+'/'+name
        h._entries[path]=custody._Entry(path,len(payload),digest,len(payload))
        h._files[path]=(fd,self._case,name,custody._identity(state))
        self.recheck()

    def write_case_files(self,payloads):
        self._active()
        if self._state!='active' or self._mutated:raise RuntimeError('Case files may be written once')
        if type(payloads) is not dict or set(payloads)!=set(CASE_FILES):raise ValueError('Exactly three case payloads required')
        payloads=copy.deepcopy(payloads)
        if any(type(p) is not bytes for p in payloads.values()) or sum(map(len,payloads.values()))>32*MiB:
            raise ValueError('Combined case payload allowance exceeded')
        if len(self.entries)+33+3>454:raise ValueError('Final case entry bound exceeded')
        from palimpsest import artifacts
        for payload in payloads.values():
            if memory.canonical_bytes(artifacts._json(payload))!=payload:
                raise ValueError('Case payload is not canonical JSON')
        self._payloads=payloads
        self._write('manifest.json',payloads['manifest.json'])
        self._write('close.json',payloads['close.json'])
        os.fsync(self._case)
        self._write('.commit.tmp',payloads['commit.json'])
        self.recheck()
        old=self.prefix+'/.commit.tmp';fd,parent,_,before=self._held._files[old]
        source._rename_noreplace(self._case)
        self._case_names.remove('.commit.tmp');self._case_names.add('commit.json')
        after=custody._identity(os.fstat(fd));named=custody._identity(os.stat('commit.json',dir_fd=self._case,follow_symlinks=False))
        if after[:5]!=before[:5] or after[-1]!=before[-1] or named!=after:
            raise RuntimeError('Marker rename changed its retained inode/bytes')
        try:os.stat('.commit.tmp',dir_fd=self._case,follow_symlinks=False)
        except FileNotFoundError:pass
        else:raise RuntimeError('Temporary marker still exists')
        entry=self._held._entries.pop(old);self._held._files.pop(old)
        path=self.prefix+'/commit.json'
        self._held._entries[path]=custody._Entry(path,entry.size,entry.sha256,entry.maximum)
        self._held._files[path]=(fd,parent,'commit.json',after)
        self._advance_directory(self._case_key,self._case_names)
        os.fsync(self._case);self._state='written';self.recheck()

    def _fsync_parent(self,name):
        os.fsync(self._pending if name=='source' else self._cases)

    def publish(self):
        self._active()
        if self._state!='written':raise RuntimeError('Complete durable case files required before move')
        self.recheck()
        _rename_case_noreplace(self._pending,self.case_id,self._cases)
        self._moved=True
        h=self._held;fd,_,name,old=h._dirs[self._case_key]
        h._dirs[self._case_key]=(fd,self._cases,name,old)
        self._pending_names.remove(self.case_id);self._cases_names.add(self.case_id)
        self._advance_directory(self._case_key,self._case_names)
        self._advance_directory(self._pending_key,self._pending_names,link_delta=-1)
        self._advance_directory(self._cases_key,self._cases_names,link_delta=1)
        self.recheck();self._fsync_parent('source');self._fsync_parent('destination')
        self.recheck();self._state='published'

    def _quarantine(self,error):
        h=self._held
        if not h._fds:return
        expected=h._dirs.get(self._case_key)
        if expected is None:return
        if custody._identity(os.fstat(self._case))[:3]!=expected[3][:3]:
            raise RuntimeError('Cannot quarantine a substituted case inode')
        try:os.stat('quarantine.json',dir_fd=self._case,follow_symlinks=False)
        except FileNotFoundError:
            source._write_file(self._case,'quarantine.json',memory.canonical_bytes({
                'schema':'memory-family-case-quarantine-v1','case_id':self.case_id,'error_type':type(error).__name__}))
        os.fsync(self._case);os.fsync(self._pending);os.fsync(self._cases)

    def _drain_dependencies(self):
        first=None
        for held in reversed(self._dependency_holds):
            try:held.__exit__(None,None,None)
            except BaseException as error:first=first or error
        self._dependency_holds=[]
        if first is not None:raise first

    def _close(self):
        first=None
        try:self._drain_dependencies()
        except BaseException as error:first=error
        try:self._held._close()
        except BaseException as error:first=first or error
        self._held._state='closed'
        if first is not None:raise first

    def __exit__(self,kind,error,traceback):
        primary=error
        try:
            if primary is None:
                self.recheck()
                if self._mutated and self._state!='published':raise RuntimeError('Case publication did not complete')
        except BaseException as failure:primary=failure
        # Teardown validation may fail after successful publication. Drain all
        # independent holds while the mutable case descriptor still permits
        # quarantine, preserving an earlier failure as the primary error.
        try:self._drain_dependencies()
        except BaseException as failure:
            if primary is None:primary=failure
            else:primary.add_note('Dependency teardown also failed: '+str(failure))
        # Closing an external validating context can itself expose a late
        # retained-file mutation. Validate the still-held case once more before
        # closing its descriptors or returning a registerable marker.
        if primary is None:
            try:self.recheck()
            except BaseException as failure:primary=failure
        if primary is not None and self._mutated:
            try:self._quarantine(primary)
            except BaseException as cleanup:primary.add_note('Quarantine durability indeterminate: '+str(cleanup))
        try:self._close()
        except BaseException as failure:
            if primary is None:primary=failure
            else:primary.add_note('Publication descriptor teardown also failed: '+str(failure))
        self._state='closed' if primary is None else 'failed'
        if primary is not None:
            if self._mutated:
                raise CasePublicationIndeterminate('Case files may be partially or indeterminately published') from primary
            if primary is not error:raise primary
        return False
