"""A uWeb3 warehousing inventory software."""
import os
# Third-party modules
import uweb3

# Application
from . import basepages


def main():
  """Creates a uWeb3 application.

  The application is created from the following components:

  - The presenter class (PageMaker) which implements the request handlers.
  - The routes iterable, where each 2-tuple defines a url-pattern and the
    name of a presenter method which should handle it.
  - The execution path, internally used to find templates etc.
  """
  return uweb3.uWeb(
      basepages.PageMaker,
      [
          ('/', 'RequestProductNew', 'POST'),
          ('/', 'RequestIndex'),

          # login / user management
          ('/login', 'HandleLogin', 'POST'),
          ('/login', 'RequestLogin'),
          ('/logout', 'RequestLogout'),
          ('/usersettings', 'RequestUserSettings'),
          ('/apisettings', 'RequestApiSettings'),
          ('/resetpassword', 'RequestResetPassword'),
          ('/resetpassword/([^/]*)/(.*)', 'RequestResetPassword'),
          ('/setup', 'RequestSetup'),
          ('/admin', 'RequestAdmin'),
          ('/gs1', 'RequestGS1'),
          ('/ean', 'RequestEAN'),
          ('/suppliers', 'RequestSupplierNew', 'POST'),
          ('/suppliers', 'RequestSuppliers'),
          ('/supplier/([^/]*)', 'RequestSupplierSave', 'POST'),
          ('/supplier/([^/]*)', 'RequestSupplier', 'GET'),
          ('/supplier/([^/]*)/remove', 'RequestSupplierRemove', 'POST'),
          ('/product/([^/]*)', 'RequestProductSave', 'POST'),
          ('/product/([^/]*)', 'RequestProduct', 'GET'),
          ('/product/([^/]*)/remove', 'RequestProductRemove', 'POST'),
          ('/product/([^/]*)/assemble', 'RequestProductAssemble', 'POST'),
          ('/product/([^/]*)/assembly', 'RequestProductAssemblySave', 'POST'),
          ('/product/([^/]*)/stock', 'RequestProductStock', 'POST'),
          ('/invoices', 'RequestInvoices', 'GET'),
          ('/invoices', 'RequestNewInvoice', 'POST'),
          ('/clients', 'RequestClients', 'GET'),
          ('/clients', 'RequestNewClient', 'POST'),
          ('/clients/save', 'RequestSaveClient', 'POST'),
          (
              '/client/(.*)',
              'RequestClient',
          ),
          ('/api/v1/product/([^/]*)', 'JsonProduct', 'GET'),
          ('/api/v1/search_product/([^/]*)', 'JsonProductSearch', 'GET'),
          ('/api/v1/product/([^/]*)/stock', 'JsonProductStock', 'POST'),

          # Helper files
          ('(/styles/.*)', 'Static'),
          ('(/js/.*)', 'Static'),
          ('(/media/.*)', 'Static'),
          ('(/favicon.ico)', 'Static'),
          ('(/.*)', 'RequestInvalidcommand')
      ],
      os.path.dirname(__file__))
