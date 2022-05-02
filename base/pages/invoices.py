#!/usr/bin/python
"""Request handlers for the uWeb3 warehouse inventory software"""

# standard modules

# uweb modules
import uweb3
from base.model import model


class PageMaker:

  @uweb3.decorators.loggedin
  @uweb3.decorators.checkxsrf
  @uweb3.decorators.TemplateParser('invoices/invoices.html')
  def RequestInvoices(self):
    return {
        'clients': list(model.Client.List(self.connection)),
        'products': list(model.Product.List(self.connection)),
        'invoices': list(model.Invoice.List(self.connection)),
        'scripts': ['/js/invoice.js']
    }

  @uweb3.decorators.loggedin
  @uweb3.decorators.checkxsrf
  def RequestNewInvoice(self):
    return self.req.Redirect('/invoices', httpcode=303)
