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
        self.forms.register_form("cancel_order", forms.CancelOrderForm)

    @uweb3.decorators.ContentType("application/json")
    @apiuser
    @json_error_wrapper
    def CreateOrder(self):
        form = self.forms.get_form("create_order")
        order_form = form.from_json(self.post.__dict__)  # type: ignore

        if not order_form.validate():
            return order_form.errors

        return model.Order.Create(self.connection, order_form.data)

    @uweb3.decorators.ContentType("application/json")
    @apiuser
    @json_error_wrapper
    def CancelOrder(self):
        form = self.forms.get_form("cancel_order")
        cancel_form = form.from_json(self.post.__dict__)  # type: ignore

        if not cancel_form.validate():
            return cancel_form.errors

        return self.post.__dict__

    @uweb3.decorators.ContentType("application/json")
    @apiuser
    @json_error_wrapper
    def ConvertReservationToRealOrder(self):
        form = self.forms.get_form("cancel_order")
        cancel_form = form.from_json(self.post.__dict__)  # type: ignore

        if not cancel_form.validate():
            return cancel_form.errors

        return self.post.__dict__

    @uweb3.decorators.ContentType("application/json")
    @apiuser
    @json_error_wrapper
    def ListOrders(self):
        orders: list[model.Order] = []
        for order in model.Order.List(self.connection):
            order["order_products"] = list(order.OrderProducts())
            orders.append(order)
        return orders
