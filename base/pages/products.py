#!/usr/bin/python
"""Request handlers for the uWeb3 warehouse inventory software"""

# standard modules
import urllib
# uweb modules
import uweb3
from base.decorators import apiuser, json_error_wrapper
from base.decorators import NotExistsErrorCatcher
from base.model import model
from base.helpers import PagedResult


class PageMaker:

  @uweb3.decorators.loggedin
  @uweb3.decorators.TemplateParser('products.html')
  def RequestProducts(self):
    """Returns the Products page"""
    supplier = None
    conditions = []
    linkarguments = {}
    if 'supplier' in self.get:
      try:
        supplier = model.Supplier.FromPrimary(
            self.connection, self.get.getfirst('supplier', None))
        conditions.append('supplier = %d' % supplier)
        linkarguments['supplier'] = int(supplier)
      except model.User.NotExistError:
        pass

    products_args = {'conditions': conditions, 'order': [('ID', True)]}
    query = ''
    if 'query' in self.get and self.get.getfirst('query', False):
      query = self.get.getfirst('query', '')
      linkarguments['query'] = query
      products_method = model.Product.Search
      products_args['query'] = query
    else:
      products_method = model.Product.List

    products = PagedResult(self.pagesize, self.get.getfirst('page', 1),
                           products_method, self.connection, products_args)
    return {
        'supplier': supplier,
        'products': products,
        'linkarguments': urllib.parse.urlencode(linkarguments) or '',
        'query': query,
        'suppliers': list(model.Supplier.List(self.connection))
    }

  @uweb3.decorators.loggedin
  @NotExistsErrorCatcher
  def RequestProductSave(self, name):
    """Saves changes to the product"""
    product = model.Product.FromName(self.connection, name)
    for key in product.keys():
      if key in self.post:
        product[key] = self.post.getfirst(key)
    product.Save()
    return self.RequestProducts()

  @uweb3.decorators.loggedin
  @NotExistsErrorCatcher
  @uweb3.decorators.TemplateParser('product.html')
  def RequestProduct(self, name):
    """Returns the product page"""
    product = model.Product.FromName(self.connection, name)
    parts = product.parts
    if 'unlimitedstock' in self.get:
      stock = list(product.Stock(order=[('dateCreated', True)]))
      stockrows = False
    else:
      stock = list(
          product.Stock(limit=int(self.pagesize),
                        order=[('dateCreated', True)],
                        yield_unlimited_total_first=True))
      stockrows = stock[0]
      stock = stock[1:]

    partsprice = {
        'partstotal': 0,
        'assembly': 0,
        'partcount': 0,
        'assembledtotal': 0
    }
    for part in list(parts):
      partsprice['partcount'] += part['amount']
      partsprice['assembly'] += part['assemblycosts']
      partsprice['partstotal'] += part.subtotal
      partsprice['assembledtotal'] += part.subtotal + part['assemblycosts']

    return {
        'products': product.AssemblyOptions(),
        'parts': parts,
        'partsprice': partsprice,
        'product': product,
        'suppliers': model.Supplier.List(self.connection),
        'stock': stock,
        'stockrows': stockrows
    }

  @uweb3.decorators.ContentType('application/json')
  @json_error_wrapper
  @apiuser
  def JsonProduct(self, name):
    """Returns the product Json"""
    product = model.Product.FromName(self.connection, name)
    return {
        'product': product,
        'currentstock': product.currentstock,
        'possiblestock': product.possiblestock['available']
    }

  @uweb3.decorators.ContentType('application/json')
  @json_error_wrapper
  @apiuser
  def JsonProductSearch(self, name):
    """Returns the product Json"""
    product = model.Product.FromName(self.connection, name)
    return {
        'product': product['name'],
        'cost': product['cost'],
        'assemblycosts': product['assemblycosts'],
        'vat': product['vat'],
    }

  @uweb3.decorators.loggedin
  @uweb3.decorators.checkxsrf
  def RequestProductNew(self):
    """Requests the creation of a new product."""
    try:
      product = model.Product.Create(
          self.connection, {
              'name':
                  self.post.getfirst('name', '').replace(' ', '_'),
              'ean':
                  int(self.post.getfirst('ean'))
                  if 'ean' in self.post else None,
              'gs1':
                  int(self.post.getfirst('gs1'))
                  if 'gs1' in self.post else None,
              'description':
                  self.post.getfirst('description', ''),
              'cost':
                  float(self.post.getfirst('cost', 0)),
              'assemblycosts':
                  float(self.post.getfirst('assemblycosts', 0)),
              'vat':
                  float(self.post.getfirst('vat', 21)),
              'sku':
                  self.post.getfirst('sku', '').replace(' ', '_')
                  if 'ski' in self.post else None,
              'supplier':
                  int(self.post.getfirst('supplier', 1))
          })
    except ValueError:
      return self.RequestInvalidcommand(
          error='Input error, some fields are wrong.')
    except model.InvalidNameError:
      return self.RequestInvalidcommand(
          error='Please enter a valid name for the product.')
    except self.connection.IntegrityError as error:
      #  if 'gs1' in error:
      #    return self.Error('That GS1 code was already taken, go back, try again!', 200)
      return self.Error('That name was already taken, go back, try again!', 200)
    return self.req.Redirect('/product/%s' % product['name'], httpcode=301)

  @uweb3.decorators.loggedin
  @NotExistsErrorCatcher
  @uweb3.decorators.checkxsrf
  def RequestProductAssemble(self, name):
    """Add a new part to an existing product"""
    product = model.Product.FromName(self.connection, name)
    try:
      part = model.Product.FromName(self.connection, self.post.getfirst('part'))
      assembly = model.Productpart.Create(
          self.connection, {
              'product':
                  product,
              'part':
                  part,
              'amount':
                  int(self.post.getfirst('amount', 1)),
              'assemblycosts':
                  float(
                      self.post.getfirst('assemblycosts', part['assemblycosts'])
                  )
          })
    except ValueError:
      return self.RequestInvalidcommand(
          error='Input error, some fields are wrong.')
    except self.connection.IntegrityError as error:
      return self.Error('That part was already assembled in this product!', 200)
    return self.req.Redirect('/product/%s' % product['name'], httpcode=301)

  @uweb3.decorators.loggedin
  @NotExistsErrorCatcher
  @uweb3.decorators.checkxsrf
  def RequestProductAssemblySave(self, name):
    """Update a products assembly by adding, removing or updating part
    references"""
    product = model.Product.FromName(self.connection, name)
    deletes = self.post.getfirst('delete', [])
    updates = {
        'amount': self.post.getfirst('amount', []),
        'assemblycosts': self.post.getfirst('assemblycosts', [])
    }

    for mate in product.parts:
      mateid = str(mate['ID'])
      if mateid in deletes:
        mate.Delete()
      else:
        for key in mate:
          if (key in updates and mateid in updates[key]):
            mate[key] = updates[key][mateid]
        mate.Save()
    return self.req.Redirect('/product/%s' % product['name'], httpcode=301)

  @uweb3.decorators.loggedin
  @NotExistsErrorCatcher
  @uweb3.decorators.checkxsrf
  def RequestProductRemove(self, product):
    """Removes the product"""
    product = model.Product.FromName(self.connection, product)
    product.Delete()
    return self.req.Redirect('/', httpcode=301)

  @uweb3.decorators.loggedin
  @NotExistsErrorCatcher
  @uweb3.decorators.checkxsrf
  def RequestProductStock(self, name):
    """Creates a stock change for the product, either from a new shipment, or
    by assembling/ disassembling a product from its parts."""
    product = model.Product.FromName(self.connection, name)
    try:
      if 'assemble' in self.post:
        product.Assemble(int(self.post.getfirst('assemble', 1)),
                         self.post.getfirst('reference', None),
                         self.post.getfirst('lot', None))
      elif 'disassemble' in self.post:
        product.Disassemble(int(self.post.getfirst('disassemble', 1)),
                            self.post.getfirst('reference', None),
                            self.post.getfirst('lot', None))
      else:
        stock = model.Stock.Create(
            self.connection, {
                'product': product,
                'amount': int(self.post.getfirst('amount', 1)),
                'reference': self.post.getfirst('reference', ''),
                'lot': self.post.getfirst('lot', '')
            })
    except model.AssemblyError as error:
      return self.Error(error)
    return self.req.Redirect('/product/%s' % product['name'], httpcode=301)

  @uweb3.decorators.ContentType('application/json')
  @apiuser
  @NotExistsErrorCatcher
  def JsonProductStock(self, name):
    """Updates the stock for a product, assembling if needed

    Send negative amount to Sell a product, positive amount to put product back
    into stock"""
    try:
      product = model.Product.FromName(self.connection, name)
    except model.NotExistError as error:
      return self.RequestInvalidJsoncommand(error)
    amount = int(self.post.getfirst('amount', -1))
    currentstock = product.currentstock
    if (amount < 0 and  # only assemble when we sell
        abs(amount) >
        currentstock):  # only assemble when we have not enough stock
      try:
        product.Assemble(
            abs(amount) -
            currentstock,  # only assemble what is missing for this sale
            'Assembly for %s' % self.post.getfirst('reference')
            if 'reference' in self.post else None)
      except model.AssemblyError as error:
        return self.RequestInvalidJsoncommand(error)
    # by now we should have enough products in stock, one way or another
    model.Stock.Create(
        self.connection, {
            'product': product,
            'amount': amount,
            'reference': self.post.getfirst('reference', '')
        })
    return True
