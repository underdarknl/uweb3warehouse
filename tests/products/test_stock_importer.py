import pytest

from tests.products.fixtures import products
from warehouse.products.helpers import StockImporter


class TestStockImporter:
    def test_parse(self, products):
        importer = StockImporter(
            {
                "amount": "Op voorraad",
                "name": "Product",
            }
        )
        data = [[{"Op voorraad": 20, "Product": "Product 1"}]]
        processed, unprocessed = importer.Import(data, products)

        assert len(processed) == 1
        assert len(unprocessed) == 0

        assert processed[0].parsed_product["name"] == "Product 1"
        # Make sure it matched the correct supplier product
        assert processed[0].supplier_product["sku"] == "sku-1"
        assert processed[0].parsed_product["amount"] == 20
