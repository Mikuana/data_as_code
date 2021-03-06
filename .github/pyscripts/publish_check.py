import json
import re
import urllib.request
from pathlib import Path

from packaging.version import parse

try:
    from importlib.metadata import version
except ImportError:
    # noinspection PyUnresolvedReferences,PyUnresolvedReferences
    from importlib_metadata import version

from distutils.version import LooseVersion


def read_version():
    try:
        v = [x for x in Path('data_as_code/__init__.py').open() if x.startswith('__version__')][0]
        v = re.match(r"__version__ *= *'(.*?)'\n", v)[1]
        return v
    except Exception as e:
        raise RuntimeError(f"Unable to read version string: {e}")


pypi_url = f'https://pypi.org/pypi/data_as_code/json'
response = urllib.request.urlopen(pypi_url).read().decode()
latest_version = max(LooseVersion(s) for s in json.loads(response)['releases'].keys())
setup_version = read_version()

if parse(setup_version) > parse(str(latest_version)):
    print(f'PASS: version {setup_version} exceeds latest published, {latest_version}')
else:
    raise Exception(f'FAIL: version {setup_version} does not exceed latest published {latest_version}')
