import pytest
from scripts import memory_family_source_raw_audit_vnext as audit


def test_auditor_rejects_foreign_before_read():
    with pytest.raises(TypeError): audit.audit_source({},None,object())
