import os

import uweb3

from warehouse import basepages
from warehouse.common.decorators import NotExistsErrorCatcher, loggedin
from warehouse.common.helpers import FormFactory, BaseFormServiceBuilder
from warehouse.orders import model, forms


class PageMaker(basepages.PageMaker):
    TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.forms = FormFactory()
        self.forms.register_form(
            "create_order", BaseFormServiceBuilder(form=forms.CreateOrderForm)
        )

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.TemplateParser("orders.html")
    def RequestOrders(self):
        return {
            "orders": list(model.Order.List(self.connection)),
        }

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.TemplateParser("order.html")
    def RequestOrder(self, id):
        order: model.Order = model.Order.FromPrimary(self.connection, id)
        order["products"] = order.OrderProducts()
        form = self.forms.get_form("create_order")

        if not self.post:
            form.process(data=order)

        return {
            "order": order,
            "create_order_form": form,
        }

    @loggedin
    @NotExistsErrorCatcher
    def RequestOrderEdit(self, id):
        order: model.Order = model.Order.FromPrimary(self.connection, id)
        form: forms.CreateOrderForm = self.forms.get_form("create_order", self.post)

        if not form.validate():
            return self.RequestOrder(id)
        
        order.update({'description': form.description.data, 'status': form.status.data})
        order.Save()
        return uweb3.Redirect(f"/order/{id}", httpcode=303)
