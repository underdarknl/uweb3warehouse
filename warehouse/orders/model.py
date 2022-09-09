from enum import Enum
import pytz
import datetime

from uweb3 import model
from uweb3.helpers import transaction
from warehouse.products import model as product_model


class OrderStatus(str, Enum):
    NEW = "new"
    RESERVATION = "reservation"
    COMPLETED = "completed"
    CANCELED = "canceled"


class Order(model.Record):
    """Provides a model abstraction for an Order."""

    @classmethod
    def FromReference(cls, connection, record):
        pass

    @classmethod
    def Create(cls, connection, record):
        products = record["products"]
        with transaction(connection, Order):
            order = super().Create(
                connection,
                {
                    "description": record["description"],
                    "status": record["status"],
                },
            )
            order["order_products"] = []
            for product in products:
                # Check if the referenced product with SKU actually exists.
                actual_product = product_model.Product.FromSku(
                    connection, product["product_sku"]
                )
                order_product = OrderProduct.Create(
                    connection,
                    {
                        "order": int(order),
                        "quantity": int(product["quantity"]),
                        "description": product["description"],
                        "product_sku": actual_product["sku"],
                    },
                )
                # XXX: Find a way to prevent loading parent because we dont want to
                # display it in this case.
                del order_product["order"]
                order["order_products"].append(order_product)  # type: ignore
        return order

    def OrderProducts(self):
        """Load the OrderProduct children from the given Order record.

        This method deletes the 'order' attribute to prevent nested loading."""
        for child in self._Children(OrderProduct, relation_field="order"):
            # XXX: Find a way to prevent loading parent because we dont want to
            # display it in this case.
            del child["order"]
            yield child

    def Delete(self):
        """Overwrites the default Delete and sets the dateDeleted datetime instead"""
        self["date_canceled"] = str(pytz.utc.localize(datetime.datetime.utcnow()))[0:19]
        self["status"] = OrderStatus.CANCELED.value
        self.Save()


class OrderProduct(model.Record):
    """Model record that is used to keep track which Product is ordered
    and the quanity of said order."""
