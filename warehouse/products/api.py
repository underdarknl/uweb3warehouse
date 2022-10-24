#!/usr/bin/python
"""Request handlers for the uWeb3 warehouse inventory software"""

import uweb3

from warehouse import basepages
from warehouse.common.decorators import apiuser, json_error_wrapper
from warehouse.products import helpers, model

# TODO: Add pydantic for DTOS.
class PageMaker(basepages.PageMaker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_user = None
        self.apikey = None
        self.dto_service = helpers.DtoManager()

    @uweb3.decorators.ContentType("application/json")
    @json_error_wrapper
    @apiuser
    def JsonProducts(self):
        """Returns the product Json"""
        product_converter = self.dto_service.get_registered_item("product")
        products = product_converter.to_dto(model.Product.List(self.connection))
        return {"products": products}

    @uweb3.decorators.ContentType("application/json")
    @json_error_wrapper
    @apiuser
    def JsonProduct(self, sku):
        """Returns the product Json"""
        product = model.Product.FromSku(self.connection, sku)
        product_converter = self.dto_service.get_registered_item("product")
        product_dto = product_converter.to_dto(product)

        return product_dto | {
            "currentstock": product.currentstock,
            "possiblestock": product.possiblestock["available"],
        }

    @uweb3.decorators.ContentType("application/json")
    @json_error_wrapper
    @apiuser
    def JsonProductSearch(self, sku):
        """Returns the product Json"""
        product = model.Product.FromSku(self.connection, sku)

        product_converter = self.dto_service.get_registered_item("product")
        product_dto = product_converter.to_dto(product)

        product_price_converter = self.dto_service.get_registered_item("product_price")
        prices = product_price_converter.to_dto(
            model.Productprice.ProductPrices(self.connection, product)
        )

        return product_dto | {
            "stock": product.currentstock,
            "possible_stock": product.possiblestock["available"],
            "prices": prices,
        }

    @uweb3.decorators.ContentType("application/json")
    @json_error_wrapper
    @apiuser
    def FindProduct(self, query):
        products = list(model.Product.Search(self.connection, query))

        if not products:
            return {"products": []}

        product_price_converter = self.dto_service.get_registered_item("product_price")

        for product in products:
            product["prices"] = product_price_converter.to_dto(
                model.Productprice.ProductPrices(self.connection, product)
            )
            product["currentstock"] = product.currentstock
            product["possiblestock"] = product.possiblestock["available"]
        return {"products": products}
