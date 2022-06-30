import decimal
import inspect
from io import StringIO

import pytest

from tests.products.fixtures import supplier_products
from warehouse.products.helpers import CustomImporters, SolarClarity
from warehouse.products.helpers.importers.custom_importers import to_decimal


class MockMissingImporter:
    def __init__(self, connection, supplierID):
        self.connection = connection
        self.supplierID = supplierID

    def Import(self, record: dict):
        return record


@pytest.fixture(scope="function")
def solar_file():
    string = inspect.cleandoc(
        """
        article_number,article_name,brand,product_reference,packing_unit,items_per_packing_unit,net,gross,quantity_step,datasheet_url_nl,datasheet_url_en,warranty_years
        1234,Product 1,brand,product_reference,packing_unit,1,net,1,quantity_step,datasheet_url_nl,datasheet_url_en,warranty_years
        5678,Product 1,brand,product_reference,packing_unit,10,net,1,quantity_step,datasheet_url_nl,datasheet_url_en,warranty_years
        9123,Product 2,brand,product_reference,packing_unit,1,net,1,quantity_step,datasheet_url_nl,datasheet_url_en,warranty_years
        9124,Product 3,brand,product_reference,packing_unit,1,net,1.25,quantity_step,datasheet_url_nl,datasheet_url_en,warranty_years
    """  # noqa E501
    )
    yield StringIO(string)


@pytest.fixture(scope="function")
def importer(solar_file):
    factory = CustomImporters()
    importer = factory.get_registered_item(
        "Solarclarity",
        file=solar_file,
        connection=None,
        supplierID=None,
    )
    yield importer


@pytest.fixture(scope="function")
def importer_missing(solar_file):
    factory = CustomImporters()
    importer = factory.get_registered_item(
        "Solarclarity (import missing products)",
        file=solar_file,
        connection=None,
        supplierID=None,
        importer=MockMissingImporter,
    )
    yield importer


class TestSolarClarityCustomImporter:
    def test_importing(self, importer: SolarClarity, supplier_products):
        """Test to stk values are imported.
        Currently there is no support for SupplierProduct prices
        based on quantity purchased."""
        processed, _ = importer.Import(supplier_products)

        for pair in processed:
            assert 1 == pair.parsed_product["items_per_packing_unit"]
            assert True is isinstance(pair.supplier_product["cost"], decimal.Decimal)

    def test_SolarClarity(self, importer: SolarClarity, supplier_products):
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

    @pytest.mark.parametrize(
        "input, expected",
        [
            (
                [
                    {
                        "items_per_packing_unit": 1,
                        "article_name": "Product 1",
                        "article_number": 1,
                    }
                ],
                (1, 0, 0),
            ),
            (
                [
                    {
                        "items_per_packing_unit": 10,
                        "article_name": "Product 1",
                        "article_number": 1,
                    },
                    {
                        "items_per_packing_unit": 1,
                        "article_name": "Product 1",
                        "article_number": 1,
                    },
                    {
                        "items_per_packing_unit": 1,
                        "article_name": "Product 2",
                        "article_number": 2,
                    },
                ],
                (2, 0, 0),
            ),
            (
                [
                    {
                        "items_per_packing_unit": 10,
                        "article_name": "Product 1",
                        "article_number": 1,
                    },
                    {
                        "items_per_packing_unit": 1,
                        "article_name": "Product 1",
                        "article_number": 1,
                    },
                    {
                        "items_per_packing_unit": 1,
                        "article_name": "Product 2",
                        "article_number": 2,
                    },
                    {
                        "items_per_packing_unit": 1,
                        "article_name": "Unknown product",
                        "article_number": 3,
                    },
                ],
                (2, 1, 0),
            ),
        ],
    )
    def test_processing(
        self,
        importer: SolarClarity,
        input,
        expected,
        supplier_products,
    ):
        """Ensure that products that are not available in the database
        are not processed and end up in the correct list."""
        importer.products = supplier_products
        importer._process(input)

        PROCESSED = 0
        UNPROCESSED = 1
        NEW_IMPORTS = 2

        assert expected[PROCESSED] == len(importer._processed_products)
        assert expected[UNPROCESSED] == len(importer._unprocessed_products)
        assert expected[NEW_IMPORTS] == len(importer._new_imports)

    @pytest.mark.parametrize(
        "input, expected",
        [
            (
                [
                    {
                        "items_per_packing_unit": 1,
                        "article_name": "Product 1",
                        "article_number": 1,
                    }
                ],
                (1, 0, 0),
            ),
            (
                [
                    {
                        "items_per_packing_unit": 10,
                        "article_name": "Product 1",
                        "article_number": 1,
                    },
                    {
                        "items_per_packing_unit": 1,
                        "article_name": "Product 1",
                        "article_number": 1,
                    },
                    {
                        "items_per_packing_unit": 1,
                        "article_name": "Product 2",
                        "article_number": 2,
                    },
                ],
                (2, 0, 0),
            ),
            (
                [
                    {
                        "items_per_packing_unit": 10,
                        "article_name": "Product 1",
                        "article_number": 1,
                    },
                    {
                        "items_per_packing_unit": 1,
                        "article_name": "Product 1",
                        "article_number": 1,
                    },
                    {
                        "items_per_packing_unit": 1,
                        "article_name": "Product 2",
                        "article_number": 2,
                    },
                    {
                        "items_per_packing_unit": 1,
                        "article_name": "Unknown product",
                        "article_number": 3,
                    },
                ],
                (2, 0, 1),
            ),
            (
                [
                    {
                        "items_per_packing_unit": 10,
                        "article_name": "Product 1",
                        "article_number": 1,
                    },
                    {
                        "items_per_packing_unit": 2,
                        "article_name": "Product 1",
                        "article_number": 1,
                    },
                ],
                (0, 0, 0),
            ),
        ],
    )
    def test_processing_missing(
        self,
        importer_missing: SolarClarity,
        input,
        expected,
        supplier_products,
    ):
        """Ensure that missing products are indeed imported to the database"""
        importer_missing.products = supplier_products
        importer_missing._process(input)

        PROCESSED = 0
        UNPROCESSED = 1
        NEW_IMPORTS = 2

        assert expected[PROCESSED] == len(importer_missing._processed_products)
        assert expected[UNPROCESSED] == len(importer_missing._unprocessed_products)
        assert expected[NEW_IMPORTS] == len(importer_missing._new_imports)
