#!/usr/bin/python
"""Request handlers for the uWeb3 warehouse inventory software"""

# standard modules

# uweb modules
from base.decorators import NotExistsErrorCatcher
import uweb3
from base.model import model


class PageMaker:
  """Holds all the request handlers for the application"""

  @uweb3.decorators.loggedin
  @uweb3.decorators.checkxsrf
  @uweb3.decorators.TemplateParser('clients/clients.html')
  def RequestClients(self):
    return {
        'title': 'Clients',
        'page_id': 'clients',
        'clients': list(model.Client.List(self.connection)),
    }

  @uweb3.decorators.loggedin
  @uweb3.decorators.checkxsrf
  def RequestNewClient(self):
    """Creates a new client, or displays an error."""
    model.Client.Create(
        self.connection, {
            'name': self.post.getfirst('name'),
            'telephone': self.post.getfirst('telephone', ''),
            'email': self.post.getfirst('email', ''),
            'address': self.post.getfirst('address', ''),
            'postalCode': self.post.getfirst('postalCode', ''),
            'city': self.post.getfirst('city', ''),
        })
    return self.req.Redirect('/clients', httpcode=303)

  @uweb3.decorators.loggedin
  @uweb3.decorators.checkxsrf
  # @basNotExistsErrorCatcher
  @uweb3.decorators.TemplateParser('clients/client.html')
  def RequestClient(self, client=None):
    """Returns the client details.

    Takes:
      client: int
    """
    client = model.Client.FromClientNumber(self.connection, int(client))
    return {'title': 'Client', 'page_id': 'client', 'client': client}

  @uweb3.decorators.loggedin
  @uweb3.decorators.checkxsrf
  @NotExistsErrorCatcher
  def RequestSaveClient(self):
    """Returns the client details.

    Takes:
      client: int
    """
    client = model.Client.FromClientNumber(self.connection,
                                           int(self.post.getfirst('client')))
    client['name'] = self.post.getfirst('name')
    client['telephone'] = self.post.getfirst('telephone', '')
    client['email'] = self.post.getfirst('email', '')
    client['address'] = self.post.getfirst('address', '')
    client['postalCode'] = self.post.getfirst('postalCode', '')
    client['city'] = self.post.getfirst('city', '')
    client.Save()
    return self.req.Redirect(f'/client/{client["clientNumber"]}')
