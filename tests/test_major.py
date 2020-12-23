from pathlib import Path
from data_as_code import Recipe, SourceLocalFile, Step, InputMetadata, Intermediary


def test_the_big_one(csv_file_a, csv_file_b):
    with Recipe() as r:
        SourceLocalFile(r, csv_file_a, name='a')
        SourceLocalFile(r, csv_file_b, name='b')

        class Merge(Step):
            a = InputMetadata('a')
            b = InputMetadata('b')

            def process(self) -> Path:
                txt = self.a.file_path.read_text()
                txt += self.a.file_path.read_text()
                pat = Path(self.recipe.workspace, 'fileC.csv')
                pat.write_text(txt)
                return pat
        Merge(r, name='c')
