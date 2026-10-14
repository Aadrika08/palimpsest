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
from .puck_scene_retained import parse_retained_puck_document, _ROW_FIELDS

MAX_FILES = 512
MAX_BYTES = 4 * 1024**2
MAX_TOTAL_BYTES = MAX_METADATA_BYTES = 64 * 1024**2
MAX_ROOTS = 32
MAX_VARIANTS = MAX_REFERENCES = 4096
MAX_OCCURRENCES = 65536
_KINDS = {'task_catalog', 'recording_manifest', 'teacher_collection_report', 'training_protocol'}
_REGISTRY_KINDS = {'on_policy_inventory','on_policy_reservation','on_policy_scene_manifest',
    'on_policy_collection_projection','on_policy_publication_commit','on_policy_publication_admission'}
_REPORT_KINDS = {'owner_result','construction_result','mechanics_report',
    'construction_report','development_report'}
_TRAINING_KINDS = {'training_report','prepared_training','model_index'}
_KINDS |= _REGISTRY_KINDS | _REPORT_KINDS | _TRAINING_KINDS
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


def _point(document, pointer):
    value=document
    for token in pointer.split('/')[1:]:
        token=token.replace('~1','/').replace('~0','~')
        value=value[int(token)] if type(value) is list else value[token]
    return value


def _report_dependency_reason(parent, target, reference):
    if reference['kind']=='training_protocol' and 'training_completed' in parent:
        objective=parent.get('training_objective_sha256')
        target_objective=target.get('balanced_objective')
        if objective is not None or target.get('schema')=='puck-balanced-training-v1':
            if (type(target_objective) is not dict
                    or objective!=target_objective.get('sha256')):
                return 'target_training_objective_differs'
        return None
    if reference['kind']=='training_report' and 'models' in parent:
        entry=_point(parent,reference['pointer'].rsplit('/files/',1)[0])
        if target['protocol_sha256']!=entry['files']['protocol.json']:
            return 'target_model_file_receipt_differs'
        checkpoints=[file for file in target['files'] if file['path']=='checkpoint.npz']
        if len(checkpoints)!=1:
            return 'target_model_checkpoint_receipt_missing'
        if checkpoints[0]['sha256']!=entry['files']['checkpoint.npz']:
            return 'target_model_file_receipt_differs'
        return None
    if reference['kind'] not in ('owner_result','construction_result','recording_manifest'):
        return None
    # Recording source refs in training/teacher reports have a different roster
    # shape. Only report owner refs carry the complete actual owner row here.
    if reference['kind']=='recording_manifest' and not reference['pointer'].startswith('/owners/'):
        return None
    if 'expected_owner_id' in reference:
        row=target.get('row',{})
        if row.get('id')!=reference['expected_owner_id'] or row.get('model_seed')!=21:
            return 'target_baseline_owner_differs'
        if target.get('snapshots',{}).get('initial',{}).get('sha256')!=reference['expected_snapshot_sha256']:
            return 'target_baseline_snapshot_differs'
        return None
    owner=_point(parent,reference['pointer'])
    if type(owner) is not dict:
        return 'parent_owner_receipt_differs'
    if reference['kind'] in ('owner_result','recording_manifest'):
        expected={key:value for key,value in owner.items() if key in _ROW_FIELDS}
        if expected!=target['row']:
            return 'target_recording_row_differs' if reference['kind']=='recording_manifest' else 'target_owner_row_differs'
    if reference['kind']=='owner_result':
        identity=target.get('student_identity',{}).get('model_identity')
        expected=parent.get('models',{}).get(str(target['row'].get('model_seed')))
        if identity is not None and expected is not None:
            from .puck_scene_reports import _MODEL_HASHES
            for field in sorted({'training_seed',*_MODEL_HASHES} & expected.keys()):
                if field not in identity:return 'target_model_identity_missing'
                if identity[field]!=expected[field]:return 'target_model_identity_differs'
    if reference['kind']!='recording_manifest' and 'result' in owner and _canonical(owner['result'])!=_canonical(target):
        return 'target_embedded_result_differs'
    return None


def resolve_retained_puck_documents(documents, *, deadline, origins=None):
    """Pure diagnostic closure over exactly the supplied typed byte views.

    Catalog identity is a raw-byte SHA, distinct from every geometry domain.
    A relative reference requires an explicitly registered historical cwd.
    Missing/null/conflicting reference evidence remains incomplete, never empty.
    """
    _deadline(deadline)
    if type(documents) is not list or not 1<=len(documents)<=MAX_FILES:
        raise ValueError('Bounded nonempty scene document views required')
    if any(type(item) is dict and type(item.get('kind')) is str
           and item['kind'] in _REGISTRY_KINDS for item in documents):
        return _resolve_mixed_registry_documents(documents,deadline=deadline,origins=origins)
    parsed={};pins={};catalogs={};raw_documents={};input_bytes=0;exposure=False
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
        elif kind in _REPORT_KINDS:
            from .puck_scene_reports import parse_puck_report_document
            value=parse_puck_report_document(payload,kind=kind)
        elif kind in _TRAINING_KINDS:
            from .puck_scene_training import parse_puck_training_document
            value=parse_puck_training_document(payload,kind=kind)
        else:value=parse_retained_puck_document(payload,kind=kind)
        parsed[path]=value
        raw_documents[path]=payload
        _clock(deadline)
    if origins is None:origins={}
    if type(origins) is not dict or any(path not in parsed for path in origins):
        raise ValueError('Reference origins must name registered documents')
    origins={_path(path):_path(cwd) for path,cwd in origins.items()}
    resolved=[];unresolved=[];missing=[];links={}
    reference_count=0

    def manifest_roster(path):
        roster=[]
        for ref in parsed[path]['references']:
            if ref['kind']!='recording_manifest':continue
            target=ref['path']
            if not target.startswith('/'):
                if path not in origins:return None
                target=str(PurePosixPath(origins[path])/target)
            roster.append((ref['scene_id'],ref['split'],target,ref['sha256']))
        return roster

    for path,value in sorted(parsed.items()):
        if pins[path]['kind']=='task_catalog':continue
        missing.extend({'document_path':path,'pointer':pointer} for pointer in value['missing_pins'])
        for ref in value['references']:
            _clock(deadline);reference_count+=1
            if reference_count>MAX_REFERENCES:raise ValueError('Reference count exceeds source ceiling')
            target=ref['path'];reason=None
            anchor=ref.get('path_base','recorded_cwd')
            if anchor not in ('recorded_cwd','document_directory'):
                raise ValueError('Unsupported retained reference anchor')
            if not target.startswith('/'):
                if anchor=='document_directory':target=str(PurePosixPath(path).parent/target)
                elif path not in origins:reason='relative_reference_without_recorded_cwd'
                else:target=str(PurePosixPath(origins[path])/target)
            if reason is None:
                _path(target)
                if ref['sha256'] is None:reason='missing_digest'
                elif target not in pins:reason='unregistered_target'
                elif pins[target]['sha256']!=ref['sha256']:reason='target_digest_differs'
                elif pins[target]['kind']!=ref['kind']:reason='target_kind_differs'
                elif 'size_bytes' in ref and pins[target]['size_bytes']!=ref['size_bytes']:
                    reason='target_byte_length_differs'
                elif 'expected_model_seed' in ref and (
                        type(json.loads(raw_documents[target]).get('training_seed')) is not int
                        or json.loads(raw_documents[target])['training_seed']!=ref['expected_model_seed']):
                    reason='target_model_seed_differs'
                elif ref['scene_id'] is not None and not any(
                        mention['scene_id']==ref['scene_id'] and mention['split']==ref['split']
                        for mention in parsed[target]['mentions']):reason='target_scene_differs'
                elif (report_reason:=_report_dependency_reason(
                        json.loads(raw_documents[path]),json.loads(raw_documents[target]),ref)):
                    reason=report_reason
                elif ref['kind'] in ('recording_manifest','owner_result') and 'expected_owner_id' not in ref:
                    parent=[mention for mention in value['mentions']
                            if mention['pointer'] in (ref['pointer']+'/seed',ref['pointer']+'/result/row/seed')]
                    children=[mention for mention in parsed[target]['mentions']
                              if mention['scene_id']==ref['scene_id'] and mention['split']==ref['split']]
                    if any(mention['catalog_sha256'] is not None
                           and any(child['catalog_sha256']!=mention['catalog_sha256'] for child in children)
                           for mention in parent):reason='target_catalog_pin_differs'
                elif ref['kind']=='teacher_collection_report':
                    parent_roster=manifest_roster(path);child_roster=manifest_roster(target)
                    if parent_roster is None or child_roster is None:
                        reason='collection_report_source_roster_unbound'
                    elif parent_roster!=child_roster:
                        reason='collection_report_source_roster_differs'
            record={'document_path':path,'pointer':ref['pointer'],'path':target,'sha256':ref['sha256']}
            if reason:unresolved.append(dict(record,reason=reason))
            else:
                resolved.append(record)
                links[path,ref['pointer'],ref['kind']]=target
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
        refs=[ref for ref in value['references'] if ref['kind'] in ('recording_manifest','owner_result')
              and mention['pointer']==ref['pointer']+'/seed'
              and ref['scene_id']==mention['scene_id'] and ref['split']==mention['split']]
        identities=[]
        for ref in refs:
            target=links.get((path,ref['pointer'],ref['kind']))
            if target is None:return None,'unresolved_manifest_reference'
            candidates=[item for item in parsed[target]['mentions']
                        if item['scene_id']==mention['scene_id'] and item['split']==mention['split']]
            if not candidates:return None,'target_scene_missing'
            for candidate in candidates:
                found,error=geometry(target,candidate,depth+1)
                if error:return None,error
                identities.append(found)
        # The parser already verifies this exact embedded owner row against the
        # report row. Its explicit student catalog pin may bind the outer roster.
        if not refs:
            embedded=[item for item in value['mentions']
                if item['pointer']==mention['pointer'].removesuffix('/seed')+'/result/row/seed'
                and item['scene_id']==mention['scene_id'] and item['split']==mention['split']]
            for candidate in embedded:
                found,error=geometry(path,candidate,depth+1)
                if error:return None,error
                identities.append(found)
        if not identities:return None,'missing_catalog_or_unique_manifest_reference'
        keys={tuple(found[0][field] for field in _FIELDS) for found in identities}
        if len(keys)!=1:return None,'target_identity_conflict'
        if len({found[1] for found in identities})!=1:
            return None,'target_catalog_identity_conflict'
        # Same digest/scene payload: retain all authentic copied catalog paths.
        return (identities[0][0],identities[0][1],
                sorted({source for found in identities for source in found[2]})),None

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


def resolve_puck_registry_documents(documents, *,deadline):
    """Bound registry references over supplied bytes; never publication admission.

    Layout-bearing rows are recomputed by the codec. Bare inventory hashes and
    historical stat tuples remain declarations. Digest references preserve every
    identical-content location; local publication names use the document parent.
    """
    from .puck_scene_registry import parse_puck_registry_document
    from . import puck_on_policy as policy
    _deadline(deadline)
    if type(documents) is not list or not 1<=len(documents)<=MAX_FILES:
        raise ValueError('Bounded nonempty registry document views required')
    parsed={};views={};pins={};by_digest={};input_bytes=0
    for item in documents:
        _clock(deadline)
        if type(item) is not dict or set(item)!={'path','kind','raw'}:
            raise ValueError('Exact registry document view fields required')
        path=_path(item['path']);kind=item['kind'];payload=item['raw']
        if path in parsed or type(kind) is not str or kind not in _REGISTRY_KINDS:
            raise ValueError('Duplicate or unsupported registry view')
        if not path.casefold().endswith('.json') or type(payload) is not bytes or not 0<len(payload)<=MAX_BYTES:
            raise ValueError('Bounded registry JSON bytes required')
        input_bytes+=len(payload)
        if input_bytes>MAX_TOTAL_BYTES:raise ValueError('Registry aggregate exceeds source ceiling')
        digest=hashlib.sha256(payload).hexdigest()
        pins[path]={'path':path,'kind':kind,'sha256':digest,'size_bytes':len(payload)}
        parsed[path]=parse_puck_registry_document(payload,kind=kind);views[path]=payload
        by_digest.setdefault((kind,digest),[]).append(path)
        _clock(deadline)
    resolved=[];unresolved=[];reference_count=0
    for path,value in sorted(parsed.items()):
        for ref in value['references']:
            _clock(deadline);reference_count+=1
            if reference_count>MAX_REFERENCES:raise ValueError('Registry references exceed source ceiling')
            reason=None;targets=[]
            if ref['path_base']=='content_digest':
                targets=sorted(by_digest.get((ref['kind'],ref['sha256']),[]))
                if not targets:reason='unregistered_content_digest'
            elif ref['path_base']=='document_directory':
                target=str(PurePosixPath(path).parent/ref['path'])
                _path(target)
                if target not in pins:reason='unregistered_target'
                elif pins[target]['kind']!=ref['kind']:reason='target_kind_differs'
                elif pins[target]['sha256']!=ref['sha256']:reason='target_digest_differs'
                else:targets=[target]
            else:raise ValueError('Unsupported registry reference anchor')
            record={'document_path':path,'pointer':ref['pointer'],'sha256':ref['sha256'],
                    'kind':ref['kind'],'relation':ref['relation'],'paths':targets}
            if reason:unresolved.append(dict(record,reason=reason));continue
            document=json.loads(views[path])
            try:
                for target in targets:
                    _clock(deadline)
                    if ref['relation']=='reservation' and pins[path]['kind']=='on_policy_scene_manifest':
                        policy._read_scene_manifest(views[path],views[target])
                    elif ref['relation']=='publication_target':
                        target_document=json.loads(views[target])
                        expected=policy._commit_receipt(document['target'],target_document,views[target])
                        if pins[path]['kind']=='on_policy_publication_commit':
                            if document!=expected:raise ValueError('Commit receipt content differs')
                        else:
                            for field in ('manifest_sha256','manifest_bytes','reservation_sha256','protocol_sha256'):
                                if document[field]!=expected[field]:raise ValueError('Admission target content differs')
                    elif ref['relation']=='commit_receipt':
                        commit=json.loads(views[target])
                        if document['receipt_bytes']!=len(views[target]):raise ValueError('Admission commit size differs')
                        for field in ('target','manifest_sha256','manifest_bytes','reservation_sha256','protocol_sha256'):
                            if document[field]!=commit[field]:raise ValueError('Admission/commit receipt content differs')
            except ValueError:
                unresolved.append(dict(record,reason='dependency_content_differs'))
            else:resolved.append(record)
    grouped={};unbound=[];unminted=[];count=0
    for path,value in sorted(parsed.items()):
        for scene in value['scenes']:
            _clock(deadline);count+=1
            if count>MAX_OCCURRENCES:raise ValueError('Registry occurrences exceed source ceiling')
            occurrence={'document_path':path,'document_sha256':pins[path]['sha256'],
                        'pointer':scene['pointer'],'scene_id':scene['scene_id'],
                        'split':scene['split'],'role':scene['role'],
                        'lineage_sha256':scene['lineage_sha256'],'layout_bound':scene['layout_bound']}
            if scene['role']=='self_reservation':unminted.append(occurrence)
            elif not scene['layout_bound']:
                unbound.append({**occurrence,**{field:scene[field] for field in _FIELDS}})
            else:
                identity=(scene['scene_id'],*(scene[field] for field in _FIELDS))
                if identity not in grouped:
                    if len(grouped)>=MAX_VARIANTS:raise ValueError('Registry variants exceed source ceiling')
                    grouped[identity]=[]
                grouped[identity].append(occurrence)
    variants=[];ids={};domains={field:{} for field in _FIELDS}
    for identity,occurrences in sorted(grouped.items()):
        _clock(deadline);index=len(variants)
        row=dict(zip(('scene_id',*_FIELDS),identity));row['occurrences']=occurrences
        variants.append(row);ids.setdefault(row['scene_id'],[]).append(index)
        for field in _FIELDS:domains[field].setdefault(row[field],[]).append(index)
    result={'kind':'puck-registry-reference-resolution-v1','version':1,
        'documents':[pins[path] for path in sorted(pins)],'variants':variants,
        'unbound_scene_declarations':unbound,'unminted_reservations':unminted,
        'id_variants':[{'scene_id':sid,'variant_indices':indices} for sid,indices in sorted(ids.items()) if len(indices)>1],
        'identity_aliases':[{'field':field,'sha256':digest,'variant_indices':indices} for field in _FIELDS
            for digest,indices in sorted(domains[field].items()) if len(indices)>1],
        'resolved_references':resolved,'unresolved_references':unresolved,
        'declared_registry_references_resolved':not unresolved,
        'historical_stat_declarations_authenticated':False,
        'inventory_complete':False,'source_closure_authenticated':False,
        'reservation_authorized':False,'collection_authorized':False,'executable':False,'qualification_claims':[]}
    _clock(deadline)
    if len(_canonical(result))>MAX_METADATA_BYTES:raise ValueError('Registry receipt exceeds source ceiling')
    _clock(deadline)
    return result


def _resolve_mixed_registry_documents(documents, *,deadline,origins):
    """Preserve old output semantics; registry evidence is explicitly scoped."""
    historical=[];registry=[];names=set();total=0
    for item in documents:
        _clock(deadline)
        if type(item) is not dict or set(item)!={'path','kind','raw'}:
            raise ValueError('Exact mixed document fields required')
        path=_path(item['path']);kind=item['kind'];payload=item['raw']
        if path in names or type(kind) is not str or kind not in _KINDS:
            raise ValueError('Ambiguous mixed document view')
        if type(payload) is not bytes or not 0<len(payload)<=MAX_BYTES:
            raise ValueError('Bounded mixed document bytes required')
        names.add(path);total+=len(payload)
        if total>MAX_TOTAL_BYTES:raise ValueError('Mixed input exceeds source ceiling')
        (registry if kind in _REGISTRY_KINDS else historical).append(item)
    if origins is None:origins={}
    if type(origins) is not dict or any(path not in names for path in origins):raise ValueError('Unregistered mixed document origin')
    origins={_path(path):_path(cwd) for path,cwd in origins.items()}
    if historical:
        result=resolve_retained_puck_documents(historical,deadline=deadline,
            origins={path:cwd for path,cwd in origins.items() if path in {item['path'] for item in historical}})
    else:
        result={'kind':'puck-retained-scene-resolution-v1','version':1,'documents':[],'variants':[],
            'resolved_references':[],'unresolved_references':[],'unresolved_mentions':[],'missing_pins':[],
            'declared_reference_closure_resolved':True,'held_out_catalog_read':False,
            'held_out_runtime_opened':False,'inventory_complete':False,'source_closure_authenticated':False,
            'reservation_authorized':False,'collection_authorized':False,'executable':False,'qualification_claims':[]}
    evidence=resolve_puck_registry_documents(registry,deadline=deadline)
    reference_count = sum(len(lane[key]) for lane in (result, evidence)
        for key in ('resolved_references', 'unresolved_references'))
    if reference_count > MAX_REFERENCES:
        raise ValueError('Mixed references exceed source ceiling')
    # Every declaration consumes the same occurrence allowance, including rows
    # that cannot bind geometry and intentional unminted reservations.
    count = (len(result['unresolved_mentions'])
        + len(evidence['unbound_scene_declarations'])
        + len(evidence['unminted_reservations']))
    if count > MAX_OCCURRENCES:
        raise ValueError('Mixed scene evidence exceeds source ceiling')
    result['registry']=evidence
    result['documents']=sorted(result['documents']+evidence['documents'],key=lambda row:row['path'])
    result['declared_reference_closure_resolved'] &= evidence['declared_registry_references_resolved'] and not evidence['unbound_scene_declarations']
    grouped={}
    for row in result['variants']+evidence['variants']:
        _clock(deadline);identity=(row['scene_id'],*(row[field] for field in _FIELDS))
        grouped.setdefault(identity,[]).extend(row['occurrences']);count+=len(row['occurrences'])
        if count>MAX_OCCURRENCES or len(grouped)>MAX_VARIANTS:raise ValueError('Mixed scene evidence exceeds source ceiling')
    variants=[];ids={};domains={field:{} for field in _FIELDS}
    for identity,occurrences in sorted(grouped.items()):
        _clock(deadline);index=len(variants)
        row=dict(zip(('scene_id',*_FIELDS),identity));row['occurrences']=sorted(occurrences,key=_canonical)
        variants.append(row);ids.setdefault(row['scene_id'],[]).append(index)
        for field in _FIELDS:domains[field].setdefault(row[field],[]).append(index)
    result['variants']=variants
    result['id_variants']=[{'scene_id':sid,'variant_indices':indices} for sid,indices in sorted(ids.items()) if len(indices)>1]
    result['identity_aliases']=[{'field':field,'sha256':digest,'variant_indices':indices} for field in _FIELDS
        for digest,indices in sorted(domains[field].items()) if len(indices)>1]
    result['legacy_scene_rows_compatible']=not result['id_variants'] and not result['identity_aliases']
    _clock(deadline)
    if len(_canonical(result))>MAX_METADATA_BYTES:raise ValueError('Mixed receipt exceeds source ceiling')
    _clock(deadline)
    return result
