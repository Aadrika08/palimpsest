"""Held declared-project inventory, historical isolation and collision projection.

This orchestrates existing operational custody. It does not qualify the installed
Git/Python/transport runtime, grant execution, or discover outside declared roots.
"""
import copy
import hashlib
import json
from pathlib import PurePosixPath
import posixpath
import re
import time

from . import puck_on_policy as policy
from .puck_execution_files import HeldCollectionFiles
from .puck_scene_roots import HeldSceneInventoryRoots, _json as root_json
from .puck_scene_git import HeldGitSceneSources
from .puck_scene_catalog import parse_task_catalog
from .puck_scene_reference_resolution import (
    resolve_retained_puck_documents, _KINDS, _FIELDS, _path, _deadline,
)
from .puck_scene_retained import _decode, _Inventory
from .puck_scene_markdown import parse_puck_markdown_document

MAX_REGISTRATION_BYTES = 1024**2
MAX_INPUTS = 512
MAX_DOCUMENT_BYTES = 4*1024**2
MAX_METADATA_BYTES = MAX_INPUT_BYTES = 64*1024**2
MAX_CONTEXTS = MAX_REFERENCES = MAX_VARIANTS = 4096
MAX_OCCURRENCES = 65536
_KIND = _KINDS | {'markdown','no_scene_json'}
_FIELDS_REG = {'id','version','root_contract','repositories','files','git_documents',
               'origins','retained_reference_roots','role_roots','prospective'}


def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()


def _sha(raw):return hashlib.sha256(raw).hexdigest()
def _under(path,root):return path==root or PurePosixPath(path).is_relative_to(root)


def _hash(value):
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}',value) is None:
        raise ValueError('Exact SHA256 required')
    return value


def _descriptor(row, *,git=False):
    fields={'repo','oid','kind','size_bytes','sha256'} if git else {'path','kind','size_bytes','sha256'}
    if type(row) is not dict or set(row)!=fields:
        raise ValueError('Exact inventory descriptor required')
    _path(row['repo'] if git else row['path'])
    if type(row['kind']) is not str or row['kind'] not in _KIND:
        raise ValueError('Unsupported inventory document schema')
    if type(row['size_bytes']) is not int or not 0<row['size_bytes']<=MAX_DOCUMENT_BYTES:
        raise ValueError('Bounded nonempty inventory payload required')
    _hash(row['sha256'])
    if git and (type(row['oid']) is not str or re.fullmatch('[0-9a-f]{40}|[0-9a-f]{64}',row['oid']) is None):
        raise ValueError('Exact Git object ID required')
    if not git and row['path'].casefold().endswith('.md')!=(row['kind']=='markdown'):
        raise ValueError('Inventory suffix/schema differs')
    if not git and not row['path'].casefold().endswith(('.json','.md')):
        raise ValueError('Inventory document suffix differs')


def _registration(raw, expected):
    if type(raw) is not bytes or not 0<len(raw)<=MAX_REGISTRATION_BYTES or _sha(raw)!=_hash(expected):
        raise ValueError('Externally hash-bound inventory registration required')
    doc=_decode(raw)
    if (_canonical(doc)!=raw or set(doc)!=_FIELDS_REG or doc['id']!='puck-scene-inventory-scope-v1'
            or type(doc['version']) is not int or doc['version']!=1):
        raise ValueError('Exact canonical inventory registration required')
    for key in ('repositories','files','git_documents','origins','retained_reference_roots','role_roots'):
        if type(doc[key]) is not list:raise ValueError('Bounded inventory registration lists required')
    if len(doc['repositories'])>32 or len(doc['files'])+len(doc['git_documents'])>MAX_INPUTS:
        raise ValueError('Inventory registration count exceeds shared ceiling')
    names=[];objects=[];repo_names=[];total=0
    for row in doc['files']:
        _descriptor(row);names.append(row['path']);total+=row['size_bytes']
    if names!=sorted(set(names)):raise ValueError('Sorted distinct registered files required')
    for row in doc['repositories']:
        if type(row) is not dict or set(row)!={'repo','remote','expected_remote_url'}:
            raise ValueError('Exact repository registration required')
        repo_names.append(_path(row['repo']))
    if len(set(repo_names))!=len(repo_names):raise ValueError('Duplicate repository provider')
    for row in doc['git_documents']:
        _descriptor(row,git=True);objects.append((row['repo'],row['oid']));total+=row['size_bytes']
        if row['repo'] not in repo_names:raise ValueError('Unregistered blob repository')
    if len(set(objects))!=len(objects) or total>MAX_INPUT_BYTES:
        raise ValueError('Inventory payload sum/identity exceeds shared ceiling')
    if len(doc['origins'])>MAX_INPUTS:raise ValueError('Origin count exceeds shared ceiling')
    origins={}
    for row in doc['origins']:
        if type(row) is not dict or set(row)!={'document_path','cwd'}:raise ValueError('Exact historical origin required')
        path=_path(row['document_path']);cwd=_path(row['cwd'])
        if path in origins:raise ValueError('Duplicate historical origin')
        origins[path]=cwd
    external=[]
    if len(doc['retained_reference_roots'])>32:raise ValueError('Too many retained reference roots')
    for path in doc['retained_reference_roots']:
        path=_path(path)
        if any(_under(path,old) or _under(old,path) for old in external):raise ValueError('Retained reference roots overlap')
        external.append(path)
    if len(doc['role_roots'])!=4 or {row.get('kind') for row in doc['role_roots'] if type(row) is dict}!=policy._INVENTORY_KINDS:
        raise ValueError('All four legacy root roles required')
    role_paths=[]
    for row in doc['role_roots']:
        if type(row) is not dict or set(row)!={'kind','path'}:raise ValueError('Exact root role required')
        role_paths.append(_path(row['path']))
    if len(set(role_paths))!=4:raise ValueError('Legacy role roots alias')
    future=doc['prospective']
    if (type(future) is not dict or set(future)!={'lineage_sha256','scene_ids'}
            or future['lineage_sha256']!=policy.PROTOCOL_SHA256
            or type(future['scene_ids']) is not list
            or policy._ids(future['scene_ids'],'prospective scenes',exact_length=8)!=policy.RESERVED_SCENE_IDS):
        raise ValueError('Exact hash-bound prospective lineage/roster required')
    return copy.deepcopy(doc),origins


class HeldPuckSceneInventory:
    def __init__(self, registration_raw, *,expected_sha256,deadline):
        _deadline(deadline)
        self._registration,self._origins=_registration(registration_raw,expected_sha256)
        self._digest=expected_sha256;self._deadline=deadline;self._state='new'
        self._children=[];self._providers=[];self._files=[];self._roots=None;self._receipt=None
        self._input_bytes=0;self._provider_metadata=0;self._contexts=[]

    def _clock(self):
        if time.monotonic()>=self._deadline:raise TimeoutError('Inventory deadline exhausted')

    def _active(self):
        if self._state!='active':raise RuntimeError('Inventory is inactive or poisoned')
        self._clock()

    def _enter(self,child):
        self._children.append(child);return child.__enter__()

    def _close(self,primary=None):
        errors=[]
        for child in reversed(self._children):
            try:child.__exit__(type(primary) if primary else None,primary,None)
            except BaseException as error:
                if primary is not None:primary.add_note('Inventory child close: '+str(error))
                else:errors.append(error);primary=error
        self._children.clear();self._state='failed' if primary else 'closed'
        if errors:raise errors[0]

    def _retain(self, payload):
        self._clock();self._input_bytes+=len(payload)
        if self._input_bytes>MAX_INPUT_BYTES:raise ValueError('Shared inventory byte ceiling exceeded')

    def _budget(self, extra=0):
        self._clock()
        size=sum(child.retained_metadata_size_bytes() for child in [self._roots,*self._providers,*self._files])
        size+=len(_canonical(self._registration))+len(_canonical(self._contexts))
        size+=len(_canonical(self._root_receipt))
        if self._receipt is not None:size+=len(_canonical(self._receipt))
        if size+extra>MAX_METADATA_BYTES:raise ValueError('Shared inventory metadata ceiling exceeded')

    def __enter__(self):
        if self._state!='new':
            error=RuntimeError('Inventory cannot be reused');self._close(error);raise error
        try:
            self._clock();root_raw=root_json(self._registration['root_contract'])
            self._roots=self._enter(HeldSceneInventoryRoots(root_raw,expected_sha256=_sha(root_raw),deadline=self._deadline))
            self._root_receipt=self._roots.snapshot()
            if self._root_receipt['excluded_scope'] or self._root_receipt['unsupported_git_candidates']:
                raise ValueError('Uncovered opaque or unsupported Git scope')
            census={row['path']:row for row in self._root_receipt['document_candidates']}
            declarations={row['path']:row for row in self._registration['files']}
            if set(census)!=set(declarations):raise ValueError('Exact live document census does not match registration')
            inodes=set()
            for path,row in census.items():
                if row['size_bytes']!=declarations[path]['size_bytes']:raise ValueError('Census/registered payload size differs')
                identity=tuple(row['stat_identity'][:2])
                if identity in inodes:raise ValueError('Selected document inode alias')
                inodes.add(identity)
            observed={row['path'] for row in self._root_receipt['observed_directories']}
            if any(path not in observed for path in self._registration['retained_reference_roots']):
                raise ValueError('Retained reference root is outside observed scope')
            classifiers={(row['repo'],row['oid']):row for row in self._registration['git_documents']}
            covered=set();common=set();snapshots=[]
            for entry in self._registration['repositories']:
                if entry['repo'] not in {row['path'] for row in self._root_receipt['repository_candidates']}:
                    raise ValueError('Registered repository was not discovered')
                provider=self._enter(HeldGitSceneSources(**entry,deadline=self._deadline));self._providers.append(provider)
                evidence=provider.snapshot()
                expected={(provider.repo,row['oid']) for row in evidence['blobs']}
                actual={key for key in classifiers if key[0]==provider.repo}
                if expected!=actual:raise ValueError('Exact historical blob classification coverage differs')
                for blob in evidence['blobs']:
                    if classifiers[provider.repo,blob['oid']]['size_bytes']!=blob['size_bytes']:
                        raise ValueError('Git descriptor/registered size differs')
                for attachment in evidence['documents']:
                    entry=classifiers[provider.repo,attachment['oid']]
                    if attachment['path'].casefold().endswith('.md')!=(entry['kind']=='markdown'):
                        raise ValueError('Historical document suffix/schema differs')
                if evidence['common_git_dir'] in common:raise ValueError('Repeated common Git provider namespace')
                common.add(evidence['common_git_dir'])
                for workspace in evidence['worktrees']:
                    if workspace['path'] not in observed:raise ValueError('Registered worktree outside declared project scope')
                    covered.add(workspace['path'])
                snapshots.append(evidence);self._budget()
            found={row['path'] for row in self._root_receipt['repository_candidates']}
            if found!=covered:raise ValueError('Repository/worktree coverage differs')
            for row in self._registration['role_roots']:
                if row['path'] not in observed|common:raise ValueError('Legacy role root is outside authenticated scope')
            live=[]
            for root in self._registration['root_contract']['search_roots']:
                rows=[row for row in self._registration['files'] if _under(row['path'],root)]
                if not rows:continue
                entries=[{'path':str(PurePosixPath(row['path']).relative_to(root)),
                    'size_bytes':row['size_bytes'],'sha256':row['sha256']} for row in rows]
                holder=self._enter(HeldCollectionFiles(root,sorted(entries,key=lambda r:r['path']),self._deadline));self._files.append(holder)
                for row in rows:
                    payload=holder.read(str(PurePosixPath(row['path']).relative_to(root)),MAX_DOCUMENT_BYTES)
                    self._retain(payload);live.append({'path':row['path'],'kind':row['kind'],'raw':payload})
            used_origins=set(self._origins)&{doc['path'] for doc in live}
            results=[self._semantic(live,{'kind':'filesystem'})]
            external=[doc for doc in live if any(_under(doc['path'],root) for root in self._registration['retained_reference_roots'])]
            for provider,evidence in zip(self._providers,snapshots):
                expected={(provider.repo,row['oid']) for row in evidence['blobs']}
                actual={key for key in classifiers if key[0]==provider.repo}
                if expected!=actual:raise ValueError('Exact historical blob classification coverage differs')
                cache={};commits={}
                for attachment in evidence['documents']:
                    self._clock();key=(provider.repo,attachment['oid']);entry=classifiers[key]
                    if attachment['oid'] not in cache:
                        context=provider.read_document(attachment['commit'],attachment['path'],expected_oid=attachment['oid'])
                        payload=context['raw']
                        if len(payload)!=entry['size_bytes'] or _sha(payload)!=entry['sha256']:
                            raise ValueError('Registered Git payload pin differs')
                        self._retain(payload);cache[attachment['oid']]=payload
                    path=str(PurePosixPath(provider.repo)/attachment['path'])
                    if path.casefold().endswith('.md')!=(entry['kind']=='markdown'):
                        raise ValueError('Historical document suffix/schema differs')
                    commits.setdefault((attachment['commit'],attachment['root_tree']),[]).append(
                        {'path':path,'kind':entry['kind'],'raw':cache[attachment['oid']]})
                for (commit,tree),documents in sorted(commits.items()):
                    if len(results)>=MAX_CONTEXTS:raise ValueError('Inventory context ceiling exceeded')
                    names={doc['path'] for doc in documents}
                    if any(doc['path'] in names for doc in external):raise ValueError('Historical/retained namespaces overlap')
                    used_origins|=set(self._origins)&(names|{doc['path'] for doc in external})
                    results.append(self._semantic(documents+external,{'kind':'git','repo':provider.repo,
                        'common_git_dir':evidence['common_git_dir'],'commit':commit,'root_tree':tree,'object_format':evidence['object_format']}))
                    self._budget()
            if used_origins!=set(self._origins):raise ValueError('Unregistered historical origin')
            snapshots=[provider.snapshot() for provider in self._providers]
            self._assemble(results,snapshots)
            self._state='active';self.recheck();return self
        except BaseException as error:self._close(error);raise

    def _semantic(self,documents,context):
        self._clock()
        if len(documents)>MAX_INPUTS:raise ValueError('Context selected input count exceeds shared ceiling')
        json_docs=[];markdown={};pins={};catalogs=[];blockers=[];variants=[]
        for doc in documents:
            self._clock();path=doc['path'];payload=doc['raw']
            if path in pins:raise ValueError('Ambiguous inventory context paths')
            pins[path]={'sha256':_sha(payload),'size_bytes':len(payload),'kind':doc['kind']}
            if doc['kind']=='markdown':
                parsed=parse_puck_markdown_document(payload);markdown[path]=parsed
                blockers.extend({'document_path':path,**row} for row in parsed['unsupported_declarations'])
                # Embedded JSON is independently classified by strict known
                # discriminators; it never gets treated as an empty free-form doc.
                for index,fence in enumerate(parsed['embedded_json']):
                    body=fence['value'];kind=self._embedded_kind(body)
                    if kind is None:
                        blockers.append({'document_path':path,'pointer':fence['pointer'],'reason':'unsupported_embedded_schema'})
                    else:
                        embedded_path=path+'/__markdown__/'+str(index)+'.json'
                        json_docs.append({'path':embedded_path,'kind':kind,'raw':fence['raw']})
                        pins[embedded_path]={'sha256':fence['sha256'],'size_bytes':len(fence['raw']),'kind':kind,
                            'markdown_source':path,'markdown_pointer':fence['pointer']}
            elif doc['kind']=='no_scene_json':
                body=_decode(payload)
                if any(type(body.get(key)) is str and body[key].startswith(('puck-','m6-puck-')) for key in ('schema','kind','id')):
                    raise ValueError('Known puck schema cannot be classified scene-free')
                _Inventory(body,'no_scene_json',payload).reject_untyped()
            else:json_docs.append(doc)
        if len(json_docs)>MAX_INPUTS:raise ValueError('Expanded context input count exceeds shared ceiling')
        json_result=resolve_retained_puck_documents(json_docs,deadline=self._deadline,
            origins={path:cwd for path,cwd in self._origins.items() if path in {doc['path'] for doc in json_docs}}) if json_docs else None
        json_references=0;unresolved_occurrences=0
        if json_result is not None:
            registry=json_result.get('registry',{})
            json_references=sum(len(lane.get(key,[])) for lane in (json_result,registry)
                for key in ('resolved_references','unresolved_references'))
            unresolved_occurrences=(len(json_result['unresolved_mentions'])
                +len(registry.get('unbound_scene_declarations',[]))+len(registry.get('unminted_reservations',[])))
            variants.extend(json_result['variants'])
            if not json_result['declared_reference_closure_resolved']:
                blockers.append({'reason':'unresolved_json_semantics','evidence':{
                    key:json_result[key] for key in ('unresolved_references','unresolved_mentions','missing_pins')}|
                    {'registry':registry}})
            for doc in json_docs:
                if doc['kind']!='task_catalog':continue
                catalog=parse_task_catalog(doc['raw']);catalogs.append((doc['path'],catalog))
                for scene in catalog['scenes']:
                    variants.append({key:scene[key] for key in ('scene_id',*_FIELDS)}|{'occurrences':[
                        {'document_path':doc['path'],'document_sha256':catalog['document_sha256'],
                         'pointer':scene['pointer'],'split':scene['split'],'catalog_sha256':catalog['document_sha256']}]})
        link_targets={};md_links=[]
        for path,parsed in sorted(markdown.items()):
            for reference in parsed['references']:
                self._clock();target=reference['path'].partition('#')[0]
                if not target.startswith('/'):
                    if reference['path_base']=='document_directory':target=posixpath.normpath(posixpath.join(str(PurePosixPath(path).parent),target))
                    elif path in self._origins:target=posixpath.normpath(posixpath.join(self._origins[path],target))
                    else:
                        blockers.append({'document_path':path,'pointer':reference['pointer'],'reason':'unbound_markdown_origin'});continue
                target=_path(target);pin=pins.get(target)
                if pin is None or reference['sha256'] is not None and reference['sha256']!=pin['sha256']:
                    blockers.append({'document_path':path,'pointer':reference['pointer'],'reason':'unresolved_markdown_reference'});continue
                md_links.append({'document_path':path,'pointer':reference['pointer'],'path':target,
                    'declared_sha256':reference['sha256'],'bound_sha256':pin['sha256'],'binding':'authenticated_context_namespace'})
                link_targets.setdefault(path,[]).append(target)
        def geometry(path,mention,seen=()):
            self._clock()
            if path in seen or len(seen)>=16:return []
            digest=mention['catalog_sha256'];found=[]
            if digest is not None:
                for catalog_path,catalog in catalogs:
                    if catalog['document_sha256']!=digest:continue
                    for scene in catalog['scenes']:
                        if scene['scene_id']==mention['scene_id'] and (mention['split'] is None or scene['split']==mention['split']):
                            found.append({key:scene[key] for key in ('scene_id',*_FIELDS)}|{'sources':[catalog_path]})
                return found
            for target in link_targets.get(path,[]):
                if target in markdown:
                    for child in markdown[target]['mentions']:
                        if child['scene_id']==mention['scene_id'] and (mention['split'] is None or child['split'] in (None,mention['split'])):
                            found.extend(geometry(target,child,seen+(path,)))
                else:
                    for variant in variants:
                        if variant['scene_id']!=mention['scene_id']:continue
                        occurrences=[row for row in variant['occurrences'] if row['document_path']==target
                            and (mention['split'] is None or row.get('split')==mention['split'])]
                        if occurrences:found.append({key:variant[key] for key in ('scene_id',*_FIELDS)}|{'sources':[target]})
            return found
        md_variants=[];md_unresolved_occurrences=0
        for path,parsed in sorted(markdown.items()):
            for mention in parsed['mentions']:
                found=geometry(path,mention)
                identities={tuple(row[key] for key in ('scene_id',*_FIELDS)) for row in found}
                if mention['geometry_claims'] or len(identities)!=1:
                    md_unresolved_occurrences+=1
                    blockers.append({'document_path':path,'pointer':mention['pointer'],'reason':'unbound_or_ambiguous_markdown_scene'});continue
                identity=next(iter(identities))
                md_variants.append(dict(zip(('scene_id',*_FIELDS),identity))|{'occurrences':[
                    {'document_path':path,'document_sha256':parsed['document_sha256'],'pointer':mention['pointer'],
                     'split':mention['split'],'identity_sources':sorted({source for row in found for source in row['sources']})}]})
        variants.extend(md_variants)
        for variant in variants:
            variant['occurrences']=[{**row,'context':context} for row in variant['occurrences']]
        result={'context':context,'documents':[{'path':path,**pin} for path,pin in sorted(pins.items())],
            'variants':variants,'blockers':blockers,'markdown_references':md_links,
            'reference_count':json_references+sum(len(parsed['references']) for parsed in markdown.values()),
            'unresolved_occurrence_count':unresolved_occurrences+md_unresolved_occurrences,
            'held_out_catalog_read':any(catalog['held_out_catalog_read'] for _,catalog in catalogs),
            'unminted_prior_reservations':json_result.get('registry',{}).get('unminted_reservations',[]) if json_result else []}
        self._contexts.append(result);self._budget();return result

    def _embedded_kind(self,body):
        identifier=body.get('id');kind=body.get('kind');schema=body.get('schema')
        if type(identifier) is str and re.fullmatch('m6-puck-pushing-plan-v[1-5]',identifier):return 'task_catalog'
        registry={'puck-on-policy-reservation-v1':'on_policy_reservation','puck-on-policy-scene-manifest-v1':'on_policy_scene_manifest',
            'puck-on-policy-collection-projection-v1':'on_policy_collection_projection','puck-on-policy-publication-commit-v1':'on_policy_publication_commit',
            'puck-on-policy-publication-admission-v1':'on_policy_publication_admission'}
        if type(kind) is str and kind in registry:return registry[kind]
        if type(schema) is str:
            if schema in ('puck-training-v1','puck-balanced-training-v1'):return 'training_protocol'
            if schema in ('puck-mechanics-v2','puck-demonstration-v1','puck-student-v1','puck-balanced-student-v1',
                'puck-student-development-v1','puck-balanced-student-development-v1'):return 'recording_manifest'
        return None

    def _assemble(self,results,snapshots):
        grouped={};count=0;references=0;blockers=[];exposure=False
        for result in results:
            blockers.extend({'context':result['context'],**row} for row in result['blockers'])
            if result['unminted_prior_reservations']:blockers.append({'context':result['context'],'reason':'historical_self_reservation_not_current_lineage'})
            exposure|=result['held_out_catalog_read'];references+=result['reference_count']
            count+=result['unresolved_occurrence_count']
            if count>MAX_OCCURRENCES:raise ValueError('Shared inventory occurrence ceiling exceeded')
            if references>MAX_REFERENCES:raise ValueError('Shared inventory reference ceiling exceeded')
            for variant in result['variants']:
                identity=tuple(variant[key] for key in ('scene_id',*_FIELDS))
                grouped.setdefault(identity,[]).extend(variant['occurrences']);count+=len(variant['occurrences'])
                if len(grouped)>MAX_VARIANTS or count>MAX_OCCURRENCES:raise ValueError('Shared inventory occurrence ceiling exceeded')
        variants=[];ids={};domains={key:{} for key in _FIELDS}
        for identity,occurrences in sorted(grouped.items()):
            index=len(variants);row=dict(zip(('scene_id',*_FIELDS),identity));row['occurrences']=sorted(occurrences,key=_canonical)
            variants.append(row);ids.setdefault(row['scene_id'],[]).append(index)
            for key in _FIELDS:domains[key].setdefault(row[key],[]).append(index)
        id_variants=[{'scene_id':key,'variant_indices':indices} for key,indices in sorted(ids.items()) if len(indices)>1]
        aliases=[{'field':key,'sha256':digest,'variant_indices':indices} for key in _FIELDS
            for digest,indices in sorted(domains[key].items()) if len(indices)>1]
        self._receipt={'id':'puck-held-inventory-scope-receipt-v1','version':1,'registration_sha256':self._digest,
            'declared_scope_covered':True,'semantic_closure_resolved':not blockers,'coverage_domain':'exact externally registered project roots',
            'root_evidence':self._root_receipt,'repository_evidence':snapshots,'contexts':results,
            'variants':variants,'id_variants':id_variants,'identity_aliases':aliases,'blockers':blockers,
            'held_out_catalog_read':exposure,'held_out_runtime_opened':False,'inventory_complete':False,
            'source_closure_authenticated':False,'runtime_qualified':False,'reservation_authorized':False,
            'collection_authorized':False,'executable':False,'qualification_claims':[]}
        self._budget()

    def recheck(self):
        try:
            self._active()
            for child in self._children:child.recheck()
            self._budget();self._clock()
        except BaseException as error:self._close(error);raise

    def snapshot(self):
        try:
            self.recheck();result=copy.deepcopy(self._receipt);self._budget(len(_canonical(result)));self.recheck();return result
        except BaseException as error:self._close(error);raise

    def legacy_projection(self):
        try:
            self.recheck();receipt=self._receipt
            if (not receipt['semantic_closure_resolved'] or receipt['id_variants'] or receipt['identity_aliases']
                    or receipt['held_out_catalog_read']):raise ValueError('Inventory is not representable by the legacy collision schema')
            roots=[];records=[]
            identity=_sha(_canonical(receipt))
            for row in sorted(self._registration['role_roots'],key=lambda r:r['kind']):
                roots.append({'kind':row['kind'],'path':row['path'],'resolved_path':row['path'],
                    'exists':True,'readable':True,'is_directory':True,'is_symlink':False,'identity_sha256':identity})
                records.append({'kind':row['kind'],'name':'authenticated-declared-scope-'+row['kind'],'root':row['path'],
                    'identity_sha256':identity,'role':'prior','lineage_sha256':None,'scenes':[],
                    'metadata':{'evidence_sha256':identity,'occurrence_count':0}})
            destination=next(row for row in records if row['kind']=='manifest')
            destination['scenes']=[{key:row[key] for key in ('scene_id',*_FIELDS)} for row in receipt['variants']]
            destination['metadata']['occurrence_count']=sum(len(row['occurrences']) for row in receipt['variants'])
            role=next(row for row in roots if row['kind']=='manifest');prospective=self._registration['prospective']
            records.append({'kind':'manifest','name':'current-prospective-lineage','root':role['path'],
                'identity_sha256':_sha(_canonical(prospective)),'role':'self_reservation','lineage_sha256':prospective['lineage_sha256'],
                'scenes':[{'scene_id':scene,**dict.fromkeys(_FIELDS)} for scene in prospective['scene_ids']],
                'metadata':{'declaration_sha256':_sha(_canonical(prospective))}})
            result={'version':1,'complete':True,'remote_refs_fresh':True,'held_out_accessed':False,'roots':roots,'records':records}
            policy._validate_inventory(result,prospective['lineage_sha256']);self.recheck();return copy.deepcopy(result)
        except BaseException as error:self._close(error);raise

    def __exit__(self,exc_type,exc,traceback):
        if exc is not None:
            try:
                if self._state=='active':self.recheck()
            except BaseException as error:exc.add_note('Inventory final check: '+str(error))
            self._close(exc);return False
        if self._state!='active':
            error=RuntimeError('Failed inventory cannot close successfully');self._close(error);raise error
        try:self.recheck();self._close();self._clock()
        except BaseException as error:self._close(error);raise
