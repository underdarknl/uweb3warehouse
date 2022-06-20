#!/usr/bin/python
"""Request handlers for the uWeb3 warehouse inventory software"""

# standard modules
import time
import locale
import urllib.parse

# uweb modules
import uweb3
from uweb3.libs import mail

# project modules
from . import model
from .helpers import PagedResult

def apiuser(f):
  """Decorator to check if the given API key is allowed to access the resource."""
  def wrapper(*args, **kwargs):
    # This is bypassed if a user is already logged in trough a session
    if args[0].user:
      args[0].apikey = None
      return f(*args, **kwargs)
    key = None
    if 'apikey' in args[0].get:
      key = args[0].get.getfirst('apikey')
    elif 'apikey' in args[0].post:
      key = args[0].post.getfirst('apikey')
    elif 'apikey' in args[0].req.headers:
      key = args[0].req.headers.get('apikey')
    try:
      args[0].apikey = model.Apiuser.FromKey(args[0].connection, key)
    except model.Apiuser.NotExistError as apierror:
      return uweb3.Response(content={'error': str(apierror)}, httpcode=403)
    return f(*args, **kwargs)
  return wrapper


def NotExistsErrorCatcher(f):
  """Decorator to return a 404 if a NotExistError exception was returned."""
  def wrapper(*args, **kwargs):
    try:
      return f(*args, **kwargs)
    except model.NotExistError as error:
      return args[0].RequestInvalidcommand(error=error)
  return wrapper


class PageMaker(uweb3.DebuggingPageMaker, uweb3.LoginMixin):
  """Holds all the request handlers for the application"""

  DEFAULTPAGESIZE = 10

  def _PostInit(self):
    """Sets up all the default vars"""
    self.parser.RegisterTag('year', time.strftime('%Y'))
    self.parser.RegisterFunction('ToID', lambda x: x.replace(' ', ''))
    self.parser.RegisterFunction('NullString', lambda x: '' if x is None else x)
    self.parser.RegisterFunction('DateOnly', lambda x: str(x)[0:10])
    self.parser.RegisterFunction('TextareaRowCount', lambda x: len(str(x).split('\n')))
    self.parser.RegisterTag('header', self.parser.JITTag(lambda: self.parser.Parse(
                'parts/header.html')))
    self.parser.RegisterTag('footer', self.parser.JITTag(lambda: self.parser.Parse(
                'parts/footer.html', year=time.strftime('%Y'))))
    self.validatexsrf()
    self.parser.RegisterTag('xsrf', self._Get_XSRF())
    self.parser.RegisterTag('user', self.user)
    self.pagesize = int(self.options['general'].get('pagesize', self.DEFAULTPAGESIZE))

  def _PreRequest(self):
    if self.config.Read():
      try:
        locale.setlocale( locale.LC_ALL, self.options['general'].get('locale', 'en_GB'))
        self.parser.RegisterFunction('currency', lambda x: locale.currency(x, symbol=False, grouping=True))
      except locale.Error:
        self.parser.RegisterFunction('currency', lambda x: x)

  @uweb3.decorators.TemplateParser('login.html')
  def RequestLogin(self, url=None):
    """Please login"""
    if self.user:
      return self.RequestIndex()
    if not url and 'url' in self.get:
      url = self.get.getfirst('url')
    return {'url': url}

  @uweb3.decorators.checkxsrf
  @uweb3.decorators.TemplateParser('logout.html')
  def RequestLogout(self):
    """Handles logouts"""
    message = 'You where already logged out.'
    if self.user:
      message = ''
      if 'action' in self.post:
        session = model.Session(self.connection)
        session.Delete()
        message = 'Logged out.'
    return {'message': message}

  @uweb3.decorators.checkxsrf
  def HandleLogin(self):
    """Handles a username/password combo post."""
    if (self.user or
        'email' not in self.post or
        'password' not in self.post):
      return self.RequestIndex()
    url = self.post.getfirst('url', None) if self.post.getfirst('url', '').startswith('/') else '/'
    try:
      self._user = model.User.FromLogin(self.connection,
          self.post.getfirst('email'), self.post.getfirst('password'))
      model.Session.Create(self.connection, int(self.user), path="/")
      print('login successful.', self.post.getfirst('email'))
      # redirect 303 to make sure we GET the next page, not post again to avoid leaking login details.
      return self.req.Redirect(url, httpcode=303)
    except model.User.NotExistError as error:
      self.parser.RegisterTag('loginerror', '%s' % error)
      print('login failed.', self.post.getfirst('email'))
    return self.RequestLogin(url)

  @uweb3.decorators.checkxsrf
  def RequestResetPassword(self, email=None, resethash=None):
    """Handles the post for the reset password."""
    message = None
    error = False
    if not email and not resethash:
      try:
        user = model.User.FromEmail(self.connection,
                                    self.post.getfirst('email', ''))
      except model.User.NotExistError:
        error = True
        if self.debug:
          print('Password reset request for unknown user %s:' % self.post.getfirst('email', ''))
      if not error:
        resethash = user.PasswordResetHash()
        content = self.parser.Parse('email/resetpass.txt', email=user['email'],
                                    host=self.options['general']['host'],
                                    resethash=resethash)
        try:
          with mail.MailSender(local_hostname=self.options['general']['host']) as send_mail:
            send_mail.Text(user['email'], 'CMS password reset', content)
        except mail.SMTPConnectError:
          if not self.debug:
            return self.Error('Mail could not be send due to server error, please contact support.')
        if self.debug:
          print('Password reset for %s:' % user['email'], content)

      message = 'If that was an email address that we know, a mail with reset instructions will be in your mailbox soon.'
      return self.parser.Parse('reset.html', message=message)
    try:
      user = model.User.FromEmail(self.connection, email)
    except model.User.NotExistError:
      return self.parser.Parse('reset.html', message='Sorry, that\'s not the right reset code.')
    if resethash != user.PasswordResetHash():
      return self.parser.Parse('reset.html', message='Sorry, that\'s not the right reset code.')

    if 'password' in self.post:
      if self.post.getfirst('password') == self.post.getfirst('password_confirm', ''):
        try:
          user.UpdatePassword(self.post.getfirst('password', ''))
        except ValueError:
          return self.parser.Parse('reset.html', message='Password too short, 8 characters minimal.')
        model.Session.Create(self.connection, int(user), path="/")
        self._user = user
        return self.parser.Parse('reset.html', message='Your password has been updated, and you are logged in.')
      else:
        return self.parser.Parse('reset.html', message='The passwords don\'t match.')
    return self.parser.Parse('resetform.html',
                             resethash=resethash,
                             resetuser=user,
                             message='')

  def _ReadSession(self):
    """Attempts to read the session for this user from his session cookie"""
    try:
      user = model.Session(self.connection)
    except Exception:
      raise ValueError('Session cookie invalid')
    user = model.User.FromPrimary(self.connection, int(str(user)))
    if user['active'] != 'true':
      raise ValueError('User not active, session invalid')
    return user

  @uweb3.decorators.checkxsrf
  @uweb3.decorators.TemplateParser('setup.html')
  def RequestSetup(self):
    """Allows the user to setup various fields, and create an admin user.

    If these fields are already filled out, this page will not function any
    longer.
    """
    if self.options.get('general', {}).get('host', False):
      return self.RequestIndex()
    if (self.post and
        'email' in self.post and
        'password' in self.post and
        'password_confirm' in self.post and
        'hostname' in self.post and
        self.post.getfirst('password') == self.post.getfirst('password_confirm')):
      user = model.User.Create(self.connection,
          {'ID': 1,
           'email': self.post.getfirst('email'),
           'password': '',
           'active': 'true'})
      try:
        user.UpdatePassword(self.post.getfirst('password', ''))
      except ValueError:
        return {'error': 'Password too short, 8 characters minimal.'}
      self.config.Create('general', 'host', self.post.getfirst('hostname'))
      self.config.Create('general', 'locale', self.post.getfirst('locale', 'en_GB'))
      model.Session.Create(self.connection, int(user), path="/")
      return self.req.Redirect('/', httpcode=301)
    if self.post:
      return {'error': 'Not all fields are properly filled out.'}
    return

  @uweb3.decorators.loggedin
  @uweb3.decorators.checkxsrf
  @uweb3.decorators.TemplateParser('admin.html')
  def RequestAdmin(self):
    """Returns the admin page."""
    if self.user['ID'] != 1:
      return self.req.Redirect('/')

    currentusers = list(model.User.List(self.connection))
    if self.post:
      values = {}
      for key in ('useremail', 'useractive', 'userpassword',
                  'userpassword_confirm', 'userdelete'):
        values[key] = self.post.getfirst(key, {})

    users = []
    for user in currentusers:
      # user changes
      userid = str(user['ID'])

      # we are posting the edit form, not the new form
      if ('useremail' in self.post and
          'new' not in values['useremail']):
        if userid in values['userdelete']:
          if user['ID'] != 1 or user['ID'] == self.user['ID']:
            user.Delete()
        else:
          if userid in values['useremail']:
            user['email'] = values['useremail'][userid].strip()
          if user['ID'] != 1 and user['ID'] != self.user['ID']:
            user['active'] = 'true' if userid in values['useractive'] else 'false'
          else:
            user['active'] = 'true'
          # handle password change
          if (userid in values['userpassword'] and
              userid in values['userpassword_confirm'] and
              len(values['userpassword'][userid].strip()) > 7):
            if values['userpassword'][userid].strip() != values['userpassword_confirm'][userid].strip():
              return {'usererror': 'Passwords do not match.',
                      'users': currentusers}
            try:
              user.UpdatePassword(values['userpassword'][userid].strip())
            except ValueError:
              return {'usererror': 'Password too short, 8 characters minimal.',
                      'users': currentusers}
          user.Save()
          users.append(user)
      else:
        users.append(user)

    # handle User creation
    if ('useremail' in self.post and
        'new' in values['useremail']):
      try:
        newuser = model.User.Create(self.connection,
          {'email': values['useremail'].get('new', '').strip(),
           'active': values['useractive'].get('new', 'true'),
           'password': ''})
        try:
          newpassword = values['userpassword'].get('new', '').strip()
          newuser.UpdatePassword(newpassword)
        except ValueError:
          return {'usererror': 'Password too short, 8 characters minimal.',
                  'users': users}
        users.append(newuser)
      except model.InvalidNameError:
        return {'usererror': 'Provide a valid email address for the new user.',
                'users': users}
      except self.connection.IntegrityError:
        return {'usererror': 'That email address was already used for another user.',
                'users': users}
      else:
        content = self.parser.Parse('email/newuser.txt', email=newuser['email'],
                                    host=self.options['general']['host'],
                                    password=newpassword)
        try:
          with mail.MailSender(local_hostname=self.options['general']['host']) as send_mail:
            send_mail.Text(newuser['email'], 'Warehouse account', content)
        except mail.SMTPConnectError:
          if not self.debug:
            return self.Error('Mail could not be send due to server error, please contact support.')
      return {'usersucces': 'Your new user was added',
              'users': users}
    return {'users': users}

  @uweb3.decorators.loggedin
  @uweb3.decorators.checkxsrf
  @uweb3.decorators.TemplateParser('usersettings.html')
  def RequestUserSettings(self):
    """Returns the user settings page."""
    # handle password change
    if ('password' in self.post or
        'password_confirm' in self.post):
      password = self.post.getfirst('password', '')
      password_confirm = self.post.getfirst('password_confirm', '')
      if password != password_confirm:
        return {'error': 'Passwords do not match, try again.'}
      try:
        self.user.UpdatePassword(password)
      except ValueError:
        return {'error': 'Passwords too short.',
                'keys': keys}
      else:
        content = self.parser.Parse('email/updateuser.txt', email=self.user['email'])
        try:
          with mail.MailSender(local_hostname=self.options['general']['host']) as send_mail:
            send_mail.Text(self.user['email'], 'Warehouse account change', content)
        except mail.SMTPConnectError:
          if not self.debug:
            return self.Error('Mail could not be send due to server error, please contact support.')
      return {'succes': 'Password has been updated.'}

  @uweb3.decorators.loggedin
  @uweb3.decorators.checkxsrf
  @uweb3.decorators.TemplateParser('apisettings.html')
  def RequestApiSettings(self):
    """Returns the api settings page."""
    currentkeys = list(model.Apiuser.List(self.connection))

    # handle api key updates
    keys = []
    if self.post:
      deleted = self.post.getfirst('delete', {})
      updates = {'name': self.post.getfirst('name', {}),
                 'collectionfilter': self.post.getfirst('collectionfilter', {}),
                 'active': self.post.getfirst('active', {})}
      for key in currentkeys:
        keyid = str(key['ID'])
        if keyid in deleted:
          key.Delete()
        else:
          for field in ('name', 'collectionfilter'):
            if keyid in updates[field]:
              key[field] = updates[field][keyid]
          key['active'] = "false"
          if keyid in updates['active']:
            key['active'] = "true"
          key.Save()
          keys.append(key)
    else:
      keys = currentkeys

    # handle password change
    if ('password' in self.post or
        'password_confirm' in self.post):
      password = self.post.getfirst('password', '')
      password_confirm = self.post.getfirst('password_confirm', '')
      if password != password_confirm:
        return {'error': 'Passwords do not match, try again.',
                'keys': keys}
      try:
        self.user.UpdatePassword(password)
      except ValueError:
        return {'error': 'Passwords too short.',
                'keys': keys}
      else:
        content = self.parser.Parse('email/updateuser.txt', email=self.user['email'])
        try:
          with mail.MailSender(local_hostname=self.options['general']['host']) as send_mail:
            send_mail.Text(self.user['email'], 'Warehouse account change', content)
        except mail.SMTPConnectError:
          if not self.debug:
            return self.Error('Mail could not be send due to server error, please contact support.')
      return {'succes': 'Password has been updated.',
              'keys': keys}

    # handle new api key creation
    if ('new_name' in self.post and
        len(self.post.getfirst('new_name')) > 0):
      try:
        newkey = model.Apiuser.Create(self.connection,
          {'name': self.post.getfirst('new_name')})
        keys.append(newkey)
      except model.InvalidNameError:
        return {'keys': keys,
                'apierror': 'Provide a valid name for the new API key.'}
      except self.connection.IntegrityError:
        return {'keys': keys,
                'apierror': 'That name was already used for another key.'}
      return {'keys': keys,
              'apisucces': 'Your new API key is: "%s".' % newkey['key']}
    return {'keys': keys}


  @uweb3.decorators.loggedin
  def RequestIndex(self):
    """Returns the homepage"""
    return self.RequestProducts()

  @uweb3.decorators.loggedin
  @uweb3.decorators.TemplateParser('products.html')
  def RequestProducts(self):
    """Returns the Products page"""
    supplier = None
    conditions = []
    linkarguments = {}
    if 'supplier' in self.get:
      try:
        supplier = model.Supplier.FromPrimary(self.connection,
            self.get.getfirst('supplier', None))
        conditions.append('supplier = %d' % supplier)
        linkarguments['supplier'] = int(supplier)
      except model.User.NotExistError:
        pass

    products_args = {'conditions': conditions,
                     'order': [('ID', True)]}
    query = ''
    if 'query' in self.get and self.get.getfirst('query', False):
      query = self.get.getfirst('query', '')
      linkarguments['query'] = query
      products_method = model.Product.FromEAN
      products_args['ean'] = query
      del(products_args['order'])
    else:
      products_method = model.Product.List

    products = PagedResult(self.pagesize,
                           self.get.getfirst('page', 1),
                           products_method,
                           self.connection,
                           products_args)
    return {
        'supplier': supplier,
        'products': products,
        'linkarguments': urllib.parse.urlencode(linkarguments) or '',
        'query': query,
        'suppliers': list(model.Supplier.List(self.connection))}

  @uweb3.decorators.loggedin
  @uweb3.decorators.TemplateParser('gs1.html')
  def RequestGS1(self):
    """Returns the gs1 page"""
    linkarguments = {}
    query = ''
    if 'query' in self.get and self.get.getfirst('query', False):
      query = self.get.getfirst('query', '')

      linkarguments['query'] = query
      try:
        product = model.Product.FromGS1(self.connection, query)
        return self.req.Redirect('/product/%s' % product['name'], httpcode=301)
      except model.Product.NotExistError:
        products = []
    else:
      products = PagedResult(self.pagesize,
                             self.get.getfirst('page', 1),
                             model.Product.List,
                             self.connection,
                             {'conditions': ['(gs1 is not null)'],
                                             'order': [('gs1', False)]})
    return {
        'products': products,
        'linkarguments': urllib.parse.urlencode(linkarguments) or '',
        'query': query}

  @uweb3.decorators.loggedin
  @uweb3.decorators.TemplateParser('ean.html')
  def RequestEAN(self):
    """Returns the EAN page"""
    supplier = None
    conditions = ['(gs1 is not null or ean is not null)']
    linkarguments = {}
    if 'supplier' in self.get:
      try:
        supplier = model.Supplier.FromPrimary(self.connection,
            self.get.getfirst('supplier', None))
        conditions.append('supplier = %d' % supplier)
        linkarguments['supplier'] = int(supplier)
      except model.User.NotExistError:
        pass

    products_args = {'conditions': conditions,
                     'order': [('ean', False)]}
    query = ''
    if 'query' in self.get and self.get.getfirst('query', False):
      query = self.get.getfirst('query', '')
      linkarguments['query'] = query
      products_method = model.Product.EANSearch
      products_args['ean'] = query
    else:
      products_method = model.Product.List

    products = PagedResult(self.pagesize,
                           self.get.getfirst('page', 1),
                           products_method,
                           self.connection,
                           products_args)
    return {
        'supplier': supplier,
        'products': products,
        'linkarguments': urllib.parse.urlencode(linkarguments) or '',
        'query': query,
        'suppliers': list(model.Supplier.List(self.connection))}

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
      stock = list(product.Stock(limit=int(self.pagesize),
                                 order=[('dateCreated', True)],
                                 yield_unlimited_total_first=True))
      stockrows = stock[0]
      stock = stock[1:]

    partsprice = {'partstotal':0,
                  'assembly':0,
                  'partcount':0,
                  'assembledtotal':0}
    for part in list(parts):
      partsprice['partcount'] += part['amount']
      partsprice['assembly'] += part['assemblycosts']
      partsprice['partstotal'] += part.subtotal
      partsprice['assembledtotal'] += part.subtotal + part['assemblycosts']

    return {'products': product.AssemblyOptions(),
            'parts': parts,
            'partsprice': partsprice,
            'product': product,
            'suppliers': model.Supplier.List(self.connection),
            'stock': stock,
            'stockrows': stockrows}

  @uweb3.decorators.ContentType('application/json')
  @apiuser
  def JsonProduct(self, name):
    """Returns the product Json"""
    try:
     product = model.Product.FromName(self.connection, name)
    except model.NotExistError as error:
      return sef.RequestInvalidJsoncommand(error)
    return {'product': product,
            'currentstock': product.currentstock,
            'possiblestock': product.possiblestock['available']}

  @uweb3.decorators.loggedin
  @uweb3.decorators.checkxsrf
  def RequestProductNew(self):
    """Requests the creation of a new product."""
    try:
      product = model.Product.Create(self.connection,
          {'name': self.post.getfirst('name', '').replace(' ', '_'),
           'ean': int(self.post.getfirst('ean')) if 'ean' in self.post else None,
           'gs1': int(self.post.getfirst('gs1')) if 'gs1' in self.post else None,
           'description': self.post.getfirst('description', ''),
           'cost': float(self.post.getfirst('cost', 0)),
           'assemblycosts': float(self.post.getfirst('assemblycosts', 0)),
           'vat': float(self.post.getfirst('vat', 21)),
           'sku': self.post.getfirst('sku', '').replace(' ', '_') if 'ski' in self.post else None,
           'supplier': int(self.post.getfirst('supplier', 1))})
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
      assembly = model.Productpart.Create(self.connection,
          {'product': product,
           'part': part,
           'amount': int(self.post.getfirst('amount', 1)),
           'assemblycosts': float(self.post.getfirst('assemblycosts', part['assemblycosts']))})
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
    updates = {'amount': self.post.getfirst('amount', []),
               'assemblycosts': self.post.getfirst('assemblycosts', [])}

    for mate in product.parts:
      mateid = str(mate['ID'])
      if mateid in deletes:
        mate.Delete()
      else:
        for key in mate:
          if (key in updates and
              mateid in updates[key]):
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
        stock = model.Stock.Create(self.connection,
            {'product': product,
             'amount': int(self.post.getfirst('amount', 1)),
             'reference': self.post.getfirst('reference', ''),
             'lot': self.post.getfirst('lot', '')})
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
      return sef.RequestInvalidJsoncommand(error)
    amount = int(self.post.getfirst('amount', -1))
    currentstock = product.currentstock
    if (amount < 0 and # only assemble when we sell
        abs(amount) > currentstock): # only assemble when we have not enough stock
      try:
        product.Assemble(abs(amount) - currentstock, # only assemble what is missing for this sale
                         'Assembly for %s' % self.post.getfirst('reference') if 'reference' in self.post else None)
      except model.AssemblyError as error:
        return self.RequestInvalidJsoncommand(error)
    # by now we should have enough products in stock, one way or another
    model.Stock.Create(self.connection,
          {'product': product,
           'amount': amount,
           'reference': self.post.getfirst('reference', '')})
    return True

  @uweb3.decorators.loggedin
  @uweb3.decorators.TemplateParser('suppliers.html')
  def RequestSuppliers(self, error=None, success=None):
    """Returns the suppliers page"""
    suppliers = None
    query = ''
    if 'query' in self.get and self.get.getfirst('query', False):
      suppliermethod = model.Supplier.Search
      supplierarguments = {'query':  self.get.getfirst('query', ''),
                           'order': [('ID', True)]}
    else:
      suppliermethod = model.Supplier.List
      supplierarguments = {'order': [('ID', True)]}

    suppliers = PagedResult(self.pagesize,
                           self.get.getfirst('page', 1),
                           suppliermethod,
                           self.connection,
                           supplierarguments)
    return {
        'suppliers': suppliers,
        'query': query,
        'error': error,
        'success': success}

  @uweb3.decorators.loggedin
  @NotExistsErrorCatcher
  @uweb3.decorators.checkxsrf
  def RequestSupplierSave(self, name):
    """Returns the supplier page"""
    supplier = model.Supplier.FromName(self.connection, name)
    for key in ('name', 'website', 'telephone', 'contact_person',
                'email_address', 'gscode'):
      supplier[key] = self.post.getfirst(key, None)
    supplier.Save()
    return self.RequestSuppliers(success='Changes saved.')

  @uweb3.decorators.loggedin
  @NotExistsErrorCatcher
  @uweb3.decorators.TemplateParser('supplier.html')
  def RequestSupplier(self, name):
    """Returns the supplier page"""
    return {'supplier': model.Supplier.FromName(self.connection, name)}

  @uweb3.decorators.loggedin
  @uweb3.decorators.checkxsrf
  def RequestSupplierNew(self):
    """Requests the creation of a new supplier."""
    try:
      supplier = model.Supplier.Create(self.connection,
          {'name': self.post.getfirst('name', '').replace(' ', '_'),
           'website': self.post.getfirst('website') if 'website' in self.post else None,
           'telephone': self.post.getfirst('telephone') if 'telephone' in self.post else None,
           'contact_person': self.post.getfirst('contact_person') if 'contact_person' in self.post else None,
           'email_address': self.post.getfirst('email_address') if 'email_address' in self.post else None,
           'gscode': self.post.getfirst('gscode') if 'gscode' in self.post else None})
    except ValueError:
      return self.RequestInvalidcommand(
                          error='Input error, some fields are wrong.')
    except model.InvalidNameError:
      return self.RequestInvalidcommand(
                          error='Please enter a valid name for the supplier.')
    except self.connection.IntegrityError:
      return self.Error('That name was already taken, go back, try again!', 200)
    return self.req.Redirect('/supplier/%s' % supplier['name'], httpcode=301)

  @uweb3.decorators.loggedin
  @NotExistsErrorCatcher
  @uweb3.decorators.checkxsrf
  def RequestSupplierRemove(self, supplier):
    """Removes the supplier"""
    supplier = model.Supplier.FromName(self.connection, supplier)
    supplier.Delete()
    return self.req.Redirect('/suppliers', httpcode=301)

  def XSRFInvalidToken(self):
    """Show that the users XSRF token is b0rked"""
    return self.Error("Your session has expired.", 403)

  def RequestInvalidcommand(self, command=None, error=None, httpcode=404):
    """Returns an error message"""
    uweb3.logging.warning('Bad page %r requested with method %s', command, self.req.method)
    if command is None and error is None:
      command = '%s for method %s' % (self.req.path, self.req.method)
    page_data = self.parser.Parse('404.html', command=command, error=error)
    return uweb3.Response(content=page_data, httpcode=httpcode)

  @uweb3.decorators.ContentType('application/json')
  def RequestInvalidJsoncommand(self, command, httpcode=404):
    """Returns an error message"""
    uweb3.logging.warning('Bad json page %r requested', command)
    return uweb3.Response(content={'error': command}, httpcode=httpcode)

  def Error(self, error='', httpcode=500, link=None):
    """Returns a generic error page based on the given parameters."""
    uweb3.logging.error('Error page triggered: %r', error)
    page_data = self.parser.Parse('error.html', error=error, link=link)
    return uweb3.Response(content=page_data, httpcode=httpcode)
