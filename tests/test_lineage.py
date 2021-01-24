import pytest

from data_as_code import Lineage

test_data = [
    Lineage('x', 'y', 'abc', 'this', None)
]


@pytest.mark.parametrize('x', test_data)
def test_has_checksum(x):
    assert x.checksum, "does not contain an object checksum"


@pytest.mark.parametrize('x', test_data)
def test_has_reference_path(x):
    assert x.path, "does not contain a reference path"


def test_has_name():
    assert False, "does not contain a name"


def test_has_node_type():
    assert False, "does not contain a node type identifier"


def test_can_recurse_ancestors():
    assert False, "a node in the lineage is not valid"


def test_can_output_json():
    assert False, "unable to generate valid JSON from lineage"


def test_can_reconstitute_json():
    assert False, "cannot rebuild valid Lineage from JSON data"


def test_can_plot_lineage():
    assert False, "unable to generate lineage plot"
