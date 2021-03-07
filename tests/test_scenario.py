from pathlib import Path
from data_as_code._recipe import Recipe
from data_as_code._step import Step

import pytest


@pytest.mark.parametrize('p_keep, p_trust, expected_from_cache', [
    (True, True, True),
    (False, True, False),
    (False, False, False),
    (True, False, False)
])
def test_use_cached(tmpdir, p_keep, p_trust, expected_from_cache):
    class R(Recipe):
        class S(Step):
            output = Path('zzz')
            keep = p_keep
            trust_cache = p_trust

            def instructions(self):
                self.output.write_text('top')

    r = R(tmpdir)
    r.execute()
    r.execute()
    assert r._results['S']._data_from_cache is expected_from_cache
