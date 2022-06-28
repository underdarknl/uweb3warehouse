import pytest
from io import StringIO
from tests.products.fixtures import products
from warehouse.products.helpers import CSVParser, CsvImporter


@pytest.fixture(scope="function")
def fake_file():
    string = """name,product,brand,reference
Product 1,test_product,test_brand,test_reference
    """
    f = StringIO(string)
    f.seek(0)
    yield f


class TestCsvImporter:
    @pytest.mark.parametrize(
        "columns, retrieved_data",
        [
            (
                ("name",),
                [{"name": "Product 1"}],
            ),
            (
                ("product",),
                [{"product": "test_product"}],
            ),
            (
                ("brand",),
                [{"brand": "test_brand"}],
            ),
            (
                ("reference",),
                [{"reference": "test_reference"}],
            ),
            (
                ("name", "reference",),
                [{"name": "Product 1", "reference": "test_reference"}],
            ),
            (
                ("name", "product", "brand"),
                [
                    {
                        "name": "Product 1",
                        "product": "test_product",
                        "brand": "test_brand",
                    }
                ],
            ),
            (
                ("name", "brand"),
                [{"name": "Product 1", "brand": "test_brand"}],
            ),
        ],
    )
    def test_found_columns(self, fake_file, columns, retrieved_data):
        data = CSVParser(fake_file, columns).Parse()

        # Make sure that the data returned matches the expected retrieved data.
        # retrieved_data contains the expected columns and their values
        assert data == retrieved_data

    @pytest.mark.parametrize(
        "columns, expected",
        [
            (
                ("name", "product", "brand"),
                {"name": "Product 1", "amount": "test_brand"},
            ),
            (
                ("name", "brand"),
                {"name": "Product 1", "amount": "test_brand"},
            ),
        ],
    )
    def test_import(self, fake_file, products, columns, expected):
        data = CSVParser(fake_file, columns).Parse()

        importer = CsvImporter({"name": "name", "amount": "brand"})
        processed, unprocessed = importer.Import(data, products)

        assert len(processed) == 1
        assert processed[0].parsed_product == expected
