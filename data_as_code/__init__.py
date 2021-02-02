from data_as_code import step
from data_as_code._metadata import Input, Reference, Metadata
from data_as_code._plotly import show_lineage
from data_as_code._recipe import Recipe, Keep

__version__ = '0.0.0'


class Product:
    """
    A package which is the result of executing a recipe. Includes cases (in
    the form of a file), metadata (including lineage), and the recipe itself.
    """
