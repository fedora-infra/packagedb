import sqlalchemy
from sqlalchemy.ext.selectresults import SelectResults
import sqlalchemy.mods.selectresults
from turbogears import controllers, expose, paginate, config
from turbogears import identity, redirect
from turbogears.database import session
from cherrypy import request, response
import logging

from pkgdb import model
from pkgdb import json

from pkgdb.acls import Acls
from pkgdb.collections import Collections
from pkgdb.packages import Packages
from pkgdb.users import Users

log = logging.getLogger("pkgdb.controllers")

# The Fedora Account System Module
from fedora.accounts.fas import AccountSystem, AuthError

ORPHAN_ID=9900
CVSEXTRAS_ID=100300

class Test(controllers.Controller):
    def __init__(self, fas=None, appTitle=None):
        self.fas = fas
        self.appTitle = appTitle

    @expose(template="pkgdb.templates.welcome", allow_json=True)
    @identity.require(identity.in_group("cvsextras"))
    def index(self):
        import time
        # log.debug("Happy TurboGears Controller Responding For Duty")
        return dict(now=time.ctime())

    @expose(template="pkgdb.templates.try")
    def test(self):
        return dict(title='Test Page', rows=({'1': 'alligator', '2':'bat'},{'1':'avocado', '2':'bannana'}))

    @expose(template='pkgdb.templates.orphans')
    def orphans(self):
        import os
        t = file('/var/tmp/t', 'w')
        t.writelines('%s' % request.headers)
        t.close()
        pkgs = {}
        orphanedPackages = SelectResults(session.query(model.PackageListing)).select(
                model.PackageListing.c.owner==ORPHAN_ID)
        for pkg in orphanedPackages:
            pkgs[pkg.package.name] = pkg.package.summary

        return dict(title='List Orphans', pkgs=pkgs)

class Root(controllers.RootController):
    appTitle = 'Fedora Package Database'
    fas = AccountSystem()

    test = Test(fas, appTitle)
    acls = Acls(fas, appTitle)
    collections = Collections(fas, appTitle)
    packages = Packages(fas, appTitle)
    users = Users(fas, appTitle)

    @expose(template='pkgdb.templates.overview')
    def index(self):
        return dict(title=self.appTitle)

    @expose(template="pkgdb.templates.login", allow_json=True)
    def login(self, forward_url=None, previous_url=None, *args, **kw):
        if not identity.current.anonymous \
            and identity.was_login_attempted() \
            and not identity.get_identity_errors():
                # Good to go
                if 'tg_format' in request.params and request.params['tg_format'] == 'json':
                    # When called as a json method, doesn't make any sense to
                    # redirect to a page.  Returning the logged in identity
                    # is better.
                    return dict(user = identity.current.user)
                if not forward_url:
                    forward_url=config.get('base_url_filter.base_url') + '/'
                raise redirect(forward_url)
        
        forward_url=None
        previous_url=request.path

        if identity.was_login_attempted():
            msg=_("The credentials you supplied were not correct or "
                   "did not grant access to this resource.")
        elif identity.get_identity_errors():
            msg=_("You must provide your credentials before accessing "
                   "this resource.")
        else:
            msg=_("Please log in.")
            forward_url= request.headers.get("Referer", "/")

        ### FIXME: Is it okay to get rid of this?
        #response.status=403
        return dict(message=msg, previous_url=previous_url, logging_in=True,
                    original_parameters=request.params,
                    forward_url=forward_url, title='Fedora Account System Login')

    @expose()
    def logout(self):
        identity.current.logout()
        raise redirect(request.headers.get("Referer","/"))

