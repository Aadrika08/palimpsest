"""Resolve supplied retained metadata through pinned manifests and catalogs.

Neither byte views nor their reference closure establish whole-project inventory,
loaded-code/runtime qualification or owner admission. The held facade authenticates
only explicitly registered JSON payloads using existing file custody.
"""
import copy
import hashlib
import json
import math
from pathlib import PurePosixPath
import re
import time

from .puck_execution_files import HeldCollectionFiles
from .puck_scene_catalog import parse_task_catalog
from .puck_scene_retained import parse_retained_puck_document

MAX_FILES = 512
MAX_BYTES = 4 * 1024**2
MAX_TOTAL_BYTES = MAX_METADATA_BYTES = 64 * 1024**2
MAX_ROOTS = 32
MAX_VARIANTS = MAX_REFERENCES = 4096
MAX_OCCURRENCES = 65536
_KINDS = {'task_catalog', 'recording_manifest', 'teacher_collection_report', 'training_protocol'}
_FIELDS = ('canonical_scene_sha256', 'scientific_initial_sha256', 'payload_sha256')


def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()+b'\n'


def _path(value, absolute=True):
    if absolute and value=='/':return value
    if (type(value) is not str or not value or value.startswith('/') != absolute
            or value.startswith('//') or '\\' in value or ':' in value
            or value != str(PurePosixPath(value))
            or any(ord(c)<32 or ord(c)==127 for c in value)
            or any(p in ('','.', '..') for p in value.split('/')[1 if absolute else 0:])):
        raise ValueError('Canonical scene document path required')
    return value


def _deadline(deadline):
    now=time.monotonic()
    if type(deadline) not in (int,float) or not math.isfinite(deadline) or deadline>now+600:
        raise ValueError('Bounded finite reference deadline required')
    _clock(deadline)


def _clock(deadline):
    if time.monotonic()>=deadline:raise TimeoutError('Scene reference deadline exhausted')


def resolve_retained_puck_documents(documents, *, deadline, origins=None):
    """Pure diagnostic closure over exactly the supplied typed byte views.

    Catalog identity is a raw-byte SHA, distinct from every geometry domain.
    A relative reference requires an explicitly registered historical cwd.
    Missing/null/conflicting reference evidence remains incomplete, never empty.
    """
    _deadline(deadline)
    if type(documents) is not list or not 1<=len(documents)<=MAX_FILES:
        raise ValueError('Bounded nonempty scene document views required')
    parsed={};pins={};catalogs={};input_bytes=0;exposure=False
    for item in documents:
        _clock(deadline)
        if type(item) is not dict or set(item)!={'path','kind','raw'}:
            raise ValueError('Exact scene document view fields required')
        path=_path(item['path']);kind=item['kind'];payload=item['raw']
        if path in parsed or type(kind) is not str or kind not in _KINDS:
            raise ValueError('Duplicate or unsupported scene document view')
        if not path.casefold().endswith('.json') or type(payload) is not bytes or not 0<len(payload)<=MAX_BYTES:
            raise ValueError('Bounded scene JSON bytes required')
        input_bytes+=len(payload)
        if input_bytes>MAX_TOTAL_BYTES:raise ValueError('Scene document aggregate exceeds source ceiling')
        digest=hashlib.sha256(payload).hexdigest()
        pins[path]={'path':path,'kind':kind,'sha256':digest,'size_bytes':len(payload)}
        if kind=='task_catalog':
            value=parse_task_catalog(payload)
            catalogs.setdefault(digest,[]).append((path,value))
            exposure|=value['held_out_catalog_read']
        else:value=parse_retained_puck_document(payload,kind=kind)
        parsed[path]=value
        _clock(deadline)
    if origins is None:origins={}
    if type(origins) is not dict or any(path not in parsed for path in origins):
        raise ValueError('Reference origins must name registered documents')
    origins={_path(path):_path(cwd) for path,cwd in origins.items()}
    resolved=[];unresolved=[];missing=[];links={}
    reference_count=0
    for path,value in sorted(parsed.items()):
        if pins[path]['kind']=='task_catalog':continue
        missing.extend({'document_path':path,'pointer':pointer} for pointer in value['missing_pins'])
        for ref in value['references']:
            _clock(deadline);reference_count+=1
            if reference_count>MAX_REFERENCES:raise ValueError('Reference count exceeds source ceiling')
            target=ref['path'];reason=None
            if not target.startswith('/'):
                if path not in origins:reason='relative_reference_without_recorded_cwd'
                else:target=str(PurePosixPath(origins[path])/target)
            if reason is None:
                _path(target)
                if ref['sha256'] is None:reason='missing_digest'
                elif target not in pins:reason='unregistered_target'
                elif pins[target]['sha256']!=ref['sha256']:reason='target_digest_differs'
                elif pins[target]['kind']!=ref['kind']:reason='target_kind_differs'
                elif ref['scene_id'] is not None and not any(
                        mention['scene_id']==ref['scene_id'] and mention['split']==ref['split']
                        for mention in parsed[target]['mentions']):reason='target_scene_differs'
            record={'document_path':path,'pointer':ref['pointer'],'path':target,'sha256':ref['sha256']}
            if reason:unresolved.append(dict(record,reason=reason))
            else:
                resolved.append(record)
                links[path,ref['pointer']]=target
    grouped={};unresolved_mentions=[];occurrence_count=0;metadata_bytes=0

    def geometry(path,mention,depth=0):
        _clock(deadline)
        if depth>16:return None,'reference_depth_exceeded'
        digest=mention['catalog_sha256']
        if digest is not None:
            if digest not in catalogs:return None,'unregistered_catalog_digest'
            selected=[]
            for catalog_path,value in catalogs[digest]:
                rows=[row for row in value['scenes'] if row['scene_id']==mention['scene_id'] and row['split']==mention['split']]
                if len(rows)!=1:return None,'catalog_scene_missing'
                selected.append((catalog_path,rows[0]))
            row=selected[0][1]
            return (row,digest,sorted(p for p,_ in selected)),None
        value=parsed[path]
        refs=[ref for ref in value['references'] if ref['kind']=='recording_manifest'
              and mention['pointer']==ref['pointer']+'/seed'
              and ref['scene_id']==mention['scene_id'] and ref['split']==mention['split']]
        if len(refs)!=1:return None,'missing_catalog_or_unique_manifest_reference'
        target=links.get((path,refs[0]['pointer']))
        if target is None:return None,'unresolved_manifest_reference'
        candidates=[item for item in parsed[target]['mentions']
                    if item['scene_id']==mention['scene_id'] and item['split']==mention['split']]
        identities=[]
        for candidate in candidates:
            found,error=geometry(target,candidate,depth+1)
            if error:return None,error
            identities.append(found)
        if not identities:return None,'target_scene_missing'
        keys={tuple(found[0][field] for field in _FIELDS) for found in identities}
        if len(keys)!=1:return None,'target_identity_conflict'
        return identities[0],None

    for path,value in sorted(parsed.items()):
        if pins[path]['kind']=='task_catalog':continue
        for mention in value['mentions']:
            _clock(deadline);occurrence_count+=1
            if occurrence_count>MAX_OCCURRENCES:raise ValueError('Scene occurrence count exceeds source ceiling')
            found,reason=geometry(path,mention)
            occurrence={'document_path':path,'document_sha256':pins[path]['sha256'],
                        'pointer':mention['pointer'],'scene_id':mention['scene_id'],'split':mention['split']}
            if reason:unresolved_mentions.append(dict(occurrence,reason=reason))
            else:
                row,digest,paths=found
                identity=(mention['scene_id'],*(row[field] for field in _FIELDS))
                occurrence.update(catalog_sha256=digest,catalog_sources=paths,catalog_pointer=row['pointer'])
                if identity not in grouped:
                    if len(grouped)>=MAX_VARIANTS:raise ValueError('Scene variants exceed source ceiling')
                    grouped[identity]=[]
                grouped[identity].append(occurrence)
            metadata_bytes+=len(_canonical(occurrence))
            if metadata_bytes>MAX_METADATA_BYTES:raise ValueError('Scene occurrence metadata exceeds source ceiling')
    variants=[];ids={};domains={field:{} for field in _FIELDS}
    for identity,occurrences in sorted(grouped.items()):
        _clock(deadline);index=len(variants)
        row=dict(zip(('scene_id',*_FIELDS),identity));row['occurrences']=occurrences
        variants.append(row);ids.setdefault(row['scene_id'],[]).append(index)
        for field in _FIELDS:domains[field].setdefault(row[field],[]).append(index)
    id_variants=[{'scene_id':sid,'variant_indices':indices} for sid,indices in sorted(ids.items()) if len(indices)>1]
    aliases=[{'field':field,'sha256':digest,'variant_indices':indices} for field in _FIELDS
             for digest,indices in sorted(domains[field].items()) if len(indices)>1]
    result={'kind':'puck-retained-scene-resolution-v1','version':1,
        'documents':[pins[path] for path in sorted(pins)],'variants':variants,
        'id_variants':id_variants,'identity_aliases':aliases,
        'legacy_scene_rows_compatible':not id_variants and not aliases,
        'resolved_references':resolved,'unresolved_references':unresolved,
        'unresolved_mentions':unresolved_mentions,'missing_pins':missing,
        'declared_reference_closure_resolved':not unresolved and not unresolved_mentions and not missing,
        'held_out_catalog_read':exposure,'held_out_runtime_opened':False,
        'inventory_complete':False,'source_closure_authenticated':False,
        'reservation_authorized':False,'collection_authorized':False,'executable':False,'qualification_claims':[]}
    _clock(deadline)
    if len(_canonical(result))>MAX_METADATA_BYTES:raise ValueError('Scene resolution receipt exceeds source ceiling')
    _clock(deadline)
    return result


def _pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate reference registration JSON key')
        result[key]=value
    return result


class HeldRetainedPuckDocuments:
    """Selected JSON payload custody, not filesystem scope or stage admission."""
    def __init__(self, registration_raw, *,expected_sha256,deadline):
        _deadline(deadline)
        if (type(registration_raw) is not bytes or not 0<len(registration_raw)<=1024**2
                or type(expected_sha256) is not str or re.fullmatch('[0-9a-f]{64}',expected_sha256) is None
                or hashlib.sha256(registration_raw).hexdigest()!=expected_sha256):
            raise ValueError('Bounded externally pinned reference registration required')
        try:
            value=json.loads(registration_raw,object_pairs_hook=_pairs,
                parse_constant=lambda text:(_ for _ in ()).throw(ValueError('Nonfinite registration')))
            canonical=_canonical(value)
        except (UnicodeError,json.JSONDecodeError,RecursionError,OverflowError) as error:
            raise ValueError('Strict canonical reference registration required') from error
        if (canonical!=registration_raw or type(value) is not dict
                or set(value)!={'id','version','roots','origins'}
                or value['id']!='puck-retained-scene-inputs-v1' or type(value['version']) is not int or value['version']!=1
                or type(value['roots']) is not list or not 1<=len(value['roots'])<=MAX_ROOTS):
            raise ValueError('Exact reference registration schema required')
        roots=[];documents={};total=0
        for root in value['roots']:
            if type(root) is not dict or set(root)!={'root','files'}:raise ValueError('Exact reference root fields required')
            path=_path(root['root'])
            if any(path==old or PurePosixPath(path).is_relative_to(old) or PurePosixPath(old).is_relative_to(path) for old in roots):
                raise ValueError('Registered reference roots overlap or repeat')
            roots.append(path)
            if type(root['files']) is not list or not root['files']:raise ValueError('Nonempty registered JSON file list required')
            names=[]
            for entry in root['files']:
                if type(entry) is not dict or set(entry)!={'path','size_bytes','sha256','kind'}:
                    raise ValueError('Exact registered JSON descriptor required')
                name=_path(entry['path'],False);absolute=str(PurePosixPath(path)/name);names.append(name)
                size=entry['size_bytes'];digest=entry['sha256']
                if (not name.casefold().endswith('.json') or type(entry['kind']) is not str or entry['kind'] not in _KINDS
                        or type(size) is not int or not 0<size<=MAX_BYTES
                        or type(digest) is not str or re.fullmatch('[0-9a-f]{64}',digest) is None):
                    raise ValueError('Registered scene descriptor types or bounds differ')
                documents[absolute]=entry['kind'];total+=size
                if len(documents)>MAX_FILES or total>MAX_TOTAL_BYTES:raise ValueError('Registered scene inputs exceed source ceiling')
            if names!=sorted(set(names)):raise ValueError('Registered scene descriptors must be sorted and distinct')
        if type(value['origins']) is not list or len(value['origins'])>MAX_FILES:raise ValueError('Bounded reference origin list required')
        origins={}
        for origin in value['origins']:
            if type(origin) is not dict or set(origin)!={'document_path','cwd'}:raise ValueError('Exact recorded origin required')
            path=_path(origin['document_path']);cwd=_path(origin['cwd'])
            if path not in documents or path in origins:raise ValueError('Origin document missing or duplicated')
            origins[path]=cwd
        self._registration=copy.deepcopy(value);self._origins=origins;self._digest=expected_sha256
        self._deadline=deadline;self._state='new';self._holders=[];self._receipt=None
        _clock(deadline)

    def _active(self):
        if self._state!='active':raise RuntimeError('Retained document custody is inactive or poisoned')

    def _close(self,primary=None):
        first=None
        for holder in reversed(self._holders):
            try:holder.__exit__(type(primary) if primary else None,primary,None)
            except BaseException as error:
                if primary is not None:primary.add_note('Retained document close failed: '+str(error))
                elif first is None:first=error;primary=error
                else:first.add_note('Further retained document close failure: '+str(error))
        self._holders.clear();self._state='failed' if primary else 'closed'
        if first is not None:raise first

    def __enter__(self):
        if self._state!='new':
            error=RuntimeError('Retained document context cannot be reused');self._close(error);raise error
        try:
            _clock(self._deadline);documents=[]
            for root in self._registration['roots']:
                entries=[{k:v for k,v in row.items() if k!='kind'} for row in root['files']]
                holder=HeldCollectionFiles(root['root'],entries,self._deadline)
                self._holders.append(holder);holder.__enter__()
                for row in root['files']:
                    _clock(self._deadline)
                    documents.append({'path':str(PurePosixPath(root['root'])/row['path']),
                        'kind':row['kind'],'raw':holder.read(row['path'],MAX_BYTES)})
            self._receipt=resolve_retained_puck_documents(documents,deadline=self._deadline,origins=self._origins)
            self._receipt.update(registration_sha256=self._digest,registered_document_bytes_authenticated=True)
            if len(_canonical(self._receipt))>MAX_METADATA_BYTES:
                raise ValueError('Registered scene receipt exceeds source metadata ceiling')
            self._state='active';self.recheck();return self
        except BaseException as error:self._close(error);raise

    def recheck(self):
        try:
            self._active();_clock(self._deadline)
            for holder in self._holders:holder.recheck()
            _clock(self._deadline)
        except BaseException as error:self._close(error);raise

    def snapshot(self):
        self.recheck()
        try:
            result=copy.deepcopy(self._receipt);self.recheck();_clock(self._deadline);return result
        except BaseException as error:self._close(error);raise

    def __exit__(self,kind,error,traceback):
        if self._state=='failed' and error is None:
            raise RuntimeError('Retained document custody failed before normal close')
        if self._state in ('closed','failed'):return False
        try:self.recheck()
        except BaseException as drift:
            if error is not None:error.add_note('Retained document final drift check failed: '+str(drift))
            else:raise
        self._close(error)
        try:_clock(self._deadline)
        except BaseException as late:
            if error is not None:error.add_note('Retained document final deadline failed: '+str(late))
            else:raise
        return False
