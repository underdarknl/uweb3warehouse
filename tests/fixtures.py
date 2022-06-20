from decimal import Decimal

import pytest

from warehouse.products import model


@pytest.fixture(scope="module")
def products():
    yield [
        model.Product(
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
        model.Product(
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
        model.Product(
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
            None, {"ID": 1, "product": 1, "price": Decimal(25), "start_range": 1}, False
        ),
        model.Productprice(
            None, {"ID": 2, "product": 1, "price": Decimal(20), "start_range": 2}, False
        ),
        model.Productprice(
            None, {"ID": 3, "product": 1, "price": Decimal(15), "start_range": 3}, False
        ),
    ]
