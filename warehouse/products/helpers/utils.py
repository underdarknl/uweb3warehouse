from warehouse.products import model


def remove_stock(connection, sku, amount, reference=None):
    product = model.Product.FromSku(connection, sku)
    currentstock = product.currentstock
    if (
        amount < 0 and abs(amount) > currentstock  # only assemble when we sell
    ):  # only assemble when we have not enough stock
        try:
            product.Assemble(
                abs(amount)
                - currentstock,  # only assemble what is missing for this sale
                "Assembly for %s" % reference,
            )
        except model.AssemblyError as error:
            raise ValueError(error.args[0])

    # only assemble when we sell
    if amount < 0 and abs(amount) > currentstock:
        # only assemble when we have not enough stock
        product.Assemble(
            abs(amount) - currentstock,  # only assemble what is missing for this sale
            "Assembly for %s" % reference,
        )
    model.Stock.Create(
        connection,
        {
            "product": product,
            "amount": amount,
            "reference": reference,
        },
    )
    return {
        "stock": product.currentstock,
        "possible_stock": product.possiblestock,
    }


def add_stock(connection, sku, amount, reference=None):
    """Used to refund after an invoice is canceled.
    This is an addition to stock.

    Args:
        connection (PageMaker.connection): The connection object
        sku (str): The product SKU
        amount (int): The amount to refund
        reference (str, optional): The description for the refund
    """
    product = model.Product.FromSku(connection, sku)
    model.Stock.Create(
        connection,
        {
            "product": product,
            "amount": amount,
            "reference": reference,
        },
    )


def possibleparts_select_list(possibleparts):
    return [(p["sku"], f"{p['sku']} - {p['name']}") for p in possibleparts]


def suppliers_select_list(suppliers):
    return [(s["ID"], s["name"]) for s in suppliers]
