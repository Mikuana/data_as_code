import json
from pathlib import Path


def x(name: str) -> dict:
    """ Read JSON case data from test folder"""
    return json.loads(Path(Path(__file__).parent, name + '.json').read_text())


empty = x('case1'), "Empty metadata"
c2 = x('case2'), "Blank metadata"

valid_cases = [c2]
