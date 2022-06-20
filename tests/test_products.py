from collections import namedtuple
from decimal import Decimal

import pytest

from tests.fixtures import product, products
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
        product = (
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
        )
        assert [
            helpers.ProductDTO(
                **{
                    "product": 1,
                    "name": "Product 1",
                    "sku": "sku-1",
                    "vat": Decimal(20.5),
                }
            )._asdict(),
        ] == helpers.ProductDTOService().to_dto(product)
