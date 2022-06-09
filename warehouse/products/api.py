#!/usr/bin/python
"""Request handlers for the uWeb3 warehouse inventory software"""

import uweb3
from uweb3.helpers import transaction

from warehouse import basepages
from warehouse.common.decorators import apiuser, json_error_wrapper
from warehouse.products import helpers, model


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
        return products

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
    def JsonProductStock(self, sku):
        """Updates the stock for a product, assembling if needed

        Send negative amount to Sell a product, positive amount to put product back
        into stock"""
        raise Exception("Not implemented yet")
        # product = model.Product.FromSku(self.connection, sku)
        # amount = int(self.post.get("amount", -1))
        # currentstock = product.currentstock
        # if (
        #     amount < 0 and abs(amount) > currentstock  # only assemble when we sell
        # ):  # only assemble when we have not enough stock
        #     try:
        #         product.Assemble(
        #             abs(amount)
        #             - currentstock,  # only assemble what is missing for this sale
        #             "Assembly for %s" % self.post.get("reference")
        #             if "reference" in self.post
        #             else None,
        #         )
        #     except model.AssemblyError as error:
        #         raise ValueError(error.args[0])

        # # by now we should have enough products in stock, one way or another
        # model.Stock.Create(
        #     self.connection,
        #     {
        #         "product": product,
        #         "amount": amount,
        #         "reference": self.post.get("reference", ""),
        #     },
        # )
        # model.Product.commit(self.connection)
        # return {"stock": product.currentstock, "possible_stock": product.possiblestock}

    @uweb3.decorators.ContentType("application/json")
    @json_error_wrapper
    @apiuser
    def JsonProductStockBulk(self):
        products = self.post.get("products")
        with transaction(self.connection, model.Product):
            for product in products:
                helpers.update_stock(
                    self.connection,
                    product["name"],
                    product["quantity"],
                    self.post.get("reference", ""),
                )
        return {"products": products}
