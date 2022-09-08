from ast import Or
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
                    "description": record['description'],
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


class OrderProduct(model.Record):
    """Model record that is used to keep track which Product is ordered
    and the quanity of said order."""
