import inspect
import json
from pathlib import Path


def x(name: str) -> dict:
    """ Read JSON case data from test folder"""
    return json.loads(Path(Path(__file__).parent, name + '.json').read_text())


c1 = x('c1'), "Empty metadata"
c2 = x('c2'), "Blank metadata"
c3 = x('c3'), "Codified only"

valid_cases = [c2, c3]
