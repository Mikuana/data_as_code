import pytest

from data_as_code._lineage import Lineage, from_dictionary
from tests.cases import *


@pytest.mark.parametrize('x,doc', valid_cases)
def test_from_dict(x, doc):
    assert isinstance(from_dictionary(**x), Lineage), "cant load lineage from dictionary"


@pytest.mark.parametrize('x,doc', valid_cases)
def test_to_dict(x, doc):
    lc = from_dictionary(**x)
    assert isinstance(lc.to_dict(), dict), "cant unload lineage to dictionary"


@pytest.mark.parametrize('x,doc', valid_cases)
def test_lineage_consistency(x, doc):
    l1 = from_dictionary(**x)
    x2 = l1.to_dict()
    assert x == x2, "lineage inconsistent between import/export"

# @pytest.mark.parametrize('x', good_data)
# def test_can_plot_lineage(x):
#     assert not x.show_lineage()
