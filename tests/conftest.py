from hashlib import sha256
from uuid import uuid4
import tempfile
from pathlib import Path

import pytest

from data_as_code.main import Product, Lineage, Recipe
from data_as_code.artifact import DataArtifact, _Intermediary


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


@pytest.fixture(scope="session")
def source_vanilla(tmpdir):
    pat = Path(tmpdir, 'vanilla_source.txt')
    pat.write_text('this is data')
    has = sha256()
    has.update(pat.read_bytes())
    yield DataArtifact(pat.name, 'testing', has, pat, uuid4(), 'this is for testing')
