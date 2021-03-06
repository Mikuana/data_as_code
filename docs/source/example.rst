Examples
############



jkfd::

    with Recipe('data_package') as r:
        s1 = premade.source_http(r, 'https://data-url.com/data.csv')

        class ChangeDelimiter(Step):
            """ Read CSV and rewrite file with star(*) delimiter """
            x = ingredient(s1)
            output = Path('starred.csv')

            def instructions(self):
                with self.output.open('w', newline='') as new:
                    writer = csv.writer(new, delimiter='*')
                    with self.x.path.open(newline='') as orig:
                        reader = csv.reader(orig)
                        for row in reader:
                            writer.writerow(row)


        ChangeDelimiter(r)

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
