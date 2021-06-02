Examples: Births in the US in 1968
##################################

For this example, we start with the question **"How many children were born in
1968?"**. To answer this question, we'll be retrieving a file from the
CDC `Vital Statistics Online Data Portal`_. Our recipe will demonstrate
retrieving a large file from the internet, pre-processing, extracting
values, then finally aggregating to a compact final product.

After walking through the specifics of the recipe, we'll then demonstrate the
ways that Recipe and Step configurations can be leveraged to support the further
development of this recipe. Finally, we'll show how the recipe and artifacts can
be versioned using Git, in order to fully embrace data as code.

The Recipe
----------

First, we're going to make clear what is part of this package, and
what is not. To do this we'll write a script that retrieves, processes, and
aggregates a data set, without using any Data as Code components. In other
words, this is a *vanilla* python script which performs everything we need to
create our data set.

.. literalinclude:: include/birth68_no_dac.py

The result of executing this script is a CSV file named ``nat1968.csv``, with
the following contents:

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

The script has three main steps:

 #. Download the file. This step uses FTP.
 #. Extract the data file from the Zip archive and recompress as a Gzip.
 #. Extract data by position from fixed-width-file to retrieve month data.

This script works fine, but it creates some problems.

 - If you send someone the csv file, they might ask where you got it from.
    The CDC is an authoritative source, and we went through pains to get this data
    from them. We want to make it *clear* that we used their data - and not a
    Google search - to generate this product.
 - The script runs from end-to-end with every execution.
    Every time you use your script it will redownload, recompress, and reprocess
    the data. This happens even if all you do is change the csv headers from
    ``Year,Month,Count`` to ``Year,Month,Births``.
 - There is no explicit link between your code and the data it produced.
    If you send someone the csv file, then change your script, how do they know
    that they have a data product which was generated with a different version
    of your script than the current one? How do *you* know?

This is where the Data as Code package can provide some solutions. We've
modified the script in the example below (with emphasis on the extra code that
is introduced).

.. literalinclude:: include/birth68.py
    :emphasize-lines: 8,11-17,24-28,34-39

.. literalinclude:: include/birth68_nat1968.csv.json

.. warning::
    Need to walk through this metadata

Configuration
-------------

Caching
=======

You may have noticed that our recipe didn't define file names for every step.
In our first iteration of the recipe, we only defined a file name for the final
csv. However, we're still able to pass the output of each step to others as an
ingredient, due to the handling that this package does for us in the background.
The file downloaded in the first step and the recompressed file in the second
only exist as temporary files, during execution of the recipe.

However, this isn't ideal when we are actively developing our recipe. The first
step downloads a file from the internet which we don't expect to change. Since
we're going to need to execute our recipe numerous times during development, it
would make sense to download the file once, and continue to refer to that same
object for subsequent executions.

Fortunately, we can make this happen with a simple change to the recipe. By
explicitly defining a file name for the Step with :meth:`result`.

.. warning::
    Make this default

.. code-block:: python
    :emphasize-lines: 3

    class Get68(Step):
        """ Download 1968 U.S. birth data file from FTP """
        output = result('Nat1968.ZIP')

        def instructions(self):
            with FTP('ftp.cdc.gov') as ftp:
                ftp.login()
                ftp.cwd('/pub/Health_Statistics/NCHS/Datasets/DVS/natality')
                with self.output.open('wb') as f:
                    ftp.retrbinary(f'RETR {self.output.name}', f.write)

Once we do this, the file downloaded in this Step will be stored as part of the
Recipe output, and all subsequent executions will discover the file and use
the cached file instead of downloading it again.

We can also easily cache the second step, since that is a fairly straightforward
pre-processing step that we're unlikely to change as we're developing our recipe
and executing it multiple times.

.. code-block:: python
    :emphasize-lines: 3
    :linenos:

    class Convert68(Step):
        """ Extract PUB file from Zip and recompress as Gzip """
        output = result('NATL1968.PUB.gz')
        z = ingredient('Get68')

        def instructions(self):
            with ZipFile(self.z.as_posix()) as zf:
                with zf.open(self.output.stem) as pf:
                    with gzip.open(self.output.as_posix(), 'wb') as gf:
                        shutil.copyfileobj(pf, gf)

.. note::
    We don't need to refer to the specific file name output of ``Get68``.
    Instead, we refer to the step name using :meth:`ingredient` on line#4, and
    the result becomes available as a :class:`~pathlib.Path` object under the
    attribute we assign it to.

Now the recipe will use the cache for our second step, saving unnecessary time
extracting and compressing our file with each execution.

Pickup
======



Version Control
---------------

At this point, we've answered our original question, and even gotten a little
more detail (i.e. month). And this table is only 201 bytes in size, which is
*much* more portable than the original 14 MB archive that we downloaded. In
fact, the table, recipe, and associated data are all small enough that we could
reasonably use Git as a tool to version control our data.

.. note::
    15 MB really isn't that big, and you could easily put a file of that size
    into a Git repo. However, for the purpose of this example, pretend that the
    source file was actually 1 GB, or 1 TB. Then you can start to get a better
    idea of why it would be a problem to version control the source data.


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _Vital Statistics Online Data Portal: https://www.cdc.gov/nchs/data_access/vitalstatsonline.htm
