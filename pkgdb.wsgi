__requires__ = 'fedora_packagedb'

import sys
sys.stdout = sys.stderr
sys.path.append('/usr/share/fedora-packagedb')

import pkg_resources
pkg_resources.require("CherryPy<3.0")

import os
os.environ['PYTHON_EGG_CACHE'] = '/var/www/.python-eggs'

import atexit
import cherrypy
import cherrypy._cpwsgi
import turbogears

turbogears.update_config(configfile="/etc/pkgdb.cfg", modulename="pkgdb.config")
turbogears.config.update({'global': {'server.environment': 'production'}})
turbogears.config.update({'global': {'autoreload.on': False}})
turbogears.config.update({'global': {'server.log_to_screen': False}})
#turbogears.config.update({'global': {'server.webpath': None}})

#from pkgdb import jobs
#turbogears.startup.call_on_startup.append(jobs.schedule)

import pkgdb.controllers
cherrypy.root = pkgdb.controllers.Root()

if cherrypy.server.state == 0:
    atexit.register(cherrypy.server.stop)
    cherrypy.server.start(init_only=True, server_class=None)

application = cherrypy._cpwsgi.wsgiApp
