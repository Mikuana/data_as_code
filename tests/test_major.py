from pathlib import Path
from data_as_code import Recipe, GetLocalFile, CustomStep, StepInput, Intermediary


def test_the_big_one(csv_file_a, csv_file_b):
    with Recipe() as r:
        GetLocalFile(r, csv_file_a, name='a')
        GetLocalFile(r, csv_file_b, name='b')

        class Merge(CustomStep):
            a = StepInput('a')
            b = StepInput('b')

            def process(self) -> Intermediary:
                txt = self.a.file_path.read_text()
                txt += self.a.file_path.read_text()
                pat = Path(self.recipe.wd, 'fileC.csv')
                pat.write_text(txt)
                return Intermediary([self.a, self.b], pat)
        Merge(r, name='c')
