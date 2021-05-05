import itertools

import jsonschema.exceptions
import pytest

from data_as_code._metadata import (
    Metadata, _Meta
)
from tests.cases import valid, meta_cases, meta_cases2, Case


class BaseMetaTester(_Meta):
    def _meta_dict(self):  # overwrite to avoid stub exception
        return {}


def test_meta_dict_stub():
    """ Ensure that stub method will raise exception if not redefined """
    with pytest.raises(Exception):
        _Meta()._meta_dict()


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
        assert BaseMetaTester(lineage=list(perm)).prep_lineage() == expected


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
