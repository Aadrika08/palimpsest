"""Pure, bounded inventory of an explicit Markdown declaration subset.

No file is opened and no link is fetched. Line pointers are one based. Scene
IDs require a scene/layout label and decimal single/list/inclusive-range syntax;
free prose, tables and code with uncertain declarations remain diagnostics.
JSON fences are strict objects for a separate schema classifier, not scene proof.
"""
import hashlib
import json
import math
import re

MAX_BYTES = 4 * 1024**2
MAX_DEPTH = 32
MAX_NODES = 65536
MAX_ITEMS = 4096
MAX_PATH_BYTES = 4096
MAX_DECLARATION_BYTES = 4096
MAX_RESULT_BYTES = 64 * 1024**2
_SPLITS = {'train', 'recorded_dev', 'closed_loop_dev', 'mechanics', 'held_out'}
_HASH = r'[0-9a-f]{64}'
_SCENE = re.compile(r'(?<![\w/.-])(?:scene(?:[ _-]?ids?|s)?|layout(?:[ _-]?(?:ids?|seeds?)|s)?)(?![\w/.-])', re.I)
_GEOMETRY = re.compile(r'\b(?:geometry(?:[_-][\w-]+)?|geometries|\w+_(?:xy|xyz|pose))\b', re.I)
_SENSITIVE = re.compile(r'\b(?:scene(?:s|[_-][\w-]+)?|layout(?:s|[_-][\w-]+)?|geometry(?:[_-][\w-]+)?|geometries|seed(?:s|[_-][\w-]+)?|\w+_(?:xy|xyz|pose))\b', re.I)
_OTHER_SEED = re.compile(r'\b(?:model|training|rng|random|environment)(?:[ _-]+(?:rng|random|number))?[ _-]+seeds?\b', re.I)
_INLINE = re.compile(r'\[([^\]\[\n]*)\]\(([^()\n]*)\)')
_DEF = re.compile(r'^\s{0,3}\[([^\]\n]+)\]:\s*(\S+)(?:\s+"[^"\n]*")?\s*$')
_USE = re.compile(r'\[([^\]\[\n]+)\]\[([^\]\[\n]*)\]')
_SHORTCUT = re.compile(r'\[([^\]\[\n]+)\]')
_CODE = re.compile(r'(?<!`)(`+)([^`\n]+)\1(?!`)')
_FENCE = re.compile(r'^ {0,3}(`{3,}|~{3,})([^\r\n]*)[\r\n]*$')
_FILE = re.compile(r'\.(?:json|md)(?:#[^\s]*)?$', re.I)


def _strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON fence key')
            result[key] = value
        return result

    def constant(_):
        raise ValueError('Nonfinite JSON fence number')

    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, RecursionError, json.JSONDecodeError) as error:
        raise ValueError('Invalid JSON fence') from error
    if type(value) is not dict:
        raise ValueError('JSON fence must be an object')
    pending = [(value, 0)]
    nodes = 0
    while pending:
        current, depth = pending.pop()
        nodes += 1
        if nodes > MAX_NODES or depth > MAX_DEPTH:
            raise ValueError('JSON fence node/depth bound exceeded')
        if type(current) is float and not math.isfinite(current):
            raise ValueError('Nonfinite JSON fence number')
        if type(current) is dict:
            try:
                for key in current:
                    key.encode('utf-8')
            except UnicodeError as error:
                raise ValueError('JSON fence keys must be UTF-8 text') from error
            pending.extend((child, depth + 1) for child in current.values())
        elif type(current) is list:
            pending.extend((child, depth + 1) for child in current)
        elif type(current) is str:
            try:
                current.encode('utf-8')
            except UnicodeError as error:
                raise ValueError('JSON fence strings must be UTF-8 text') from error
    return value, nodes


def _ids(text):
    text = text.strip().strip('`').strip()
    if text.startswith('[') and text.endswith(']'):
        text = text[1:-1].strip()
    single = r'(?:0|[1-9][0-9]*)'
    if re.fullmatch(single + r'\s*(?:\.\.|-|–)\s*' + single, text):
        start, end = map(int, re.split(r'\s*(?:\.\.|-|–)\s*', text))
        if start > end or end - start + 1 > MAX_ITEMS:
            raise ValueError('Scene range must be ordered and bounded')
        values = list(range(start, end + 1))
    elif re.fullmatch(single + r'(?:\s*,\s*' + single + ')*', text):
        values = [int(item.strip()) for item in text.split(',')]
    else:
        raise ValueError('Unsupported scene single/list/range syntax')
    if len(values) > MAX_ITEMS or any(value > 2**31 - 1 for value in values):
        raise ValueError('Scene integer/item bound exceeded')
    if len(set(values)) != len(values):
        raise ValueError('Repeated scene IDs in declaration')
    return values


def _path(target):
    target = target.strip()
    if target.startswith('<') and target.endswith('>'):
        target = target[1:-1]
    if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', target) or target.startswith('//'):
        raise ValueError('Declared external document link')
    if (not target or len(target.encode('utf-8')) > MAX_PATH_BYTES
            or any(ord(c) < 33 or ord(c) == 127 for c in target)
            or any(c in target for c in '\\:%?<>')):
        raise ValueError('Unsupported local document path')
    path, separator, fragment = target.partition('#')
    parts = path.lstrip('/').split('/')
    if (not _FILE.search(path) or any(part == '' for part in parts)
            or any(part == '.' for part in parts[1:])
            or ('..' in parts and any(part != '..' for part in parts[:parts.index('..')]))
            or (separator and not fragment)):
        raise ValueError('Unsupported canonical local document path')
    # Leading ./ and ../ are lexical references; no filesystem normalization.
    return path, fragment if separator else None


def parse_puck_markdown_document(raw):
    """Inventory supplied UTF-8 bytes; never claim arbitrary Markdown coverage."""
    if type(raw) is not bytes or len(raw) > MAX_BYTES:
        raise ValueError('Markdown document must be bytes within 4 MiB')
    try:
        text = raw.decode('utf-8')
    except UnicodeError as error:
        raise ValueError('Markdown document must be UTF-8') from error
    if '\x00' in text or any(ord(c) < 32 and c not in '\n\r\t' for c in text):
        raise ValueError('Markdown document has nontext controls')
    if text.count('\n') + 1 > MAX_NODES:
        raise ValueError('Markdown line/node bound exceeded')
    lines = text.splitlines(keepends=True)
    if len(lines) > MAX_NODES:
        raise ValueError('Markdown line/node bound exceeded')
    result = {'kind': 'puck-markdown-scene-references-v1',
        'document_kind': 'markdown', 'document_sha256': hashlib.sha256(raw).hexdigest(),
        'document_bytes': len(raw), 'mentions': [], 'references': [], 'embedded_json': [],
        'unsupported_declarations': [], 'missing_pins': [], 'held_out_mentions': False,
        'inventory_complete': False, 'source_closure_authenticated': False,
        'executable': False, 'native_authorized': False, 'collection_authorized': False,
        'qualification_claims': [], 'grammar': 'explicit-label-single-list-range-v1'}
    nodes = len(lines)
    result_bytes = 0
    active = []
    index = 0
    byte_offset = 0

    def add(bucket, row):
        nonlocal result_bytes
        serializable = {key: value for key, value in row.items() if key != 'raw'}
        result_bytes += len(json.dumps(serializable, ensure_ascii=False,
                                       allow_nan=False).encode('utf-8'))
        result_bytes += len(row.get('raw', b''))
        if result_bytes > MAX_RESULT_BYTES:
            raise ValueError('Markdown inventory result byte bound exceeded')
        result[bucket].append(row)
        if sum(len(result[key]) for key in ('mentions', 'references', 'embedded_json',
                                           'unsupported_declarations')) > MAX_ITEMS:
            raise ValueError('Markdown inventory item bound exceeded')

    def unsupported(pointer, reason, declaration):
        encoded = declaration.encode('utf-8')
        add('unsupported_declarations', {'pointer': pointer, 'reason': reason,
            'text': encoded[:MAX_DECLARATION_BYTES].decode('utf-8', errors='ignore'),
            'text_truncated': len(encoded) > MAX_DECLARATION_BYTES})

    while index < len(lines):
        line = lines[index]
        pointer = '/lines/' + str(index + 1)
        opening = _FENCE.fullmatch(line)
        if opening:
            marker, language = opening.groups()
            start = index
            content_start = byte_offset + len(line.encode('utf-8'))
            index += 1
            closing = None
            while index < len(lines):
                candidate = _FENCE.fullmatch(lines[index])
                if (candidate and candidate[1][0] == marker[0]
                        and len(candidate[1]) >= len(marker) and not candidate[2].strip()):
                    closing = index
                    break
                index += 1
            content = ''.join(lines[start + 1:index])
            if closing is None:
                unsupported(pointer, 'Unclosed Markdown fence', line + content)
            elif language.strip().lower() == 'json':
                embedded_raw = content.encode('utf-8')
                value, count = _strict_json(embedded_raw)
                nodes += count
                if nodes > MAX_NODES:
                    raise ValueError('Markdown/JSON combined node bound exceeded')
                add('embedded_json', {'raw': embedded_raw, 'value': value,
                    'pointer': pointer + '/embedded_json', 'sha256': hashlib.sha256(embedded_raw).hexdigest(),
                    'byte_start': content_start, 'byte_end': content_start + len(embedded_raw)})
            elif _SENSITIVE.search(content) or re.search(r'\.(?:json|md)\b', content, re.I):
                unsupported(pointer, 'Declarations in unsupported code fence', content)
            byte_offset += len(''.join(lines[start:index + 1]).encode('utf-8'))
            index += 1
            continue
        if len(re.match(r'^[ \t>]*', line)[0].expandtabs(4)) > MAX_DEPTH * 4:
            raise ValueError('Markdown nesting bound exceeded')
        active.append((index + 1, line, pointer))
        byte_offset += len(line.encode('utf-8'))
        index += 1

    definitions = {}
    for number, line, pointer in active:
        definition = _DEF.fullmatch(line.rstrip('\r\n'))
        if definition:
            label = ' '.join(definition[1].lower().split())
            if label in definitions:
                unsupported(pointer, 'Repeated Markdown reference definition', line.rstrip())
                definitions[label] = None
            else:
                definitions[label] = (definition[2], pointer)

    def reference(target, pointer, line, *, scene_document=False):
        external = re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', target) or target.startswith('//')
        if external and (scene_document or re.search(r'\.(?:md|json)\b', target, re.I)):
            unsupported(pointer, 'Declared external document link', target)
            return
        if not _FILE.search(target.strip('<>')):
            if re.search(r'\.(?:md|json)\b', target, re.I):
                unsupported(pointer, 'Unsupported document link target', target)
            return
        try:
            path, fragment = _path(target)
        except ValueError as error:
            unsupported(pointer, str(error), target)
            return
        pins = re.findall(r'\b(?i:sha256)\s*[:=]\s*(' + _HASH + r')(?=$|[\s;|])', line)
        pin_labels = re.findall(r'\b(?i:sha256)\s*[:=]', line)
        if len(pin_labels) > 1 or pins and len(re.findall(r'\.(?:md|json)\b', line, re.I)) > 1:
            unsupported(pointer, 'Ambiguous document SHA-256 declaration', line.rstrip())
            pin = None
        else:
            pin = pins[0] if pins else None
        add('references', {'kind': None, 'path': path, 'sha256': pin,
            'pointer': pointer, 'path_base': 'recorded_cwd' if re.search(
                r'\b(?:project[ _-]path|recorded_cwd)\s*[:=]', line, re.I) else 'document_directory',
            'pin_source': 'declared' if pin else 'absent', 'fragment': fragment})

    def label_declaration(label, pointer):
        # Link labels are visible document content. Removing the link syntax must
        # not erase a scene/seed/geometry declaration embedded in that content.
        # This grammar does not bind label declarations; retain a coverage blocker.
        numeric_label = (_SCENE.search(label) or re.search(
            r'(?<![\w/.-])seeds?(?![\w/.-])', label, re.I))
        if (_GEOMETRY.search(label) or numeric_label
                and re.search(r'\d', label) and not _FILE.search(label)):
            unsupported(pointer, 'Declarations in unsupported Markdown link label', label)

    for number, original, pointer in active:
        line = original.rstrip('\r\n')
        definition = _DEF.fullmatch(line)
        if definition:
            label_declaration(definition[1], pointer + '/reference_definition_label')
            reference(definition[2], pointer + '/reference_definition', line)
            continue
        excluded = []
        for match in _INLINE.finditer(line):
            label_declaration(match[1], pointer + '/link_labels/' + str(match.start()))
            target = re.sub(r'\s+"[^"\n]*"\s*$', '', match[2]).strip()
            reference(target, pointer + '/links/' + str(match.start()), line,
                      scene_document=bool(_SCENE.search(match[1]) or re.search(r'\bdocument\b', match[1], re.I)))
            excluded.append(match.span())
        for match in _USE.finditer(line):
            label_declaration(match[1], pointer + '/reference_link_labels/' + str(match.start()))
            label = ' '.join((match[2] or match[1]).lower().split())
            resolved = definitions.get(label)
            if resolved is not None:
                reference(resolved[0], pointer + '/reference_links/' + str(match.start()), line)
            elif _SCENE.search(match[1]) or label in definitions:
                unsupported(pointer, 'Unresolved or ambiguous Markdown reference', match[0])
            excluded.append(match.span())
        for match in _SHORTCUT.finditer(line):
            if any(start <= match.start() < end for start, end in excluded):
                continue
            label = ' '.join(match[1].lower().split())
            if label in definitions:
                label_declaration(match[1], pointer + '/shortcut_link_labels/' + str(match.start()))
                resolved = definitions[label]
                if resolved is not None:
                    reference(resolved[0], pointer + '/shortcut_links/' + str(match.start()), line)
                else:
                    unsupported(pointer, 'Ambiguous Markdown shortcut reference', match[0])
                excluded.append(match.span())
        replacements = []
        for match in _CODE.finditer(line):
            if _FILE.search(match[2]):
                reference(match[2], pointer + '/code_paths/' + str(match.start()), line)
                excluded.append(match.span())
            else:
                replacements.append((match.start(), match.end(), match[2]))
        chars = list(line)
        for start, end, content in replacements:
            chars[start:end] = content + ' ' * (end - start - len(content))
        for start, end in excluded:
            chars[start:end] = ' ' * (end - start)
        declaration = ''.join(chars).replace('**', '').strip().lstrip('#>*- ').strip()
        if re.search(r'\.(?:md|json)\b', declaration, re.I):
            unsupported(pointer, 'Unclassified document path syntax', line)
        if declaration.startswith('|') and _SENSITIVE.search(declaration):
            unsupported(pointer, 'Declarations in unsupported Markdown table', line)
            continue
        # Known non-scene seeds never become authored layouts.
        reduced = _OTHER_SEED.sub('other_parameter', declaration)
        split_matches = list(re.finditer(r'\bsplit\s*[:=]\s*([\w-]+)', reduced, re.I))
        if len(split_matches) > 1:
            unsupported(pointer, 'Multiple scene split declarations', line)
            continue
        split_match = split_matches[0] if split_matches else None
        split = split_match[1] if split_match else None
        prefix = re.match(r'^(train|recorded_dev|closed_loop_dev|mechanics|held_out)\s+', reduced)
        if prefix:
            if split is not None and split != prefix[1]:
                unsupported(pointer, 'Conflicting scene split declarations', line)
                continue
            split = prefix[1]
            reduced = reduced[prefix.end():]
        if split is not None and split not in _SPLITS:
            unsupported(pointer, 'Unsupported scene split', line)
            continue
        reduced = re.sub(r'\bsplit\s*[:=]\s*[\w-]+', '', reduced, flags=re.I)
        catalogs = list(re.finditer(r'\bcatalog_sha256\s*[:=]\s*(' + _HASH + r')(?=$|[\s;|])', reduced))
        catalog_labels = re.findall(r'\bcatalog_sha256\s*[:=]', reduced)
        if len(catalog_labels) > 1:
            unsupported(pointer, 'Multiple catalog SHA-256 declarations', line)
        catalog = catalogs[0] if len(catalogs) == len(catalog_labels) == 1 else None
        catalog_pin = catalog[1] if catalog else None
        reduced = re.sub(r'\bcatalog_sha256\s*[:=]\s*\S+', '', reduced)
        geometry = bool(_GEOMETRY.search(reduced))
        if geometry:
            unsupported(pointer, 'Unbound Markdown geometry declaration', line)
        scene_matches = list(_SCENE.finditer(reduced))
        if scene_matches:
            for i, match in enumerate(scene_matches):
                end = scene_matches[i + 1].start() if i + 1 < len(scene_matches) else len(reduced)
                value = reduced[match.end():end].strip().lstrip(':=').strip().strip(';| ').strip()
                try:
                    ids = _ids(value)
                except ValueError as error:
                    unsupported(pointer + '/declarations/' + str(i), str(error), line)
                    continue
                for seed in ids:
                    add('mentions', {'scene_id': seed, 'split': split,
                        'pointer': pointer + '/declarations/' + str(i), 'catalog_sha256': catalog_pin,
                        'geometry_bound': False, 'identity_bound': False,
                        'geometry_claims': [line] if geometry else []})
                    result['held_out_mentions'] |= split == 'held_out'
        elif _SENSITIVE.search(reduced) and re.search(r'\d', reduced) and not geometry:
            unsupported(pointer, 'Unclassified numeric scene/layout/seed declaration', line)
        elif split_match:
            unsupported(pointer, 'Scene split without an explicit scene declaration', line)
        if ('catalog_sha256' in declaration and catalog is None
                or re.search(r'\b(?i:sha256)\s*[:=]', declaration)
                and not re.search(r'\b(?i:sha256)\s*[:=]\s*' + _HASH + r'(?=$|[\s;|])', declaration)):
            unsupported(pointer, 'Unsupported SHA-256 declaration', line)
    return result
