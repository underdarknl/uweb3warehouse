#!/usr/bin/python3
"""Database abstraction model for the warehouse."""

__author__ = 'Jan Klopper <janklopper@underdark.nl>'
__version__ = '1.0'

# standard modules
import re

# Custom modules
from uweb3 import model
from base.libs import modelcache

from passlib.hash import pbkdf2_sha256
import secrets

NOTDELETEDDATE = '1000-01-01 00:00:00'
NOTDELETED = 'dateDeleted = "%s"' % NOTDELETEDDATE


class InvalidNameError(Exception):
  """Invalid name value."""


class WarehouseException(Exception):
  """A general Catch all error for the warehouse software"""


class AssemblyError(WarehouseException):
  """The requested operation cannot continue because we could not assemble a
  product as requested."""


class RichModel(modelcache.Record):
  """Provides a richer uweb Record class."""

  SEARCHABLE_COLUMNS = []

  def PagedChildren(self, classname, *args, **kwargs):
    """Return child objects with extra argument options."""
    if 'conditions' in kwargs:
      kwargs['conditions'].append('%s = %d' % (self.TableName(), self.key))
    else:
      kwargs['conditions'] = '%s = %d' % (self.TableName(), self.key)
    if 'offset' in kwargs and kwargs['offset'] < 0:
      kwargs['offset'] = 0
    return classname.List(*args, **kwargs)

  @classmethod
  def List(cls,
           connection,
           conditions=None,
           limit=None,
           offset=None,
           order=None,
           yield_unlimited_total_first=False,
           search=None,
           tables=None,
           escape=True,
           fields=None):
    """Yields a Record object for every table entry.

    Arguments:
      @ connection: object
        Database connection to use.
      % conditions: str / iterable ~~ None
        Optional query portion that will be used to limit the list of results.
        If multiple conditions are provided, they are joined on an 'AND' string.
      % limit: int ~~ None
        Specifies a maximum number of items to be yielded. The limit happens on
        the database side, limiting the query results.
      % offset: int ~~ None
        Specifies the offset at which the yielded items should start. Combined
        with limit this enables proper pagination.
      % order: iterable of str/2-tuple
        Defines the fields on which the output should be ordered. This should
        be a list of strings or 2-tuples. The string or first item indicates the
        field, the second argument defines descending order (desc. if True).
      % yield_unlimited_total_first: bool ~~ False
        Instead of yielding only Record objects, the first item returned is the
        number of results from the query if it had been executed without limit.
      % search: str
        Specifies what string should be searched for in the default searchable
        database columns.

    Yields:
      Record: Database record abstraction class.
    """
    if not tables:
      tables = [cls.TableName()]
    group = None
    if fields is None:
      fields = '%s.*' % cls.TableName()
    if search:
      search = search.strip()
      group = '%s.%s' % (cls.TableName(), (cls.RecordKey() if getattr(
          cls, "RecordKey", None) else cls._PRIMARY_KEY))
      tables, newconditions = cls._GetColumnData(tables, search)
      if conditions:
        if type(conditions) == list:
          conditions.extend(newconditions)
        else:
          newconditions.append(conditions)
          conditions = newconditions
      else:
        conditions = newconditions
    with connection as cursor:
      if hasattr(cls, '_addToCache'):
        connection.modelcache['_stats']['queries'].append(
            '%s VersionedRecord.List' % cls.TableName())
      records = cursor.Select(fields=fields,
                              table=tables,
                              conditions=conditions,
                              limit=limit,
                              offset=offset,
                              order=order,
                              totalcount=yield_unlimited_total_first,
                              escape=escape,
                              group=group)
    if yield_unlimited_total_first:
      yield records.affected
    records = [cls(connection, record) for record in list(records)]
    for record in records:
      yield record
    if hasattr(cls, '_addToCache'):
      # and not fields or fields == '*':
      # dont cache partial objects
      list(cls._cacheListPreseed(records))

  @classmethod
  def _GetColumnData(cls, tables, search):
    """Extracts table information from the searchable columns."""
    conditions = []
    #XXX search needs to be escaped properly
    condition = 'like "%%%s%%" or ' % search
    searchcondition = ''
    for column in cls.SEARCHABLE_COLUMNS:
      columndata = column.split('.')
      if len(columndata) == 2:
        classname = columndata[0]
        table = cls._SUBTYPES[classname]
        fkey = cls._FOREIGN_RELATIONS.get(classname, False)
        if fkey and fkey.get('LookupKey', False):
          key = fkey.get('LookupKey')
        elif getattr(table, "RecordKey", None):
          key = table.RecordKey()
        else:
          key = table._PRIMARY_KEY
        conditions.append(
            '`%s`.`%s` = %s.%s' %
            (cls.TableName(), table.TableName(), table.TableName(), key))
        if (table.TableName() not in tables and
            table.TableName() != cls.TableName()):
          tables.append(table.TableName())
        searchcondition += '`%s`.`%s` %s' % (table.TableName(), columndata[1],
                                             condition)
      else:
        searchcondition += '`%s`.`%s` %s' % (cls.TableName(), column, condition)
    if searchcondition:
      searchcondition = '(%s)' % searchcondition[:
                                                 -4]  #TODO use ' or '.join on search conditions instead
      conditions.append(searchcondition)
    return tables, conditions


class RichVersionedRecord(model.VersionedRecord):
  """Provides a richer uweb VersionedRecord class."""

  SEARCHABLE_COLUMNS = []

  @classmethod
  def List(cls,
           connection,
           conditions=None,
           limit=None,
           offset=None,
           order=None,
           yield_unlimited_total_first=False,
           search=None,
           tables=None,
           escape=True,
           fields=None):
    """Yields the latest Record for each versioned entry in the table.

    Arguments:
    @ connection: object
      Database connection to use.
    % conditions: str / iterable ~~ None
      Optional query portion that will be used to limit the list of results.
      If multiple conditions are provided, they are joined on an 'AND' string.
    % limit: int ~~ None
      Specifies a maximum number of items to be yielded. The limit happens on
      the database side, limiting the query results.
    % offset: int ~~ None
      Specifies the offset at which the yielded items should start. Combined
      with limit this enables proper pagination.
    % order: iterable of str/2-tuple
      Defines the fields on which the output should be ordered. This should
      be a list of strings or 2-tuples. The string or first item indicates the
      field, the second argument defines descending order (desc. if True).
    % yield_unlimited_total_first: bool ~~ False
      Instead of yielding only Record objects, the first item returned is the
      number of results from the query if it had been executed without limit.
    % search: str
      Specifies what string should be searched for in the default searchable
      database columns.

    Yields:
      Record: The Record with the newest version for each versioned entry.
    """
    if not tables:
      tables = [cls.TableName()]
    if not fields:
      fields = "%s.*" % cls.TableName()
    else:
      if fields != '*':
        if type(fields) != str:
          fields = ', '.join(connection.EscapeField(fields))
        else:
          fields = connection.EscapeField(fields)
    if search:
      search = search.strip()
      tables, newconditions = cls._GetColumnData(tables, search)
      if conditions:
        if type(conditions) == list:
          conditions.extend(newconditions)
        else:
          newconditions.append(conditions)
          conditions = newconditions
      else:
        conditions = newconditions
    field_escape = connection.EscapeField if escape else lambda x: x
    if yield_unlimited_total_first and limit is not None:
      totalcount = 'SQL_CALC_FOUND_ROWS'
    else:
      totalcount = ''
    with connection as cursor:
      records = cursor.Execute(
          """
          SELECT %(totalcount)s %(fields)s
          FROM %(tables)s
          JOIN (SELECT MAX(`%(primary)s`) AS `max`
                FROM `%(table)s`
                GROUP BY `%(record_key)s`) AS `versions`
              ON (`%(table)s`.`%(primary)s` = `versions`.`max`)
          WHERE %(conditions)s
          %(order)s
          %(limit)s
          """ % {
              'totalcount': totalcount,
              'primary': cls._PRIMARY_KEY,
              'record_key': cls.RecordKey(),
              'fields': fields,
              'table': cls.TableName(),
              'tables': cursor._StringTable(tables, field_escape),
              'conditions': cursor._StringConditions(conditions, field_escape),
              'order': cursor._StringOrder(order, field_escape),
              'limit': cursor._StringLimit(limit, offset)
          })
    if yield_unlimited_total_first and limit is not None:
      with connection as cursor:
        records.affected = cursor._Execute('SELECT FOUND_ROWS()')[0][0]
      yield records.affected
    # turn sqltalk rows into model
    records = [cls(connection, record) for record in list(records)]
    for record in records:
      yield record
    if hasattr(cls, '_addToCache') and not fields or (fields == '*' and
                                                      len(tables) == 1):
      list(cls._cacheListPreseed(records))

  @classmethod
  def _GetColumnData(cls, tables, search):
    """Extracts table information from the searchable columns."""
    conditions = []
    #XXX search needs to be escaped properly
    condition = 'like "%%%s%%" or ' % search
    searchcondition = ''
    for column in cls.SEARCHABLE_COLUMNS:
      columndata = column.split('.')
      if len(columndata) == 2:
        classname = columndata[0][0].upper() + columndata[0][1:]
        table = globals()[classname]
        if getattr(table, "RecordKey", None):
          key = table.RecordKey()
        else:
          key = table._PRIMARY_KEY
        conditions.append(
            '`%s`.`%s` = %s.%s' %
            (cls.TableName(), table.TableName(), table.TableName(), key))
        if (table.TableName() not in tables and
            table.TableName() != cls.TableName()):
          tables.append(table.TableName())
        searchcondition += '`%s`.`%s` %s' % (table.TableName(), columndata[1],
                                             condition)
      else:
        searchcondition += '`%s`.`%s` %s' % (cls.TableName(), column, condition)
    searchcondition = '(%s)' % searchcondition[:-4]
    conditions.append(searchcondition)
    return tables, conditions


class Client(RichVersionedRecord):
  """Abstraction class for Clients stored in the database."""

  _RECORD_KEY = 'clientNumber'
  MIN_NAME_LENGTH = 5
  MAX_NAME_LENGTH = 100

  @classmethod
  def FromClientNumber(cls, connection, clientnumber):
    """Returns the client belonging to the given clientnumber."""
    client = list(
        Client.List(connection,
                    conditions='ID = %d' % int(clientnumber),
                    order=[('ID', True)],
                    limit=1))
    if not client:
      raise cls.NotExistError('There is no client with clientnumber %r.' %
                              clientnumber)
    return cls(connection, client[0])


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
      user = cursor.Select(
          table=cls.TableName(),
          conditions=[
              'email=%s' % connection.EscapeValues(email), 'active = "true"'
          ] + conditions)
    if not user:
      raise cls.NotExistError('There is no user with the email address: %r' %
                              email)
    return cls(connection, user[0])

  @classmethod
  def FromLogin(cls, connection, email, password):
    """Returns the user with the given login details."""
    user = list(
        cls.List(connection,
                 conditions=('email = %s' % connection.EscapeValues(email),
                             'active = "true"')))
    if not user:
      # fake a login attempt, and slow down, even though we know its never going
      # to end in a valid login, we dont want to let anyone know the account
      # does or does not exist.
      if connection.debug:
        print('password for non existant user would have been: ',
              pbkdf2_sha256.hash(password))
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
    return pbkdf2_sha256.hash('%d%s%s' %
                              (self['ID'], self['email'], self['password']),
                              salt=bytes(self['ID']))


class Session(model.SecureCookie):
  """Provides a model to request the secure cookie named 'session'"""


class Apiuser(model.Record):
  """Provides a model abstraction for the apiuser table"""

  KEYLENGTH = 32

  def _PreCreate(self, cursor):
    super()._PreCreate(cursor)

    self['key'] = secrets.token_hex(int(self.KEYLENGTH / 2))
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
    user = list(
        cls.List(connection,
                 conditions=('`key` = %s' % connection.EscapeValues(key),
                             '`active` = "true"')))
    if not user:
      raise cls.NotExistError('Invalid key, or inactive key.')
    return user[0]


from base.model.product import Product, Stock, Productpart
from base.model.invoice import Invoice
from base.model.supplier import Supplier

NotExistError = model.NotExistError
