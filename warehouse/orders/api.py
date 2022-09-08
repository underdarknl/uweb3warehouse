#!/usr/bin/python
"""Request handlers for the uWeb3 warehouse inventory software"""

import uweb3

from warehouse import basepages
from warehouse.common.helpers import FormFactory
from warehouse.common.decorators import apiuser, json_error_wrapper
from warehouse.orders import forms, model

class PageMaker(basepages.PageMaker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_user = None
        self.apikey = None
        self.forms = FormFactory()
        self.forms.register_form("create_order", forms.CreateOrderForm)

    @uweb3.decorators.ContentType("application/json")
    @apiuser
    @json_error_wrapper
    def CreateOrder(self):
        json_data = self.post.__dict__
        form = self.forms.get_form("create_order")
        order_form = form.from_json(json_data)  # type: ignore

        if not order_form.validate():
            return order_form.errors

        model.Order.Create(self.connection, order_form.data)
        return json_data

    @uweb3.decorators.ContentType("application/json")
    @apiuser
    @json_error_wrapper
    def ListOrders(self):
        return {}
