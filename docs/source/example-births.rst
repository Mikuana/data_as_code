Examples: Births in the US in 1968
##################################

For this example, we start with the question **"How many children were born in
1968?"**. To answer this question, we'll be retrieving a file from the
CDC `Vital Statistics Online Data Portal`_. Our recipe will demonstrate
retrieving a large file from the internet, performs pre-processing, extracting
values, then finally aggregates to a compact final product.

After walking through the specifics of the recipe, we'll then demonstrate the
ways that Recipe and Step configurations can be leveraged to support the further
development of this recipe. Finally, we'll show how the recipe and artifacts can
be versioned using Git, in order to fully embrace data as code.

First off, here's the recipe. There are three main steps:

 #. Download the file. This step uses FTP, as that is how it is hosted by the CDC

 #. Extract the data file from the Zip archive and recompress is as a Gzip.
    While we do want the data to be compressed (because they are large), most
    analytical and data processing tools can't work directly with tabular text
    data that is part of a zip archive.

 #. Extract bytes by position to retrieve month data. The PUB file is formatted
    as a fixed-width file, with column layout positions match the original
    tape positions that the data were stored on in 1968. Unfortunately, the data
    dictionary is not machine readable, so we are forced to supply the correct
    positions manually.

.. code-block:: python

    import csv
    import gzip
    import shutil
    from collections import defaultdict
    from ftplib import FTP
    from pathlib import Path
    from zipfile import ZipFile

    from data_as_code import Recipe, Step, result, ingredient


    class BirthData(Recipe):
        """ Aggregate CDC Vital Statistics data to count births in 1968 """
        pickup = True

        class Get68(Step):
            """ Download 1968 U.S. birth data file from FTP """
            output = result('Nat1968.ZIP')

            def instructions(self):
                with FTP('ftp.cdc.gov') as ftp:
                    ftp.login()
                    ftp.cwd('/pub/Health_Statistics/NCHS/Datasets/DVS/natality')
                    with self.output.open('wb') as f:
                        ftp.retrbinary(f'RETR {self.output.name}', f.write)

        class Convert68(Step):
            """ Extract PUB file from Zip and recompress as Gzip """
            output = result('NATL1968.PUB.gz')
            z = ingredient('Get68')
            keep = True

            def instructions(self):
                with ZipFile(self.z.as_posix()) as zf:
                    with zf.open(self.output.stem) as pf:
                        with gzip.open(self.output.as_posix(), 'wb') as gf:
                            shutil.copyfileobj(pf, gf)

        class Reduce68(Step):
            """ Extract month column from PUB file an count births """
            output = result('nat1968.csv')
            g = ingredient('Convert68')
            keep = True
            trust_cache = False

            def instructions(self):
                def handle_int(x: bytes):
                    x = x.decode('utf8')
                    return int(x) if x.strip() else None

                with gzip.open(self.g, 'rb') as gf:
                    counts = defaultdict(lambda: 0)
                    for line in gf:
                        if not line.isspace():
                            k = (1968, handle_int(line[31:33]))
                            counts[k] += 2  # 1968 is a 50% sample of birth records

                with self.output.open('w', newline='') as cf:
                    w = csv.writer(cf)
                    w.writerow(['Year', 'Month', 'Count'])
                    for k in sorted(counts.keys()):
                        w.writerow([*k] + [counts[k]])


The result is a CSV file with the following contents:

.. csv-table::

    Year,Month,Count
    1968,1,277404
    1968,2,266082
    1968,3,282152
    1968,4,273564
    1968,5,288468
    1968,6,287432
    1968,7,308396
    1968,8,311676
    1968,9,305752
    1968,10,304288
    1968,11,291584
    1968,12,304766

At this point, we've answered our original question, and even gotten a little
more detail (i.e. month).

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _Vital Statistics Online Data Portal: https://www.cdc.gov/nchs/data_access/vitalstatsonline.htm
