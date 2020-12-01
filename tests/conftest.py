import tempfile
from pathlib import Path

import pytest

from data_as_code.main import Product, Lineage, Recipe


@pytest.fixture(scope="session")
def tmpdir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture(scope="session")
def product_vanilla(tmpdir):
    pat = Path(tmpdir, 'xyz')
    lin = Lineage()
    rec = Recipe()
    yield Product(file_path=pat, lineage=lin, recipe=rec)
