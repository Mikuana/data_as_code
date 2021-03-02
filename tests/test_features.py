"""
 - metadata paths to file in project folder when kept
 - if path is not set explicitly in step, it should not be retained in metadata
"""
import json
from pathlib import Path
from data_as_code.premade import source_local
from data_as_code._metadata import from_dictionary
from data_as_code._step import Step, ingredient


def test_cache_path_is_relative(tmpdir, default_recipe, csv_file_a):
    """
    Test kept file path

    Ensure that the metadata artifacts path value corresponds to the expected
    file path in the data folder, relative to the root project folder, when the
    keep option is set to True. In other words, if we keep a file after the
    recipe completes, the value in path should lead directly to the corresponding
    if the working directory is set to the root project folder.
    """
    with default_recipe as r:
        s1 = source_local(r, csv_file_a, keep=True)

        class Rewrite(Step):
            """ Make Data into Code """
            role = 'product'
            output = Path('x.csv')
            x = ingredient(s1)

            def instructions(self):
                self.output.write_text(self.x.path.read_text())

        Rewrite(r)

    mp = Path(r.destination, 'metadata/product/x.csv.json')
    mj = from_dictionary(**json.loads(mp.read_text()))
    assert mj.path.as_posix() == 'data/product/x.csv'
