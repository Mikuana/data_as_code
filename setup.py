import re
from pathlib import Path

import setuptools


def read_version():
    try:
        v = [x for x in Path('us_birth_data/__init__.py').open() if x.startswith('__version__')][0]
        v = re.match(r"__version__ *= *'(.*?)'\n", v)[1]
        return v
    except Exception as e:
        raise RuntimeError(f"Unable to read version string: {e}")


setuptools.setup(
    name="dac",
    version=read_version(),
    author="Christopher Boyd",
    description="A framework for treating Data as Code (DaC)",
    long_description_content_type="text/markdown",
    url="https://github.com/Mikuana/dac",
    long_description=Path('README.md').read_text(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"
    ],
    python_requires=">=3.8",
    install_requires=[
      'pandas>=1.1',
      'pyarrow',
      'requests',
      'tqdm'
    ],
    extras_require={
        'Testing': ['pytest', 'pytest-mock', 'pytest-cov']
    },
    packages=setuptools.find_packages()
)
