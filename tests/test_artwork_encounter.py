"""Synthetic derivative-only checks; never read the retained artwork ZIP."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/prepare_artwork_encounter.py'
spec = importlib.util.spec_from_file_location('encounter', SCRIPT)
encounter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(encounter)


class EncounterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        times = [4., 4.04, 4.2]
        self.meta = {'kind': 'afterimage-v1', 'model_dt_seconds': .02,
                     'mapping': {'id': 'response-plane-v1', 'axis_limits': [-360, 360]},
                     'stimulus': {'manifest': {'source_times_seconds': times}},
                     'alignment': [{'frame': i, 'source_timestamp_seconds': t,
                                    'model_time_seconds': (i + 1) * .02,
                                    'action': [0., 0.], 'point': [0., -0.]}
                                   for i, t in enumerate(times)]}
        self.files = {name: b'synthetic derivative' for name in encounter.MEMBERS
                      if name != 'checksums.json'}
        self.files['afterimage.svg'] = self.svg()
        self.files['counterfactual-choir.wav'] = self.wav()
        self.files['README.md'] = b'Fixture </script><script>alert(1)</script>'

    def wav(self, *, compose=False, mutate=None):
        count = 6000 if compose else 3
        pcm = bytes(count * 960 * 2)
        timing = {'control_interval_seconds': .02, 'episode': 0, 'start_tick': 0,
                  'end_tick_inclusive': count - 1, 'sample_boundaries': [i * 960 for i in range(count + 1)]}
        if compose:
            timing.update(clock='concatenated simulation time', duration_seconds=120,
                          selected_intervals=6000, final_episode_prefix=True,
                          segments=[{'episode': i, 'start_tick': 0, 'end_tick_inclusive': 599,
                                     'simulation_start_seconds': 0., 'simulation_end_seconds': 12.,
                                     'output_start_sample': i * 576000,
                                     'output_end_sample_exclusive': (i + 1) * 576000} for i in range(10)])
        meta = {'version': 2 if compose else 1, 'artwork': 'counterfactual choir',
                'pcm_sha256': hashlib.sha256(pcm).hexdigest(), 'timing': timing,
                'mapping': {'sample_rate_hz': 48000, 'channels': 1, 'sample_width_bytes': 2,
                            'voices': [{'population': 'visual_left'}]}}
        if mutate:
            mutate(meta)
        def chunk(kind, payload):
            return struct.pack('<4sI', kind, len(payload)) + payload + b'\0' * (len(payload) % 2)
        body = b'WAVE' + chunk(b'fmt ', struct.pack('<HHIIHH', 1, 1, 48000, 96000, 2, 16))
        body += chunk(b'data', pcm) + chunk(b'plmp', json.dumps(meta).encode())
        return b'RIFF' + struct.pack('<I', len(body)) + body

    def test_choir_duration_and_episode_boundaries_come_from_audio(self):
        page = encounter.encounter_html(self.files).decode()
        self.assertIn('Playback ends after 0.06 seconds', page)
        self.assertNotIn('Playback ends after 25.34 seconds', page)
        self.files['counterfactual-choir.wav'] = self.wav(compose=True)
        page = encounter.encounter_html(self.files).decode()
        self.assertIn('Playback ends after 120 seconds', page)
        self.assertIn('Episode boundaries', page)
        self.assertIn('Final episode uses a recorded prefix', page)
        self.assertIn('<td>9</td><td>108–120</td><td>0–599</td>', page)
        self.assertNotIn('autoplay', page)

    def test_afterimage_presentation_requires_matched_camera_provenance(self):
        times = [i / 10 for i in range(600)]
        self.meta['stimulus']['manifest']['source_times_seconds'] = times
        self.meta['stimulus']['manifest']['frame_file_sha256'] = 'a' * 64
        self.meta['policy_identity'] = {'controller': 'male-original'}
        self.meta['alignment'] = [dict(self.meta['alignment'][0], frame=i,
            source_timestamp_seconds=t, model_time_seconds=(i + 1) * .02, frame_sha256='b' * 64)
            for i, t in enumerate(times)]
        self.files['afterimage.svg'] = self.svg()
        source = {'schema_version': 1, 'camera': 'cam_left', 'source_controller': 'manual',
                  'source_run_id': '0' * 32, 'selected_intervals': 3000, 'source_intervals': 3000,
                  'clock': 'concatenated source time', 'presentation_seconds': 60,
                  'frame_file_sha256': 'a' * 64,
                  'frames': [{'frame': i, 'source_interval': i * 5, 'episode': i // 120,
                              'tick': (i % 120) * 5, 'presentation_seconds': t, 'eyes': [True, True],
                              'simulation_time_seconds': ((i % 120) * 5 + 1) * .02,
                              'observation_time_seconds': (i % 120) * 5 * .02,
                              'frame_sha256': 'b' * 64} for i, t in enumerate(times)]}
        self.files['afterimage-source.json'] = json.dumps(source).encode()
        page = encounter.encounter_html(self.files).decode()
        self.assertIn('Play 60-second portrait', page)
        self.assertIn('scripted manual-controller', page)
        self.assertIn('59.9 source seconds', page)
        self.assertNotIn('Insufficient for assessing sustained material', page)
        source['frames'][1]['frame_sha256'] = 'c' * 64
        self.files['afterimage-source.json'] = json.dumps(source).encode()
        with self.assertRaises(ValueError): encounter.encounter_html(self.files)

    def test_route_captions_follow_validated_parent_and_branch_metadata(self):
        import html
        parent, branch, snapshot = '1' * 32, '2' * 32, '3' * 32
        left = {'run_id': parent, 'provenance': {'controller': 'flynn', 'control_interval_seconds': .02},
                'traces': [{'episode': 0, 'start_tick': 0, 'points': [[0., 0.]] * 601}]}
        right = {'run_id': branch, 'provenance': {'controller': 'flynn', 'control_interval_seconds': .02,
                 'parent_run_id': parent, 'source_snapshot_id': snapshot,
                 'interventions': [{'kind': 'intervention', 'episode': 0, 'episode_step': 100,
                                   'change': {'kind': 'move_goal', 'new': {'xy': [0., 0.]}}}]},
                 'traces': [{'episode': 0, 'start_tick': 100, 'points': [[0., 0.]] * 501}]}
        self.files['borrowed-body.svg'] = ('<svg xmlns="http://www.w3.org/2000/svg"><metadata>' + html.escape(json.dumps(left)) + '</metadata></svg>').encode()
        self.files['one-map-many-lives.html'] = ('<pre id="comparison-metadata">' + html.escape(json.dumps({'comparison': {'left': left, 'right': right}})) + '</pre>').encode()
        source = {'parent_run_id': parent, 'branch_run_id': branch, 'snapshot_id': snapshot,
                  'branch_tick': 100, 'intervention': {'kind': 'move_goal', 'xy': [0., 0.]},
                  'files_sha256': {n: hashlib.sha256(self.files[n]).hexdigest() for n in ('borrowed-body.svg', 'one-map-many-lives.html')}}
        self.files['routes-source.json'] = json.dumps(source).encode()
        page = encounter.encounter_html(self.files).decode()
        self.assertIn('600 intervals, 601 points, 12 simulation seconds', page)
        self.assertIn('500 intervals / 10 simulation seconds', page)
        self.assertIn('branch at tick 100', page)
        self.assertNotIn('two route sources have no parent relationship', page)
        source['snapshot_id'] = '4' * 32
        self.files['routes-source.json'] = json.dumps(source).encode()
        with self.assertRaises(ValueError): encounter.encounter_html(self.files)

    def test_choir_rejects_malformed_audio_and_inconsistent_metadata(self):
        for mutate in (lambda m: m.update(pcm_sha256='0' * 64),
                       lambda m: m['timing'].update(duration_seconds=119),
                       lambda m: m['timing']['segments'][1].update(output_start_sample=0),
                       lambda m: m['timing']['segments'][-1].update(end_tick_inclusive=598),
                       lambda m: m['timing']['segments'][1].update(episode='<script>'),
                       lambda m: m['mapping']['voices'][0].update(population='<script>')):
            with self.assertRaises(ValueError):
                encounter.choir_details(self.wav(compose=True, mutate=mutate))
        raw = self.wav()
        for bad in (b'not audio', raw[:-1], raw + b'trailing'):
            with self.assertRaises(ValueError):
                encounter.choir_details(bad)

    def svg(self):
        import html
        return ('<svg xmlns="http://www.w3.org/2000/svg"><metadata>' +
                html.escape(json.dumps(self.meta)) + '</metadata></svg>').encode()

    def archive(self, files=None, extra=None):
        files = dict(files or self.files)
        files['checksums.json'] = json.dumps({'files': {
            name: {'size_bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
            for name, raw in files.items()}, 'qualification_claims': []}).encode()
        path = self.root / 'fixture.zip'
        with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_STORED) as bundle:
            for name, raw in files.items():
                info = zipfile.ZipInfo(name)
                info.create_system, info.external_attr = 3, 0o100644 << 16
                bundle.writestr(info, raw)
            if extra:
                bundle.writestr(*extra)
        return path, encounter.pin(path)

    def test_archive_and_encounter_preserve_all_six_targets_and_alignment(self):
        path, expected = self.archive()
        files = encounter.read_archive(path, expected, lambda: None)
        self.assertEqual(files['afterimage.svg'], self.files['afterimage.svg'])
        page = encounter.encounter_html(files).decode()
        for name in encounter.ARTIFACTS:
            self.assertIn('href="' + name + '"', page)
        self.assertIn('<audio controls preload="none"', page)
        self.assertNotIn('autoplay', page)
        self.assertNotIn('fetch(', page)
        self.assertIn('3 frames', page)
        self.assertIn('0.2 source seconds', page)
        self.assertIn('0.06 model seconds', page)
        self.assertIn('Insufficient for assessing sustained material', page)
        rows = encounter.alignment(files['afterimage.svg'])
        self.assertEqual(rows, self.meta['alignment'])
        self.assertEqual(rows[0]['point'], rows[1]['point'])
        self.assertIn('aria-live="polite"', page)
        self.assertIn('id="previous"', page)
        self.assertIn('id="next"', page)

    def test_whole_file_corruption_and_wrong_pin_rejected(self):
        path, expected = self.archive()
        path.write_bytes(path.read_bytes() + b'corruption')
        with self.assertRaisesRegex(ValueError, 'ZIP pin'):
            encounter.read_archive(path, expected, lambda: None)

    def test_missing_unexpected_duplicate_and_escaping_members_rejected(self):
        missing = dict(self.files)
        missing.pop('atlas.svg')
        for files, extra in ((missing, None), (self.files, ('unexpected', b'x')),
                             (self.files, ('../escape', b'x')),
                             (self.files, ('afterimage.svg', b'duplicate'))):
            with self.subTest(extra=extra):
                path, expected = self.archive(files, extra)
                with self.assertRaisesRegex(ValueError, 'member'):
                    encounter.read_archive(path, expected, lambda: None)

    def test_checksum_size_hash_and_symlink_rejected(self):
        path, _ = self.archive()
        with zipfile.ZipFile(path) as bundle:
            files = {name: bundle.read(name) for name in bundle.namelist()}
        checks = json.loads(files['checksums.json'])
        for key, bad in (('sha256', '0' * 64), ('size_bytes', 1)):
            broken = json.loads(json.dumps(checks))
            broken['files']['afterimage.svg'][key] = bad
            files['checksums.json'] = json.dumps(broken).encode()
            with zipfile.ZipFile(path, 'w') as bundle:
                for name, raw in files.items():
                    info = zipfile.ZipInfo(name)
                    info.create_system, info.external_attr = 3, 0o100644 << 16
                    bundle.writestr(info, raw)
            with self.assertRaisesRegex(ValueError, 'checksum'):
                encounter.read_archive(path, encounter.pin(path), lambda: None)
        files['checksums.json'] = json.dumps(checks).encode()
        with zipfile.ZipFile(path, 'w') as bundle:
            for name, raw in files.items():
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = (0o120777 if name == 'atlas.svg' else 0o100644) << 16
                bundle.writestr(info, raw)
        with self.assertRaisesRegex(ValueError, 'regular stored'):
            encounter.read_archive(path, encounter.pin(path), lambda: None)

    def test_malformed_alignment_and_single_frame_boundary(self):
        original = json.loads(json.dumps(self.meta))
        for field, bad in (('frame', 2), ('point', [1., 0.]),
                           ('action', [math.inf, 0.]), ('source_timestamp_seconds', 9.),
                           ('model_time_seconds', .5)):
            self.meta = json.loads(json.dumps(original))
            self.meta['alignment'][0][field] = bad
            with self.subTest(field=field), self.assertRaises(ValueError):
                encounter.alignment(self.svg())
        self.meta = original
        self.meta['alignment'] = self.meta['alignment'][:1]
        self.meta['stimulus']['manifest']['source_times_seconds'] = [4.]
        self.assertEqual(len(encounter.alignment(self.svg())), 1)

    def test_producer_float32_heading_endpoints_remain_admissible(self):
        limit = struct.unpack('!f', struct.pack('!f', math.pi))[0]
        for heading in (-limit, limit):
            row = self.meta['alignment'][0]
            row.update(action=[0., heading], point=[0., -360 * heading / math.pi])
            self.assertEqual(encounter.alignment(self.svg())[0], row)
        row['action'][1] = math.nextafter(limit, math.inf)
        row['point'][1] = -360 * row['action'][1] / math.pi
        with self.assertRaises(ValueError):
            encounter.alignment(self.svg())

    def test_html_and_json_embedding_cannot_close_script(self):
        self.meta['title'] = '</script><script>alert(1)</script>&\u2028\u2029'
        self.files['afterimage.svg'] = self.svg()
        page = encounter.encounter_html(self.files).decode()
        self.assertNotIn('<script>alert(1)</script>', page)
        self.assertIn('&lt;/script&gt;', page)
        self.assertNotIn(self.meta['title'], encounter.script_json(self.meta))
        self.assertEqual(json.loads(encounter.script_json(self.meta)), self.meta)

    def test_output_reuse_escape_and_budget_deadline_rejected(self):
        existing = self.root / 'already'
        existing.mkdir()
        with patch.object(encounter, 'ROOT', self.root):
            with self.assertRaisesRegex(ValueError, 'fresh'):
                encounter.destination(existing)
            with self.assertRaises(ValueError):
                encounter.destination(self.root.parent / 'escape')
        output = self.root / 'new'
        output.mkdir()
        guard = encounter.Guard(output)
        with patch.object(encounter.time, 'monotonic', return_value=guard.start + 121):
            with self.assertRaisesRegex(ValueError, 'deadline'):
                guard.check()
        with patch.object(encounter, 'OUTPUT_LIMIT', 1):
            with self.assertRaisesRegex(ValueError, 'output byte'):
                guard.check(2)
        with patch.object(encounter.shutil, 'disk_usage', return_value=SimpleNamespace(free=1)):
            with self.assertRaisesRegex(ValueError, 'free space'):
                guard.check()

    def test_synthetic_preparation_preserves_bytes_and_retains_failure(self):
        archive, expected = self.archive()
        with patch.object(encounter, 'ROOT', self.root), patch.object(encounter, 'ARCHIVE', archive), \
                patch.object(encounter, 'ARCHIVE_PIN', expected), patch.object(encounter, 'head', return_value='fixture'):
            for fail in (False, True):
                output = self.root / ('failed' if fail else 'passed')
                registered = {'output': str(output), 'sources': {}, 'head': 'fixture'}
                with patch.object(encounter, 'registration', return_value=registered):
                    if fail:
                        with patch.object(encounter, 'encounter_html', side_effect=ValueError('synthetic failure')):
                            self.assertEqual(encounter.prepare(registered), 1)
                    else:
                        self.assertEqual(encounter.prepare(registered), 0)
                receipt = json.loads((output / 'result.json').read_bytes())
                self.assertEqual(receipt['status'], 'failed' if fail else 'passed')
                self.assertTrue((output / 'launched.json').is_file())
                self.assertEqual(receipt['qualification_claims'], [])
                self.assertLess(sum(p.stat().st_size for p in output.iterdir()), encounter.OUTPUT_LIMIT)
                if not fail:
                    for name, raw in self.files.items():
                        self.assertEqual((output / name).read_bytes(), raw)
                with self.assertRaisesRegex(ValueError, 'fresh'):
                    encounter.prepare(registered)

    def test_emitted_javascript_controls_exact_prefix_and_stop_audio(self):
        self.assertIsNotNone(shutil.which('node'), 'existing UI Node runtime is required for this software check')
        page = encounter.encounter_html(self.files).decode()
        code = re.search(r'<script>(.*?)</script>', page, re.S).group(1)
        stub = '''const assert=(condition)=>{if(!condition)throw Error('control assertion failed');};
const elements=Object.fromEntries(['previous','next','prefix','selected','frame-status','controls','stop-audio','alignment'].map(id=>[id,{hidden:true,handlers:{},attrs:{},addEventListener(e,f){this.handlers[e]=f;},setAttribute(k,v){this.attrs[k]=v;}}]));
const player={currentTime:4,paused:false,pause(){this.paused=true;}};
globalThis.document={getElementById:id=>elements[id],querySelector:()=>player};
elements['source-index']={textContent:'null'};
elements.alignment.textContent=ROWS;
'''.replace('ROWS', json.dumps(json.dumps(self.meta['alignment'])))
        checks = '''
assert(elements.previous.disabled&& !elements.next.disabled&&!elements.controls.hidden);
assert(elements.prefix.attrs.points==='0,0');
elements.next.handlers.click();assert(elements.prefix.attrs.points==='0,0 0,0');
elements.next.handlers.click();elements.next.handlers.click();assert(elements.next.disabled&&elements.prefix.attrs.points==='0,0 0,0 0,0');
elements.previous.handlers.click();elements.previous.handlers.click();elements.previous.handlers.click();assert(elements.previous.disabled&&elements.prefix.attrs.points==='0,0');
elements['stop-audio'].handlers.click();assert(player.paused&&player.currentTime===0);
'''
        result = subprocess.run(['node', '--input-type=module', '-e', stub + code + checks], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
