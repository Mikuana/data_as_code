import itertools

import jsonschema.exceptions
import pytest

from data_as_code._metadata import (
    Metadata, _Meta, Codified, Incidental
)
from tests.cases import valid, meta_cases, meta_cases2, Case


def test_meta_dict_stub():
    """ Ensure that stub method will raise exception if not redefined """
    with pytest.raises(Exception):
        _Meta().to_dict()


@pytest.mark.parametrize('metadata', meta_cases)
def test_dict_maker(metadata):
    assert isinstance(metadata.to_dict(), dict)


def test_base_lineage_prep():
    """ lineage should be consistently sorted by fingerprint """

    class Prep(_Meta):
        # noinspection PyMissingConstructor
        def __init__(self, x: str):
            self.ex = x

        def fingerprint(self) -> str:  # overload fingerprint method
            return self.ex.rjust(8, '0')

    lineage = [Prep(str(x)) for x in range(3)]
    expected = [x.fingerprint() for x in lineage]
    for perm in itertools.permutations(lineage):
        assert _Meta(lineage=list(perm)).prep_lineage() == expected


def test_empty_metadata():
    with pytest.raises(jsonschema.exceptions.ValidationError):
        Metadata.from_dict({})


@pytest.mark.parametrize('case', valid, ids=[x.label for x in valid])
def test_from_dict(case):
    assert isinstance(
        Metadata.from_dict(case.meta), Metadata
    ), "cant load lineage from dictionary"


@pytest.mark.parametrize('case', valid, ids=[x.label for x in valid])
def test_to_dict(case):
    lc = Metadata.from_dict(case.meta)
    assert isinstance(lc.to_dict(), dict), "cant unload lineage to dictionary"


@pytest.mark.parametrize('case', valid, ids=[x.label for x in valid])
def test_lineage_consistency(case):
    m = Metadata.from_dict(case.meta)
    x2 = m.to_dict()
    assert case.meta == x2, "lineage inconsistent between import/export"


@pytest.mark.parametrize('case', meta_cases2, ids=[x.label for x in meta_cases2])
def test_expected_errors(case: Case):
    with pytest.raises(case.error):
        m = Metadata.from_dict(case.meta)
        m.to_dict()


def test_fingerprint():
    c = Codified('x')
    assert c.to_dict()['fingerprint'] == c.fingerprint()


def test_fingerprint_empty():
    """ Raise exception when trying to fingerprint empty dict """
    m = _Meta()
    with pytest.raises(Exception):
        m._fingerprinter({})


def test_fingerprint_a_fingerprint():
    """ Raise exception when trying to fingerprint a fingerprint """
    m = _Meta()
    with pytest.raises(Exception):
        m._fingerprinter(dict(fingerprint='abcd1234'))


@pytest.mark.parametrize('kwargs', [
    {'x': 1, 'y': 2, 'z': 3},
    {'path': 'abc.txt', 'y': 2, 'usage': 'this', 'z': 3},
    {'path': 'abc.txt', 'z': 3, 'usage': 'this', 'directory': 'folder'}
])
def test_incidental_consistency(kwargs):
    """
    Incidental metadata results in identical dictionary

    Regardless of provided ordered, or mixture of expected versus unexpected
    keywords. All unexpected keywords should be incorporated
    """
    comp = Incidental(**kwargs).to_dict()
    assert all([x in kwargs.keys() for x in comp])
    for perm in itertools.permutations(kwargs):
        new_kwargs = {k: kwargs[k] for k in perm}
        assert Incidental(**new_kwargs).to_dict() == comp
