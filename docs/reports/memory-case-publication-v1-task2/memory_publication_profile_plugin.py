"""Explicit authored current-profile semantic regression harness, not qualification."""
import pytest
from test_memory_family_case_publication_v1 import _authored_current_profile
@pytest.fixture(scope='module',autouse=True)
def prospective_profile_for_affected_authored_tests(request,tmp_path_factory):
    if request.module.__name__ != 'test_memory_family_case_publication_v1':
        patch=pytest.MonkeyPatch();request.addfinalizer(patch.undo)
        _authored_current_profile(tmp_path_factory.mktemp('authored-profile'),patch,request)
