from uweb3 import model
from uweb3.helpers import transaction
from warehouse.products import model as product_model


class Order(model.Record):
    """Provides a model abstraction for an Order."""

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
            for product in products:
                # Check if the referenced product with SKU actually exists.
                actual_product = product_model.Product.FromSku(
                    connection, product["product_sku"]
                )
                OrderProduct.Create(
                    connection,
                    {
                        "order": int(order),
                        "quantity": int(product["quantity"]),
                        "description": product["description"],
                        "product_sku": actual_product["sku"],
                    },
                )

    def OrderProducts(self):
        """Load the OrderProduct children from the given Order record.

        This method deletes the 'order' attribute to prevent nested loading."""
        for child in self._Children(OrderProduct, relation_field="order"):
            del child["order"]
            yield child


class OrderProduct(model.Record):
    """Model record that is used to keep track which Product is ordered
    and the quanity of said order."""
