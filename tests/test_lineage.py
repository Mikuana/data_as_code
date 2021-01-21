import pytest

x = {
    'node_type': 'source',
    'name': 'X',
    'location': 'https://internet.com',
    'ancestors': [],
    'checksum': 'abd123',
    'reference_path': '/home/user1/project_folder/X/',
    'notes': 'words'
}


@pytest.mark.parametrize("lineage", [x])
@pytest.mark.parametrize("key,value_type", [
    ('node_type', str),
    ('name', str),
    ('location', str),
    ('ancestors', list),
    ('reference_path', str)
])
def test_source_attributes(lineage: dict, key, value_type):
    assert isinstance(lineage[key], value_type)
