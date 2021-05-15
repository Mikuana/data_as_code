from pathlib import Path

import pytest

import json
from data_as_code import exceptions as ex
from data_as_code._metadata import Metadata
from data_as_code._step import Step, result, ingredient, _Ingredient
from data_as_code import exceptions as ex


def test_step_content_write(tmpdir):
    """Content is written to a file in step workspace"""
    file_name = 'file.txt'
    file_content = 'file_content'

    class S(Step):
        output = result(file_name)

        def instructions(self):
            self.output.write_text(file_content)

    s = S(tmpdir, {})._execute(tmpdir)
    p = Path(s._workspace, file_name)
    assert p.is_file()
    assert p.read_text() == file_content


def test_error_on_return(tmpdir):
    """
    Check for no return from instructions

    All output should be handled in side-effect by writing results to the step
    output file. This helps prevent *other* side-effects from sneaking in if the
    instructions are allowed to communicate back using anything but the output.
    """

    class S(Step):
        def instructions(self):
            return 1

    with pytest.raises(ex.StepNoReturnAllowed):
        S(tmpdir, {})._execute(tmpdir)


def test_error_on_missing_output(tmpdir):
    """
    Output must get populated

    Steps should automatically check output after instructions are executed to
    ensure output has been populated.
    """

    class X(Step):
        def instructions(self):
            pass

    with pytest.raises(ex.StepOutputMustExist):
        X(tmpdir, {})._execute(tmpdir)


def test_error_on_missing_multi_output(tmpdir):
    """
    Output must get populated

    Steps should automatically check output after instructions are executed to
    ensure output has been populated for all declared results.
    """

    class X(Step):
        x = result('x')
        y = result('y')

        def instructions(self):
            self.x.write_text('x')
            # no y output

    with pytest.raises(ex.StepOutputMustExist):
        X(tmpdir, {})._execute(tmpdir)


def test_error_on_default_output_product(tmpdir):
    """A keep step must define output name"""

    class X(Step):
        keep = True

    with pytest.raises(ex.StepUndefinedOutput):
        X(tmpdir, {})._execute(tmpdir)


def test_ingredient_collection(tmpdir):
    """
    Step attributes declared as an ingredient get converted into a Path object,
    for ease of use during instruction declaration.
    """

    class X(Step):
        def instructions(self):
            self.output.write_text('abc')

    class Y(Step):
        x = ingredient('x')

        def instructions(self):
            self.output.write_text('efg')

    x = X(tmpdir, {})
    x._execute(tmpdir)
    y = Y(tmpdir, {'x': x.metadata})
    y._execute(tmpdir)
    assert isinstance(y.x, Path)


def test_multi_ingredient(tmpdir):
    """
    Read one result as an ingredient from prior multi-step
    """

    class X(Step):
        a = result('a')
        b = result('b')

        def instructions(self):
            self.a.write_text('a')
            self.b.write_text('b')

    class Y(Step):
        b = ingredient('X', 'b')

        def instructions(self):
            self.output.write_text(
                self.b.read_text()
            )

    x = X(tmpdir, {})
    x._execute(tmpdir)
    y = Y(tmpdir, {'X': x.metadata})
    y._execute(tmpdir)
    assert y.output.read_text() == 'b'


def test_multi_non_specific(tmpdir):
    """
    Raise an error on under-qualified multi-result

    If an ingredient provides multiple results, the call to the ingredient
    method must contain an explicit result name, else an exception is raised.
    """

    class X(Step):
        a = result('a')
        b = result('b')

        def instructions(self):
            self.a.write_text('')
            self.b.write_text('')

    class Y(Step):
        a = ingredient('X')

    x = X(tmpdir, {})
    x._execute(tmpdir)
    with pytest.raises(Exception):
        Y(tmpdir, {'X': x.metadata})


def test_multi_non_existent(tmpdir):
    """
    Raise an error when previous multi-result doesn't exist

    If an ingredient asks for a result that doesn't exist, and exception is
    raised.
    """

    class X(Step):
        a = result('a')
        b = result('b')

        def instructions(self):
            self.a.write_text('')
            self.b.write_text('')

    class Y(Step):
        a = ingredient('X', 'c')

    x = X(tmpdir, {})
    x._execute(tmpdir)
    with pytest.raises(Exception):
        Y(tmpdir, {'X': x.metadata})


def test_undefined_instructions(tmpdir):
    class X(Step):
        pass

    with pytest.raises(Exception):
        X(tmpdir, {})._execute(tmpdir)
