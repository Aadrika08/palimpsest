import copy
import pytest
from scripts import memory_family_source_records_vnext as records


def test_concrete_roster_is_exact336_sorted_unique():
    rows = records.output_roster('case', '00000000-0000-4000-8000-000000000001')
    assert len(rows) == 336
    assert rows == sorted(rows, key=lambda row: (row['role'], row['path']))
    assert len({row['path'] for row in rows}) == 336
    assert len({row['role'] for row in rows}) == 336
    assert sum(row['path'].endswith('.pending') for row in rows) == 128
    assert sum(row['path'].endswith('.tmp') for row in rows) == 39
    assert not any('*.npz' in row['path'] for row in rows)


@pytest.mark.parametrize('raw', [b'{"a":1,"a":1}', b'{ "a":1}', b'{"a":NaN}', b'{"a":true}\n'])
def test_wire_rejects_noncanonical_duplicate_nonfinite(raw):
    with pytest.raises(ValueError): records.decode(raw)


def test_wire_depth_and_bool_integer():
    with pytest.raises(ValueError): records.integer(True, 0, 2)
    value = None
    for _ in range(34): value = [value]
    with pytest.raises(ValueError): records.encode(value)


def test_claims_integer_zero_cannot_impersonate_false():
    value=dict(schema=records.record_schema('owner'),claims=dict(records.CLAIMS,go_authorized=0))
    with pytest.raises(ValueError): records.schema(value,'owner')


@pytest.mark.parametrize('bad',['actual-schema','authority','external','fixture','claims-int','extra'])
def test_authored_namespace_refuses_authority_or_path_or_domain_confusion(bad):
    root='/var/tmp/source-vertical-wire/attempt'
    d=lambda path:dict(path=path,size_bytes=1,sha256='1'*64)
    value=dict(schema=records.record_schema('namespace-export-binding',True),purpose='training-namespace',fixture_id='fixture',coverage_contract=d(root+'/freeze/metadata/authored-namespace-coverage.json'),root=root+'/freeze/namespaces/training-namespace',export=d(root+'/freeze/namespaces/training-namespace/namespace-export.json'),scope='software-unit-only',claims=records.CLAIMS.copy())
    assert records._validate_authored_namespace_binding(value,'fixture',root)==value
    if bad=='actual-schema': value['schema']=records.record_schema('namespace-export-binding')
    elif bad=='authority': value['authority_reference']=d('/external/authority')
    elif bad=='external': value['root']='/external'
    elif bad=='fixture': value['fixture_id']='other'
    elif bad=='claims-int': value['claims']['allocation_authorized']=0
    else: value['unknown']=None
    with pytest.raises(ValueError): records._validate_authored_namespace_binding(value,'fixture',root)


def actual_coverage_metadata():
    expected=dict(entries=1,files=1,bytes=1,inventory_sha256='1'*64,export_bytes=1,export_sha256='2'*64)
    for name in ('known_sources','historical_run_ids','historical_authored_ids','training_seeds'):
        expected[name+'_count']=1 if name=='known_sources' else 0; expected[name+'_sha256']='3'*64
    return dict(schema='memory-family-namespace-coverage-v3',coverage_status='resolved',allocation_authorized=True,reason=None,source_ids=['pre-heldout-development-history','training-namespace'],export_schema='memory-family-namespace-export-v3',file_allowlist=['namespace-export.json'],sources=[dict(source_id=source,kind=kind,expected=copy.deepcopy(expected)) for source,kind in [('pre-heldout-development-history','historical'),('training-namespace','training')]],max_identity_characters=128,max_metadata_bytes=33554432,max_values=100000)


@pytest.mark.parametrize('defect',['third','kind','extra','bool','large','expected-extra','expected-bool','bad-hash'])
def test_fix1_actual_coverage_metadata_refuses_before_any_payload(defect,monkeypatch):
    from scripts import memory_source_parent_entry_vnext as parent
    value=actual_coverage_metadata()
    accepted=records._validate_actual_namespace_coverage(copy.deepcopy(value))
    assert accepted==value and accepted is not value
    if defect=='third': value['sources'].append(copy.deepcopy(value['sources'][0]))
    elif defect=='kind': value['sources'][0]['kind']='training'
    elif defect=='extra': value['sources'][0]['extra']=True
    elif defect=='bool': value['max_values']=True
    elif defect=='large': value['max_metadata_bytes']=33554433
    elif defect=='expected-extra': value['sources'][1]['expected']['extra']=0
    elif defect=='expected-bool': value['sources'][0]['expected']['entries']=True
    else: value['sources'][0]['expected']['export_sha256']='BAD'
    def forbidden(*args,**kwargs): pytest.fail('Metadata validator opened a payload')
    monkeypatch.setattr(parent.RuntimeHandle,'__enter__',forbidden)
    monkeypatch.setattr(parent.os,'open',forbidden)
    with pytest.raises(ValueError): records._validate_actual_namespace_coverage(value)
