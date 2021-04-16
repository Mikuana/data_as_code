import pytest
from data_as_code import Recipe, Step, ingredient, result, premade


@pytest.fixture(scope='module')
def x():
    class DataAsCode(Recipe):
        # TODO: mock request for download
        wiki = premade.source_http('https://en.wikipedia.org/wiki/Data', keep=True)

        class ChangeDelimiter(Step):
            """Change all instance of the word 'Data' to 'Code'"""
            x = ingredient('wiki')
            output = result('code.html')

            def instructions(self):
                self.output.write_text(
                    self.x.read_text().replace('Data', 'Code')
                )

    return DataAsCode


def test_1(x, tmpdir):
    x(tmpdir).execute()
    assert x.destination.is_dir()
