"""
 - metadata paths to file in project folder when kept
 - if path is not set explicitly in step, it should not be retained in metadata
"""
import json
from pathlib import Path

import pytest

from data_as_code._metadata import from_dictionary
from data_as_code._step import Step


@pytest.mark.parametrize('v_role, v_keep', [
    ('source', True),
    ('intermediary', True),
    ('product', True),
    ('product', False)  # products should be cached regardless of keep setting
])
def test_cache(tmpdir, default_recipe, v_role, v_keep):
    """
    Check cache for artifacts
    """
    filename = 'x.csv'
    with default_recipe as r:
        class Rewrite(Step):
            output = Path(filename)
            role = v_role
            keep = v_keep

            def instructions(self):
                self.output.write_text('xyz')

        Rewrite(r)

    mp = Path(r.destination, 'metadata', v_role, filename + '.json')
    assert mp.is_file()
    mj = json.loads(mp.read_text())
    meta = from_dictionary(**mj, relative_to=r.destination)
    assert meta.path.is_file()
