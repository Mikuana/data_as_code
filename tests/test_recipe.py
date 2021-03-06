import pytest
from pathlib import Path
import os

from data_as_code._recipe import Recipe


def test_destination_explicit(tmpdir):
    assert Recipe(destination=tmpdir).destination == tmpdir, \
        'destination attribute does not match explicit parameter'


def test_destination_absolute(tmpdir):
    assert Recipe().destination.is_absolute(), \
        'destination attribute is not an absolute path'


def test_destination_default(tmpdir):
    cwd = os.getcwd()
    try:
        os.chdir(tmpdir)
        assert Recipe().destination == tmpdir, \
            'default destination does not match working directory'
    finally:
        os.chdir(cwd)


def test_makes_destination(tmpdir):
    p = Path(tmpdir, 'dest_dir')
    Recipe(p).execute()
    assert p.is_dir()


def test_makes_workspace(tmpdir):
    r = Recipe(tmpdir)
    r._begin()
    assert r.workspace.is_dir()


def test_cleanup_workspace(tmpdir):
    r = Recipe(tmpdir)
    r._begin()
    r._end()
    assert r.workspace.exists() is False


def test_existing_keep_error(tmpdir):
    """Raise error when package file exists, and keep settings True"""
    Path(tmpdir, tmpdir.name + '.tar').touch()
    with pytest.raises(FileExistsError):
        Recipe(tmpdir, keep=dict(existing=True)).execute()
