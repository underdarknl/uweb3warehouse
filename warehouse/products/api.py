#!/usr/bin/python
"""Request handlers for the uWeb3 warehouse inventory software"""

import uweb3
from uweb3.helpers import transaction

from warehouse import basepages
from warehouse.common.decorators import apiuser, json_error_wrapper
from warehouse.products import helpers, model, schemas


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
    def JsonProductStockRemove(self):
        data = schemas.BulkStockSchema().load(self.post)

        products = data["products"]
        reference = data["reference"]

        with transaction(self.connection, model.Product):
            for product in products:
                helpers.remove_stock(
                    self.connection, product["sku"], product["quantity"], reference
                )
        return data

    @uweb3.decorators.ContentType("application/json")
    @json_error_wrapper
    @apiuser
    def JsonProductStockBulkAdd(self):
        data = schemas.BulkRefundSchema().load(self.post)

        products = data["products"]
        reference = data["reference"]

        with transaction(self.connection, model.Product):
            for product in products:
                helpers.add_stock(
                    self.connection,
                    product["sku"],
                    product["quantity"],
                    reference,
                )
        return data
