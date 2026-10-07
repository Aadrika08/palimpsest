"""Bounded software fixtures only; no Playwright, native engine or real-user lease."""
from contextlib import ExitStack
import importlib.util
import json
import os
from pathlib import Path
import signal
import select
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from palimpsest.storage import StorageBudget, StorageLimits, StorageLimitError
from palimpsest.worker import _episode_preflight

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/manual_lab_refresh_v3.py'
spec = importlib.util.spec_from_file_location('manual_v3_fixture', SCRIPT)
v3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v3)
producer = v3.v2


class AdmissionAndGrace(unittest.TestCase):
    def test_real_episode_reservation_and_bound_configuration(self):
        engine = SimpleNamespace(observation={name: np.zeros((128,128,3), dtype=np.uint8)
                                              for name in ('cam_left','cam_right')}, policy=None)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (root / 'retained-bytes').open('wb') as stream:
                stream.truncate(8_354_907)
            def budget(limit):
                return StorageBudget((root,),StorageLimits(max_bytes=limit,min_free_bytes=0),headroom_bytes=10_485_760)
            with self.assertRaises(StorageLimitError):
                _episode_preflight(engine,root,budget(128*1024**2))
            limit = int(producer.SERVER[producer.SERVER.index('--storage-max-bytes')+1])
            report = _episode_preflight(engine,root,budget(limit))
            self.assertEqual(report['recording_bytes_estimate'],121_470_976)
            self.assertEqual(report['admission']['used_bytes'],8_354_907)
            self.assertEqual(limit,256*1024**2)
            with (root/'retained-bytes').open('wb') as stream:
                stream.truncate(256*1024**2)
            with self.assertRaises(StorageLimitError):
                _episode_preflight(engine,root,budget(limit))

    def test_delayed_live_reused_and_group_identity(self):
        row={'pid':7,'start_ticks':20,'group':7,'state':'S'}
        clock=[0.]
        def sleep(seconds):clock[0]+=seconds
        for mode in ('delayed','live','reused','group-changed'):
            clock[0]=0.;v3.IDENTITIES.clear()
            def read(pid):
                if mode=='delayed' and clock[0]>=.2:return None
                return {**row,'start_ticks':21 if mode=='reused' else 20,'group':8 if mode=='group-changed' else 7}
            with self.subTest(mode=mode),patch.object(v3,'READ_PROCESS',side_effect=read),patch.object(v3.time,'monotonic',side_effect=lambda:clock[0]),patch.object(v3.time,'sleep',side_effect=sleep),patch.object(producer,'BUDGET'):
                report=v3.exit_grace([row],10.)
                expected={'delayed':'exited','live':'live','reused':'identity-changed','group-changed':'identity-changed'}[mode]
                self.assertEqual(report['outcomes'][0]['outcome'],expected)
                self.assertLessEqual(report['elapsed_seconds'],2.01)
                if mode=='live':self.assertGreaterEqual(report['elapsed_seconds'],2.)
                if mode in ('reused','group-changed'):self.assertIsNone(v3.matched_process(7))

    def test_actual_worker_interrupt_and_survivor_cleanup(self):
        row={'pid':7,'start_ticks':20,'group':7,'state':'S'}
        for mode in ('delayed','live','reused'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as directory,ExitStack() as patches:
                root=Path(directory);clock=[0.];saved=[]
                def read(pid):
                    if mode=='delayed' and clock[0]>=.2:return None
                    return {**row,'start_ticks':21 if mode=='reused' else 20}
                def write(path,value,budget):
                    saved.append(value)
                    v3.WRITE_JSON(path,value,budget)
                def interrupted(*args,**kwargs):
                    saved[0]['status']='passed'
                    raise KeyboardInterrupt('fixture provisional-pass interruption')
                for context in [patch.object(producer,'PHASE',root),patch.object(producer,'REGISTRATION',root/'registration.json'),
                    patch.object(producer,'pins',return_value={}),patch.object(producer,'BUDGET'),patch.object(producer,'observe'),
                    patch.object(producer,'OBSERVED',{'7:20':row}),patch.object(producer,'bounded_process',side_effect=interrupted),
                    patch.object(producer,'write_json',side_effect=write),patch.object(producer.signal,'signal'),
                    patch.object(v3,'READ_PROCESS',side_effect=read),patch.object(v3.time,'monotonic',side_effect=lambda:clock[0]),
                    patch.object(v3.time,'sleep',side_effect=lambda seconds:clock.__setitem__(0,clock[0]+seconds))]:patches.enter_context(context)
                (root/'registration.json').write_text('{"sources":{}}')
                with patch.object(producer.os,'kill') as kill:
                    self.assertEqual(producer.worker(),1)
                    result=json.loads((root/'worker.json').read_text())
                    self.assertEqual(result['status'],'failed')
                    self.assertEqual(result['failure']['type'],'KeyboardInterrupt')
                    self.assertEqual(result['owned_survivors_requiring_kill'],[7] if mode=='live' else [])
                    if mode=='live':kill.assert_called_once_with(7,signal.SIGKILL)
                    else:kill.assert_not_called()

    def test_real_tracker_exits_after_last_inherited_pipe_writer_closes(self):
        code = """import multiprocessing as m,sys,os,subprocess,re,time
ctx=m.get_context('spawn');event=ctx.Event()
children=open(f'/proc/{os.getpid()}/task/{os.getpid()}/children').read().split()
tracker=next(pid for pid in children if b'multiprocessing.resource_tracker' in open(f'/proc/{pid}/cmdline','rb').read())
cmd=open(f'/proc/{tracker}/cmdline','rb').read().decode()
reader=int(re.search(r'main\((\d+)\)',cmd).group(1))
pipe=os.readlink(f'/proc/{tracker}/fd/{reader}')
writer=next(int(fd) for fd in os.listdir('/proc/self/fd') if fd.isdigit() and os.path.exists(f'/proc/self/fd/{fd}') and os.readlink(f'/proc/self/fd/{fd}')==pipe)
holder=subprocess.Popen([sys.executable,'-B','-c','import time;time.sleep(.5)'],pass_fds=(writer,),stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
print('ready',flush=True);sys.stdin.readline()
"""
        child=subprocess.Popen([sys.executable,'-B','-c',code],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
        rows=[]
        try:
            self.assertTrue(select.select([child.stdout],[],[],5.)[0], 'Software fixture readiness deadline')
            self.assertEqual(child.stdout.readline().strip(),'ready')
            rows=producer.descendants(child.pid)
            tracker=next(row for row in rows if 'multiprocessing.resource_tracker' in row['command'])
            child.stdin.write('\n');child.stdin.flush();child.wait(timeout=5)
            self.assertEqual(child.returncode,0)
            current=v3.READ_PROCESS(tracker['pid'])
            self.assertIsNotNone(current)
            self.assertNotEqual(current['state'],'Z')
            with patch.object(producer,'BUDGET'):
                report=v3.exit_grace(rows,time.monotonic()+2.)
            self.assertTrue(all(row['outcome']=='exited' for row in report['outcomes']))
            self.assertGreater(report['elapsed_seconds'],.1)
            self.assertLessEqual(report['elapsed_seconds'],2.01)
            print('TRACKER EOF CHARACTERIZATION',json.dumps(report))
        finally:
            if child.poll() is None:
                rows = producer.descendants(child.pid)
                child.kill();child.wait(timeout=5)
            for stream in (child.stdin,child.stdout,child.stderr):
                stream.close()
            for row in rows:
                current=v3.READ_PROCESS(row['pid'])
                if current and (current['start_ticks'],current['group'])==(row['start_ticks'],row['group']) and current['state']!='Z':
                    os.kill(row['pid'],signal.SIGKILL)


class PublicationControls(unittest.TestCase):
    def run_fixture(self,fault=None):
        with tempfile.TemporaryDirectory() as directory,ExitStack() as patches:
            root=Path(directory);(root/'home').mkdir();phase=root/'phase';publication=root/'publication'
            registration=root/'registration.json'
            registration.write_text(json.dumps({'schema':producer.SCHEMA,'code_base':producer.BASE,'sources':{},
                'commands':{'selection':producer.SELECTION,'build':producer.BUILD,'server':producer.SERVER,'browser':producer.BROWSER,'worker':[sys.executable,'-B',str(v3.WRAPPER),'--worker']},
                'cached_dependencies':{},'runtime_versions':{},'managed_storage_bytes':256*1024**2,'natural_exit_grace_seconds':2}))
            budget=StorageBudget((phase,publication),StorageLimits(max_bytes=16*1024**2,min_free_bytes=0))
            clock=[0.];pending=[];original_write=v3.WRITE_JSON
            def complete(*args,**kwargs):
                (phase/'worker.json').write_text(json.dumps({'status':'passed','process':{},'owned_survivors_requiring_kill':[]}))
                (phase/'processes.json').write_text('[]');return {'status':'completed','returncode':0}
            def write(path,value,target_budget):
                if path==publication/'publication.json':
                    pending.append(json.loads((phase/'result.json').read_text())['status'])
                    if fault=='refusal':path.mkdir(exist_ok=True)
                    if fault=='term':signal.getsignal(signal.SIGTERM)(signal.SIGTERM,None)
                original_write(path,value,target_budget)
                if path==publication/'publication.json' and fault=='deadline':clock[0]=346.
                if path==phase/'result.json' and value['status']=='passed' and fault=='canonical-deadline':clock[0]=346.
            for name,value in {'ROOT':root,'PHASE':phase,'PUBLICATION':publication,'REGISTRATION':registration,'BUDGET':budget}.items():patches.enter_context(patch.object(producer,name,value))
            for context in [patch('palimpsest.storage.Path.home',return_value=root/'home'),
                patch.object(producer.subprocess,'check_output',side_effect=lambda argv,**kw:'v24.21.0\n' if argv[-1]=='--version' else ''),
                patch.object(producer.subprocess,'run'),patch.object(producer.socket,'socket'),
                patch('shutil.disk_usage',return_value=SimpleNamespace(free=8*1024**3)),patch.object(producer,'pins',return_value={}),
                patch.object(producer,'cached_dependencies',return_value={}),patch.object(producer,'bounded_process',side_effect=complete),
                patch.object(producer,'cleanup_check',return_value={'passed':True}),patch.object(producer.time,'monotonic',side_effect=lambda:clock[0]),
                patch.object(producer,'write_json',side_effect=write)]:patches.enter_context(context)
            code=v3.launch();result=json.loads((phase/'result.json').read_text())
            self.assertEqual(pending[0],'pending-publication');return code,result

    def test_actual_publication_success(self):
        code,result=self.run_fixture();self.assertEqual((code,result['status']),(0,'passed'))

    def test_refusal_term_and_late_publication_fail(self):
        for fault in ('refusal','term','deadline','canonical-deadline'):
            with self.subTest(fault=fault):
                code,result=self.run_fixture(fault);self.assertEqual((code,result['status']),(1,'failed'))
