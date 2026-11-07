import pytest
from scripts import memory_family_source_qualifier_vnext as qualifier


def test_qualifier_refuses_foreign_before_load():
    with pytest.raises(TypeError): qualifier.qualify_source({},None,object())
