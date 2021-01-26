import json
from pathlib import Path


def rj(name: str) -> dict:
    """ Read JSON case data from test folder"""
    return json.loads(Path(Path(__file__).parent, name + '.json').read_text())


c1 = rj('case1'), "Basic good without nested lineage"
