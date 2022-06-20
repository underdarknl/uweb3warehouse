from collections import namedtuple
from decimal import Decimal

import pytest

from tests.products.fixtures import product, product_price, product_prices, products
from warehouse.products import helpers, model


class TestProductDTOService:
    @pytest.mark.parametrize(
        "fixture, expected",
        [
            (
                "product",
                helpers.ProductDTO(
                    **{
                        "product": 1,
                        "name": "Product 1",
                        "sku": "sku-1",
                        "vat": Decimal(20.5),
                    }
                )._asdict(),
            ),
            (
                "products",
                [
                    helpers.ProductDTO(
                        **{
                            "product": 1,
                            "name": "Product 1",
                            "sku": "sku-1",
                            "vat": Decimal(20.5),
                        }
                    )._asdict(),
                    helpers.ProductDTO(
                        **{
                            "product": 2,
                            "name": "Product 2",
                            "sku": "sku-2",
                            "vat": Decimal(20.5),
                        }
                    )._asdict(),
                    helpers.ProductDTO(
                        **{
                            "product": 3,
                            "name": "Product 3",
                            "sku": "sku-3",
                            "vat": Decimal(20.5),
                        }
                    )._asdict(),
                ],
            ),
        ],
    )
    def test_products_to_dto(self, fixture, expected, request):
        test_input = request.getfixturevalue(fixture)
        assert expected == helpers.ProductDTOService().to_dto(test_input)

    def test_empty_list_to_dto(self):
        assert [] == helpers.ProductDTOService().to_dto([])

    def test_unsupported_type(self):
        unsupported_type = namedtuple("unsupported_type", "name product vat sku")
        data = unsupported_type(
            name="Product 1", product=1, vat=Decimal(20.5), sku="sku-1"
        )
        with pytest.raises(TypeError):
            helpers.ProductDTOService().to_dto(data)

    def test_convert_generator(self):
        products = [
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
        ]
        assert [
            helpers.ProductDTO(
                **{
                    "product": 1,
                    "name": "Product 1",
                    "sku": "sku-1",
                    "vat": Decimal(20.5),
                }
            )._asdict(),
        ] == helpers.ProductDTOService().to_dto(
            (p for p in products)
        )  # Create a generator


class TestProductPriceDTOService:
    @pytest.mark.parametrize(
        "fixture, expected",
        [
            (
                "product_price",
                helpers.ProductPriceDTO(
                    **{
                        "ID": 1,
                        "start_range": 1,
                        "price": Decimal(25),
                    }
                )._asdict(),
            ),
            (
                "product_prices",
                [
                    helpers.ProductPriceDTO(
                        **{
                            "ID": 1,
                            "start_range": 1,
                            "price": Decimal(25),
                        }
                    )._asdict(),
                    helpers.ProductPriceDTO(
                        **{
                            "ID": 2,
                            "start_range": 2,
                            "price": Decimal(20),
                        }
                    )._asdict(),
                    helpers.ProductPriceDTO(
                        **{
                            "ID": 3,
                            "start_range": 3,
                            "price": Decimal(15),
                        }
                    )._asdict(),
                ],
            ),
        ],
    )
    def test_products_to_dto(self, fixture, expected, request):
        test_input = request.getfixturevalue(fixture)
        assert expected == helpers.ProductPriceDTOService().to_dto(test_input)

    def test_empty_list_to_dto(self):
        assert [] == helpers.ProductPriceDTOService().to_dto([])

    def test_unsupported_type(self):
        unsupported_type = namedtuple(
            "unsupported_type", "ID product price start_range"
        )
        data = unsupported_type(
            ID="Product 1", product=1, price=Decimal(20.5), start_range=1
        )
        with pytest.raises(TypeError):
            helpers.ProductPriceDTOService().to_dto(data)

    def test_convert_generator(self):
        prices = [
            model.Productprice(
                None,
                {"ID": 1, "product": 1, "price": Decimal(25), "start_range": 1},
                False,
            ),
        ]
        assert [
            helpers.ProductPriceDTO(
                **{
                    "ID": 1,
                    "start_range": 1,
                    "price": Decimal(25),
                }
            )._asdict(),
        ] == helpers.ProductPriceDTOService().to_dto(
            (p for p in prices)
        )  # Create a generator for testing
