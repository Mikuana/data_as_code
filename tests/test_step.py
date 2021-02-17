from pathlib import Path
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
