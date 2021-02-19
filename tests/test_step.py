from pathlib import Path

import pytest

from data_as_code import exceptions as ex
from data_as_code._step import Step, ingredient, _Ingredient
from data_as_code.boxed import source_local
from data_as_code.metadata import Metadata


class SafeTestStep(Step):
    """ Customize step class to be safe for testing small parts """

    def _get_metadata(self):
        return Metadata(Path(__file__), 'xyz', 'abc', list())


def test_ingredient_handling(default_recipe, csv_file_a):
    """
    Check appropriate handling of ingredients

    Step ingredients should be added to a step as a Step class, then
    converted to a Metadata class after initialization.
    """
    with default_recipe as r:
        s1 = source_local(r, __file__)

        class Pre(SafeTestStep):
            x = ingredient(s1)

            def instructions(self):
                self.output.write_text('x')

        post = Pre(r)
        assert isinstance(Pre.x, _Ingredient)
        assert isinstance(post.x, Metadata)


def test_error_on_return(default_recipe):
    """
    Check for no return from instructions

    All output should be handled in side-effect by writing results to the step
    output files. This helps prevent *other* side-effects from sneaking in if the
    instructions are allowed to communicate back using anything but the output.
    """
    with default_recipe as r:
        class X(Step):
            def instructions(self):
                return 1

        with pytest.raises(ex.NoReturnAllowed):
            X(r).instructions()


def test_error_on_missing_output(default_recipe):
    """
    Test all output

    Steps should automatically check output after instructions are executed to
    ensure that all expected output has been populated.
    """
    with default_recipe as r:
        class X(Step):
            def instructions(self):
                pass

        with pytest.raises(ex.OutputMustExist):
            X(r)
