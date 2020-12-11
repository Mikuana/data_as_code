from data_as_code.artifact import _Artifact


def test_file(source_vanilla: _Artifact):
    assert source_vanilla.file_path.exists()
