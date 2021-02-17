import tempfile
from pathlib import Path

import pytest

from data_as_code import Recipe
from data_as_code.step import SourceLocal


@pytest.fixture
def tmpdir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def csv_file_a(tmpdir) -> Path:
    pat = Path(tmpdir, 'fileA.csv')
    pat.write_text('x,y,z\n1,2,3')
    yield pat


@pytest.fixture
def csv_file_b(tmpdir) -> Path:
    pat = Path(tmpdir, 'fileB.csv')
    pat.write_text('a,b,c\n4,5,6')
    yield pat


@pytest.fixture
def frozen_pizza(csv_file_a, csv_file_b):
    with Recipe() as r:
        SourceLocal(r, csv_file_a)
        SourceLocal(r, csv_file_b)
        yield r


@pytest.fixture
def default_recipe(tmpdir):
    yield Recipe(tmpdir.as_posix() + '/default')
