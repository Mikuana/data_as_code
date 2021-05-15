import os
from pathlib import Path
from uuid import uuid4

import pytest

from data_as_code._recipe import Recipe
from data_as_code._step import Step, result, ingredient


def test_destination_explicit(tmpdir):
    assert Recipe(destination=tmpdir).destination == tmpdir, \
        'destination attribute does not match explicit parameter'


def test_destination_absolute(tmpdir):
    r = Recipe(tmpdir)
    r.execute()
    assert r._target.folder.is_absolute(), \
        'destination attribute is not an absolute path'


def test_destination_default(tmpdir):
    cwd = os.getcwd()
    try:
        os.chdir(tmpdir)
        r = Recipe()
        r.execute()
        assert r._target.folder == tmpdir, \
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
    assert r._workspace.is_dir()


def test_cleanup_workspace(tmpdir):
    r = Recipe(tmpdir)
    r._begin()
    r._end()
    assert r._workspace.exists() is False


def test_artifact_sub_folder(tmpdir):
    """
    Test artifact sub-folder creation

    When result path is declared as a file in sub-folder, the result is output
    in a corresponding path in the recipe data folder.
    """
    sub = 'sub/file.txt'

    class R(Recipe):
        class S(Step):
            output = result(sub)

            def instructions(self):
                self.output.touch()

    R(tmpdir).execute()
    assert Path(tmpdir, 'data', sub).is_file()


def test_step_execution(tmpdir):
    """Ensure execution order matches declaration"""
    order = {}

    class S(Step):
        keep = False

        def instructions(self):
            self.output.touch()
            order[self.__class__.__name__] = len(order) + 1

    class T(Recipe):
        class S1(S):
            pass

        class S2(S):
            pass

        class S3(S):
            pass

    t = T(tmpdir)
    t.execute()
    assert order['S1'] == 1
    assert order['S2'] == 2
    assert order['S3'] == 3


@pytest.mark.parametrize('expected', (True, False))
def test_uses_cache(tmpdir, expected):
    """
    Cached result

    When cache is trusted, the existence of a metadata file along with a data
    artifact that matches the checksum results in the Step using the cached
    artifact. The instructions will not be executed.

    When cache is not trusted, the non-deterministic function below (it calls
    UUID-4) results in the
    """
    file_name = 'file.txt'

    class R(Recipe):
        class S(Step):
            output = result(file_name)
            trust_cache = expected

            def instructions(self):
                """intentionally non-deterministic"""
                self.output.write_text(uuid4().hex)

    p = Path(tmpdir, 'data', file_name)

    R(tmpdir).execute()
    txt1 = p.read_text()
    R(tmpdir).execute()
    txt2 = p.read_text()
    assert (txt1 == txt2) is expected


def test_catches_diff(tmpdir):
    """
    Step identifies difference in codified metadata
    """
    same_file_name = 'file.txt'
    p = Path(tmpdir, 'data', same_file_name)

    class R1(Recipe):
        class S1(Step):
            output = result(same_file_name)

            def instructions(self):
                self.output.write_text(uuid4().hex)

    class R2(Recipe):
        class S1(Step):
            output = result(same_file_name)

            def instructions(self):
                self.output.touch()

    R1(tmpdir).execute()
    first = p.read_text()
    R1(tmpdir).execute()
    second = p.read_text()
    assert first == second
    R2(tmpdir).execute()
    third = p.read_text()
    assert third == ''
