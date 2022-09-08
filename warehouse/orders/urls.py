from warehouse.orders.api import PageMaker as OrderPageMaker

urls = [
    ('/api/v1/order/create', (OrderPageMaker, 'CreateOrder'), 'POST'),
    ('/api/v1/orders', (OrderPageMaker, 'ListOrders'), 'GET'),
    
]