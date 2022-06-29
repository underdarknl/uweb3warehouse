from decimal import Decimal
from io import StringIO

import pytest
import uweb3

from warehouse.products import model
from warehouse.products.helpers import StockParser
from warehouse.suppliers.model import Supplierproduct


class MockRecord(uweb3.model.Record):
    def Save(self):
        difference = self._Changes()
        if difference:
            self._record.update(difference)

    def Refresh(self):
        return self._record


class FakeProduct(model.Product, MockRecord):
    """Class for unittest mocking purposes."""


class FakeSupplierProduct(Supplierproduct, MockRecord):
    """Class for unittest mocking purposes."""


@pytest.fixture(scope="module")
def products():
    yield [
        FakeProduct(
            None,
            {
                "ID": 1,
                "name": "Product 1",
                "sku": "sku-1",
                "vat": Decimal(20.5),
                "price": (100.25),
                "ean": "ean-1",
                "description": "description-1",
                "assemblycosts": Decimal(1),
            },
            False,
        ),
        FakeProduct(
            None,
            {
                "ID": 2,
                "name": "Product 2",
                "sku": "sku-2",
                "vat": Decimal(20.5),
                "price": (100.25),
                "ean": "ean-2",
                "description": "description-2",
                "assemblycosts": Decimal(1),
            },
            False,
        ),
        FakeProduct(
            None,
            {
                "ID": 3,
                "name": "Product 3",
                "sku": "sku-3",
                "vat": Decimal(20.5),
                "price": (100.25),
                "ean": "ean-3",
                "description": "description-3",
                "assemblycosts": Decimal(1),
            },
            False,
        ),
    ]


@pytest.fixture(scope="module")
def supplier_products():
    yield [
        FakeSupplierProduct(
            None,
            {
                "ID": 1,
                "name": "Product 1",
                "supplier_sku": "sku-1",
                "vat": Decimal(20.5),
                "cost": (100.25),
            },
            False,
        ),
        FakeSupplierProduct(
            None,
            {
                "ID": 2,
                "name": "Product 2",
                "supplier_sku": "sku-2",
                "vat": Decimal(20.5),
                "cost": (100.25),
            },
            False,
        ),
        FakeSupplierProduct(
            None,
            {
                "ID": 3,
                "name": "Product 3",
                "supplier_sku": "sku-3",
                "vat": Decimal(20.5),
                "cost": (100.25),
            },
            False,
        ),
    ]


@pytest.fixture(scope="module")
def product():
    yield model.Product(
        None,
        {
            "ID": 1,
            "name": "Product 1",
            "sku": "sku-1",
            "vat": Decimal(20.5),
            "price": (100.25),
            "ean": "ean-1",
            "description": "description-1",
            "assemblycosts": Decimal(1),
        },
        False,
    )


@pytest.fixture(scope="module")
def product_price():
    yield model.Productprice(
        None, {"ID": 1, "product": 1, "price": Decimal(25), "start_range": 1}, False
    )


@pytest.fixture(scope="module")
def product_prices():
    yield [
        model.Productprice(
            None,
            {"ID": 1, "product": 1, "price": Decimal(25), "start_range": 1},
            False,
        ),
        model.Productprice(
            None,
            {"ID": 2, "product": 1, "price": Decimal(20), "start_range": 2},
            False,
        ),
        model.Productprice(
            None,
            {"ID": 3, "product": 1, "price": Decimal(15), "start_range": 3},
            False,
        ),
    ]


@pytest.fixture(scope="module")
def basic_file():
    yield StringIO(
        """
            <table>
                <tbody>
                    <tr>
                        <td>Product</td>
                        <td>Aantal</td>
                    </tr>
                    <tr>
                        <td>
                            Optimizer P700
                        </td>
                        <td>
                            20
                        </td>
                    </tr>
                    <tr>
                        <td>
                            Optimizer P650
                        </td>
                        <td>
                            10
                        </td>
                    </tr>
                </tbody>
            </table>
            """
    )


@pytest.fixture(scope="module")
def simple_parser(basic_file):
    yield StockParser(basic_file, ("Product", "Aantal"), ("Product",))
