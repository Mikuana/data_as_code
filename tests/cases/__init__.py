import json
from pathlib import Path


def rj(name: str) -> dict:
    """ Read JSON case data from test folder"""
    return json.loads(Path(Path(__file__).parent, name + '.json').read_text())


c1 = rj('case1'), "Source without nested lineage"
c2 = rj('case2'), "Source with single layer lineage"
c3 = rj('case3'), "Source with single layer multi-lineage"
c4 = rj('case4'), "Source with multi-layer lineage"

valid_cases = [c1, c2, c3, c4]
