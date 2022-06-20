#!/usr/bin/python3
"""Database abstraction model for the warehouse."""

__author__ = 'Jan Klopper <janklopper@underdark.nl>'
__version__ = '1.0'

# standard modules
import datetime
import pytz
import re
import json
import math

# Custom modules
from uweb3 import model
from passlib.hash import pbkdf2_sha256
import secrets

NOTDELETEDDATE = '1000-01-01 00:00:00'
NOTDELETED = 'dateDeleted = "%s"' % NOTDELETEDDATE

class Product(model.Record):
  """Provides a model abstraction for the Product table"""
  _possiblestock = None
  _parts = None
  _products = None

  @classmethod
  def List(cls, connection, conditions=[], *args, **kwargs):
    """Returns the Products filtered on not deleted"""
    return super().List(
      connection,
      conditions=[NOTDELETED] + conditions,
      *args, **kwargs)

  @classmethod
  def FromGS1(cls, connection, gs1, conditions=[]):
    """Returns the product of the given gs1.

    Arguments:
      @ connection: sqltalk.connection
        Database connection to use.
      @ gs1: str
        The gs1 code of the product.

    Raises:
      NotExistError:
        The given product gs1 code does not exist.

    Returns:
      Product: product abstraction class.
    """
    with connection as cursor:
      product = cursor.Select(table=cls.TableName(),
                              conditions=['gs1=%s' % int(gs1),
                                          NOTDELETED] + conditions)
    if not product:
      raise cls.NotExistError(
          'There is no product with gs1 code %r' % gs1)
    return cls(connection, product[0])

  @classmethod
  def FromEAN(cls, connection, ean, conditions=[]):
    """Returns the product of the given ean.

    Arguments:
      @ connection: sqltalk.connection
        Database connection to use.
      @ ean: str
        The ean code of the product.

    Raises:
      NotExistError:
        The given product ean code does not exist.

    Returns:
      Product: product abstraction class.
    """
    with connection as cursor:
      product = cursor.Select(table=cls.TableName(),
                              conditions=['ean=%s' % int(ean),
                                          NOTDELETED] + conditions)
    if not product:
      raise cls.NotExistError(
          'There is no product with ean code %r' % ean)
    return cls(connection, product[0])

  @classmethod
  def EANSearch(cls, connection, ean=None, order=None, conditions=None, **kwargs):
    """Returns the products matching the searched (partial) EAN

      Arguments:
      @ connection: sqltalk.connection
        Database connection to use.
      % ean: str
        Filters on ean or part of
    """
    if not conditions:
      conditions = []
    queryorder = [('product.dateCreated', True)]
    if order:
      queryorder = order + queryorder

    return super().List(
      connection,
      conditions=["""( ean like "%%%d%%" or
                       concat(supplier.gscode, LPAD(gs1, 3, 0)) like "%%%d%%") and
                       product.supplier = supplier.ID and
                       product.dateDeleted = "%s"
                  """ %
        (int(ean),
         int(ean),
         NOTDELETEDDATE)
      ] + conditions,
      order=queryorder,
      tables=('product', 'supplier'),
      **kwargs)

  @classmethod
  def Search(cls, connection, query=None, order=None, conditions=None, **kwargs):
    """Returns the products matching the search

      Arguments:
      @ connection: sqltalk.connection
        Database connection to use.
      % query: str
        Filters on name
    """
    if not conditions:
      conditions = []
    queryorder = [('product.dateCreated', True)]
    if order:
      queryorder = order + queryorder
    return cls.List(
      connection,
      conditions=['name like "%%%s%%"' % connection.EscapeValues(query)[1:-1]] + conditions,
      order=queryorder,
      **kwargs)

  @classmethod
  def FromName(cls, connection, name, conditions=None):
    """Returns the product of the given common name.

    Arguments:
      @ connection: sqltalk.connection
        Database connection to use.
      @ name: str
        The common name of the product.

    Raises:
      NotExistError:
        The given product name does not exist.

    Returns:
      Collection: product abstraction class.
    """
    if not conditions:
      conditions = []
    safe_name = connection.EscapeValues(name)
    with connection as cursor:
      product = cursor.Select(table=cls.TableName(),
                                 conditions=['name=%s' % safe_name,
                                             NOTDELETED] + conditions)
    if not product:
      raise cls.NotExistError(
          'There is no product with common name %r' % name)
    return cls(connection, product[0])

  def Delete(self):
    """Overwrites the default Delete and sets the dateDeleted datetime instead"""
    self['dateDeleted'] = str(pytz.utc.localize(
        datetime.datetime.utcnow()))[0:19]
    self.Save()

  def _PreCreate(self, cursor):
    super()._PreCreate(cursor)
    if self['name']:
      self['name'] = re.search('([\w\-_\.,]+)',
          self['name'].replace(' ', '_')).groups()[0][:255]
    if not self['gs1']: # set empty string to None for key contraints
      self['gs1'] = None
    if not self['sku']: # set empty string to None for key contraints
      self['sku'] = None
    if not self['name']:
      raise InvalidNameError('Provide a valid name')

  def _PreSave(self, cursor):
    super()._PreSave(cursor)
    if self['name']:
      self['name'] = re.search('([\w\-_\.,]+)',
          self['name'].replace(' ', '_')).groups()[0][:255]
    if not self['gs1']: # set empty string to None for key contraints
      self['gs1'] = None
    if not self['sku']: # set empty string to None for key contraints
      self['sku'] = None
    if not self['name']:
      raise InvalidNameError('Provide a valid name')

  @property
  def parts(self):
    """List products used as parts for this product"""
    if self._parts is None:
      self._parts = list(self._Children(Productpart))
    return self._parts

  @property
  def products(self):
    """List products that use this product as a part"""
    if self._products is None:
      self._products = list(self._Children(Productpart, relation_field="part"))
    return self._products

  def Stock(self, *args, **kwargs):
    """List stock changes for this product"""
    return self._Children(Stock, *args, **kwargs)

  @property
  def currentstock(self):
    """Returns the current stock"""
    with self.connection as cursor:
      stock = cursor.Select(table=Stock.TableName(),
                            fields='sum(amount) as currentstock',
                            conditions=['product=%d' % self.key],
                            escape=False)
    if stock[0]['currentstock']:
      return int(stock[0]['currentstock'])
    return 0

  @property
  def possiblestock(self):
    """Returns the possible stock when using up currently available parts"""
    if self._possiblestock:
      return self._possiblestock

    parts = list(self.parts)
    if not parts:
      self._possiblestock = {'available': 0,
                             'parts': None,
                             'limitedby': None}
      return self._possiblestock

    limitedby = parts[0]
    availableassemblies = math.inf
    for part in parts:
      part['availablestock'] = part['part'].currentstock
      part['availablepossiblestock'] = part['part'].possiblestock
      if part['amount']:
        part['availableassemblies'] = int((part['availablestock'] + part['availablepossiblestock']['available']) / part['amount'])
        if part['availableassemblies'] < availableassemblies:
          limitedby = part
        availableassemblies = min(availableassemblies, part['availableassemblies'])

    self._possiblestock = {'available': availableassemblies,
                           'parts': parts,
                           'limitedby': limitedby}
    return self._possiblestock

  def Assemble(self, amount=1, reference='Assembled from parts', lot=None):
    """Tries to use up this products parts and assembles them, mutating stock on all products involved."""
    if amount > 0:
      possiblestock = self.possiblestock
      if not possiblestock['available'] and not possiblestock['limitedby']:
        raise AssemblyError('Cannot assemble this product, is not an assembled product.')
      if not possiblestock['available'] or possiblestock['available'] < amount:
        raise AssemblyError('Cannot assemble this product, not enough parts. Limited by: %s' % possiblestock['limitedby']['part']['name'])
      parts = possiblestock['parts']
    elif amount < 0:
      if self.currentstock < abs(amount):
        raise AssemblyError('Cannot Disassemble this product, not enough stock available.')
      parts = list(self.parts)
      if parts == 0:
        raise AssemblyError('Cannot Disassemble this product, is not an assembled product.')

    # Mutate parts one by one
    for part in parts:
      subreference = 'Assembly: %s, %s' % (self['name'], reference)
      Stock.Create(self.connection, {'product': int(part['part']),
                                     'amount': (part['amount'] * amount) * -1,
                                     'reference': subreference[0:45]})
    # Mutate this product as requested
    return Stock.Create(self.connection, {'product': self.key,
                                   'amount': amount,
                                   'reference': reference[0:45] if reference else '',
                                   'lot': lot})

  def Disassemble(self, amount=1, reference="Disassembled for parts", lot=None):
    """Remove as many assemblies as requested and create stock for parts"""
    return self.Assemble(amount * -1,
                         reference or 'Disassembled for parts',
                         lot)

  def AssemblyOptions(self):
    partIds = []
    for part in self.parts:
      partIds.append(str(int(part['part'])))

    return self.List(self.connection,
        conditions=['ID != %d' % self.key,
                    'ID not in (%s)' % ','.join(partIds) if partIds else 'true'])

  @property
  def Eancode(self):
    if self['ean']:
      return self['ean']
    if self['gs1']:
      try:
        return '%d%03d' % (int(self['supplier']['gscode']), self['gs1'])
      except (KeyError, ValueError):
        return None
    return None


class Stock(model.Record):
  """Provides a model abstraction for the stock table"""


class Productpart(model.Record):
  """Provides a model abstraction for the Productpart table"""
  _FOREIGN_RELATIONS = {'part': Product}

  @property
  def subtotal(self):
    return (self['amount'] * self['part']['cost']) + self['assemblycosts']

class Supplier(model.Record):
  """Provides a model abstraction for the Supplier table"""

  @classmethod
  def List(cls, connection, conditions=[], *args, **kwargs):
    """Returns the Suppliers filterd on not deleted"""
    return super().List(
      connection,
      conditions=[NOTDELETED] + conditions,
      *args, **kwargs)

  @classmethod
  def Search(cls, connection, query=None, conditions=None, **kwargs):
    """Returns the articles matching the search

      Arguments:
      @ connection: sqltalk.connection
        Database connection to use.
      % query: str
        Filters on name
    """
    if not conditions:
      conditions = []
    return cls.List(
      connection,
      conditions=['name like "%%%s%%"' % connection.EscapeValues(query)[1:-1]] + conditions,
      order=[('ID', True)],
      **kwargs)

  @classmethod
  def FromName(cls, connection, name, conditions=[]):
    """Returns the supplier of the given common name.

    Arguments:
      @ connection: sqltalk.connection
        Database connection to use.
      @ name: str
        The common name of the collection.

    Raises:
      NotExistError:
        The given supplier name does not exist.

    Returns:
      Supplier: supplier abstraction class.
    """
    safe_name = connection.EscapeValues(name)
    with connection as cursor:
      supplier = cursor.Select(table=cls.TableName(),
                               conditions=['name=%s' % safe_name,
                                           NOTDELETED] + conditions)
    if not supplier:
      raise cls.NotExistError(
          'There is no supplier with common name %r' % name)
    return cls(connection, supplier[0])

  def Delete(self):
    """Overwrites the default Delete and sets the dateDeleted datetime instead"""
    self['dateDeleted'] = str(pytz.utc.localize(
        datetime.datetime.utcnow()))[0:19]
    self.Save()

  def Products(self):
    """List products for this supplier"""
    return self.__children__(Products)

  def _PreCreate(self, cursor):
    super()._PreCreate(cursor)
    if self['gscode']:
      self['gscode'] = self['gscode'][:10]
    if self['name']:
      self['name'] = re.search('([\w\-_\.,]+)',
          self['name'].replace(' ', '_')).groups()[0][:45]
    if not self['name']:
      raise InvalidNameError('Provide a valid name')

  def _PreSave(self, cursor):
    super()._PreSave(cursor)
    if self['gscode']:
      self['gscode'] = self['gscode'][:10]
    if self['name']:
      self['name'] = re.search('([\w\-_\.,]+)',
          self['name'].replace(' ', '_')).groups()[0][:45]
    if not self['name']:
      raise InvalidNameError('Provide a valid name')


class User(model.Record):
  """Provides interaction to the user table"""

  @classmethod
  def FromEmail(cls, connection, email, conditions=None):
    """Returns the user with the given email address.

    Arguments:
      @ connection: sqltalk.connection
        Database connection to use.
      @ email: str
        The email address of the user.

    Raises:
      NotExistError:
        The given user does not exist.

    Returns:
      User: user abstraction class.
    """
    if not conditions:
      conditions = []
    with connection as cursor:
      user = cursor.Select(table=cls.TableName(),
          conditions=['email=%s' % connection.EscapeValues(email),
                      'active = "true"'] + conditions)
    if not user:
      raise cls.NotExistError(
          'There is no user with the email address: %r' % email)
    return cls(connection, user[0])

  @classmethod
  def FromLogin(cls, connection, email, password):
    """Returns the user with the given login details."""
    user = list(cls.List(connection,
        conditions=('email = %s' % connection.EscapeValues(email),
                    'active = "true"')))
    if not user:
      # fake a login attempt, and slow down, even though we know its never going
      # to end in a valid login, we dont want to let anyone know the account
      # does or does not exist.
      if connection.debug:
        print('password for non existant user would have been: ', pbkdf2_sha256.hash(password))
      raise cls.NotExistError('Invalid login, or inactive account.')
    if pbkdf2_sha256.verify(password, user[0]['password']):
      return user[0]
    raise cls.NotExistError('Invalid password')

  def UpdatePassword(self, password):
    """Hashes the password and stores it in the database"""
    if len(password) < 8:
      raise ValueError('password too short, 8 characters minimal.')
    self['password'] = pbkdf2_sha256.hash(password)
    self.Save()

  def _PreCreate(self, cursor):
    super()._PreCreate(cursor)
    self['email'] = self['email'][:255]
    self['active'] = 'true' if self['active'] == 'true' else 'false'

  def _PreSave(self, cursor):
    super()._PreSave(cursor)
    self['email'] = self['email'][:255]
    self['active'] = 'true' if self['active'] == 'true' else 'false'

  def PasswordResetHash(self):
    """Returns a hash based on the user's ID, name and password."""
    return pbkdf2_sha256.hash('%d%s%s' % (
         self['ID'], self['email'], self['password']),
         salt=bytes(self['ID']))


class Session(model.SecureCookie):
  """Provides a model to request the secure cookie named 'session'"""


class Apiuser(model.Record):
  """Provides a model abstraction for the apiuser table"""

  KEYLENGTH = 32

  def _PreCreate(self, cursor):
    super()._PreCreate(cursor)

    self['key'] = secrets.token_hex(int(self.KEYLENGTH/2))
    if 'active' not in self:
      self['active'] = 'true'
    self['active'] = 'true' if self['active'] == 'true' else 'false'
    self['name'] = re.search('([\w\-_\.,]+)',
        self['name'].replace(' ', '_')).groups()[0][:45]
    if not self['name']:
      raise InvalidNameError('Provide a valid name')

  def _PreSave(self, cursor):
    super()._PreSave(cursor)

    self['name'] = re.search('([\w\-_\.,]+)',
        self['name'].replace(' ', '_')).groups()[0][:45]
    self['active'] = 'true' if self['active'] == 'true' else 'false'
    if not self['name']:
      raise InvalidNameError('Provide a valid name')

  @classmethod
  def FromKey(cls, connection, key):
    """Returns a user object by API key."""
    if not key:
      raise cls.NotExistError('No API key given.')
    user = list(cls.List(connection,
        conditions=('`key` = %s' % connection.EscapeValues(key),
                    '`active` = "true"')))
    if not user:
      raise cls.NotExistError('Invalid key, or inactive key.')
    return user[0]


class InvalidNameError(Exception):
  """Invalid name value."""

class WarehouseException(Exception):
  """A general Catch all error for the warehouse software"""

class AssemblyError(WarehouseException):
  """The requested operation cannot continue because we could not assemble a
  product as requested."""

NotExistError = model.NotExistError
