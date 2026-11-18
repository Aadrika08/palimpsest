"""S1 data worker: v3's in-process data path, run in a child because the readers are the T-f port.

Run only by ``train_male_navigation_v4.py`` (inside the S1 unit, before Torch) as
``python -I -B <this> <config json>`` with PALIMPSEST_M7_V4_PINS naming S0f's live locator.
``sys.path`` holds only the T-f port worktree (``src`` then ``scripts``): the S1 process already
holds CURRENT ``palimpsest`` modules whose bytes differ from the port's, so the S0f readers cannot
be imported in-process. This is the same derivation v3 used (``train_male_navigation_v2.prepare``):

* BEFORE any data is read, T-f's own ``reader_identity`` must equal the S0f data manifest's
  ``current_reader_sources``, its ``SELF_SHA`` the manifest's ``adapter_sha256`` and the feature
  protocol digest the manifest's ``feature_protocol_sha256``;
* old arrays come from ``read_old_transfer`` (S0f's historical-arrays.npz, re-checked against the
  T-h historical identity); advice arrays are derived with ``advice_arrays(iter_ticks(...))`` from
  the S0e recordings after ``admit_collection``/``admit_record``;
* every source must hash (features + targets bytes) to its manifest ``feature_target_sha256``
  and both arms must equal the manifest's ordered ``arms`` (v3's exact check).

The result is a TRANSIENT ``.npz`` keyed ``<feature_target_sha256>/{features,targets}``, created
exclusively in S1's own output directory. It is not a pinned artifact: trust rests on the hash
equality above, and the parent re-validates it. Nothing is written outside ``config['output']``.
One JSON line on stdout.
"""
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import sys
import time

FORBIDDEN = ('mujoco', 'torch')


def refuse(reason):
    print(json.dumps({'status': 'refused', 'reason': reason}, sort_keys=True)); sys.stdout.flush()
    raise SystemExit(1)


def fts(episode):
    return hashlib.sha256(episode['features'].tobytes() + episode['targets'].tobytes()).hexdigest()


def main():
    config = json.loads(sys.argv[1])
    port = Path(config['port_root']).resolve()
    sys.path[:0] = [str(port/'src'), str(port/'scripts')]
    np = importlib.import_module('numpy')
    prep = importlib.import_module('prepare_male_navigation_v2')
    if not Path(prep.__file__).resolve().is_relative_to(port): refuse('prepare_male_navigation_v2 is not from the T-f port')
    deadline = time.monotonic() + float(config['seconds'])
    raw = Path(config['manifest']['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != config['manifest']['sha256']: refuse('Data manifest bytes differ from the S0z pin')
    manifest = json.loads(raw)
    artifacts, model, iter_ticks, old, nav = prep.helpers()
    # Code gate first: nothing below runs (and no recording is opened) unless the code is S0f's.
    if prep.reader_identity(deadline) != manifest['current_reader_sources']: refuse('T-f reader/feature code differs from S0f current_reader_sources')
    if prep.SELF_SHA != manifest['adapter_sha256']: refuse('T-f adapter differs from S0f adapter_sha256')
    if model.digest(model.FEATURE_PROTOCOL) != manifest['feature_protocol_sha256']: refuse('Feature protocol differs from S0f')
    p = prep.protocol()
    historical = prep.historical_identity(p, deadline)
    if historical != manifest['historical_reader']: refuse('Historical reader identity differs from S0f')
    prepared = prep.read_json(Path(config['data_root'])/'after-admission.json')
    sources = {x['path'] for x in manifest['old_sources'] + manifest['new_sources']}
    if (prepared.get('status') != 'obtained-after-inventory' or prepared.get('errors') != [] or prepared.get('qualification_claims') != [] or
            prepared.get('reader') != manifest['current_reader_sources'] or prepared.get('historical') != historical or
            len(prepared.get('sources', [])) != 26 or {x['path'] for x in prepared['sources']} != sources or
            any(prepared['documents'][k]['sha256'] != v['sha256'] for k, v in manifest['input_documents'].items() if k in prepared['documents'])):
        refuse('S0f after-admission inventory differs from the manifest')
    if (manifest.get('status') != 'prepared-navigation-advice-research-only' or manifest.get('labels') != {'old': 'unchanged executed targets', 'new': 'nav_advice_action'} or
            any(manifest['arms'][arm]['held_out'] for arm in ('old', 'augmented'))):
        refuse('Manifest status/labels/held-out differ')
    old_manifest = prep.read_json(manifest['input_documents']['old_manifest']['path'], expected=manifest['old_manifest_sha256'])
    data = prep.read_old_transfer(Path(config['data_root']), old_manifest, historical)
    counts = manifest['counts']
    if old.validate_splits(data) != {'train': counts['old_train_rows'], 'dev': counts['recorded_dev_rows'], 'held_out': 0}:
        refuse('Unchanged old arm differs')
    augmented = {'train': list(data['train']), 'dev': list(data['dev']), 'held_out': []}
    collection = prep.admit_collection(p, prep.pinned_documents(p, deadline))
    root = Path(manifest['input_documents']['accepted_collection']['path']).parent
    for case, source in zip(nav.CASES, manifest['new_sources'], strict=True):
        item = collection['cases'][case['id']]; run = artifacts._safe_path(item['run'])
        owner = prep.read_json(root/case['id']/'result.json', expected=item['result_sha256'])
        count = nav.admit_record(run, owner, collection['identities_before'][str(case['learner_seed'])])
        features, targets = prep.advice_arrays(iter_ticks(run/'recording'), deadline)
        if (run != Path(source['path']) or run.name != source['run_id'] or source['episode'] != 0 or len(targets) != count or
                count != source['ticks'] or hashlib.sha256(features.tobytes() + targets.tobytes()).hexdigest() != source['feature_target_sha256']):
            refuse(f'Byte drift: advice source {source["run_id"]} differs from its S0f feature_target_sha256')
        augmented['train'].append({'run_id': run.name, 'episode': 0, 'features': features, 'targets': targets})
    for name, arm in (('old', data), ('augmented', augmented)):
        actual = {split: [{'run_id': ep['run_id'], 'episode': ep['episode'], 'ticks': len(ep['targets']), 'feature_target_sha256': fts(ep)}
                          for ep in arm[split]] for split in ('train', 'dev', 'held_out')}
        if actual != manifest['arms'][name]: refuse('Exact manifest arm order/bytes differ')
    if old.validate_splits(augmented, check_counts=False) != {'train': counts['augmented_train_rows'], 'dev': counts['recorded_dev_rows'], 'held_out': 0}:
        refuse('Augmented fixed counts differ')
    if prep.reader_identity(deadline) != manifest['current_reader_sources']: refuse('T-f reader code changed during the read')
    arrays = {}
    for episode in augmented['train'] + augmented['dev']:
        digest = fts(episode)
        arrays[digest + '/features'], arrays[digest + '/targets'] = episode['features'], episode['targets']
    stream = io.BytesIO(); np.savez(stream, **arrays)
    with Path(config['output']).open('xb') as handle:
        handle.write(stream.getvalue()); handle.flush(); os.fsync(handle.fileno())
    print(json.dumps({'status': 'derived', 'sources': len(augmented['train']) + len(augmented['dev']),
                      'forbidden_modules': sorted(n for n in sys.modules if n.split('.')[0] in FORBIDDEN),
                      'output_sha256': hashlib.sha256(stream.getvalue()).hexdigest(),
                      'reader_origin': str(Path(prep.__file__).resolve())}, sort_keys=True))


if __name__ == '__main__':
    main()
