import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmpdir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)
