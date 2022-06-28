import decimal
import pytest
from io import StringIO
from tests.products.fixtures import supplier_products
from warehouse.products.helpers import CustomImporters
import inspect

from warehouse.products.helpers.importers.custom_importers import SolarCity


@pytest.fixture(scope="function")
def solar_file():
    string = inspect.cleandoc(
        """
        article_number,article_name,brand,product_reference,packing_unit,items_per_packing_unit,net,gross,quantity_step,datasheet_url_nl,datasheet_url_en,warranty_years
        1234,Product 1,brand,product_reference,packing_unit,1,net,1,quantity_step,datasheet_url_nl,datasheet_url_en,warranty_years
        1234,Product 1,brand,product_reference,packing_unit,10,net,1,quantity_step,datasheet_url_nl,datasheet_url_en,warranty_years
        1234,Product 2,brand,product_reference,packing_unit,1,net,1,quantity_step,datasheet_url_nl,datasheet_url_en,warranty_years
        1234,Product 3,brand,product_reference,packing_unit,1,net,1.25,quantity_step,datasheet_url_nl,datasheet_url_en,warranty_years
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
    def test_only_import_singular_items(self, importer: SolarCity, supplier_products):
        processed, unprocessed = importer.Import(supplier_products)

        for pair in processed:
            assert 1 == pair.parsed_product["items_per_packing_unit"]

    def test_correct_currency_conversion(self, importer: SolarCity, supplier_products):
        processed, unprocessed = importer.Import(supplier_products)
        for pair in processed:
            assert True == isinstance(pair.supplier_product["cost"], decimal.Decimal)

    def test_solarcity(self, importer: SolarCity, supplier_products):
        processed, unprocessed = importer.Import(supplier_products)
