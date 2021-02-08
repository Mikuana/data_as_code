# Data as Code

# Quick Start

To use this package, you'll need (1) access to source data files, (2) a series
of steps to transform the data using python. In the example below, we're going
to retrieve a csv file from the internet, and replace the delimiter.

```python
import csv
from pathlib import Path

from data_as_code import Recipe, step

with Recipe() as r:
    url = 'https://data.transportation.gov/api/views/bagt-569v/rows.csv?accessType=DOWNLOAD'
    step.SourceHTTP(r, url, 'road_data.csv')
    
    class ChangeDelimiter(step.Custom):
        """ Read CSV and rewrite file with star(*) delimiter """
        kind = step.Product
        x = step.Input('road_data.csv')

        def instructions(self):
            op = Path('road_data_starred.csv')
            with op.open('w', newline='') as new:
                writer = csv.writer(new, delimiter='*')
                with self.x.path.open(newline='') as orig:
                    reader = csv.reader(orig)
                    for row in reader:
                        writer.writerow(row)
            return op 
    
    ChangeDelimiter(r)
```

# Concepts

- **Artifact**: an objects which represents data, and provide a direct means of
  obtaining it, typically via file path

    - **MockSource**: a lineage *artifact* which precedes the *source*, but
      which is not actually available for use by the recipe. Allows for a more
      complete lineage to be declared when appropriate

    - **Source**: primary data *artifact*; the "original" that is used by a
      *recipe*, before it has been changed in any way

    - **Intermediary**: an intermediate data *artifact* that is the result of
      applying incremental changes to a *source*, but not yet the final data
      product produced by the *recipe*. Not meant to be used outside the recipe,
      and treated as disposable

    - **Product**: the ultimate data *artifact* produced by a *recipe*, which is
      intended for use outside the *recipe*. Includes the complete *lineage*
      as a component of the packaged product, and optionally includes the
      *recipe* that was used to create it

- **Processor**: a step where data artifacts are changed in any way

    - **Bypass**: a *processor* that does not actually do the work, but instead
      represents work that occurs outside the *recipe*. Useful if data are
      treated by a third party, or by other software that cannot be represented
      in any way in the *recipe*

- **Recipe**: the set of instructions which use the specified *sources*, and
  *processes* them in steps to generate the final data *product*

- **Lineage**: metadata that can be used to trace a *product* back to its
  *source*, which includes all data *artifacts*

# Example

Lets

```python

```