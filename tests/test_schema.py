import pytest

from data_as_code._schema import metadata
from tests.cases import Case, valid, invalid


@pytest.mark.parametrize('case', valid, ids=[x.label for x in valid])
def test_valid(case: Case):
    assert not metadata(case.meta)


@pytest.mark.parametrize('case', invalid, ids=[x.label for x in invalid])
def test_invalid(case: Case):
    with pytest.raises(case.error):
        metadata(case.meta)
