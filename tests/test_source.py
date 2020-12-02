from data_as_code.artifact import Artifact


def test_file(source_vanilla: Artifact):
    assert source_vanilla.file_path.exists()
