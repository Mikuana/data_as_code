import pytest

from data_as_code import Lineage

test_data = [
    Lineage('x', 'y', 'abc', 'this', None)
]


@pytest.mark.parametrize('x', test_data)
@pytest.mark.parametrize('attribute', [
    'name', 'path', 'checksum', 'kind', 'guid'
])
def test_has_attribute(x, attribute):
    assert getattr(x, attribute), "does not have attribute"
    assert isinstance(getattr(x, attribute), str), "attribute is not a string"


def test_can_output_json():
    assert False, "unable to generate valid JSON from lineage"


def test_can_reconstitute_json():
    assert False, "cannot rebuild valid Lineage from JSON data"


def test_can_plot_lineage():
    assert False, "unable to generate lineage plot"
