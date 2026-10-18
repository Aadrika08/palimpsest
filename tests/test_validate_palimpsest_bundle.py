"""Stdlib palimpsest-bundle-v1 validator and npz/npy reader over authored runs."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import zipfile

import pytest

ROOT=Path(__file__).resolve().parents[1]


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def api():
    assert (ROOT/'scripts/validate_palimpsest_bundle.py').is_file(),'bundle validator is missing'
    return load(ROOT/'scripts/validate_palimpsest_bundle.py','bundle_validator_fixture')


FAKE=load(ROOT/'tests/authored_puck_held_episode.py','authored_episode_fixture')


def authored_run(tmp_path,run_id='0'*32,replay=False):
    run=tmp_path/run_id;run.mkdir()
    _,registered=FAKE.register_snapshot(run,run_id)
    FAKE.write_recording(run,run_id,FAKE.tick_arrays(range(40),[[0,1.0,0.0],[20,1.0,0.5]]),seed=7,events_extra=[registered])
    if replay:(run/'replay-report.json').write_text('{"status":"passed"}\n')
    receipt=FAKE.bundle(run,tmp_path/'bundle.zip')
    return run,tmp_path/'bundle.zip',receipt


def test_npz_reader_parses_the_recorded_arrays(tmp_path):
    v=api();run,_,_=authored_run(tmp_path)
    arrays=v.read_npz((run/'recording/chunks/000000.npz').read_bytes())
    assert arrays['cam_left'].descr=='|u1' and arrays['cam_left'].shape==(32,128,128,3)
    assert arrays['action'].values()[:4]==(1.0,0.0,1.0,0.0) and arrays['eyes'].descr=='|b1'
    assert arrays['revision'].values()==(0,)*32 and len(arrays['cam_right'].rows())==32
    second=v.read_npz((run/'recording/chunks/000001.npz').read_bytes())
    assert second['pose'].shape==(8,3)


def test_npz_reader_matches_numpy_when_available(tmp_path):
    np=pytest.importorskip('numpy');v=api();stream=io.BytesIO()
    values=dict(frames=np.arange(2*4*4*3,dtype=np.uint8).reshape(2,4,4,3),pose=np.linspace(0,1,6).reshape(2,3),
                flags=np.array([True,False]),count=np.array([3,4],dtype=np.int64),small=np.array([1.5,2.5],dtype=np.float32))
    np.savez(stream,**values);arrays=v.read_npz(stream.getvalue())
    for name,value in values.items():
        assert arrays[name].descr==value.dtype.str and arrays[name].shape==value.shape and arrays[name].data==value.tobytes()


@pytest.mark.parametrize('replay',[False,True])
def test_bundle_validates_against_its_run(tmp_path,replay):
    v=api();run,bundle,receipt=authored_run(tmp_path,replay=replay)
    result=v.validate_bundle(bundle,run)
    assert result['sha256']==receipt['sha256'] and result['members']==5+replay


def rewrite(bundle,members,*,manifest=None,compression=zipfile.ZIP_STORED,last_manifest=True):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',compression=compression) as archive:
        for name,payload in members:archive.writestr(name,payload)
        if manifest is not None and last_manifest:archive.writestr('bundle-manifest.json',manifest)
    bundle.write_bytes(stream.getvalue())


def members(bundle):
    with zipfile.ZipFile(bundle) as archive:
        return [(i.filename,archive.read(i)) for i in archive.infolist()]


@pytest.mark.parametrize('defect',['traversal','absolute','duplicate','deflated','crc','unlisted','size','manifest-first',
    'format','run-file','run-missing','extra-run-file'])
def test_bundle_refuses_unsafe_or_inconsistent_archives(tmp_path,defect):
    v=api();run,bundle,_=authored_run(tmp_path);rows=members(bundle);manifest=rows[-1][1];body=rows[:-1]
    data=json.loads(manifest)
    if defect=='traversal':rewrite(bundle,body+[('../escape.txt',b'x')],manifest=manifest)
    elif defect=='absolute':rewrite(bundle,body+[('/etc/escape.txt',b'x')],manifest=manifest)
    elif defect=='duplicate':
        import warnings
        with warnings.catch_warnings():warnings.simplefilter('ignore');rewrite(bundle,body+[body[0]],manifest=manifest)
    elif defect=='deflated':rewrite(bundle,body,manifest=manifest,compression=zipfile.ZIP_DEFLATED)
    elif defect=='crc':
        raw=bytearray(bundle.read_bytes());offset=raw.find(body[0][1][:16]);raw[offset+3]^=1;bundle.write_bytes(bytes(raw))
    elif defect=='unlisted':rewrite(bundle,body+[('recording/extra.txt',b'unlisted')],manifest=manifest)
    elif defect=='size':
        data['files'][0]['size_bytes']+=1;rewrite(bundle,body,manifest=json.dumps(data).encode())
    elif defect=='manifest-first':rewrite(bundle,[('bundle-manifest.json',manifest)]+body,manifest=None,last_manifest=False)
    elif defect=='format':data['format']='palimpsest-bundle-v0';rewrite(bundle,body,manifest=json.dumps(data).encode())
    elif defect=='run-file':
        path=run/'recording/manifest.json';path.write_bytes(path.read_bytes().replace(b'"seed": 7',b'"seed": 8'))
    elif defect=='run-missing':(run/'snapshots/initial.snp').unlink()
    else:(run/'replay-report.json').write_text('{}\n')
    with pytest.raises((ValueError,zipfile.BadZipFile,KeyError,FileNotFoundError)):
        v.validate_bundle(bundle,run if defect.startswith(('run','extra')) else None)


def patched(bundle,old,new):
    raw=bundle.read_bytes();assert raw.count(old)>=1;bundle.write_bytes(raw.replace(old,new))


@pytest.mark.parametrize('defect',['prepended','trailing','between','comment','local-name','local-crc','data-descriptor',
    'nul-name','control-name','case-collision','symlink-mode','manifest-duplicate-key','manifest-nan','manifest-bool-size',
    'symlinked-bundle','total-bound'])
def test_bundle_layout_is_exact_and_contiguous(tmp_path,defect,monkeypatch):
    v=api();run,bundle,_=authored_run(tmp_path);rows=members(bundle);manifest=json.loads(rows[-1][1]);body=rows[:-1]
    target=bundle
    if defect=='prepended':bundle.write_bytes(b'PREPENDED'+bundle.read_bytes())
    elif defect=='trailing':bundle.write_bytes(bundle.read_bytes()+b'TRAILING')
    elif defect=='between':
        raw=bundle.read_bytes();second=raw.index(b'PK\x03\x04',4);bundle.write_bytes(raw[:second]+b'GAP!'+raw[second:])
    elif defect=='comment':
        with zipfile.ZipFile(bundle,'a') as archive:archive.comment=b'authored comment'
    elif defect=='local-name':patched(bundle,b'PK\x03\x04',b'PK\x03\x04') or None;raw=bytearray(bundle.read_bytes());i=raw.index(b'recording/');raw[i]=ord('R');bundle.write_bytes(bytes(raw))
    elif defect=='local-crc':raw=bytearray(bundle.read_bytes());raw[14]^=1;bundle.write_bytes(bytes(raw))
    elif defect=='data-descriptor':
        class Stream(io.RawIOBase):
            def __init__(self):self.data=bytearray()
            def writable(self):return True
            def write(self,b):self.data+=b;return len(b)
        out=Stream()
        with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_STORED) as archive:
            for name,payload in rows:
                with archive.open(name,'w') as stream:stream.write(payload)
        bundle.write_bytes(bytes(out.data))
    elif defect=='nul-name':rewrite(bundle,body+[('recording/aaaa',b'x')],manifest=rows[-1][1]);patched(bundle,b'recording/aaaa',b'recording/a\x00aa')
    elif defect=='control-name':rewrite(bundle,body+[('recording/a\x07b',b'x')],manifest=rows[-1][1])
    elif defect=='case-collision':
        upper=[(n.replace('recording/manifest.json','recording/MANIFEST.json'),p) for n,p in body if n=='recording/manifest.json']
        rewrite(bundle,body+upper,manifest=rows[-1][1])
    elif defect=='symlink-mode':
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as archive:
            for name,payload in body:
                info=zipfile.ZipInfo(name);info.external_attr=0o120777<<16 if name.endswith('.snp') else 0o600<<16
                archive.writestr(info,payload)
            archive.writestr('bundle-manifest.json',rows[-1][1])
        bundle.write_bytes(stream.getvalue())
    elif defect=='manifest-duplicate-key':
        rewrite(bundle,body,manifest=rows[-1][1][:-1]+b',"format":"palimpsest-bundle-v1"}')
    elif defect=='manifest-nan':rewrite(bundle,body,manifest=rows[-1][1].replace(b'"derived": {',b'"derived": {"x": NaN, ',1))
    elif defect=='manifest-bool-size':
        manifest['files'][0]['size_bytes']=True;rewrite(bundle,[(body[0][0],b'x')]+body[1:],manifest=json.dumps(manifest).encode())
    elif defect=='symlinked-bundle':target=tmp_path/'link.zip';target.symlink_to(bundle.name)
    else:monkeypatch.setattr(v,'MAX_TOTAL_BYTES',1024)
    with pytest.raises((ValueError,OSError)):v.validate_bundle(target)


def test_symlinked_run_files_are_refused(tmp_path):
    v=api();run,bundle,_=authored_run(tmp_path)
    path=run/'recording/manifest.json';real=run/'manifest-real.json';path.rename(real);path.symlink_to(real)
    with pytest.raises((ValueError,OSError)):v.validate_bundle(bundle,run)
