import sys, pathlib, tempfile, traceback, json, os
ROOT=pathlib.Path.cwd()
sys.path[:0]=[str(ROOT/p) for p in ('src','scripts','tests')]
import test_puck_worker_dependencies as deps
import test_puck_native_cache_bindings as native
import test_puck_runtime_entry_v4 as q4
original=deps.dependency_fixture

def instrument(reg, source):
    path=source/'src/palimpsest/puck_execution_files.py'
    text=path.read_text()
    old="raise RuntimeError('Collection root or ancestor changed while held')"
    new="raise RuntimeError('Collection root or ancestor changed while held; DIAGNOSTIC ' + repr({'path': os.readlink('/proc/self/fd/' + str(fd)), 'fields': ('dev','ino','mode','size','mtime_ns','ctime_ns','nlink'), 'expected': expected, 'held': _identity(os.fstat(fd)), 'named': _identity(os.stat(name, dir_fd=parent, follow_symlinks=False))}))"
    assert text.count(old)==1
    path.write_text(text.replace(old,new))
    for i,row in enumerate(reg['source_files']):
        if row['path']=='src/palimpsest/puck_execution_files.py':
            reg['source_files'][i]=deps.descriptor(path,row['path']);break
    else: raise AssertionError('missing descriptor')

def wrapped(*args,**kwargs):
    prior=kwargs.pop('source_change',None)
    def change(reg,source):
        if prior: prior(reg,source)
        instrument(reg,source)
    result, reg=original(*args,source_change=change,**kwargs)
    print('CHILD',result.returncode,result.stdout,result.stderr,flush=True)
    return result,reg
native.dependency_fixture=q4.dependency_fixture=deps.dependency_fixture=wrapped
cases=[('native-python',lambda:native.test_physical_alternatives_refuse_before_entry('physical-python')),('native-extension',lambda:native.test_physical_alternatives_refuse_before_entry('physical-native')),('q4-v1',lambda:q4.test_q4_requires_v3_tmpfs_custody_before_authored_initializers(1)),('q4-v2',lambda:q4.test_q4_requires_v3_tmpfs_custody_before_authored_initializers(2)),('q4-captured',q4.test_q4_initializer_cannot_rewrite_the_captured_expected_version)]
for name,fn in ([] if '--interference' in sys.argv else cases):
    print('CASE',name,flush=True)
    try:fn();print('PASS',name,flush=True)
    except Exception:traceback.print_exc()
with tempfile.TemporaryDirectory(prefix='palimpsest-native-diagnostic-',dir='/tmp') as p:
    print('CASE native-held',flush=True)
    if '--interference' in sys.argv:
        import threading,time
        stop=threading.Event()
        sibling=pathlib.Path('/tmp')/('palimpsest-custody-interference-'+str(os.getpid()))
        def interfere():
            while not stop.is_set():
                sibling.mkdir(); sibling.rmdir(); time.sleep(.005)
        thread=threading.Thread(target=interfere);thread.start()
        print('CONTROLLED sibling mkdir/rmdir',str(sibling),flush=True)
    try:deps.test_native_extension_initializes_from_held_file_and_is_observed(pathlib.Path(p));print('PASS native-held',flush=True)
    except Exception:traceback.print_exc()

    if '--interference' in sys.argv: stop.set(); thread.join()
