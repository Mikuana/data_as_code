import pytest
from pathlib import Path
from data_as_code.artifact import Artifact


def test_1():
    s1 = Artifact('1', 'www.com', 'abc123', Path('x'))
    s2 = Artifact('2', s1, 'efg456', Path('y'))
    assert s2.is_descendent('1')


def test_2():
    s1 = Artifact('1', 'www.com', 'abc123', Path('x'))
    s2 = Artifact('2', s1, 'efg456', Path('y'))
    s3 = Artifact('3', s2, 'hij789', Path('z'))
    assert s3.is_descendent('2', '1')


def test_3():
    s1 = Artifact('1', 'www.com', 'abc123', Path('x'))
    s2 = Artifact('2', s1, 'efg456', Path('y'))
    s3 = Artifact('3', s2, 'hij789', Path('z'))
    with pytest.raises(KeyError):
        s3.is_descendent('2', '3')
