"""Stdlib-only palimpsest-bundle-v1 validator and .npz/.npy reader; imports no project code.

A bundle is one ZIP_STORED archive whose ``bundle-manifest.json`` (last member)
lists every other member with its exact size and SHA-256. ``validate_bundle``
checks member names (no traversal, absolute paths, directories or duplicates),
storage method, CRC-32, per-member and total byte limits, and the manifest; with
``run`` it also requires the members to be exactly the run's bundled files with
identical bytes. ``read_npz`` parses ``palimpsest-npz-v1`` chunks without numpy.
"""
import argparse
import ast
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import struct
import zipfile
import zlib

MiB=1024**2
FORMAT='palimpsest-bundle-v1'
MAX_MEMBERS=4096
MAX_MEMBER_BYTES=16*MiB
MAX_TOTAL_BYTES=64*MiB
MAX_MANIFEST_BYTES=4*MiB
DTYPES={'|u1':('B',1),'|b1':('?',1),'|i1':('b',1),'<i2':('h',2),'<u2':('H',2),'<i4':('i',4),'<u4':('I',4),
        '<i8':('q',8),'<u8':('Q',8),'<f4':('f',4),'<f8':('d',8)}


def sha(raw):return hashlib.sha256(raw).hexdigest()


def require(value,message):
    if not value:raise ValueError(message)


class Array:
    """One little-endian C-order array: dtype descriptor, shape and raw bytes."""
    def __init__(self,descr,shape,data):self.descr,self.shape,self.data=descr,tuple(shape),data
    @property
    def itemsize(self):return DTYPES[self.descr][1]
    @property
    def count(self):
        value=1
        for size in self.shape:value*=size
        return value
    def values(self):
        return struct.unpack('<%d%s' % (self.count,DTYPES[self.descr][0]),self.data)
    def rows(self):
        """Raw bytes of each leading-axis row."""
        step=len(self.data)//self.shape[0] if self.shape and self.shape[0] else 0
        return [self.data[i*step:(i+1)*step] for i in range(self.shape[0])]


def read_npy(raw):
    require(raw[:6]==b'\x93NUMPY' and raw[6:8] in (b'\x01\x00',b'\x02\x00'),'NPY magic/version differs')
    if raw[6]==1:length=struct.unpack('<H',raw[8:10])[0];start=10
    else:length=struct.unpack('<I',raw[8:12])[0];start=12
    require(length<=65536 and len(raw)>=start+length,'NPY header bound differs')
    header=ast.literal_eval(raw[start:start+length].decode('latin1'))
    require(type(header) is dict and set(header)=={'descr','fortran_order','shape'} and header['fortran_order'] is False
            and header['descr'] in DTYPES and type(header['shape']) is tuple
            and all(type(n) is int and 0<=n<2**31 for n in header['shape']),'NPY header differs')
    array=Array(header['descr'],header['shape'],raw[start+length:])
    require(len(array.data)==array.count*array.itemsize,'NPY payload size differs')
    return array


def read_npz(raw,maximum=128*MiB):
    require(len(raw)<=maximum,'NPZ exceeds its bound')
    result={}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names=archive.namelist();require(len(names)==len(set(names))<=256,'NPZ members differ')
        for info in archive.infolist():
            require(info.filename.endswith('.npy') and '/' not in info.filename and info.compress_type==zipfile.ZIP_STORED,
                    'NPZ member differs: '+info.filename)
            result[info.filename[:-4]]=read_npy(archive.read(info))
    return result


def _member(name):
    path=PurePosixPath(name)
    require(type(name) is str and name and not name.startswith('/') and '\\' not in name
            and not any(ord(c)<32 or ord(c)==127 for c in name) and not name.endswith('/') and str(path)==name
            and all(p not in ('','.','..') for p in path.parts),'Unsafe bundle member name: '+repr(name))
    return name


def read_regular(path,maximum):
    """Bounded read of one regular file, never following a symlink."""
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
    try:
        state=os.fstat(fd);require(stat.S_ISREG(state.st_mode) and state.st_size<=maximum,'Bounded regular file required: '+str(path))
        with os.fdopen(os.dup(fd),'rb') as stream:raw=stream.read(maximum+1)
        require(len(raw)==state.st_size,'File changed while read: '+str(path))
        return raw
    finally:os.close(fd)


def _zip64(extra,sizes):
    """Resolve 0xFFFFFFFF size/offset fields from one zip64 extra block."""
    values=list(sizes);position=0
    while position+4<=len(extra):
        tag,length=struct.unpack_from('<HH',extra,position);body=extra[position+4:position+4+length]
        require(len(body)==length,'Truncated ZIP extra field')
        if tag==1:
            fields=[i for i,v in enumerate(values) if v==0xFFFFFFFF]
            require(len(body)>=8*len(fields),'Short zip64 extra field')
            for slot,index in enumerate(fields):values[index]=struct.unpack_from('<Q',body,8*slot)[0]
        position+=4+length
    require(position==len(extra),'Malformed ZIP extra fields')
    return values


def parse_zip(raw):
    """Exact layout: contiguous stored members from offset 0, the central directory, then one comment-free EOCD."""
    require(len(raw)>=22 and raw[-22:-18]==b'PK\x05\x06','ZIP end record must close the file with no trailing bytes')
    disk,cd_disk,entries_disk,entries,cd_size,cd_offset,comment=struct.unpack_from('<HHHHIIH',raw,len(raw)-18)
    require(comment==0 and disk==cd_disk==0 and entries_disk==entries,'ZIP end record must be single-disk with no comment')
    end=len(raw)-22
    if end>=20 and raw[end-20:end-16]==b'PK\x06\x07':
        record=struct.unpack_from('<Q',raw,end-12)[0];require(raw[record:record+4]==b'PK\x06\x06','ZIP64 end record differs')
        size=struct.unpack_from('<Q',raw,record+4)[0];require(record+12+size==end-20,'ZIP64 end record must be contiguous')
        entries,_,cd_size,cd_offset=struct.unpack_from('<QQQQ',raw,record+24);end=record
    require(cd_offset+cd_size==end and 0<entries<=MAX_MEMBERS,'ZIP central directory must end at the end records')
    members=[];position=cd_offset;names=set();folded=set()
    for _ in range(entries):
        require(raw[position:position+4]==b'PK\x01\x02','ZIP central directory entry differs')
        (_,_,flags,method,_,_,crc,csize,usize,nlen,xlen,clen,_,_,external,offset)=struct.unpack_from('<HHHHHHIIIHHHHHII',raw,position+4)
        name_raw=raw[position+46:position+46+nlen];extra=raw[position+46+nlen:position+46+nlen+xlen]
        csize,usize,offset=_zip64(extra,(csize,usize,offset)) if 0xFFFFFFFF in (csize,usize,offset) else (csize,usize,offset)
        name=name_raw.decode('utf-8' if flags&0x800 else 'cp437');_member(name)
        mode=external>>16
        require(flags in (0,0x800) and method==0 and clen==0 and csize==usize and stat.S_IFMT(mode) in (0,stat.S_IFREG)
                and name not in names and name.lower() not in folded,'Bundle member must be a distinct stored regular file: '+name)
        names.add(name);folded.add(name.lower())
        members.append(dict(name=name,name_raw=name_raw,flags=flags,crc=crc,size=usize,offset=offset))
        position+=46+nlen+xlen+clen
    require(position==end,'ZIP central directory size differs')
    require(sum(m['size'] for m in members)<=MAX_TOTAL_BYTES and all(m['size']<=MAX_MEMBER_BYTES for m in members),
            'Bundle members exceed the total or per-member bound')
    cursor=0
    for member in sorted(members,key=lambda m:m['offset']):
        require(member['offset']==cursor and raw[cursor:cursor+4]==b'PK\x03\x04','ZIP members must be contiguous from offset 0')
        (_,flags,method,_,_,crc,csize,usize,nlen,xlen)=struct.unpack_from('<HHHHHIIIHH',raw,cursor+4)
        name_raw=raw[cursor+30:cursor+30+nlen];extra=raw[cursor+30+nlen:cursor+30+nlen+xlen]
        csize,usize=_zip64(extra,(csize,usize)) if 0xFFFFFFFF in (csize,usize) else (csize,usize)
        require(name_raw==member['name_raw'] and flags==member['flags'] and method==0 and crc==member['crc']
                and csize==usize==member['size'],'ZIP local header differs from the central directory: '+member['name'])
        start=cursor+30+nlen+xlen;member['data']=raw[start:start+member['size']];cursor=start+member['size']
        require(len(member['data'])==member['size'] and zlib.crc32(member['data'])&0xffffffff==member['crc'],
                'Bundle member CRC differs: '+member['name'])
    require(cursor==cd_offset,'ZIP central directory must follow the last member')
    return members


def _manifest(raw):
    def pairs(rows):
        result={}
        for key,value in rows:
            require(key not in result,'Duplicate bundle manifest key');result[key]=value
        return result
    def constant(_):raise ValueError('Nonfinite bundle manifest value')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=constant)


def run_members(run):
    """The files a palimpsest bundle carries for one run directory."""
    run=Path(run);members={}
    for path in sorted((run/'recording').rglob('*')):
        require(not path.is_symlink(),'Run symlink refused')
        if path.is_file():members['recording/'+path.relative_to(run/'recording').as_posix()]=path
    index=_manifest(read_regular(run/'snapshots/index.json',MAX_MANIFEST_BYTES))
    for record in index['snapshots'].values():members['snapshots/'+record['filename']]=run/'snapshots'/record['filename']
    for name in ('job-events.jsonl','replay-report.json'):
        if os.path.lexists(run/name):members[name]=run/name
    return members


def validate_bundle(bundle,run=None):
    raw=read_regular(bundle,MAX_TOTAL_BYTES+MAX_MANIFEST_BYTES+MAX_MEMBERS*1024)
    parsed=parse_zip(raw);names=[m['name'] for m in sorted(parsed,key=lambda m:m['offset'])]
    require(names[-1]=='bundle-manifest.json','Bundle manifest must be the last member')
    members={m['name']:m['data'] for m in parsed}
    manifest_raw=members.pop('bundle-manifest.json');require(len(manifest_raw)<=MAX_MANIFEST_BYTES,'Bundle manifest exceeds its bound')
    manifest=_manifest(manifest_raw)
    require(type(manifest) is dict and set(manifest)=={'format','files','derived'} and manifest['format']==FORMAT
            and type(manifest['derived']) is dict and type(manifest['files']) is list,'Bundle manifest schema differs')
    listed={}
    for row in manifest['files']:
        require(type(row) is dict and set(row)=={'path','size_bytes','sha256'} and _member(row['path']) not in listed
                and type(row['size_bytes']) is int and type(row['sha256']) is str,'Bundle manifest row differs')
        listed[row['path']]=row
    require(set(listed)==set(members),'Bundle members differ from the manifest: '+str(sorted(set(listed)^set(members))))
    for name,payload in members.items():
        require(listed[name]['size_bytes']==len(payload) and listed[name]['sha256']==sha(payload),'Bundle member hash differs: '+name)
    if run is not None:
        expected=run_members(run)
        require(set(expected)==set(members),'Bundle members differ from the run: '+str(sorted(set(expected)^set(members))))
        for name,path in expected.items():
            require(read_regular(path,MAX_MEMBER_BYTES)==members[name],'Bundle member differs from the run file: '+name)
    return dict(sha256=sha(raw),size_bytes=len(raw),members=len(members),member_bytes=sum(len(v) for v in members.values()))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle');parser.add_argument('--run')
    args=parser.parse_args()
    print(json.dumps(validate_bundle(args.bundle,args.run),sort_keys=True))


if __name__=='__main__':main()
