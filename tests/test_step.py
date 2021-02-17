from pathlib import Path

import pytest

from data_as_code.exceptions import StepError
from data_as_code import step, Metadata


class SafeTestStep(step._Step):
    """ Customize step class to be safe for testing small parts """

    def _get_metadata(self):
        return Metadata(Path(__file__), 'xyz', 'abc', list())


def test_ingredient_handling(default_recipe, csv_file_a):
    """
    Check appropriate handling of ingredients

    Step ingredients should be added to a step as a Step class, then ultimately
    be converted into a Metadata class after initialization.
    """
    with default_recipe as r:
        s1 = step.SourceLocal(r, __file__)

        class Pre(SafeTestStep):
            x = step.ingredient(s1)

        post = Pre(r)
        assert isinstance(Pre.x, step._Step)
        assert isinstance(post.x, Metadata)


# TODO: param with all step subclasses
@pytest.mark.parametrize('s', [])
def test_instruction_no_return(default_recipe, s):
    """
    Check for no return from instructions

    All output should be handled in side-effect by writing results to the step
    output files. This helps prevent *other* side-effects from sneaking in if the
    instructions is allowed to communicate using anything but the output.
    """
    with default_recipe as r:
        x = s(r)
        assert x.instructions() is None


# TODO: param with all step subclasses
@pytest.mark.parametrize('s', [])
def test_all_output_exists(default_recipe, s: step._Step):
    """
    Test all output

    Steps should automatically check output after instructions are executed to
    ensure that all expected output has been populated.
    """
    with default_recipe as r:
        s1 = step.SourceLocal(r, __file__)

        class BrokenInstructions(s):
            x = step.ingredient(s1)

            def instructions(self):
                pass

        with pytest.raises(StepError):  # TODO: make this specific to output
            BrokenInstructions(r)
