from data_as_code.artifact import DataArtifact


def test_file(source_vanilla: DataArtifact):
    assert source_vanilla.file_path.exists()
