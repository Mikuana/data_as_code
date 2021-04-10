import itertools
import re

import pytest

from data_as_code._metadata import Metadata, _Meta
from data_as_code.exceptions import InvalidMetadata
from tests.cases import valid_cases, c1


class BaseMetaTester(_Meta):
    def _meta_dict(self):  # overwrite to avoid stub exception
        return {}


def test_meta_dict_stub():
    """ Ensure that stub method will raise exception if not redefined """
    with pytest.raises(Exception):
        _Meta()._meta_dict()


def test_fingerprinter():
    """ fingerprint should look like first 8 characters of an md5 """
    assert re.match(r'[a-f0-9]{8}', BaseMetaTester().fingerprint())


@pytest.mark.parametrize('x', ['abcd1234', None])
def test_fingerprint_param(x):
    """
    If a fingerprint is provided, it should be retained. Otherwise it should be
    calculated from the dictionary.
    """
    m = BaseMetaTester(x)
    assert m.fingerprint == x or m.fingerprint()


def test_dict_maker():
    m = BaseMetaTester()
    assert m.to_dict() == {'fingerprint': m.fingerprint()}


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
    with pytest.raises(InvalidMetadata):
        Metadata.from_dict(c1[0])


@pytest.mark.parametrize('x,doc', valid_cases)
def test_from_dict(x, doc):
    assert isinstance(Metadata.from_dict(x), Metadata), "cant load lineage from dictionary"


@pytest.mark.parametrize('x,doc', valid_cases)
def test_to_dict(x, doc):
    lc = Metadata.from_dict(x)
    assert isinstance(lc.to_dict(), dict), "cant unload lineage to dictionary"


@pytest.mark.parametrize('x,doc', valid_cases)
def test_lineage_consistency(x, doc):
    l1 = Metadata.from_dict(x)
    x2 = l1.to_dict()
    assert x == x2, "lineage inconsistent between import/export"
