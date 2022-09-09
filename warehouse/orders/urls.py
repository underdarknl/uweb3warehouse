from warehouse.orders.api import PageMaker as OrderAPIPageMaker
from warehouse.orders.orders import PageMaker as OrderPageMaker

urls = [
    ("/orders", (OrderPageMaker, "RequestOrders")),
    ("/order/([0-9]+)", (OrderPageMaker, "RequestOrder"), "GET"),
    ("/order/([0-9]+)", (OrderPageMaker, "RequestOrderEdit"), "POST"),
    ("/api/v1/order/create", (OrderAPIPageMaker, "CreateOrder"), "POST"),
    ("/api/v1/order/cancel", (OrderAPIPageMaker, "CancelOrder"), "POST"),
    (
        "/api/v1/order/convert",
        (OrderAPIPageMaker, "ConvertReservationToRealOrder"),
        "POST",
    ),
    ("/api/v1/orders", (OrderAPIPageMaker, "ListOrders"), "GET"),
]
