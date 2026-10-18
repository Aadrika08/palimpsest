"""C1 boot and preparation02 stage guard for every attempt-11b one-shot step.

Reads the boot id, the pinned preparation02 result and the metadata of five directories
(opened O_DIRECTORY|O_NOFOLLOW, never listed or written). A reboot or a recreated stage
fails here, before any admission, observer or audit is consumed.
"""
import ctypes,hashlib,json,os,stat

BOOT='7f875223-b4cf-421e-b04d-81e3c1f19460'
STAGE='/tmp/palimpsest-puck-cpu-held-02'
RESULT='runs/puck-cpu-held-preparation-02/result.json'
RESULT_SHA='4ef13965e6f312a0bcdef9c49e57190f6a9526988f20f1959357bcc31400e0d4'
ROOTS=[dict(device=55,inode=10400+index,root_index=index) for index in range(4)]
TMPFS_MAGIC=0x01021994


def require(value,message):
    if not value:raise RuntimeError(message)


def tmpfs(fd):
    data=ctypes.create_string_buffer(256);libc=ctypes.CDLL(None,use_errno=True)
    libc.fstatfs.argtypes=(ctypes.c_int,ctypes.c_void_p);libc.fstatfs.restype=ctypes.c_int
    return libc.fstatfs(fd,data)==0 and ctypes.c_long.from_buffer(data).value==TMPFS_MAGIC


def verify(stage,rows,boot,expected_boot):
    """Directory identity, mode, owner and filesystem only; returns the observed metadata."""
    require(boot==expected_boot,'Boot changed since preparation02: '+boot)
    require([r['root_index'] for r in rows]==[0,1,2,3],'Four ordered staged roots required')
    head,name=os.path.split(stage);fds=[];observed={}
    def child(parent,leaf,label):
        fd=os.open(leaf,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=parent);fds.append(fd)
        state=os.fstat(fd)
        require(stat.S_ISDIR(state.st_mode) and stat.S_IMODE(state.st_mode)==0o700 and state.st_uid==os.getuid(),
            'Private 0700 operator-owned directory required: '+label)
        require(tmpfs(fd),'tmpfs directory required: '+label)
        observed[label]=dict(device=state.st_dev,inode=state.st_ino,mode='0700',filesystem='tmpfs');return fd,state
    try:
        top=os.open(head,os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC);fds.append(top)
        parent,pstate=child(top,name,'stage_parent')
        inputs,istate=child(parent,'inputs','inputs')
        for row in rows:
            _,state=child(inputs,'root-'+str(row['root_index']).zfill(4),'root-'+str(row['root_index']).zfill(4))
            require((state.st_dev,state.st_ino)==(row['device'],row['inode']),'Staged root identity differs: '+str(row['root_index']))
        require(pstate.st_dev==istate.st_dev==rows[0]['device'],'Stage parent is not on the staged roots device')
    finally:
        for fd in reversed(fds):os.close(fd)
    return observed


def check(root):
    boot=open('/proc/sys/kernel/random/boot_id').read().strip()
    fd=os.open(os.path.join(str(root),RESULT),os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        with os.fdopen(os.dup(fd),'rb') as stream:raw=stream.read(1024**2+1)
    finally:os.close(fd)
    require(hashlib.sha256(raw).hexdigest()==RESULT_SHA,'Preparation02 result differs')
    result=json.loads(raw)
    require(result['stage_parent']==STAGE and result['staged_roots']==ROOTS and result['status']=='prepared','Preparation02 stage record differs')
    observed=verify(STAGE,ROOTS,boot,BOOT)
    return dict(kind='held11b-stage-boot-guard-v1',status='PASS_STAGE_AND_BOOT',boot_id=boot,stage_parent=STAGE,
        result_sha256=RESULT_SHA,directories=observed,scope='metadata of five directories only; staged bytes are re-hashed by admission/runtime/audit')
