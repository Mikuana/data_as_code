import json
from pathlib import Path


def rj(name: str) -> dict:
    """ Read JSON case data from test folder"""
    return json.loads(Path(Path(__file__).parent, name + '.json').read_text())


c1 = rj('case1'), "HTTP Source"
c2 = rj('case2'), "Local Source"
c3 = rj('case3'), "Product with multi-step lineage"

valid_cases = [c1, c2, c3]
