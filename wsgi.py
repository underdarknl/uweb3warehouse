import os
import site

from warehouse import main

site.addsitedir(os.path.dirname(__file__))
application = main()
