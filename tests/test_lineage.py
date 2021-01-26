from hashlib import sha256
from pathlib import Path
import json

import pytest
from tests.cases import *
from data_as_code._lineage import Lineage, from_objects, from_dictionary

good_data = [
    Lineage('x', Path('y'), dict(algorithm='fake', value='abc'), 'this', 'source', []),
    from_objects('z', Path('y'), sha256(), 'source', None)
]


@pytest.mark.parametrize('x', good_data)
def test_output_json(x):
    assert isinstance(json.dumps(x.unload()), str)


@pytest.mark.parametrize('x', good_data)
def test_input_json(x):
    j1 = json.dumps(x.unload())
    assert isinstance(from_dictionary(**json.loads(j1)), Lineage)
    j2 = json.dumps(from_dictionary(**json.loads(j1)).unload())
    assert j1 == j2, "lineage cases not consistent between import/export"


# @pytest.mark.parametrize('x', good_data)
# def test_can_plot_lineage(x):
#     assert not x.show_lineage()

@pytest.mark.parametrize('c,doc', [c1])
def test_json_input(c, doc):
    assert isinstance(from_dictionary(**c), Lineage), doc
