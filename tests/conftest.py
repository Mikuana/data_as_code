import tempfile
from pathlib import Path

import pytest

from data_as_code.main import Product


@pytest.fixture(scope="session")
def tmpdir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture(scope="session")
def product_vanilla():
    return Product()
