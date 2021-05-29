Examples
########

In our first example, we're going to do an analysis of the letters which appear
most frequently in a file. We'll start by building out the recipe, step by step.
Then we'll look at the metadata files which are generated with each execution.
Next, we'll change some of the recipe and step configuration options to optimize
use of the recipe. Then finally, we'll look out how we can treat the recipe, and
key artifacts of the execution as code, and take advantages of version control
tools.

Building the Recipe
-------------------

.. testsetup::

    import os
    import random
    from pathlib import Path
    from string import ascii_letters
    from tempfile import TemporaryDirectory
    from unittest.mock import patch

    od = os.getcwd()
    td = TemporaryDirectory()
    os.chdir(td.name)


    def side(y):
        p = Path(y)
        random.seed(8752)
        letters = random.choices(ascii_letters, k=int(1e7))
        p.write_text(''.join(letters))
        return y, {'Content-Length': str(p.stat().st_size)}


    mock = patch('urllib.request.urlretrieve').start()
    mock.side_effect = lambda x, y: side(y)

To begin we will download a file from the internet
using the common step :meth:`~common.source_http`. This file contains 10 million
random upper and lower case ASCII letters.

.. note::
    The URL is not real, so the download is mocked for demonstration purposes.

.. testcode::

    from data_as_code import Recipe, Step, result, ingredient
    from data_as_code.common import source_http

    class GetData(Recipe):
        download = source_http('https://not.real.url/file.txt')

    # Execute and print for demonstration only
    GetData().execute()
    with open('data/file.txt') as f:
        print(f.read(50))

We print the first 50 bytes of the file so that we can get an idea of what
data we've got.

.. testoutput::

    AIeVgikImhosvWRWwawFsfYQgbsNKeCLhKmzWmwuljxZtRJSmq

Since we're not interested in the difference between upper and lower for our
analysis, we'll add a step to convert the contents of the downloaded file to all
CAPS. This requires a few extra imports to be added to our recipe script. We
add a new step, ``Caps`` which uses the result of the ``download`` step as an
ingredient. ``download`` is assigned to the attribute ``x`` for brevity, so that
we can easily call it to read the contents of the file in the instructions.

.. testcode::

    import csv
    from collections import Counter

    from data_as_code import Recipe, Step, result, ingredient
    from data_as_code.common import source_http

    class GetData(Recipe):
        download = source_http('https://not.real.url/file.txt')

        class Caps(Step):
            x = ingredient('download')
            y = result('CAPS.TXT')

            def instructions(self):
                self.y.write_text(
                    self.x.read_text().upper()
                )

    # Execute and print for demonstration only
    GetData().execute()
    with open('data/CAPS.TXT') as f:
        print(f.read(50))

.. testoutput::

    AIEVGIKIMHOSVWRWWAWFSFYQGBSNKECLHKMZWMWULJXZTRJSMQ

Next, we want to do some analysis on these data and shape them into a tabular
file. In the next step, we're going to count the number of occurrences of each
letter, then write that to a CSV file.

.. testcode::

    import csv
    from collections import Counter
    from string import ascii_uppercase

    from data_as_code import Recipe, Step, result, ingredient
    from data_as_code.common import source_http


    class GetData(Recipe):
        download = source_http('https://not.real.url/file.txt')

        class Caps(Step):
            x = ingredient('download')
            y = result('CAPS.TXT')

            def instructions(self):
                self.y.write_text(self.x.read_text().upper())

        class Letters(Step):
            x = ingredient('Caps')
            y = result('letters.csv')

            def instructions(self):
                d = Counter(self.x.read_text())
                with self.y.open('w', newline='') as cf:
                    w = csv.writer(cf)
                    w.writerow(['letter', 'occurrences'])
                    for letter in ascii_uppercase:
                        w.writerow([letter, d.get(letter, 0)])


    # Execute and print for demonstration only
    GetData().execute()
    with open('data/letters.csv') as f:
        print(f.read())


.. testoutput::
   :options: -ELLIPSIS, +NORMALIZE_WHITESPACE

    letter,occurrences
    A,383052
    B,384490
    C,384764
    D,385388
    E,386029
    F,383948
    G,384675
    H,384803
    I,385601
    J,383861
    K,384854
    L,385071
    M,384203
    N,385555
    O,384767
    P,383801
    Q,383661
    R,384078
    S,383501
    T,385287
    U,384525
    V,384502
    W,385073
    X,384503
    Y,385454
    Z,384554

For our last step, we're going to identify the top 5 most frequent letters.

.. testcode::

    import csv
    from collections import Counter
    from string import ascii_uppercase

    from data_as_code import Recipe, Step, result, ingredient
    from data_as_code.common import source_http


    class GetData(Recipe):
        download = source_http('https://not.real.url/file.txt')

        class Caps(Step):
            x = ingredient('download')
            y = result('CAPS.TXT')

            def instructions(self):
                self.y.write_text(self.x.read_text().upper())

        class Letters(Step):
            x = ingredient('Caps')
            y = result('letters.csv')

            def instructions(self):
                d = Counter(self.x.read_text())
                with self.y.open('w', newline='') as cf:
                    w = csv.writer(cf)
                    w.writerow(['letter', 'occurrences'])
                    for letter in ascii_uppercase:
                        w.writerow([letter, d.get(letter, 0)])

        class Top5(Step):
            x = ingredient('Letters')
            y = result('Top5.txt')

            def instructions(self):
                with self.x.open(newline='') as cf:
                    top = [
                        a for a, _ in
                        sorted(csv.reader(cf), key=lambda b: b[1])
                    ]
                self.y.write_text(','.join(top[:5]))

    # Execute and print for demonstration only
    GetData().execute()
    with open('data/Top5.txt') as f:
        print(f.read())

.. testoutput::

    A,S,Q,P,J

Artifact Metadata
-----------------

Now that we've got a working recipe, it's time to take a look at some of our
metadata. Every file that is produced (and kept) by our recipe will have a
corresponding JSON metadata file. The metadata for our last file
``data/Top5.txt`` is located in the relative path ``metadata/Top5.txt.json``.

.. automodule:: data_as_code._metadata


.. testcleanup::

    mock.stop()
    os.chdir(od)
    td.cleanup()



Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
