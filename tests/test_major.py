from pathlib import Path
from data_as_code import Recipe, SourceLocal, Step, Input, Intermediary


def test_the_big_one(csv_file_a, csv_file_b):
    with Recipe() as r:
        SourceLocal(r, csv_file_a, name='a')
        SourceLocal(r, csv_file_b, name='b')

        class Merge(Step):
            a = Input('a')
            b = Input('b')

            def process(self) -> Path:
                txt = self.a.path.read_text()
                txt += self.a.path.read_text()
                pat = Path(self.recipe.workspace, 'fileC.csv')
                pat.write_text(txt)
                return pat
        Merge(r, name='c')
