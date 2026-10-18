"""Read-only package-data custody for one separately admitted retained installation.

No imports, leases, bytecode loaders or runtime/collection authority are granted.
This profile preserves explicit empty directories without changing collection caps.
"""
import json
import os
import stat

from .puck_execution_files import _HeldFileCore, _identity, _relative

MiB = 1024**2
INERT_PYC_PATH = 'numpy/distutils/__pycache__/conv_template.cpython-311.pyc'


class _AdmissionFileCore(_HeldFileCore):
    _full_selected_tree = False

    def _edge(self,key,identity):
        prefix=self.root.parts[1:]
        selected=self._full_selected_tree and key[:len(prefix)]==prefix
        return identity if selected else identity[:3]

    def _directory(self,key):
        if key in self._dirs:return self._dirs[key][0]
        self._clock()
        if not key:
            parent,name=None,'/'
            fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        else:
            parent,name=self._directory(key[:-1]),key[-1]
            fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent)
        self._fds.append(fd)
        before=_identity(os.fstat(fd))
        if self._edge(key,before)!=self._edge(key,_identity(os.stat(name,dir_fd=parent,follow_symlinks=False))):
            raise RuntimeError('Retained directory edge changed during open: /'+'/'.join(key))
        self._dirs[key]=(fd,parent,name,before)
        return fd

    def _check_dirs(self):
        for key,(fd,parent,name,expected) in self._dirs.items():
            self._clock();wanted=self._edge(key,expected)
            if (self._edge(key,_identity(os.fstat(fd)))!=wanted or
                    self._edge(key,_identity(os.stat(name,dir_fd=parent,follow_symlinks=False)))!=wanted):
                raise RuntimeError('Retained directory identity changed: /'+'/'.join(key))


class AdmissionInputs(_AdmissionFileCore):
    def __init__(self, root, entries, deadline):
        super().__init__(root,entries,deadline,limits=(512,32*MiB,64*MiB))

    def read_json(self, relative):
        relative = self._guard(relative)
        if self._files[relative][3][3] > 8*MiB:
            raise ValueError('Admission JSON exceeds its private eight MiB cap')
        raw = self._check_file(relative,copy_bytes=True)
        self._check_dirs();self._clock()
        def pairs(items):
            result = {}
            for key,value in items:
                if key in result:raise ValueError('Duplicate admission JSON key')
                result[key]=value
            return result
        def bad(value):raise ValueError('Nonfinite admission JSON')
        value = json.loads(raw,object_pairs_hook=pairs,parse_constant=bad)
        pending,count=[(value,0)],0
        while pending:
            self._clock();current,depth=pending.pop();count+=1
            if count>300000 or depth>32:raise ValueError('Admission JSON structure cap')
            if type(current) is dict:pending.extend((v,depth+1) for v in current.values())
            elif type(current) is list:pending.extend((v,depth+1) for v in current)
        return value


def validate_inert_files(entries,expected):
    if type(expected) is not dict or expected.get('path')!=INERT_PYC_PATH:
        raise ValueError('Unsupported inert bytecode exception')
    actual=[]
    for row in entries:
        path=_relative(row['path'])
        if path.endswith('.pth'):raise ValueError('Installed startup hook refused')
        if path.endswith('.pyc'):actual.append(row)
    if actual!=[expected]:raise ValueError('Authenticated inert bytecode identity differs')
    return dict(expected)


class HeldInstalledFiles(_AdmissionFileCore):
    _full_selected_tree = True
    def __init__(self,root,entries,directories,deadline,*,check=None):
        if (type(directories) is not list or directories!=sorted(set(directories))
                or len(directories)>5000):
            raise ValueError('Installed directory inventory differs')
        children={'':{}}
        for directory in directories:
            _relative(directory)
            if len(directory.split('/'))>32:raise ValueError('Installed directory depth exceeds32')
            children[directory]={}
        for directory in directories:
            parent,_,name=directory.rpartition('/')
            if parent not in children:raise ValueError('Missing admitted directory ancestor')
            children[parent][name]='directory'
        for row in entries:
            path=_relative(row['path']);parent,_,name=path.rpartition('/')
            if parent not in children or name in children[parent]:
                raise ValueError('Missing parent or installed file/directory collision')
            children[parent][name]='file'
        self._children=children
        self._budget_check=check
        super().__init__(root,entries,deadline,limits=(40000,1024*MiB,3072*MiB))

    def _clock(self):
        if self._budget_check is not None:self._budget_check()
        super()._clock()

    def _check_subtrees(self):
        key=self.root.parts[1:]
        for relative,expected in self._children.items():
            self._clock()
            directory=self._directory((*key,*relative.split('/'))) if relative else self._directory(key)
            scan=os.open('.',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=directory)
            names=set()
            try:
                with os.scandir(scan) as iterator:
                    for item in iterator:
                        self._clock()
                        if item.name not in expected or item.name in names:
                            raise ValueError('Installed namespace has an unregistered entry')
                        names.add(item.name)
                        state=item.stat(follow_symlinks=False)
                        matches=(stat.S_ISDIR(state.st_mode) if expected[item.name]=='directory'
                                 else stat.S_ISREG(state.st_mode) and state.st_nlink==1)
                        if not matches:raise ValueError('Installed entry type or alias count differs')
            finally:os.close(scan)
            if names!=set(expected):raise ValueError('Installed namespace lacks an admitted entry')
