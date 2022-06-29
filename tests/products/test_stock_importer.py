import pytest

from tests.products.fixtures import supplier_products
from warehouse.products.helpers import StockImporter


class TestStockImporter:
    @pytest.mark.parametrize(
        "data, expected",
        [
            (
                [[{"Op voorraad": 20, "Product": "Product 1"}]],
                {"name": "Product 1", "supplier_sku": "sku-1", "amount": 20},
            ),
            (
                [[{"Op voorraad": 100, "Product": "Product 2"}]],
                {"name": "Product 2", "supplier_sku": "sku-2", "amount": 100},
            ),
            (
                [[{"Op voorraad": 5, "Product": "Product 3"}]],
                {"name": "Product 3", "supplier_sku": "sku-3", "amount": 5},
            ),
        ],
    )
    def test_parse(self, supplier_products, data, expected):
        importer = StockImporter(
            {
                "amount": "Op voorraad",
                "name": "Product",
            }
        )
        processed, unprocessed = importer.Import(data, supplier_products)

        assert len(processed) == 1
        assert len(unprocessed) == 0

        assert expected["name"] == processed[0].parsed_product["name"]
        assert expected["supplier_sku"] == processed[0].supplier_product["supplier_sku"]
        assert expected["amount"] == processed[0].parsed_product["amount"]

    @pytest.mark.parametrize(
        "data, expected",
        [
            (
                [[{"Op voorraad": 20, "Product": "Product 12"}]],
                [{"name": "Product 12", "amount": 20}],
            ),
            (
                [
                    [{"Op voorraad": 20, "Product": "Product 1"}],
                    [{"Op voorraad": 10, "Product": "Product 12"}],
                    [{"Op voorraad": 5, "Product": "Pro"}],
                ],
                [{"name": "Product 12", "amount": 10}, {"name": "Pro", "amount": 5}],
            ),
        ],
    )
    def test_parse_no_result(self, supplier_products, data, expected):
        importer = StockImporter(
            {
                "amount": "Op voorraad",
                "name": "Product",
            }
        )
        _, unprocessed = importer.Import(data, supplier_products)
        assert unprocessed == expected

    def test_wrong_mapping(self, supplier_products):
        importer = StockImporter(
            {
                "amount": "Op voorraad",
                "name": "Product",
            }
        )
        data = [{"wrong_key": 20, "Product": "Product 1"}]
        with pytest.raises(TypeError):
            importer.Import(data, supplier_products)
