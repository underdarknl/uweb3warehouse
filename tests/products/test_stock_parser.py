from io import StringIO

import pytest

from tests.products.fixtures import basic_file, simple_parser
from warehouse.products.helpers import ProductPair, StockImporter, StockParser


class TestStockParser:
    def test_simple_parse(self, simple_parser):
        """Validates that the parser can parse a simple file."""
        assert [
            [
                {"Product": "Optimizer P700", "Aantal": 20},
                {"Product": "Optimizer P650", "Aantal": 10},
            ]
        ] == simple_parser.Parse()

    def test_missing_keys(self, basic_file):
        """Validates that when a key is missing, the parser will raise an error."""
        parser = StockParser(basic_file, ("Missing key", "Aantal"), ("Product",))
        with pytest.raises(KeyError):
            parser.Parse()

    def test_normalize_values(self):
        """Validate that the parser normalizes the column values that are passed."""
        file = StringIO(
            """
            <table>
                <tbody>
                    <tr>
                        <td>Product</td>
                        <td>Aantal</td>
                    </tr>
                    <tr>
                        <td>
                            Optimizer/P700
                        </td>
                        <td>
                            20
                        </td>
                    </tr>
                </tbody>
            </table>
            """
        )
        parser = StockParser(file, ("Product", "Aantal"), ("Product",))
        assert [
            [
                {"Product": "Optimizer_P700", "Aantal": 20},
            ]
        ] == parser.Parse()

    def test_column_names(self):
        """Validate that the parser can handle custom column names."""
        file = StringIO(
            """
            <table>
                <tbody>
                    <tr>
                        <td>Product name</td>
                        <td>Quantity</td>
                    </tr>
                    <tr>
                        <td>
                            Optimizer P700
                        </td>
                        <td>
                            20
                        </td>
                    </tr>
                </tbody>
            </table>
            """
        )
        parser = StockParser(file, ("Product name", "Quantity"), ("Product name",))
        assert [
            [
                {"Product name": "Optimizer P700", "Quantity": 20},
            ]
        ] == parser.Parse()

    def test_parse_only_wanted_columns(self):
        file = StringIO(
            """
            <table>
                <tbody>
                    <tr>
                        <td>Product name</td>
                        <td>Random column</td>
                        <td>Quantity</td>
                    </tr>
                    <tr>
                        <td>
                            Optimizer P700
                        </td>
                        <td>
                            Some random column
                        </td>
                        <td>
                            20
                        </td>
                    </tr>
                </tbody>
            </table>
            """
        )
        parser = StockParser(file, ("Product name", "Quantity"), ("Product name",))
        assert [
            [
                {"Product name": "Optimizer P700", "Quantity": 20},
            ]
        ] == parser.Parse()

    def test_normalize_target_only(self):
        file = StringIO(
            """
            <table>
                <tbody>
                    <tr>
                        <td>Product name</td>
                        <td>Random column</td>
                        <td>Quantity</td>
                    </tr>
                    <tr>
                        <td>
                            Optimizer P700
                        </td>
                        <td>
                            Some/random/column
                        </td>
                        <td>
                            20
                        </td>
                    </tr>
                </tbody>
            </table>
            """
        )
        parser = StockParser(
            file, ("Product name", "Random column", "Quantity"), ("Product name",)
        )
        assert [
            [
                {
                    "Product name": "Optimizer P700",
                    "Random column": "Some/random/column",
                    "Quantity": 20,
                },
            ]
        ] == parser.Parse()
