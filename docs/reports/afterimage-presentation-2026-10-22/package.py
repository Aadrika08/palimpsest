"""Add lossless source-frame presentation without changing recorded artworks."""
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

import numpy as np
from PIL import Image
from palimpsest.storage import StorageBudget
from record_route_material import LIMITS
from prepare_artwork_encounter import encounter_html

root = Path('runs/afterimage-presentation-2026-10-22-v2').absolute()
previous = Path('runs/route-obstacle-material-2026-10-22-v1/palimpsest-obstacle-review-2026-10-22.zip')
previous_sha = '9299bcdad062da11ca3060e1ef2be573aae701d830a40a308b91e1d2a77a3c23'
assert hashlib.sha256(previous.read_bytes()).hexdigest() == previous_sha
assert not root.exists(), 'fresh output required'
store = StorageBudget((root,), LIMITS)
with store.lock():
    with zipfile.ZipFile(previous) as z:
        files = {name: z.read(name) for name in z.namelist()}
    for name, pin in json.loads(files['checksums.json'])['files'].items():
        assert len(files[name]) == pin['size_bytes'] and hashlib.sha256(files[name]).hexdigest() == pin['sha256']
    artworks = {name: files[name] for name in ('afterimage.svg', 'counterfactual-choir.wav',
        'borrowed-body.svg', 'one-map-many-lives.html', 'atlas.svg', 'space-between-two-flies.svg')}
    source = json.loads(files['afterimage-source.json'])
    frame_path = Path('runs/afterimage-material-2026-10-22-v1/stimulus/frames.npy')
    frame_bytes = frame_path.read_bytes()
    npy_sha = hashlib.sha256(frame_bytes).hexdigest()
    assert npy_sha == source['frame_file_sha256']
    frames = np.load(io.BytesIO(frame_bytes), allow_pickle=False)
    assert frames.shape == (600, 128, 128, 3) and frames.dtype == np.uint8
    assert len(source['frames']) == 600
    sheet = np.empty((60 * 128, 10 * 128, 3), dtype=np.uint8)
    for i, frame in enumerate(frames):
        assert source['frames'][i]['frame'] == i
        assert hashlib.sha256(frame.tobytes()).hexdigest() == source['frames'][i]['frame_sha256']
        y, x = divmod(i, 10)
        sheet[y * 128:(y + 1) * 128, x * 128:(x + 1) * 128] = frame
    buffer = io.BytesIO()
    Image.fromarray(sheet).save(buffer, format='PNG')
    png = buffer.getvalue()
    with Image.open(io.BytesIO(png)) as decoded_image:
        assert decoded_image.mode == 'RGB' and decoded_image.size == (1280, 7680)
        decoded = np.asarray(decoded_image)
        for i, frame in enumerate(frames):
            y, x = divmod(i, 10)
            assert np.array_equal(decoded[y * 128:(y + 1) * 128, x * 128:(x + 1) * 128], frame)
    sprite = {'schema_version': 1, 'columns': 10, 'rows': 60, 'width': 128, 'height': 128,
              'png_sha256': hashlib.sha256(png).hexdigest()}
    files['afterimage-frames.png'] = png
    files['afterimage-frames.json'] = json.dumps(sprite, indent=2).encode()
    files['README.md'] = ('''# Afterimage source-frame presentation — 22 October 2026

Open index.html locally. Afterimage now pairs each recorded response with its
original effective left-camera frame. The lossless 10-column, 60-row PNG contains
all 600 original 128×128 RGB frames, in chronological order, without resizing.
Every decoded tile was compared byte-for-byte against the hash-verified NPY and
source frame index. afterimage-frames.json identifies the layout and PNG hash.
No inference, new source recording, smoothing or aesthetic frame selection occurs.

All six artwork files are byte-identical to the previous obstacle-review package.
Their source provenance, mappings and limitations remain in this pack. The new
Afterimage presentation needs its own browser verification; prior duration checks
do not establish this changed presentation's acceptance. Human Afterimage viewing
and artistic acceptance remain pending, as do independent operator and rights/use
declarations. See human-review.md. These are artificial model responses, not
biological perception. The retained source-image files increase this derivative
pack's contents; raw NPY and simulator recordings remain local.

## Previous material and evidence

''' + files['README.md'].decode()).encode()
    review = files['human-review.md'].decode().replace('Afterimage presentation is next.', 'Afterimage source-frame presentation is implemented; human viewing remains pending.')
    review = re.sub(r'`(?:runs/[^`\n]+/)?index\.html`', '`index.html`', review)
    files['human-review.md'] = (review + '\nThe new Afterimage source-frame presentation still requires human viewing and acceptance; no prior judgment is carried forward.\n').encode()
    files['index.html'] = encounter_html(files)
    assert all(files[name] == raw for name, raw in artworks.items())
    files['checksums.json'] = json.dumps({'qualification_claims': [], 'files': {
        name: {'size_bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        for name, raw in files.items() if name != 'checksums.json'}}, indent=2).encode()
    assert sum(map(len, files.values())) < 64 * 1024**2
    out = root / 'encounter'
    store.check(2 * sum(map(len, files.values())) + 1024**2, path=root)
    out.mkdir(parents=True, exist_ok=False)
    for name, raw in files.items():
        assert Path(name).name == name
        store.check(len(raw), path=out / name)
        with (out / name).open('xb') as stream:
            stream.write(raw)
    target = root / 'palimpsest-afterimage-presentation-2026-10-22.zip'
    store.check(sum(map(len, files.values())) + 65536, path=target)
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_STORED) as z:
        for name in sorted(files):
            z.writestr(name, files[name])
    with zipfile.ZipFile(target) as z:
        assert set(z.namelist()) == set(files) and all(z.read(name) == raw for name, raw in files.items())
    result = {'archive': str(target), 'size_bytes': target.stat().st_size,
              'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'files': len(files),
              'previous_archive_sha256': previous_sha, 'frame_npy_sha256': npy_sha,
              'sprite': sprite, 'decoded_tiles_exact': 600,
              'unchanged_artwork_sha256': {name: hashlib.sha256(raw).hexdigest() for name, raw in artworks.items()},
              'encounter_script_sha256': hashlib.sha256(Path('scripts/prepare_artwork_encounter.py').read_bytes()).hexdigest(),
              'package_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'browser_verification': 'pending', 'human_acceptance': 'pending', 'qualification_claims': []}
    with (root / 'artifacts.json').open('x') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result))
