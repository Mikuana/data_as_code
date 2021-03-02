# Data as Code

A python package which handles the transformation of data as a recipe which
enables versioning, reproducibility, and portability of data. The example below
will download a CSV file, read it line by line, and convert the delimiter to a
star.

```python
# star_convert_recipe.py
import csv
from pathlib import Path

from data_as_code import Recipe, Step, ingredient, premade

with Recipe('data_package') as r:
    s1 = premade.source_http(r, 'https://data-url.com/data.csv')


    class ChangeDelimiter(Step):
        """ Read CSV and rewrite file with star(*) delimiter """
        x = ingredient(s1)
        output = Path('starred.csv')

        def instructions(self):
            with self.output.open('w', newline='') as new:
                writer = csv.writer(new, delimiter='*')
                with self.x.absolute_path.open(newline='') as orig:
                    reader = csv.reader(orig)
                    for row in reader:
                        writer.writerow(row)


    ChangeDelimiter(r)
```

This produces a package in a directory of files.

```
|-- data_package/
    |-- env/
        |-- requirements.txt
    |-- metadata/
        |-- data_starred.json
    |-- data/
        |-- data_starred.csv
    |-- recipe.py
```

## Why though?

The value of treating *data as code* becomes apparent when you have the right
use cases.

### Large, publicly available data

Alice is working on a project with Bob which uses a public data set that is 100
GB in size. Alice is the data expert, and is responsible for cleaning up the
file before Bob looks at it. She does this in Python, but the end result is
still 100 GB. That's big enough that sending it to Bob over the internet is
challenging.

*Instead of sending the final data, Alice can send the recipe to Bob, who can
then use the recipe to process the data from the same source that Alice used.*

### Mixing public and private data

Alice is working with Bob again, and he wants her to enhance the large public
data set with a smaller proprietary data that she holds. She does this in a
recipe, but still doesn't want to send the final product over the internet
because it is too large.

*Alice can package her proprietary data along with the recipe, without needing
to send the public data. Bob can again generate the final product, including the
enhancements.*

### Are we using the same data?

When Alice sends her data to Bob, he wants to know if various source files used
to produce the final product are the same ones that were used for another
project.

*Alice delivers automatically generated metadata for all source and intermediate
files involved in creating the final product, including filenames, notes, and
checksums*

# Installation

This package requires Python 3.6+

```shell
pip install data_as_code
```
