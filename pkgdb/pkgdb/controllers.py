import logging

import cherrypy

import turbogears
from turbogears import controllers, expose, validate, redirect

from pkgdb import json

log = logging.getLogger('pkgdb.controllers')

class Test(controllers.RootController):
    @expose(template='pkgdb.templates.welcome')
    def index(self):
        import time
        log.debug('Happy TurboGears Controller Responding For Duty')
        return dict(now=time.ctime())

class Root(controllers.RootController):
    @expose(template='pkgdb.templates.pkgoverview')
    def index(self):
        return dict(title='Fedora Package Database')
    
    @expose(template='pkgdb.templates.pkgpage')
    def pkgpage(self):
        return dict(title='Fedora Package Database')
    test = Test()
