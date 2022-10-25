#!/usr/bin/python
"""Request handlers for the uWeb3 warehouse inventory software"""

import uweb3
from pydantic import BaseModel
from typing import Optional

from warehouse import basepages
from warehouse.common.decorators import apiuser, json_error_wrapper
from warehouse.products import model


class ProductPrices(BaseModel):
    price: str
    start_range: int


class ProductDTO(BaseModel):
    ID: int
    sku: str
    name: str
    prices: Optional[list[ProductPrices]]
    currentstock: Optional[int]
    possiblestock: Optional[int]


# TODO: Add pydantic for DTOS.
class PageMaker(basepages.PageMaker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_user = None
        self.apikey = None

    @uweb3.decorators.ContentType("application/json")
    @json_error_wrapper
    @apiuser
    def JsonProducts(self):
        """Returns the product Json"""
        products = model.Product.List(self.connection)
        return {
            "products": [
                ProductDTO(**product).dict(exclude_unset=True) for product in products
            ]
        }

    @uweb3.decorators.ContentType("application/json")
    @json_error_wrapper
    @apiuser
    def JsonProduct(self, sku):
        """Returns the product Json"""
        product = model.Product.FromSku(self.connection, sku)

        return ProductDTO(
            **product
            | {
                "stock": product.currentstock,
                "possible_stock": product.possiblestock["available"],
            }
        ).dict(exclude_unset=True)

    @uweb3.decorators.ContentType("application/json")
    @json_error_wrapper
    @apiuser
    def JsonProductSearch(self, sku):
        """Returns the product Json"""
        product = model.Product.FromSku(self.connection, sku)

        product_price_converter = self.dto_service.get_registered_item("product_price")
        prices = product_price_converter.to_dto(
            model.Productprice.ProductPrices(self.connection, product)
        )

        return ProductDTO(
            **product
            | {
                "stock": product.currentstock,
                "possible_stock": product.possiblestock["available"],
                "prices": prices,
            }
        ).dict(exclude_unset=True)

    @uweb3.decorators.ContentType("application/json")
    @json_error_wrapper
    @apiuser
    def FindProduct(self, query):
        products = list(model.Product.Search(self.connection, query, limit=10))

        if not products:
            return {"products": []}

        product_price_converter = self.dto_service.get_registered_item("product_price")

        for product in products:
            product["prices"] = product_price_converter.to_dto(
                model.Productprice.ProductPrices(self.connection, product)
            )
            product["currentstock"] = product.currentstock
            product["possiblestock"] = product.possiblestock["available"]

        return {
            "products": [
                ProductDTO(**product).dict(exclude_unset=True) for product in products
            ]
        }
