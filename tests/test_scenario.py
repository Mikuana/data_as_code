from pathlib import Path

import pytest

from data_as_code._recipe import Recipe
from data_as_code._step import Step
from data_as_code.misc import SOURCE


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
    r.execute()  # execute first time to establish cache
    r.execute()  # execute second to see if data are loaded from cache
    assert r._results['S']._data_from_cache is expected_from_cache


def test_one_step(tmpdir):
    class R(Recipe):
        class Trusted(Step):
            output = Path('zzz')
            keep = True
            trust_cache = True

            def instructions(self):
                self.output.write_text('top')

        class Untrusted(Step):
            output = Path('aaa')
            keep = True
            trust_cache = False

            def instructions(self):
                self.output.write_text('bottom')

    r = R(tmpdir)
    r.execute()  # execute first time to establish cache
    r.execute()  # execute second to see if data are loaded from cache
    assert r._results['Trusted']._data_from_cache is True
    assert r._results['Untrusted']._data_from_cache is False


@pytest.mark.parametrize('recipe, step, expected_from_cache', [
    (True, None, True),
    (True, None, True),
    (True, False, False),
    (False, None, False),
    (False, True, True),
    (None, None, True),
    (None, False, False),
])
def test_global_trust(tmpdir, recipe, step, expected_from_cache):
    class R(Recipe):
        if recipe is not None:
            trust_cache = recipe

        class S(Step):
            if step is not None:
                trust_cache = step

            keep = True
            output = Path('zzz')
            _role = SOURCE

            def instructions(self):
                self.output.write_text('top')

    r = R(tmpdir)
    r.execute()  # execute first time to establish cache
    r.execute()  # execute second to see if data are loaded from cache
    assert r._results['S']._data_from_cache is expected_from_cache
