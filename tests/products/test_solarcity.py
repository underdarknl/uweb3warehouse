import decimal
import inspect
from io import StringIO

import pytest

from tests.products.fixtures import supplier_products
from warehouse.products.helpers import CustomImporters
from warehouse.products.helpers.importers.custom_importers import SolarCity, to_decimal


@pytest.fixture(scope="function")
def solar_file():
    string = inspect.cleandoc(
        """
        article_number,article_name,brand,product_reference,packing_unit,items_per_packing_unit,net,gross,quantity_step,datasheet_url_nl,datasheet_url_en,warranty_years
        1234,Product 1,brand,product_reference,packing_unit,1,net,1,quantity_step,datasheet_url_nl,datasheet_url_en,warranty_years
        5678,Product 1,brand,product_reference,packing_unit,10,net,1,quantity_step,datasheet_url_nl,datasheet_url_en,warranty_years
        9123,Product 2,brand,product_reference,packing_unit,1,net,1,quantity_step,datasheet_url_nl,datasheet_url_en,warranty_years
        9124,Product 3,brand,product_reference,packing_unit,1,net,1.25,quantity_step,datasheet_url_nl,datasheet_url_en,warranty_years
    """
    )
    yield StringIO(string)


@pytest.fixture(scope="function", autouse=True)
def importer(solar_file):
    factory = CustomImporters()
    builder = factory.get_registered_item("Solarcity")
    importer = builder(solar_file)
    yield importer


class TestSolarCityCustomImporter:
    def test_importing(self, importer: SolarCity, supplier_products):
        """Test to stk values are imported.
        Currently there is no support for SupplierProduct prices based on quantity purchased."""
        processed, _ = importer.Import(supplier_products)

        for pair in processed:
            assert 1 == pair.parsed_product["items_per_packing_unit"]
            assert True is isinstance(pair.supplier_product["cost"], decimal.Decimal)

    def test_solarcity(self, importer: SolarCity, supplier_products):
        """Ensure the correct results are found"""
        processed, unprocessed = importer.Import(supplier_products)

        assert processed[0].parsed_product == {
            "article_number": 1234,
            "article_name": "Product 1",
            "product_reference": "product_reference",
            "packing_unit": "packing_unit",
            "items_per_packing_unit": 1,
            "gross": 1.0,
        }
        assert processed[1].parsed_product == {
            "article_number": 9123,
            "article_name": "Product 2",
            "product_reference": "product_reference",
            "packing_unit": "packing_unit",
            "items_per_packing_unit": 1,
            "gross": 1.0,
        }
        assert processed[2].parsed_product == {
            "article_number": 9124,
            "article_name": "Product 3",
            "product_reference": "product_reference",
            "packing_unit": "packing_unit",
            "items_per_packing_unit": 1,
            "gross": 1.25,
        }
        assert len(processed) == 3

    @pytest.mark.parametrize(
        "input, expected",
        [
            ("10", decimal.Decimal(10)),
            ("10.25", decimal.Decimal(10.25)),
            ("0.25", decimal.Decimal(0.25)),
            ("100,25", decimal.Decimal(100.25)),
            (0.25, decimal.Decimal(0.25)),
            (1, decimal.Decimal(1)),
            ("€20", decimal.Decimal(20)),
            ("€20.25", decimal.Decimal(20.25)),
            ("€20,25", decimal.Decimal(20.25)),
        ],
    )
    def test_to_decimal(self, input, expected):
        """Test to ensure all values are converted to the appropriate decimal
        value"""
        assert expected == to_decimal(input)
