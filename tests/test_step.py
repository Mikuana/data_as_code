from pathlib import Path

import pytest

from data_as_code import exceptions as ex
from data_as_code._step import Step, result


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
        X(tmpdir, tmpdir, {}).instructions()


def test_error_on_default_output_product(tmpdir):
    """A product step must define output name"""

    class X(Step):
        keep = True

    with pytest.raises(ex.StepUndefinedOutput):
        X(tmpdir, tmpdir, {})
