import time
import pytest
from pathlib import Path
import os

from data_as_code._recipe import Recipe
from data_as_code._step import Step
from data_as_code.misc import source


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


def test_artifact_subfolder(tmpdir):  # TODO: move this to step (I think)
    class T(Recipe):
        class S(Step):
            output = Path('subfolder', 'file.txt')
            role = source

            def instructions(self):
                self.output.touch()

    T(tmpdir).execute()
    assert Path(tmpdir, 'data', source, 'subfolder', 'file.txt').is_file()


def test_step_execution(tmpdir):
    """Check timestamps of step output to ensure correct execution order"""
    s1, s2, s3 = Path('s1'), Path('s2'), Path('s3')

    class S(Step):
        role = source

        def instructions(self):
            time.sleep(0.01)
            self.output.touch()

    class T(Recipe):
        class S1(S):
            output = s1

        class S2(S):
            output = s2

        class S3(S):
            output = s3

    T(tmpdir).execute()
    p = Path(tmpdir, 'data', source)
    p1, p2, p3 = Path(p, s1), Path(p, s2), Path(p, s3)
    assert p1.stat().st_mtime_ns < p2.stat().st_mtime_ns < p3.stat().st_mtime_ns
