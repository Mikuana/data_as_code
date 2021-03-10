Examples
############



jkfd::

    import csv
    import itertools

    from data_as_code._step import Step
    from data_as_code import Recipe, ingredient, PRODUCT


    class MyRecipe(Recipe):
        class Abc(Step):
            def instructions(self):
                self.output.write_text(','.join(['a', 'b', 'c']))

        class OneTwoThree(Step):
            def instructions(self):
                self.output.write_text(','.join(['1', '2', '3']))

        class YouAndMe(Step):
            role = PRODUCT
            output = 'cartesian.csv'
            x = ingredient('Abc')
            y = ingredient('OneTwoThree')

            def instructions(self):
                x = self.x.read_text().split(',')
                y = self.y.read_text().split(',')

                with self.output.open('w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['letter', 'number'])
                    for row in itertools.product(x, y):
                        writer.writerow([row])

    MyRecipe().execute()


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
