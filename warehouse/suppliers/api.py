#!/usr/bin/python
"""Request handlers for the uWeb3 warehouse inventory software"""
import uweb3

from warehouse import basepages
from warehouse.common.decorators import apiuser, json_error_wrapper
from warehouse.suppliers import model


class PageMaker(basepages.PageMaker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_user = None
        self.apikey = None

    @uweb3.decorators.ContentType("application/json")
    @json_error_wrapper
    @apiuser
    def find_supplier_product(self):
        name = self.get.getfirst("name")
        supplier = self.get.getfirst("supplier")
        result = list(model.Supplierproduct.NameLike(self.connection, supplier, name))
        if result:
            return result
        return []
