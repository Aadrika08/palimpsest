"""S0z independent compact audit of the S0f outputs: a separate code path from the pinning controller.

Reads the S0f pin record and re-derives everything from bytes with the standard library and
NumPy only (no Torch, no ``palimpsest`` import, no schedule code of the trainer):

* every S0f output file re-hashes to its pin-record sha256 and byte count;
* the S0f record is exactly the S0a..S0f chain at the T-f port head with its locator bound;
* the data manifest is the passed research-only v4 corpus: old arm = 8 teacher then 2 recovery
  sources (recovery <= 120 rows), augmented = that prefix then 12 advice sources in scene
  3100..3103 x learner 10, 11, 12 order (each <= 600), 4 shared dev sources, no held-out, 26
  unique ``feature_target_sha256``, counts equal to the sums, ``new_sources`` run ids equal;
* old and dev ``feature_target_sha256`` equal the S0c manifest's ordered sources, in order;
* ``historical-arrays.npz`` loads with ``allow_pickle=False``: 28 float32 members of shape
  (ticks, 388) / (ticks, 2), finite, and each source hashes to its manifest identity;
* N, q, r and the source rows of both arms in the schedule derivation equal an independent
  divmod of the 46,080 presentations over the manifest rows.

Advice-array identity is NOT vouched for here: the advice arrays are not published by S0f, so
they are enforced only at S1 by the feature_target_sha256 gate (see the S0z manifest).
"""
import hashlib
import json
from pathlib import Path

PRESENTATIONS = 46080
FEATURES = 388
ORDER = ('S0a', 'S0b', 'S0c', 'S0d', 'S0e', 'S0f')
ADVICE = tuple(f'learner-{scene}-seed-{seed}' for scene in (3100, 3101, 3102, 3103) for seed in (10, 11, 12))
ADVICE_ORDER = tuple((scene, seed) for scene in (3100, 3101, 3102, 3103) for seed in (10, 11, 12))
STATUS = 'prepared-navigation-advice-research-only'
LABELS = {'old': 'unchanged executed targets', 'new': 'nav_advice_action'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _hex(value, size=64):
    return isinstance(value, str) and len(value) == size and set(value) <= set('0123456789abcdef')


def audit(record_path, *, expected_manifest_sha256, expected_derivation_sha256, derivation_bytes, protocol_sha256,
          ports_path=None, waivers=()):
    """Return {'status', 'checks', 'failures', ...}; never raises on a failed check."""
    import numpy as np
    checks = []

    def check(name, test):
        try: ok, detail = test()
        except Exception as error: ok, detail = False, f'{type(error).__name__}: {error}'[:512]
        checks.append({'name': name, 'ok': bool(ok), 'detail': detail})

    raw_record = Path(record_path).read_bytes()
    record = json.loads(raw_record)
    root = Path(record['output_root'])
    state = {}

    def record_shape():
        chain = record.get('chain', {})
        ok = (record.get('schema') == 'm7-navigation-v4-pin-record-1' and record.get('stage') == 'S0f' and
              record.get('protocol_sha256') == protocol_sha256 and list(chain) == list(ORDER) and
              chain['S0f'].get('outputs') == record.get('outputs') and record.get('port', {}).get('tree') == 'T-f' and
              record.get('port', {}).get('head') == record.get('producing_commit') and record.get('qualification_claims') == [])
        locator = Path(record['port']['locator_path']).read_bytes()
        return ok and sha(locator) == record['port']['locator_sha256'], 'S0f record shape, chain S0a..S0f and bound locator'

    def outputs():
        bad = []
        for rel, item in record['outputs'].items():
            path = root/rel
            if path.is_symlink() or not path.is_file() or path.stat().st_size != item['bytes'] or sha(path.read_bytes()) != item['sha256']:
                bad.append(rel)
        return not bad and 'data-manifest.json' in record['outputs'], f'{len(record["outputs"])} outputs re-hashed; differing {bad[:6]}'

    def manifest_pin():
        raw = (root/'data-manifest.json').read_bytes()
        state['manifest'] = json.loads(raw)
        return sha(raw) == expected_manifest_sha256 == record['outputs']['data-manifest.json']['sha256'], 'data manifest sha256'

    def structure():
        m, arms = state['manifest'], state['manifest']['arms']
        old, aug, dev = arms['old']['train'], arms['augmented']['train'], arms['old']['dev']
        ok = (m.get('status') == STATUS and m.get('labels') == LABELS and m.get('qualification_claims') == [] and
              set(arms) == {'old', 'augmented'} and all(a['held_out'] == [] for a in arms.values()) and
              arms['augmented']['dev'] == dev and len(old) == 10 and len(dev) == 4 and len(aug) == 22 and aug[:10] == old)
        rows = lambda arm: [s['ticks'] for s in arm]
        ok = ok and all(type(n) is int and 0 < n for n in rows(old) + rows(dev) + rows(aug)) and max(rows(old)[8:]) <= 120 and max(rows(aug)[10:]) <= 600
        advice = m['new_sources']
        ok = ok and [(s['scene_seed'], s['learner_seed']) for s in advice] == list(ADVICE_ORDER) and \
            [s['run_id'] for s in advice] == [s['run_id'] for s in aug[10:]] and rows(advice) == rows(aug[10:])
        digests = [s['feature_target_sha256'] for s in aug + dev]
        ok = ok and all(_hex(d) for d in digests) and len(set(digests)) == 26
        c = m['counts']
        ok = ok and (c['old_train_rows'], c['new_advice_train_rows'], c['recorded_dev_rows'], c['augmented_train_rows'], c['combined_rows'],
                     c['held_out_rows'], c['held_out_sources'], c['old_sources'], c['new_sources'], c['combined_unique_sources']) == (
            sum(rows(old)), sum(rows(aug[10:])), sum(rows(dev)), sum(rows(aug)), sum(rows(aug)) + sum(rows(dev)), 0, 0, 14, 12, 26)
        return ok, 'rosters (8+2 old, 12 advice in scene/learner order, 4 dev, no held-out), bounds, 26 unique hashes, counts'

    def old_corpus():
        m = state['manifest']
        item = m['input_documents']['old_manifest']
        raw = Path(item['path']).read_bytes()
        s0c = json.loads(raw)['ordered_sources']
        want = [(s['run_id'], s['ticks'], s['feature_target_sha256']) for split in ('train', 'dev') for s in s0c[split]]
        got = [(s['run_id'], s['ticks'], s['feature_target_sha256']) for s in m['arms']['old']['train'] + m['arms']['old']['dev']]
        return sha(raw) == item['sha256'] == m['old_manifest_sha256'] and want == got and s0c['held_out'] == [], \
            'old and dev identities equal the S0c data manifest, in order'

    def historical():
        m = state['manifest']
        meta = json.loads((root/'historical-result.json').read_bytes())['arrays']
        ordered = m['arms']['old']['train'] + m['arms']['old']['dev']
        if len(meta) != 14 or len(ordered) != 14: return False, 'historical roster length differs'
        bad = []
        with np.load(root/'historical-arrays.npz', allow_pickle=False) as bundle:
            if len(bundle.files) != 28: return False, f'{len(bundle.files)} members, expected 28'
            for item, source in zip(meta, ordered, strict=True):
                f, t = bundle[item['prefix'] + '_features'], bundle[item['prefix'] + '_targets']
                if (item['run_id'] != source['run_id'] or item['ticks'] != source['ticks'] or f.dtype != np.float32 or t.dtype != np.float32 or
                        f.shape != (source['ticks'], FEATURES) or t.shape != (source['ticks'], 2) or not np.isfinite(f).all() or
                        not np.isfinite(t).all() or sha(f.tobytes() + t.tobytes()) != source['feature_target_sha256']):
                    bad.append(source['run_id'])
        return not bad, f'14 old/dev arrays: dtype, shape, finiteness and hashes; differing {bad[:4]}'

    def derivation():
        if sha(derivation_bytes) != expected_derivation_sha256: return False, 'derivation sha256 differs from the expected pin'
        doc, arms = json.loads(derivation_bytes), state['manifest']['arms']
        ok = doc.get('data_manifest_sha256') == expected_manifest_sha256 and doc.get('presentations') == PRESENTATIONS
        for name, key in (('old-corpus', 'old'), ('augmented', 'augmented')):
            rows = [s['ticks'] for s in arms[key]['train']]
            n = sum(rows); q, r = divmod(PRESENTATIONS, n)
            got = doc['arms'][name]
            ok = ok and (got['N'], got['q'], got['r'], got['source_rows']) == (n, q, r, rows)
        ok = ok and doc.get('dev_rows') == sum(s['ticks'] for s in arms['old']['dev'])
        return ok, 'N, q, r and source rows recomputed independently'

    def chain_audit():
        ports = json.loads(Path(ports_path or Path(__file__).resolve().parents[1]/'docs/plans/m7-navigation-v4-pins/ports.json').read_text())['trees']
        chain, m = record['chain'], state['manifest']
        commits = {'S0a': 'cc1cea93d4c3333a0ee2a091dd34fff0b2986887', 'S0b': 'c382c86781a7a5d6651af721119789729cc890ae',
                   'S0c': ports['T-c']['port_commit'], 'S0d': ports['T-d']['port_commit'], 'S0e': ports['T-e']['port_commit'],
                   'S0f': ports['T-f']['port_commit']}
        if {k: v.get('producing_commit') for k, v in chain.items()} != commits: return False, 'producing commits differ from ports.json'
        if not _hex(record.get('previous_record_sha256')): return False, 'S0f previous_record_sha256 missing'
        s0e_root = Path(m['input_documents']['accepted_collection']['path']).parents[1]
        s0e_raw = (s0e_root/'control/collector-pin-record.json').read_bytes()
        s0e = json.loads(s0e_raw)
        canon = lambda v: (json.dumps(v, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
        # The driver hashes a controlled previous stage as {chain, records}: the merged chain below S0f plus the S0e record sha.
        link = sha(canon({'chain': {k: chain[k] for k in ORDER[:-1]}, 'records': [sha(canon(s0e))]}))
        if not (record['previous_record_sha256'] == link and s0e.get('stage') == 'S0e' and _hex(s0e.get('previous_record_sha256')) and
                {k: s0e['chain'][k] for k in ORDER[:4]} == {k: chain[k] for k in ORDER[:4]}):
            return False, 'S0f -> S0e previous_record_sha256 linkage or S0a..S0d chain entries differ'
        advice = [s['ticks'] for s in m['new_sources']]
        counts = chain['S0e'].get('counts', {})
        if [counts.get(c) for c in ADVICE] != advice or len(counts) != 12: return False, 'S0e chain counts differ from the 12 advice tick counts'
        s0c = chain['S0c']['outputs']['data-manifest.json']['sha256']
        if not (s0c == m['old_manifest_sha256'] == sha(Path(m['input_documents']['old_manifest']['path']).read_bytes())):
            return False, 'old manifest sha differs from the S0c chain record'
        return True, 'commits vs ports.json, S0f->S0e linkage, S0e counts == advice ticks, old manifest from the S0c record'

    def s0e_audit():
        item = state['manifest']['input_documents']['root_raw_audit']
        raw = Path(item['path']).read_bytes()
        doc = json.loads(raw)
        rel = Path(item['path']).relative_to(Path(state['manifest']['input_documents']['accepted_collection']['path']).parents[1]).as_posix()
        recorded = record['chain']['S0e']['outputs'].get(rel, {}).get('sha256')
        covered = doc.get('not_covered')
        unwaived = [i for i in covered if i not in waivers] if isinstance(covered, list) else ['<missing>']
        state['s0e_audit'] = {'path': item['path'], 'sha256': sha(raw), 'bytes': len(raw)}
        return (sha(raw) == item['sha256'] == recorded and doc.get('kind') == 'm7-navigation-v4-root-raw-audit-1' and
                doc.get('status') == 'passed' and doc.get('failures') == [] and not unwaived), 'S0e-A audit passed, no failures, not_covered empty (no waiver)'

    for name, test in (('s0f_record', record_shape), ('outputs', outputs), ('manifest_pin', manifest_pin), ('structure', structure),
                       ('old_corpus', old_corpus), ('chain', chain_audit), ('s0e_audit', s0e_audit), ('historical_arrays', historical), ('derivation', derivation)):
        if name != 's0f_record' and name != 'outputs' and name != 'manifest_pin' and 'manifest' not in state:
            checks.append({'name': name, 'ok': False, 'detail': 'skipped: data manifest not admitted'}); continue
        check(name, test)
    failures = [c for c in checks if not c['ok']]
    return {'kind': 'm7-navigation-v4-s0z-audit-1', 'status': 'failed' if failures else 'passed', 'checks': checks, 'failures': failures,
            'torch_imported': 'torch' in __import__('sys').modules, 'advice_arrays': 'not vouched for here; enforced at S1 by the fts gate',
            's0f_record_sha256': sha(raw_record), 's0e_audit': state.get('s0e_audit'), 'waivers': list(waivers)}
