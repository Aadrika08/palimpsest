"""Frozen reference: the S1 detector as of f0b8bcb, before the r6 performance work.

Copied verbatim for differential tests; the optimised module must produce identical findings.
"""
from palimpsest import puck_v4_scene_admission as _s1

globals().update({name: getattr(_s1, name) for name in dir(_s1)
                  if not name.startswith('__') and name not in ['_ids_in_text', '_raw_new_ids', '_walk', '_raw_only_hits', '_parse_document', '_analyze']})


def _ids_in_text(text):
    found, spans = [], []
    for match in _RANGE.finditer(text):
        low, high = int(match[1]), int(match[2])
        if low <= high and high - low <= MAX_RANGE:
            found.extend(range(low, high + 1))
            spans.append(match.span())
    for match in _TOKEN.finditer(text):
        if not any(start <= match.start() < end for start, end in spans):
            found.append(int(match[1]))
    return found


def _raw_new_ids(raw):
    """New IDs mentioned anywhere in raw bytes, with ranges and all dash forms expanded."""
    return set(_ids_in_text(raw.decode('utf-8', errors='replace'))) & set(NEW_SCENE_IDS)


def _walk(value, pointer, typed, occurrences, held_out_payloads):
    if type(value) is dict:
        geometry = bool(_GEOMETRY_KEYS & set(value))
        ids = [value[key] for key in value if key in _ID_KEYS]
        if geometry and any(type(item) is int and item in HELD_OUT_SCENE_IDS for item in ids):
            held_out_payloads.append((pointer, next(
                item for item in ids if type(item) is int and item in HELD_OUT_SCENE_IDS)))
        for key, child in value.items():
            child_pointer = pointer + '/' + _escape(key)
            child_geometry = type(child) is dict and bool(_GEOMETRY_KEYS & set(child))
            if re.fullmatch(r'\d{1,7}', key) and (typed or child_geometry):
                # A numeric key is a scene ID in typed context, or when it maps to geometry.
                occurrences.append((child_pointer, int(key)))
                if child_geometry and int(key) in HELD_OUT_SCENE_IDS:
                    held_out_payloads.append((child_pointer, int(key)))
            child_typed = (typed or _key_is_scene(key)) and not _key_is_non_scene(key)
            if geometry and key in _ID_KEYS:
                child_typed = True  # bare id beside geometry is a scene identity
            if key in _GEOMETRY_KEYS:
                child_typed = False  # geometry values are never scene IDs nor compared
            _walk(child, child_pointer, child_typed, occurrences, held_out_payloads)
    elif type(value) is list:
        for index, child in enumerate(value):
            _walk(child, f'{pointer}/{index}', typed, occurrences, held_out_payloads)
    elif typed and type(value) is int:
        occurrences.append((pointer, value))
    elif typed and type(value) is float and math.isfinite(value) and value.is_integer():
        occurrences.append((pointer, int(value)))  # e.g. 6510.0 or 6.51e3
    elif typed and type(value) is str:
        occurrences.extend((pointer, item) for item in _ids_in_text(value))


def _raw_only_hits(relative, raw):
    """Classify new-ID hits in untyped formats: (ambiguous_ids, non_scene_ids)."""
    text = raw.decode('utf-8', errors='replace')
    ambiguous, non_scene = set(), set()
    if relative.endswith('.csv'):
        try:
            rows = list(csv.reader(io.StringIO(text)))
        except csv.Error:
            return set(_ids_in_text(text)) & set(NEW_SCENE_IDS), set()  # raw-scan only
        header = rows[0] if rows else []
        for number, row in enumerate(rows):
            for column, cell in enumerate(row):
                hits = set(_ids_in_text(cell)) & set(NEW_SCENE_IDS)
                name = header[column] if number and column < len(header) else ''
                typed_non_scene = bool(name) and _key_is_non_scene(name) \
                    and not _key_is_scene(name)
                (non_scene if typed_non_scene else ambiguous).update(hits)
        return ambiguous, non_scene
    for line in text.splitlines():
        hits = set(_ids_in_text(line)) & set(NEW_SCENE_IDS)
        if not hits:
            continue
        match = None if relative.endswith('.txt') else re.match(
            r'\s*"?([A-Za-z0-9_.\- ]+?)"?\s*[:=]\s*[^:=]*$', line)
        if match and _key_is_non_scene(match[1]) and not _key_is_scene(match[1]):
            non_scene.update(hits)
        else:
            ambiguous.update(hits)
    return ambiguous, non_scene


def _parse_document(relative, raw):
    """Return (occurrences, held_out_payload_objects, unsupported_texts) or None if unparsed."""
    occurrences, held_out, unsupported = [], [], []
    try:
        if relative.endswith('.md'):
            result = parse_puck_markdown_document(raw)
            occurrences = [(row['pointer'], row['scene_id']) for row in result['mentions']]
            unsupported = [row['text'] for row in result['unsupported_declarations']]
        elif relative.endswith('.jsonl'):
            for number, line in enumerate(raw.split(b'\n'), 1):
                if line.strip():
                    _walk(_strict_json(line, 'jsonl'), f'/lines/{number}', False,
                          occurrences, held_out)
        else:
            _walk(_strict_json(raw, 'json'), '', False, occurrences, held_out)
    except (ValueError, AdmissionRefused, RecursionError):
        return None
    return occurrences, held_out, unsupported


def _analyze(relative, raw, digest):
    """Pure content analysis; depends only on the bytes and the file suffix."""
    result = {'lineage': LINEAGE_SHA256.get(digest), 'prefiltered': False, 'unparsed': False,
              'ambiguous': [], 'untyped': [], 'occurrences': [], 'held_out': []}
    if result['lineage'] is not None:
        return result
    if not prefilter_hit(raw):
        result['prefiltered'] = True
        return result
    raw_new = _raw_new_ids(raw)
    if relative.endswith(RAW_SUFFIXES):
        ambiguous, non_scene = _raw_only_hits(relative, raw)
        if ambiguous:
            result['ambiguous'].append(('untyped format mentions new IDs', sorted(ambiguous)))
        result['untyped'] = sorted(non_scene - ambiguous)
        return result
    parsed = _parse_document(relative, raw)
    if parsed is None:
        result['unparsed'] = True
        if raw_new:
            result['ambiguous'].append(('unparsed document contains new IDs', sorted(raw_new)))
        return result
    occurrences, held_out, unsupported = parsed
    for text in unsupported:
        hits = sorted(_raw_new_ids(text.encode()))
        if hits:
            result['ambiguous'].append(('unsupported typed declaration', hits))
    result['occurrences'] = occurrences
    result['untyped'] = sorted(raw_new - {scene_id for _, scene_id in occurrences})
    result['held_out'] = held_out
    return result
