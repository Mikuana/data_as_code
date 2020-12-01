import pandas as pd

from data_as_code.main import Product, Lineage, Recipe


def test_load_data(product_vanilla: Product):
    assert isinstance(product_vanilla.load(), pd.DataFrame)


def test_lineage(product_vanilla: Product):
    assert isinstance(product_vanilla.lineage, Lineage)


def test_recipe(product_vanilla: Product):
    assert isinstance(product_vanilla.recipe, Recipe)
