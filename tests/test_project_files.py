import json
from pathlib import Path
from data_as_code.premade import source_local
from data_as_code.metadata import from_dictionary


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
        source_local(r, csv_file_a, keep=True)

    mp = Path(r.destination, 'metadata', 'source', csv_file_a.name + '.json')
    mj = from_dictionary(**json.loads(mp.read_text()))
    assert mj.path.as_posix() == Path(r.destination, 'data/source/fileA.csv').as_posix()
