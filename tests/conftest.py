import os
import tempfile
from pathlib import Path

import pytest

from data_as_code import Recipe
from data_as_code._step import _SourceLocal


@pytest.fixture
def tmpdir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture()
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
        _SourceLocal(r, csv_file_a)
        _SourceLocal(r, csv_file_b)
        yield r


@pytest.fixture
def default_recipe(tmpdir):
    cwd = os.getcwd()
    os.chdir(tmpdir)
    r = Recipe()
    os.chdir(cwd)
    yield r
