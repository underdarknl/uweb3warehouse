#!/usr/bin/python
"""Request handlers for the uWeb3 warehouse inventory software"""

from http import HTTPStatus
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
        self.forms.register_form("id_or_ref", forms.OrderFromIdOrReferenceForm)

    @uweb3.decorators.ContentType("application/json")
    @apiuser
    @json_error_wrapper
    def CreateOrder(self):
        form = self.forms.get_form("create_order")
        order_form = form.from_json(self.post.__dict__)  # type: ignore

        if not order_form.validate():
            return uweb3.Response(
                {
                    "error": True,
                    "errors": order_form.errors,
                    "http_status": HTTPStatus.CONFLICT,
                },
                httpcode=HTTPStatus.CONFLICT,
            )
        return model.Order.Create(self.connection, order_form.data)

    @uweb3.decorators.ContentType("application/json")
    @apiuser
    @json_error_wrapper
    def CancelOrder(self):
        form = self.forms.get_form("id_or_ref")
        cancel_form: forms.OrderFromIdOrReferenceForm = form.from_json(  # type: ignore
            self.post.__dict__,
        )

        if not cancel_form.validate():
            return uweb3.Response(
                {
                    "error": True,
                    "errors": cancel_form.errors,
                    "http_status": HTTPStatus.CONFLICT,
                },
                httpcode=HTTPStatus.CONFLICT,
            )

        if cancel_form.ID.data:
            order: model.Order = model.Order.FromPrimary(
                self.connection, cancel_form.ID.data
            )
        else:
            order: model.Order = model.Order.FromReference(
                self.connection, cancel_form.reference.data
            )
        order.Delete()
        return order

    @uweb3.decorators.ContentType("application/json")
    @apiuser
    @json_error_wrapper
    def ConvertReservationToRealOrder(self):
        form = self.forms.get_form("id_or_ref")
        order_form = form.from_json(self.post.__dict__)  # type: ignore

        if not order_form.validate():
            return order_form.errors

        if order_form.ID.data:
            order: model.Order = model.Order.FromPrimary(
                self.connection, order_form.ID.data
            )
        else:
            order: model.Order = model.Order.FromReference(
                self.connection, order_form.reference.data
            )

        if order["status"] != model.OrderStatus.RESERVATION:
            return uweb3.Response(
                {
                    "error": True,
                    "errors": "No order with reservation status was found for this ID or reference.",
                    "http_status": HTTPStatus.NOT_FOUND,
                },
                httpcode=HTTPStatus.NOT_FOUND,
            )

        order.ReservationToNewOrder()
        return order

    @uweb3.decorators.ContentType("application/json")
    @apiuser
    @json_error_wrapper
    def ListOrders(self):
        orders: list[model.Order] = []
        for order in model.Order.List(self.connection):
            order["order_products"] = list(order.OrderProducts())
            orders.append(order)
        return orders
