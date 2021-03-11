from pathlib import Path

import pytest

from data_as_code import exceptions as ex, ingredient
from data_as_code._recipe import Recipe
from data_as_code._step import Step
from data_as_code.misc import SOURCE, PRODUCT


def test_step_content_pass(tmpdir):
    """Content can be handed successfully from one step to another"""

    class R(Recipe):
        class S1(Step):
            _role = SOURCE
            keep = False

            def instructions(self):
                self.output.write_text('abc')

        class S2(Step):
            output = Path('product.txt')
            _role = PRODUCT
            x = ingredient('S1')

            def instructions(self):
                self.output.write_text(self.x.read_text().upper())

    R(tmpdir).execute()
    assert Path(tmpdir, 'data', PRODUCT, 'product.txt').read_text() == 'ABC'


def test_error_on_return(tmpdir):
    """
    Check for no return from instructions

    All output should be handled in side-effect by writing results to the step
    output file. This helps prevent *other* side-effects from sneaking in if the
    instructions are allowed to communicate back using anything but the output.
    """

    class X(Step):
        def instructions(self):
            return 1

    with pytest.raises(ex.StepNoReturnAllowed):
        X(tmpdir, tmpdir, {}).instructions()


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
