import base64,hashlib,io,json,os,subprocess,sys,zipfile
from pathlib import Path
r=Path(__file__).resolve().parent
cache=r/'cache';venv=r/'venv';wheel=r/'cache_layout_probe-0.0.0-py3-none-any.whl'
assert not cache.exists() and not venv.exists() and not wheel.exists()
module=b'VALUE = 37\n#'+b'x'*65536+b'\n'
files={'cache_layout_probe.py':module,'cache_layout_probe-0.0.0.dist-info/METADATA':b'Metadata-Version: 2.1\nName: cache-layout-probe\nVersion: 0.0.0\n','cache_layout_probe-0.0.0.dist-info/WHEEL':b'Wheel-Version: 1.0\nGenerator: authored-probe\nRoot-Is-Purelib: true\nTag: py3-none-any\n'}
record=''.join(name+',sha256='+base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).decode().rstrip('=')+','+str(len(payload))+'\n' for name,payload in files.items())
files['cache_layout_probe-0.0.0.dist-info/RECORD']=(record+'cache_layout_probe-0.0.0.dist-info/RECORD,,\n').encode()
with zipfile.ZipFile(wheel,'x',compression=zipfile.ZIP_STORED) as z:
 for name,payload in files.items():z.writestr(name,payload)
subprocess.run([sys.executable,'-B','-m','venv','--without-pip',str(venv)],check=True)
python=venv/'bin/python'
uv='/home/utkarsh/.local/bin/uv'
subprocess.run([uv,'pip','install','--offline','--no-index','--no-deps','--python',str(python),'--cache-dir',str(cache),'--link-mode','hardlink',str(wheel)],check=True)
package=venv/'lib/python3.11/site-packages/cache_layout_probe.py'
backing=list((cache/'archive-v0').glob('*/cache_layout_probe.py'))
assert len(backing)==1
before=os.stat(package);cached=os.stat(backing[0]);assert(before.st_dev,before.st_ino)==(cached.st_dev,cached.st_ino) and before.st_nlink>=2
before_sha=hashlib.sha256(package.read_bytes()).hexdigest()
subprocess.run([str(python),'-B','-c','import cache_layout_probe;assert cache_layout_probe.VALUE == 37'],check=True)
subprocess.run([uv,'cache','clean','--cache-dir',str(cache)],check=True)
after=os.stat(package);assert after.st_nlink==1 and not package.is_symlink() and hashlib.sha256(package.read_bytes()).hexdigest()==before_sha==hashlib.sha256(module).hexdigest()
subprocess.run([str(python),'-B','-c','import cache_layout_probe;assert cache_layout_probe.VALUE == 37'],check=True)
value={'schema':'authored-ci-cache-layout-check-v1','uv_version':subprocess.check_output([uv,'--version'],text=True).strip(),'before_nlink':before.st_nlink,'after_nlink':after.st_nlink,'shared_cache_env_inode_before_clean':True,'installed_module_sha256':before_sha,'installed_bytes_unchanged':True,'imports_before_and_after_clean':True,'dependency_versions_changed':False,'actual_research_inputs_read':False,'scope':'tiny authored local wheel; actual hosted locked dependency installation remains unverified'}
(r/'receipt.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value))
