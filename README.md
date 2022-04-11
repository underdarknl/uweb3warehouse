# µWeb3 Warehouse

# How to run

* Run `serve.py` from the commandline
* Run `gunicorn.sh.py` from the commandline for running on Gunicorn
* Use the included `base.wsgi` script to set up Apache + mod_wsgi

The base/config.ini holds the database passwords and login
A secret key will be generated on first boot and writen to the config.ini file
by the server, it needs to be writeable.

# Setup the database

Import schema/schema.sql

# how to create a login

Navigate to /setup and you will be presented a form to setup the config and
first admin account.
