from data_as_code import step, Metadata


def test_ingredient_handling(default_recipe, csv_file_a):
    """
    Check appropriate handling of ingredients

    Step ingredients should be added to a step as a Step class, then ultimately
    be converted into a Metadata class for ease of use in the instructions.
    """
    with default_recipe as r:
        step1 = step.SourceLocal(r, __file__)

        class X(step.Custom):
            # noinspection PyMissingConstructor
            def __init__(self):
                pass

            s1 = step.ingredient(step1)

        assert isinstance(X.s1, step._Step)

        x = X()
        x._get_ingredients()

        assert isinstance(x.s1, Metadata)
