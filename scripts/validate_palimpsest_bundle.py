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
from pathlib import Path, PurePosixPath
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
    require(type(name) is str and name and not name.startswith('/') and '\\' not in name and '\x00' not in name
            and not name.endswith('/') and str(path)==name and all(p not in ('','.','..') for p in path.parts),
            'Unsafe bundle member name: '+repr(name))
    return name


def run_members(run):
    """The files a palimpsest bundle carries for one run directory."""
    run=Path(run);members={}
    for path in sorted((run/'recording').rglob('*')):
        require(not path.is_symlink(),'Run symlink refused')
        if path.is_file():members['recording/'+path.relative_to(run/'recording').as_posix()]=path
    index=json.loads((run/'snapshots/index.json').read_bytes())
    for record in index['snapshots'].values():members['snapshots/'+record['filename']]=run/'snapshots'/record['filename']
    for name in ('job-events.jsonl','replay-report.json'):
        if (run/name).is_file():members[name]=run/name
    return members


def validate_bundle(bundle,run=None):
    raw=Path(bundle).read_bytes();require(len(raw)<=MAX_TOTAL_BYTES,'Bundle exceeds its byte bound')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos=archive.infolist();names=[info.filename for info in infos]
        require(0<len(infos)<=MAX_MEMBERS and len(names)==len(set(names)),'Bundle members are bounded and distinct')
        require(names[-1]=='bundle-manifest.json','Bundle manifest must be the last member')
        total=0;members={}
        for info in infos:
            _member(info.filename)
            require(not info.is_dir() and info.compress_type==zipfile.ZIP_STORED and info.file_size<=MAX_MEMBER_BYTES
                    and info.compress_size==info.file_size,'Bundle member must be a bounded stored file: '+info.filename)
            payload=archive.read(info)
            require(zlib.crc32(payload)&0xffffffff==info.CRC and len(payload)==info.file_size,'Bundle member CRC differs: '+info.filename)
            total+=len(payload);members[info.filename]=payload
        require(total<=MAX_TOTAL_BYTES,'Bundle members exceed the total bound')
    manifest_raw=members.pop('bundle-manifest.json');require(len(manifest_raw)<=MAX_MANIFEST_BYTES,'Bundle manifest exceeds its bound')
    manifest=json.loads(manifest_raw)
    require(type(manifest) is dict and set(manifest)=={'format','files','derived'} and manifest['format']==FORMAT
            and type(manifest['derived']) is dict and type(manifest['files']) is list,'Bundle manifest schema differs')
    listed={}
    for row in manifest['files']:
        require(type(row) is dict and set(row)=={'path','size_bytes','sha256'} and _member(row['path']) not in listed,'Bundle manifest row differs')
        listed[row['path']]=row
    require(set(listed)==set(members),'Bundle members differ from the manifest: '+str(sorted(set(listed)^set(members))))
    for name,payload in members.items():
        require(listed[name]['size_bytes']==len(payload) and listed[name]['sha256']==sha(payload),'Bundle member hash differs: '+name)
    if run is not None:
        expected=run_members(run)
        require(set(expected)==set(members),'Bundle members differ from the run: '+str(sorted(set(expected)^set(members))))
        for name,path in expected.items():require(path.read_bytes()==members[name],'Bundle member differs from the run file: '+name)
    return dict(sha256=sha(raw),size_bytes=len(raw),members=len(members),member_bytes=sum(len(v) for v in members.values()))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle');parser.add_argument('--run')
    args=parser.parse_args()
    print(json.dumps(validate_bundle(args.bundle,args.run),sort_keys=True))


if __name__=='__main__':main()
