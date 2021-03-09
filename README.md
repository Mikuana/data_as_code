# Data as Code

A python package which handles the transformation of data as a recipe which
enables versioning, reproducibility, and portability of data.

The example below will download the HTML for the wikipedia page on Data, and
replace all occurrences of the word 'Data' with 'Code'.

```python
from pathlib import Path

from data_as_code import Recipe, Step, ingredient, source_http, PRODUCT


class DataAsCode(Recipe):
    wiki = source_http('https://en.wikipedia.org/wiki/Data', keep=True)

    class ChangeDelimiter(Step):
        """Change all instance of the word 'Data' to 'Code'"""
        x = ingredient('wiki')
        output = Path('code.html')
        role = PRODUCT

        def instructions(self):
            self.output.write_text(
                self.x.read_text().replace('Data', 'Code')
            )


DataAsCode().execute()

```

Upon execution, the recipe will create a series of folders and files based upon
the instructions in the recipe. Note the mirrored structure between the `data/`
folder and the `metadata/` folder; every file output by the recipe is created
with a corresponding JSON file that fully describes the history of that file,
based upon the recipe.

```
|-- my_data_package/
    |-- data/
        |-- source/
            |-- Data
        |-- product/
            |-- code.html
    |-- metadata/
        |-- source/
            |-- Data.json
        |-- product/
            |-- code.html.json
    |-- requirements.txt
    |-- recipe.py
    |-- my_data_package.tar.gz
 
```

If we look at the metadata for the `code.html` product, we can see quite a bit
of detail about how that file was created. We can see a path to the file which
contains the actual data (relative to the project folder), a description of what
transformations were performed in the final step, an MD5 checksum (to verify
the referenced file is correct, and the contents match those expected). We can
also so the lineage of the file, referencing the `Data` source HTML that was
downloaded from Wikipedia.

```json5
// metadata/product/code.html.json
{
  "path": "data/product/code.html",
  "step_description": "Change all instance of the word 'Data' to 'Code'",
  "role": "product",
  "checksum": {"algorithm": "md5",  "value": "9b8767c67aba0bbdbb074639be47e664"},
  "fingerprint": "fc9d3bc6f95a927993085b0e0b6f4083",
  "lineage": [
    {
      "path": "data/source/Data",
      "step_description": "Retrieve file from URL via HTTP.",
      "role": "source",
      "checksum": {"algorithm": "md5", "value": "f44a941b9492de289cf9f8478acac47c"},
      "fingerprint": "ff2811f4b54d2a3a721e31bf5d12f555",
      "url": "https://en.wikipedia.org/wiki/Data"
    }
  ]
}
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
