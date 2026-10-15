"""Throwaway metadata assessment; never install, extract or import wheel code."""
import hashlib, html.parser, io, json, os, re, sys, time, tomllib, urllib.parse, urllib.request, zipfile
from email.parser import BytesParser
from pathlib import Path

ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
OUT=ROOT/'docs/reports/puck-cpu-footprint-01'
MAX_RESPONSE=8*1024**2
MAX_TOTAL=32*1024**2
remaining=MAX_TOTAL
requests=[]
deadline=time.monotonic()+480

def fetch(url, *, method='GET', headers=None, expected=None):
    global remaining
    if time.monotonic() >= deadline: raise TimeoutError('Metadata assessment deadline exhausted')
    parsed=urllib.parse.urlsplit(url)
    assert parsed.scheme=='https' and parsed.hostname in ('download.pytorch.org','download-r2.pytorch.org','files.pythonhosted.org','pypi.org')
    request=urllib.request.Request(url, method=method, headers={'Accept-Encoding':'identity', **(headers or {})})
    with urllib.request.urlopen(request, timeout=20) as response:
        final=urllib.parse.urlsplit(response.geturl())
        assert final.scheme=='https' and final.hostname in ('download.pytorch.org','download-r2.pytorch.org','files.pythonhosted.org','pypi.org')
        if expected is not None and response.status != expected: raise ValueError('Unexpected HTTP status '+str(response.status))
        if method=='HEAD': data=b''
        else:
            limit=min(MAX_RESPONSE, remaining)
            length=response.headers.get('Content-Length')
            if length is not None and int(length)>limit: raise ValueError('Response exceeds metadata bound')
            data=response.read(limit+1)
            if len(data)>limit: raise ValueError('Response exceeds metadata bound')
            remaining-=len(data)
        row={'url':url,'final_url':response.geturl(),'method':method,'status':response.status,
            'headers':{k:v for k,v in response.headers.items() if k.lower() in ('content-length','content-range','etag','last-modified','content-encoding')},
            'read_bytes':len(data),'body_sha256':hashlib.sha256(data).hexdigest()}
        requests.append(row)
        return data,response.headers

class Links(html.parser.HTMLParser):
    def __init__(self): super().__init__(); self.rows=[]
    def handle_starttag(self, tag, attrs):
        if tag=='a': self.rows.append(dict(attrs))

def cpu(name, version):
    url='https://download.pytorch.org/whl/cpu/'+name+'/'
    data,_=fetch(url)
    (OUT/(name+'-index.html')).write_bytes(data)
    parser=Links();parser.feed(data.decode())
    filename=name+'-'+version+'-cp311-cp311-manylinux_2_28_x86_64.whl'
    rows=[r for r in parser.rows if urllib.parse.unquote(urllib.parse.urlsplit(r['href']).path).rsplit('/',1)[-1]==filename]
    assert len(rows)==1, (name, len(rows))
    row=rows[0];target=urllib.parse.urljoin(url,row['href']);parts=urllib.parse.urlsplit(target)
    hashes=urllib.parse.parse_qs(parts.fragment)
    digest=hashes.get('sha256',[])
    assert len(digest)==1 and re.fullmatch('[0-9a-f]{64}',digest[0])
    return {'name':name,'version':version,'url':urllib.parse.urlunsplit(parts._replace(fragment='')),'filename':filename,
        'archive_sha256_index_declared':digest[0],'selection':'official CPU index exact CPython311 manylinux_2_28_x86_64',
        'index_metadata_attributes':{k:v for k,v in row.items() if k!='href'}}

class RemoteZip:
    def __init__(self, url, declared_size=None):
        self.url=url; self.pos=0
        _,headers=fetch(url,method='HEAD')
        self.size=int(headers['Content-Length'])
        if declared_size is not None and self.size != declared_size: raise ValueError('HEAD size differs from locked size')
        self.etag=headers.get('ETag')
        if not self.etag or self.etag.startswith('W/'): raise ValueError('Strong ETag required')
    def tell(self): return self.pos
    def seek(self, pos, whence=0):
        self.pos=pos if whence==0 else self.pos+pos if whence==1 else self.size+pos
        if not 0<=self.pos<=self.size: raise OSError('seek outside archive')
        return self.pos
    def seekable(self): return True
    def read(self, amount=-1):
        if amount<0: amount=self.size-self.pos
        amount=min(amount,self.size-self.pos)
        if not amount: return b''
        if amount>MAX_RESPONSE: raise ValueError('Range exceeds metadata bound')
        start=self.pos;end=start+amount-1
        data,headers=fetch(self.url,headers={'Range':'bytes='+str(start)+'-'+str(end),'If-Match':self.etag},expected=206)
        if headers.get('Content-Range')!='bytes '+str(start)+'-'+str(end)+'/'+str(self.size): raise ValueError('Content-Range mismatch')
        if headers.get('ETag')!=self.etag: raise ValueError('ETag changed')
        if len(data)!=amount: raise ValueError('Short range')
        self.pos+=amount
        return data

lock=tomllib.loads((ROOT/'uv.lock').read_text())
retained=json.loads((ROOT/'docs/reports/puck-v3-held-runtime-qualification-01/preparation-payload/dependencies.json').read_bytes())
norm=lambda x:re.sub('[-_.]+','-',x).lower()
versions={norm(r['name']):r['version'] for r in retained['distributions']}
locked={r['name']:r for r in lock['package']}
selected=[];missing=[]
for name,version in sorted(versions.items()):
    if name=='palimpsest' or name=='triton' or name.startswith('nvidia-'): continue
    if name in ('torch','torchvision'):
        selected.append(cpu(name,version+'+cpu'));continue
    package=locked[name];assert package['version']==version
    wheels=[]
    for w in package.get('wheels',[]):
        filename=urllib.parse.unquote(w['url']).rsplit('/',1)[-1]
        stem=filename[:-4]; fields=stem.rsplit('-',3)
        py,abi,platform=fields[-3:]
        if py not in ('cp311','cp310','cp39','cp38','cp37','cp36','py3','py2.py3'):continue
        if py not in ('cp311','py3','py2.py3') and abi!='abi3':continue
        if abi not in ('cp311','abi3','none'):continue
        if platform!='any' and not (platform.endswith('_x86_64') and ('manylinux' in platform or platform=='linux_x86_64')):continue
        wheels.append((0 if py=='cp311' else 1,filename,w))
    if not wheels:
        missing.append({'name':name,'version':version,'reason':'no compatible locked wheel','sdist':package.get('sdist')});continue
    _,filename,w=sorted(wheels,key=lambda r:(r[0],r[1]))[0]
    selected.append({'name':name,'version':version,'filename':filename,'url':w['url'],
        'archive_sha256_index_declared':w['hash'].removeprefix('sha256:'),'locked_archive_bytes':w['size'],
        'selection':'existing lock exact version compatible CPython311 Linux x86_64 wheel'})
summary={'kind':'puck-cpu-wheel-metadata-assessment-v1','version':1,'status':'in_progress',
    'selection_basis':'retained Linux distributions minus NVIDIA/Triton/local Palimpsest; replace only Torch and torchvision with CPU variants',
    'started_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'wheels':[],'missing':missing,
    'archive_payload_hashes_verified':False,'installed':False,'numerical_imports_executed':False,
    'runtime_qualified':False,'collection_authorized':False,'executable':False,'qualification_claims':[]}
try:
    for row in selected:
        print('ASSESS',row['name'],flush=True)
        first_request=len(requests)
        remote=RemoteZip(row['url'],row.get('locked_archive_bytes'))
        with zipfile.ZipFile(remote) as z:
            infos=z.infolist()
            if len(infos)>32768: raise ValueError('Wheel entry count exceeds bound')
            names=set()
            for info in infos:
                parts=info.filename.rstrip('/').split('/')
                if info.filename.startswith('/') or '\\' in info.filename or any(p in ('','.','..') for p in parts): raise ValueError('Unsafe wheel entry')
                if info.filename in names: raise ValueError('Duplicate wheel name')
                names.add(info.filename)
            metadata=[i for i in infos if i.filename.endswith('.dist-info/METADATA')]
            if len(metadata)!=1 or metadata[0].file_size>1024**2: raise ValueError('Bounded unique METADATA required')
            payload=z.read(metadata[0])
            parsed=BytesParser().parsebytes(payload)
            if norm(parsed['Name'])!=row['name'] or parsed['Version']!=row['version']: raise ValueError('Wheel metadata identity differs')
            (OUT/(row['name']+'-METADATA')).write_bytes(payload)
            entry_rows=[{'name':i.filename,'size_bytes':i.file_size,'compressed_size':i.compress_size,'crc32':i.CRC,
                'external_attr':i.external_attr,'compression':i.compress_type} for i in infos]
            (OUT/(row['name']+'-entries.json')).write_text(json.dumps(entry_rows,sort_keys=True,indent=2)+'\n')
            row.update(archive_bytes=remote.size,entry_count=len(infos),file_count=sum(not i.is_dir() for i in infos),
                declared_expanded_bytes=sum(i.file_size for i in infos),metadata_path=metadata[0].filename,
                metadata_sha256=hashlib.sha256(payload).hexdigest(),requires_dist=parsed.get_all('Requires-Dist',[]),
                licence=parsed.get_all('License',[]),licence_expression=parsed.get_all('License-Expression',[]),
                licence_files=parsed.get_all('License-File',[]),requires_python=parsed.get('Requires-Python'),
                transfer_read_bytes=sum(r['read_bytes'] for r in requests[first_request:]),
                etag=remote.etag,archive_payload_hash_verified=False)
        summary['wheels'].append(row)
        (OUT/'assessment.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
    summary['status']='metadata_complete_with_gaps' if missing else 'metadata_complete'
except BaseException as error:
    summary['status']='metadata_failed';summary['failure']=type(error).__name__+': '+str(error)
    raise
finally:
    summary['ended_at_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    summary['total_declared_expanded_bytes']=sum(r['declared_expanded_bytes'] for r in summary['wheels'])
    summary['total_archive_bytes']=sum(r['archive_bytes'] for r in summary['wheels'])
    summary['total_file_count']=sum(r['file_count'] for r in summary['wheels'])
    summary['http_body_bytes_read']=MAX_TOTAL-remaining
    summary['http_body_limit_bytes']=MAX_TOTAL
    (OUT/'requests.json').write_text(json.dumps(requests,sort_keys=True,indent=2)+'\n')
    (OUT/'assessment.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ('wheels',)},indent=2))
