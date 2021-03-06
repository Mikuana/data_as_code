import pytest

from data_as_code._metadata import Metadata, from_dictionary
from tests.cases import valid_cases


@pytest.mark.parametrize('x,doc', valid_cases)
def test_from_dict(x, doc):
    assert isinstance(from_dictionary(**x), Metadata), "cant load lineage from dictionary"


@pytest.mark.parametrize('x,doc', valid_cases)
def test_to_dict(x, doc):
    lc = from_dictionary(**x)
    assert isinstance(lc.to_dict(), dict), "cant unload lineage to dictionary"


@pytest.mark.parametrize('x,doc', valid_cases)
def test_lineage_consistency(x, doc):
    l1 = from_dictionary(**x)
    x2 = l1.to_dict()
    assert x == x2, "lineage inconsistent between import/export"
