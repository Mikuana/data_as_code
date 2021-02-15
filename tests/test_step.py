from pathlib import Path
from data_as_code.recipe import Recipe
from data_as_code.step import Custom, Input, _SourceStep
from data_as_code._metadata import Metadata


def test_get_input(frozen_pizza):
    class MyStep(Custom):
        file_a = Input('fileA.csv')

        def instructions(self):
            p = Path('my_step.txt')
            p.write_text(self.file_a.path.read_text())
            return p

    assert isinstance(MyStep(frozen_pizza).file_a, Metadata)


def test_add_output(frozen_pizza):
    class MyStep(Custom):
        file_a = Input('fileA.csv')

        def instructions(self):
            p = Path('my_step.txt')
            p.write_text(self.file_a.path.read_text())
            return p

    assert 'my_step.txt' in [x.name for x in MyStep(frozen_pizza).output]


def test_return_path():
    assert False, "process did not return a file path"
