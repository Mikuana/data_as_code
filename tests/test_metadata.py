import re

import pytest

from data_as_code._metadata import Metadata, _Meta
from data_as_code.exceptions import InvalidMetadata
from tests.cases import valid_cases, empty


class BaseMetaTester(_Meta):
    def _meta_dict(self):  # overwrite to avoid stub exception
        return {}


def test_meta_dict_stub():
    """ Ensure that stub method will raise exception if not redefined """
    with pytest.raises(Exception):
        _Meta()._meta_dict()


def test_fingerprinter():
    """ fingerprint should look like first 8 characters of an md5 """
    assert re.match(r'[a-f0-9]{8}', BaseMetaTester().calculate_fingerprint())


@pytest.mark.parametrize('x', ['abcd1234', None])
def test_fingerprint_param(x):
    """
    If a fingerprint is provided, it should be retained. Otherwise it should be
    calculated from the dictionary.
    """
    m = BaseMetaTester(x)
    assert m.fingerprint == x or m.calculate_fingerprint()


def test_dict_maker():
    m = BaseMetaTester()
    assert m.to_dict() == {'fingerprint': m.fingerprint}


def test_base_lineage_prep():
    """ lineage should be consistently sorted by fingerprint """
    l1 = BaseMetaTester('00000001')
    l2 = BaseMetaTester('00000002')
    l3 = BaseMetaTester('00000003')
    l4 = BaseMetaTester('00000004')
    expected = [x.fingerprint for x in (l1, l2, l3, l4)]

    assert BaseMetaTester(lineage=[l1, l2, l3, l4]).prep_lineage() == expected
    assert BaseMetaTester(lineage=[l2, l1, l3, l4]).prep_lineage() == expected
    assert BaseMetaTester(lineage=[l3, l2, l1, l4]).prep_lineage() == expected
    assert BaseMetaTester(lineage=[l1, l4, l3, l2]).prep_lineage() == expected

# def test_empty_metadata():
#     with pytest.raises(InvalidMetadata):
#         Metadata.from_dict(empty[0])
#
#
# @pytest.mark.parametrize('x,doc', valid_cases)
# def test_from_dict(x, doc):
#     assert isinstance(Metadata.from_dict(x), Metadata), "cant load lineage from dictionary"
#
#
# @pytest.mark.parametrize('x,doc', valid_cases)
# def test_to_dict(x, doc):
#     lc = Metadata.from_dict(x)
#     assert isinstance(lc.to_dict(), dict), "cant unload lineage to dictionary"
#
#
# @pytest.mark.parametrize('x,doc', valid_cases)
# def test_lineage_consistency(x, doc):
#     l1 = Metadata.from_dict(x)
#     x2 = l1.to_dict()
#     assert x == x2, "lineage inconsistent between import/export"
