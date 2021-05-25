Data as Code
############

A python package which handles the transformation of data as a recipe. This
enables versioning, reproducibility, and portability of data. It provides the
additional context of lineage to enhance the interpretability of all data.


Installation
############

The recommended method to install is via pip::

    pip install data_as_code

This package requires python version 3.8 or higher.


Overview
########

This package is used to define a *recipe* script, which is executed in order to
produce data in files according to the instructions within that recipe.

.. module:: data_as_code
    :noindex:

.. testcode::

    # recipe.py
    from data_as_code import Recipe, Step, result

    class MyRecipe(Recipe):
        class MyStep(Step):
            """ This is my first step """
            output = result('my_file.txt')

            def instructions(self):
                self.output.write_text('my data')


The recipe includes a class method, :func:`~Recipe.execute`, which will execute
the defined instructions, and generate a pair of files in the specified
directory.

 1. A data file at the path `data/my_file.txt`, containing the text "my data"
 2. A metadata file at the path `metadata/my_file.txt.json` containing details
    about the file, including the description in the step docstring, a checksum
    of the python code used to define the instructions, and a checksum of the
    data file


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   self
   tutorial
   example
   reference

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
