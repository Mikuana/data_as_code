from pathlib import Path
from data_as_code import Recipe, GetLocalFile, Step, Input, Intermediary


def test_the_big_one(csv_file_a, csv_file_b):
    with Recipe() as r:
        GetLocalFile(r, csv_file_a, name='a')
        GetLocalFile(r, csv_file_b, name='b')

        class Merge(Step):
            a = Input('a')
            b = Input('b')

            def process(self) -> Path:
                txt = self.a.file_path.read_text()
                txt += self.a.file_path.read_text()
                pat = Path(self.recipe.wd, 'fileC.csv')
                pat.write_text(txt)
                return pat
        Merge(r, name='c')
