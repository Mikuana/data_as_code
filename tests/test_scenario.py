from pathlib import Path
from data_as_code._recipe import Recipe
from data_as_code._step import Step
from data_as_code.misc import source, intermediary, product


def test_use_cached(tmpdir):
    class R(Recipe):
        class S(Step):
            output = Path('zzz')
            keep = True

            def instructions(self):
                self.output.write_text('top')

    r = R(tmpdir)
    r.execute()
    assert r._results['S']._data_from_cache is False
    r.execute()
    assert r._results['S']._data_from_cache is True
